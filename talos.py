#!/usr/bin/env python3

import requests
import sys
import os


API_BASE_URL = "https://api.modrinth.com/v2"


class TalosError(Exception):
    pass


class BadRequestError(TalosError):
    pass


class DownloadFailedError(TalosError):
    pass


class MissingModError(TalosError):
    pass


def _url_from(id: int, api_base_url: str = API_BASE_URL) -> str:
    res = requests.get(f"{api_base_url}/version/{id}")
    if not res.ok:
        raise BadRequestError

    return res.json()["files"][0]["url"]


def _deps_of(id: int, api_base_url: str = API_BASE_URL) -> set:
    urls = []

    res = requests.get(f"{api_base_url}/version/{id}")
    if not res.ok:
        raise BadRequestError

    deps = res.json()["dependencies"]

    # Recursively add dependencies
    for dep in deps:
        urls.append(_url_from(dep["version_id"], api_base_url))
        urls.append(_deps_of(dep["version_id"], api_base_url))

    return set(urls)


def _search_mod(mod_name: str) -> int:
    request = {
        "query": mod_name,
    }

    res = requests.get(f"{API_BASE_URL}/search", params=request)
    if not res.ok:
        raise BadRequestError

    return res.json()["hits"][0]["project_id"]


def _latest_mod_version(mod_name: str, game_version: str, loader_type: str, api_base_url: str = API_BASE_URL) -> int:
    mod_id = _search_mod(mod_name)
    res = requests.get(f"{api_base_url}/project/{mod_id}/version")
    if not res.ok:
        raise BadRequestError

    versions = res.json()

    # Versions are sorted from latest to oldest.
    for version in versions:
        if game_version in version["game_versions"] and loader_type in version["loaders"]:
            return version["id"]

    raise MissingModError


def get_mods(mods: list, game_version: str, loader_type: str, silent: bool = True, api_base_url: str = API_BASE_URL) -> set:
    urls = []
    for mod in mods:
        name = mod.strip()
        id = 0
        try:
            if not silent:
                print(f"Searching for {name}...")
            id = _latest_mod_version(name, game_version, loader_type)
            urls.append(_url_from(id))
        except MissingModError:
            if not silent:
                print(f"Could not find {name}")
            continue

        if not silent:
            print(f"Found {name} with id: {id}")
            print(f"Searching for {name}'s dependencies...")

        deps = _deps_of(id)
        urls.extend(deps)

        if not silent:
            print(f"\tFound {len(deps)} dependencies")
            print()

    return set(urls)


def download_mods(urls: list, output_dir: str, silent: bool = True):
    for url in urls:
        file_name = f"{output_dir}/{os.path.basename(url)}"

        res = requests.get(url)
        if not res.ok:
            raise DownloadFailedError

        if not silent:
            print(f"Downloading {url} as {file_name}")

        with open(file_name, "wb") as f:
            f.write(res.content)


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} modlist output_directory")
        exit(0)

    mods = []
    with open(sys.argv[1], "r") as f:
        mods = f.readlines()

    download_mods(get_mods(mods, "1.16.5", "fabric", False),
                  sys.argv[2], False)
    print("Done")


if __name__ == "__main__":
    main()
