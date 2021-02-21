#!/usr/bin/env python3
import json
import requests
import argparse
import pathlib
import hashlib
import plistlib
import tarfile
import subprocess
import re
from typing import Dict

REPO = "cinderella-project/iMast"
APP_FILE_NAME = "iMast.app"
REGEX_EXTRACT_EDSIG = re.compile("sparkle:edSignature=\"(.+?)\"")

def find_expected_asset(assets: Dict, expected_file: pathlib.Path):
    expected_length = expected_file.stat().st_size
    expected_etag = '"{}"'.format(hashlib.md5(expected_file.read_bytes()).hexdigest())
    for asset in assets:
        if asset["size"] != expected_length:
            continue
        etag_res = requests.head(asset["browser_download_url"], allow_redirects=True)
        etag_res.raise_for_status()
        etag = etag_res.headers["etag"]
        if expected_etag != etag:
            print("{name}: Invalid Etag (local: {local}, remote: {remote}".format(
                name = asset["name"],
                local = expected_etag,
                remote = etag,
            ))
            continue
        return asset
    print("Failed to find expected asset from GitHub Releases")
    exit(1)

def read_info_plist(path: pathlib.Path):
    with tarfile.open(path, "r:gz") as tar:
        with tar.extractfile(APP_FILE_NAME+"/Contents/Info.plist") as f:
            return plistlib.load(f)

def sign(path: pathlib.Path):
    result = subprocess.run([
        "../iMast/thirdparty/SparkleBinaries/bin/sign_update",
        path,
    ], stdout=subprocess.PIPE)
    stdout = result.stdout.decode("UTF-8")
    match = REGEX_EXTRACT_EDSIG.match(stdout)
    if match is None:
        print("Failed to sign")
        print(stdout)
        exit(1)
    return match[1]

parser = argparse.ArgumentParser()
parser.add_argument("path", type=pathlib.Path, help="Path of Uploaded File (for signature)")
args = parser.parse_args()

info_plist = read_info_plist(args.path)
tag = "{}b{}".format(info_plist["CFBundleShortVersionString"], info_plist["CFBundleVersion"])

current_builds = json.load(open("builds.json", "r"))

# Get Release Info from GitHub API
release_info_res = requests.get("https://api.github.com/repos/{repo}/releases/tags/{tag}".format(
    repo=REPO,
    tag=tag,
))
release_info_res.raise_for_status()
release_info = release_info_res.json()

sparkle_asset = find_expected_asset(release_info["assets"], args.path)

version = info_plist["CFBundleShortVersionString"]
build_number = int(info_plist["CFBundleVersion"])

new_build = {
    "version": version,
    "build_number": build_number,
    "created_at": release_info["published_at"],
    "os_required": info_plist["LSMinimumSystemVersion"],
    "patchnote": "https://cinderella-project.github.io/iMast-AppCast/patchnotes/{}/{}.html".format(version, build_number),
    "binary": {
        "url": sparkle_asset["browser_download_url"],
        "length": sparkle_asset["size"],
        "ed_sig": sign(args.path),
    }
}

current_builds.insert(0, new_build)

json.dump(current_builds, open("builds.json", "w"), ensure_ascii=False, indent="\t")