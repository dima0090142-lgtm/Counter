"""Updates from GitHub Releases: one PTW_Generator.exe, nothing else to install.

The GitHub Actions workflow (.github/workflows/release.yml) builds the exe for every
new version and publishes it as a release "v<version>". The program asks the GitHub
API for the latest release, downloads the .exe, puts it in place of itself and starts
the new one. Data folders next to the exe are not touched.
"""
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

from . import __version__

DEFAULT_REPO = "dima0090142-lgtm/Counter"
TIMEOUT = 15


class UpdateError(Exception):
    pass


def version_tuple(text):
    return tuple(int(x) for x in re.findall(r"\d+", text or "")[:4]) or (0,)


def _get(url, accept="application/vnd.github+json"):
    req = urllib.request.Request(url, headers={"Accept": accept,
                                               "User-Agent": f"PTW-Generator/{__version__}"})
    return urllib.request.urlopen(req, timeout=TIMEOUT)  # noqa: S310 - https GitHub API only


def latest_release(repo=DEFAULT_REPO):
    """{'version', 'tag', 'url' (exe download), 'page', 'notes'} of the newest release."""
    try:
        with _get(f"https://api.github.com/repos/{repo}/releases/latest") as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise UpdateError("no release found (the repository must be public and have a "
                              "release with PTW_Generator.exe)") from None
        raise UpdateError(f"GitHub: HTTP {e.code}") from None
    except (urllib.error.URLError, OSError) as e:
        raise UpdateError(f"no connection to GitHub: {getattr(e, 'reason', e)}") from None
    exe = next((a for a in data.get("assets", []) if a.get("name", "").lower().endswith(".exe")),
               None)
    return {"version": data.get("tag_name", "").lstrip("vV"), "tag": data.get("tag_name", ""),
            "url": exe["browser_download_url"] if exe else "", "size": exe["size"] if exe else 0,
            "page": data.get("html_url", ""), "notes": data.get("body") or ""}


def is_newer(release):
    return version_tuple(release["version"]) > version_tuple(__version__)


def can_self_update():
    return getattr(sys, "frozen", False) and sys.platform.startswith("win")


def download(release, progress=None, cancelled=None):
    """Download the new exe next to the running one; returns its path."""
    if not release.get("url"):
        raise UpdateError("the release has no .exe file")
    target = os.path.join(os.path.dirname(sys.executable), "PTW_Generator.new.exe")
    try:
        with _get(release["url"], accept="application/octet-stream") as r, open(target, "wb") as f:
            total = int(r.headers.get("Content-Length") or release.get("size") or 0)
            done = 0
            while True:
                if cancelled and cancelled():
                    raise UpdateError("cancelled")
                chunk = r.read(256 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if progress:
                    progress(done // 1024, max(total // 1024, done // 1024), "PTW_Generator.exe")
    except (urllib.error.URLError, OSError) as e:
        if os.path.exists(target):
            os.remove(target)
        raise UpdateError(f"download failed: {e}") from None
    except UpdateError:
        if os.path.exists(target):
            os.remove(target)
        raise
    return target


def install_and_restart(new_exe):
    """Windows lets a running exe be renamed: old -> .old, new -> the exe name, start it."""
    exe = sys.executable
    old = exe + ".old"
    if os.path.exists(old):
        os.remove(old)
    os.replace(exe, old)
    os.replace(new_exe, exe)
    subprocess.Popen([exe], cwd=os.path.dirname(exe), close_fds=True)


def cleanup_old():
    """Remove the previous exe left by an update (it was still running at that time)."""
    if getattr(sys, "frozen", False):
        old = sys.executable + ".old"
        try:
            if os.path.exists(old):
                os.remove(old)
        except OSError:
            pass
