#!/usr/bin/env python
import argparse
import concurrent.futures
import itertools
import json
import os
import re
import sys
from json import JSONDecodeError
import shutil
import subprocess
from collections import defaultdict
from os.path import join
from typing import Dict, List, Optional, Tuple

here = os.path.dirname(__file__)
build_dir = join(here, "build")
snippet_dir = join(here, "snippets")


def main():
    """ Build the snippets from their source repos """
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


def build_source(config: str, rev: Optional[str] = None) -> Tuple[str, List[Dict]]:
    dirname = url_basename(config["url"])
    dirpath = join(build_dir, dirname)
    try:
        if os.path.isdir(dirpath):
            if rev is None:
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

    with open(join(dirpath, "package.json"), "r") as package:
        package_data = json.load(package)
    snippets = package_data.get("contributes", {}).get("snippets", [])
    if not snippets:
        raise Exception(f"Source {dirname} is missing snippets in package.json")

    dest_dir = join(snippet_dir, dirname)
    os.makedirs(dest_dir, exist_ok=True)
    for license in get_licenses(dirpath, config):
        license_path = join(dirpath, license)
        if not os.path.isfile(license_path):
            raise Exception(f"Source {dirname} missing license {license}")
        shutil.copyfile(license_path, join(dest_dir, license))

    language_remap = config.get("remap_language", {})
    our_snippets = []
    for data in snippets:
        language = language_remap.get(data["language"], data["language"])
        path = join(dirpath, data["path"])
        basename = os.path.basename(data["path"])
        destpath = join(dest_dir, basename)
        # We deserialize & reserialize because some of these packages are very
        # optimistic about the JSON standard (trailing commas, duplicate keys, comments,
        # etc)
        with open(path, "r") as ifile:
            try:
                data = json.load(ifile)
                with open(destpath, "w") as ofile:
                    json.dump(data, ofile, indent=2)
            except JSONDecodeError as e:
                sys.stderr.write(f"File {destpath} is malformed json\n\t{e}\n")
        our_snippets.append(
            {"language": language, "path": str(os.path.relpath(destpath, here))}
        )

    return rev, our_snippets


def get_licenses(dirpath: str, config: dict) -> List[str]:
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


if __name__ == "__main__":
    main()
