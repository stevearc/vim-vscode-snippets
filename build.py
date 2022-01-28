#!/usr/bin/env python
import argparse
import concurrent.futures
import glob
import json
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
build_dir = join(here, "build")
snippet_dir = join(here, "snippets")


class BaseConfig(TypedDict):
    url: str


class Config(BaseConfig, total=False):
    license: Union[str, Tuple[str]]
    remap_language: Dict[str, str]
    hook: str
    root: str


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
    args = parser.parse_args()

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

    package_data = {"contributes": {"snippets": all_snippets}}
    with open(join(here, "package.json"), "w") as package_file:
        json.dump(package_data, package_file, indent=2)

    with open(lockfile_path, "w") as ofile:
        json.dump(lock_data, ofile, indent=2)

    update_readme(packages_by_language)


def build_source(config: Config, rev: Optional[str] = None) -> Tuple[str, List[Dict]]:
    dirname = url_basename(config["url"])
    dirpath = join(build_dir, dirname)
    try:
        if os.path.isdir(dirpath):
            if rev is None:
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
            subprocess.check_call(
                ["git", "clone", config["url"]],
                cwd=build_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except Exception as e:
        raise Exception(f"Error cloning or updating {dirname}")

    if rev is not None:
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
        subprocess.run(hook, cwd=dirpath, shell=True)

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

        os.makedirs(snippet_dest, exist_ok=True)
        for data in snippets:
            language = language_remap.get(data["language"], data["language"])
            path = normpath(join(root, data["path"]))
            basename = os.path.basename(data["path"])
            destpath = abspath(join(snippet_dest, basename))
            # We deserialize & reserialize because some of these packages are very
            # optimistic about the JSON standard (trailing commas, duplicate keys, comments,
            # etc)
            with open(path, "r") as ifile:
                try:
                    data = cast(Dict, json5.load(ifile))
                    data = maybe_unwrap(data)
                    with open(destpath, "w") as ofile:
                        json.dump(data, ofile, indent=2)
                except JSONDecodeError as e:
                    sys.stderr.write(f"File {path} is malformed json\n\t{e}\n")
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
        language_lines.append(f"* {language} - {', '.join(links)}\n")

    all_lines = prefix_lines + language_lines + ["\n"] + postfix_lines
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
