#!/usr/bin/env python
import argparse
import concurrent.futures
import glob
import json
import logging
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from json import JSONDecodeError
from os.path import abspath, join, normpath, relpath
from typing import Dict, List, Optional, Sequence, Tuple, Union, cast

import json5

if sys.version_info < (3, 8):
    from typing_extensions import TypedDict
else:
    from typing import TypedDict

here = os.path.dirname(__file__)
build_dir = join(here, "_build")
snippet_dir = join(here, "snippets")
LOG = logging.getLogger(__name__)


class BaseConfig(TypedDict):
    url: str


class Config(BaseConfig, total=False):
    license: Union[str, Tuple[str]]
    remap_language: Dict[str, str]
    hook: str
    root: str
    min_snippets: int


def main():
    """Build the snippets from their source repos"""
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument(
        "-u",
        "--update",
        help="repo to update, or 'all' to update all source repos",
    )
    parser.add_argument(
        "-p", type=int, help="Number of threads (default %(default)s)", default=5
    )
    parser.add_argument(
        "-l",
        "--log-level",
        type=lambda l: logging.getLevelName(l.upper()),
        default=logging.WARNING,
        help="Stdout logging level (default 'warning')",
    )
    args = parser.parse_args()
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(levelname)s %(asctime)s [%(name)s] %(message)s")
    handler.setFormatter(formatter)
    logging.root.addHandler(handler)
    level = logging.getLevelName(args.log_level)
    logging.root.setLevel(level)

    os.makedirs(build_dir, exist_ok=True)
    shutil.rmtree(snippet_dir)
    os.makedirs(snippet_dir)
    with open(join(here, "sources.json"), "r") as ifile:
        sources = json.load(ifile)
    lockfile_path = join(here, "sources.lock")
    if os.path.isfile(lockfile_path):
        with open(lockfile_path, "r") as ifile:
            lock_data = json.load(ifile)
    else:
        lock_data = {}

    def execute(config):
        should_update = args.update is not None and (
            args.update == "all" or config["url"].endswith(args.update)
        )
        rev = None if should_update else lock_data.get(config["url"])
        return build_source(config, rev)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.p) as executor:
        results = executor.map(execute, sources)

    all_snippets = []
    packages_by_language = defaultdict(set)
    lock_data = {}
    for config, (git_rev, snippets) in zip(sources, results):
        config = cast(Config, config)
        all_snippets.extend(snippets)
        lock_data[config["url"]] = git_rev
        for snip in snippets:
            packages_by_language[snip["language"]].add(config["url"])
    all_snippets.sort(key=lambda x: (x["language"], x["path"]))

    LOG.info("Writing package.json")
    package_data = {"contributes": {"snippets": all_snippets}}
    with open(join(here, "package.json"), "w") as package_file:
        json.dump(package_data, package_file, indent=2)

    LOG.info("Writing sources.lock")
    with open(lockfile_path, "w") as ofile:
        json.dump(lock_data, ofile, indent=2)

    LOG.info("Writing README")
    update_readme(packages_by_language)


def build_source(config: Config, rev: Optional[str] = None) -> Tuple[str, List[Dict]]:
    dirname = url_basename(config["url"])
    LOG.info("Building snippets from %s", dirname)
    dirpath = join(build_dir, dirname)
    try:
        if os.path.isdir(dirpath):
            if rev is None:
                LOG.info("Updating repo %s", dirname)
                remote_main = (
                    subprocess.check_output(
                        ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
                        cwd=dirpath,
                    )
                    .decode("utf-8")
                    .split("/")[-1]
                    .strip()
                )
                subprocess.check_call(
                    ["git", "checkout", remote_main],
                    cwd=dirpath,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                subprocess.check_call(
                    ["git", "pull"],
                    cwd=dirpath,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        else:
            LOG.info("Cloning repo %s", dirname)
            subprocess.check_call(
                ["git", "clone", config["url"]],
                cwd=build_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except Exception as e:
        raise Exception(f"Error cloning or updating {dirname}")

    if rev is not None:
        LOG.info("Checking out %s(%s)", dirname, rev)
        try:
            subprocess.check_call(
                ["git", "checkout", rev],
                cwd=dirpath,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            raise Exception(f"Error checking out repo {dirname} rev {rev}")

    rev = (
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=dirpath)
        .decode("utf-8")
        .strip()
    )

    hook = config.get("hook")
    if hook is not None:
        LOG.info("Running hook in dir(%s): %s", dirpath, hook)
        output = subprocess.check_output(hook, cwd=dirpath, shell=True)
        LOG.debug("Hook output(%s):\n%s", dirpath, output)

    dest_dir = join(snippet_dir, dirname)
    os.makedirs(dest_dir, exist_ok=True)
    for license in get_licenses(dirpath, config):
        license_path = join(dirpath, license)
        if not os.path.isfile(license_path):
            raise Exception(f"Source {dirname} missing license {license}")
        shutil.copyfile(license_path, join(dest_dir, license))

    language_remap = config.get("remap_language", {})

    our_snippets = []
    for root in iter_roots(config, dirpath):
        snippet_dest = normpath(join(dest_dir, relpath(root, dirpath)))
        package_file = join(root, "package.json")
        if not os.path.exists(package_file):
            continue
        with open(package_file, "r") as package:
            package_data = json.load(package)
        snippets = package_data.get("contributes", {}).get("snippets", [])
        if not snippets:
            continue

        for data in snippets:
            language = language_remap.get(data["language"], data["language"])
            path = normpath(join(root, data["path"]))
            basename = os.path.basename(data["path"])
            destpath = abspath(join(snippet_dest, basename))
            if os.path.exists(destpath):
                # Some extensions use the same snippet file for multiple languages.
                # We only need to process them once.
                our_snippets.append(
                    {"language": language, "path": str(relpath(destpath, here))}
                )
                continue

            # We deserialize & reserialize because some of these packages are very
            # optimistic about the JSON standard (trailing commas, duplicate keys, comments,
            # etc)
            with open(path, "r") as ifile:
                try:
                    data = cast(Dict, json5.load(ifile))
                except JSONDecodeError as e:
                    LOG.exception("File %s is malformed json", path)
                    continue

            # vscode has some extensions that helpfully only give you a "Region Start" and "Region End" snippet.
            # This allows us to filter those out
            if "min_snippets" in config and len(data) < config["min_snippets"]:
                LOG.info("Skip %s: only %d snippets", path, len(data))
                continue

            data = maybe_unwrap(data)
            LOG.info("Writing snippet file %s", join(snippet_dest, basename))
            os.makedirs(snippet_dest, exist_ok=True)
            with open(destpath, "w") as ofile:
                json.dump(data, ofile, indent=2)
            our_snippets.append(
                {"language": language, "path": str(relpath(destpath, here))}
            )

    if not our_snippets:
        raise Exception(f"Source {dirname} is missing snippets in package.json")

    return rev, our_snippets


def needs_unwrap(snip_data: Dict) -> bool:
    for snip in snip_data.values():
        if "body" not in snip:
            return True
    return False


def maybe_unwrap(snip_data: Dict) -> Dict:
    if not needs_unwrap(snip_data):
        return snip_data
    ret = {}
    for snippets in snip_data.values():
        ret.update(snippets)
    return ret


def get_licenses(dirpath: str, config: Config) -> Sequence[str]:
    if "license" in config:
        if isinstance(config["license"], str):
            return [config["license"]]
        else:
            return config["license"]
    else:
        licenses = [f for f in os.listdir(dirpath) if re.match(r"LICENSE.*", f)]
        if len(licenses) == 1:
            return licenses
        else:
            return ["LICENSE.md"]


def url_basename(url: str) -> str:
    basename = url
    if "/" in basename:
        basename = basename[basename.rindex("/") + 1 :]
    if basename.endswith(".git"):
        basename = basename[:-4]
    return basename


def update_readme(packages_by_language: dict) -> None:
    # These are not real languages
    packages_by_language.pop("javascriptreact", None)
    packages_by_language.pop("typescriptreact", None)

    readme_file = join(here, "README.md")
    prefix_lines = []
    postfix_lines = []
    readme_lines = prefix_lines
    with open(readme_file, "r") as ifile:
        language_section = False
        for line in ifile:
            if language_section:
                if line.startswith("#"):
                    language_section = False
                    readme_lines = postfix_lines
                    readme_lines.append(line)
            else:
                if line.startswith("## Languages"):
                    language_section = True
                readme_lines.append(line)

    language_lines = []
    for language, repos in sorted(packages_by_language.items()):
        links = [f"[{url_basename(url)}]({url})" for url in sorted(repos)]
        language_lines.append(f"- {language} - {', '.join(links)}\n")

    all_lines = prefix_lines + ["\n"] + language_lines + ["\n"] + postfix_lines
    with open(readme_file, "w") as ofile:
        ofile.write("".join(all_lines))


def iter_roots(config: Config, dirpath: str):
    if "root" in config:
        for path in glob.glob(join(dirpath, config["root"])):
            yield path
        yield dirpath
    else:
        yield dirpath


if __name__ == "__main__":
    main()
