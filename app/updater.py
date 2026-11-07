# Copyright (c) 2026 AKA. All rights reserved.
# Part of Video Downloader - see LICENSE.txt. Unauthorised copying or modification is prohibited.
"""
Safe update check.

What it does
  * Asks GitHub (HTTPS, certificate verified) for the latest published release of the
    official repository and compares its version with this app's version.
  * If newer, the app shows a notice with a button that opens the official release page.

What it never does
  * Never downloads or runs anything by itself - the user downloads the new ZIP, and
    the official installer is published with its SHA-256 checksum and build attestation.
  * Sends no personal data: a plain request with a generic User-Agent, no cookies.
  * Only ever opens https://github.com/<official repo>/releases/... links.
"""
import json
import re
import ssl
import time
import urllib.request

# Filled in automatically by the official GitHub build (.github/workflows/release.yml)
# with this repository's "owner/name". Left empty (local builds), the update check is off.
UPDATE_REPO = ""

CHECK_EVERY_SECONDS = 24 * 3600
_VER = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")
_REPO = re.compile(r"^[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}$")


def parse_version(v):
    m = _VER.match((v or "").strip())
    return tuple(int(x) for x in m.groups()) if m else None


def is_configured():
    return bool(_REPO.match(UPDATE_REPO))


def check(current_version, timeout=6):
    """
    Returns (latest_version_str, release_page_url) if a newer release exists, else None.
    Raises on network errors (the caller decides whether to show them).
    """
    if not is_configured():
        return None
    api = f"https://api.github.com/repos/{UPDATE_REPO}/releases/latest"
    req = urllib.request.Request(api, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "VideoDownloader-update-check",
    })
    ctx = ssl.create_default_context()  # verifies certificates and hostname
    # fixed https:// URL to the official repo only
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:  # nosec B310
        if r.status != 200:
            return None
        data = json.loads(r.read(200_000).decode("utf-8"))

    if data.get("draft") or data.get("prerelease"):
        return None
    latest = parse_version(data.get("tag_name", ""))
    mine = parse_version(current_version)
    if not latest or not mine or latest <= mine:
        return None

    page = data.get("html_url", "")
    official_prefix = f"https://github.com/{UPDATE_REPO}/releases/"
    if not page.startswith(official_prefix):  # never open anything outside the official repo
        page = f"https://github.com/{UPDATE_REPO}/releases/latest"
    return ".".join(map(str, latest)), page


def due(last_check_ts):
    try:
        return time.time() - float(last_check_ts or 0) >= CHECK_EVERY_SECONDS
    except (TypeError, ValueError):
        return True
