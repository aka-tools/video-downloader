# Copyright (c) 2026 AKA. All rights reserved.
# Part of Video Downloader - see LICENSE.txt. Unauthorised copying or modification is prohibited.
"""
Built-in sign-in and automatic video finding for Canvas / Panopto.

Security design
---------------
* Uses the Microsoft Edge already installed on Windows, but with the app's OWN
  isolated profile: it never touches your normal browser, its passwords or history.
* Only cookies for the configured Canvas site and Panopto are kept; everything else
  is discarded.
* The saved login is encrypted with Windows DPAPI (see secure_store.py) and is
  never written to disk in plain text. Cookies for downloads are passed in memory.
* Automation only ever runs against the configured Canvas host or Panopto.
"""
import json
import os
import re
import shutil
import time

from playwright.sync_api import sync_playwright

import secure_store

DATA_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "VideoDownloader")
PROFILE_DIR = os.path.join(DATA_DIR, "browser-profile")
SESSION_FILE = os.path.join(DATA_DIR, "login.dat")              # DPAPI-encrypted
LEGACY_PLAINTEXT = os.path.join(DATA_DIR, "saved-login.json")  # from older versions - removed on sight

PANOPTO_RE = re.compile(r"https://([a-z0-9.-]*panopto\.(?:com|eu))/Panopto/Pages/"
                        r"(?:Embed|Viewer)\.aspx\?[^\"'\s<>]*?id=([0-9a-fA-F-]{36})")
PANOPTO_DOMAIN_RE = re.compile(r"(^|\.)panopto\.(com|eu)$")
HOST_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")
BROWSER_CHANNELS = ("msedge", "chrome")
NAV_TIMEOUT = 45000  # ms


class NeedLogin(Exception):
    pass


# ---------- helpers ----------
def _purge_legacy():
    if os.path.exists(LEGACY_PLAINTEXT):
        try:
            os.remove(LEGACY_PLAINTEXT)
        except OSError:
            pass


def valid_host(host):
    return bool(HOST_RE.match(host or ""))


def host_of(url):
    m = re.match(r"https://([^/:?#]+)", url or "", re.I)
    return (m.group(1) if m else "").lower()


def is_panopto_host(host):
    return bool(PANOPTO_DOMAIN_RE.search(host))


def _cookie_in_scope(domain, canvas_host):
    d = domain.lstrip(".").lower()
    return d == canvas_host or canvas_host.endswith("." + d) or d.endswith("." + canvas_host) \
        or is_panopto_host(d)


def _scoped(cookies, canvas_host):
    return [c for c in cookies if _cookie_in_scope(c.get("domain", ""), canvas_host)]


def is_signed_in():
    _purge_legacy()
    return os.path.exists(SESSION_FILE)


def sign_out():
    """Forget the saved login and delete the app's private browser profile."""
    _purge_legacy()
    for p in (SESSION_FILE,):
        if os.path.exists(p):
            os.remove(p)
    shutil.rmtree(PROFILE_DIR, ignore_errors=True)


def _save_login(ctx, canvas_host):
    """Browsers drop 'session' cookies on close, so keep our own ENCRYPTED copy."""
    _purge_legacy()
    if not secure_store.available():
        return  # never fall back to plain text
    try:
        data = json.dumps(_scoped(ctx.cookies(), canvas_host)).encode("utf-8")
        os.makedirs(DATA_DIR, exist_ok=True)
        tmp = SESSION_FILE + ".tmp"
        with open(tmp, "wb") as f:
            f.write(secure_store.protect(data))
        os.replace(tmp, SESSION_FILE)
    except Exception:  # noqa: BLE001
        pass


def _load_login():
    if not os.path.exists(SESSION_FILE) or not secure_store.available():
        return []
    try:
        with open(SESSION_FILE, "rb") as f:
            return json.loads(secure_store.unprotect(f.read()).decode("utf-8"))
    except Exception:  # noqa: BLE001  (corrupt / other user / other PC) -> forget it
        try:
            os.remove(SESSION_FILE)
        except OSError:
            pass
        return []


def _restore_login(ctx):
    now = time.time()
    good = []
    for c in _load_login():
        exp = c.get("expires", -1)
        if exp not in (-1, None) and 0 < exp < now:
            continue
        c = {k: v for k, v in c.items()
             if k in ("name", "value", "domain", "path", "expires", "httpOnly", "secure", "sameSite")}
        if c.get("expires", -1) in (-1, None):
            c.pop("expires", None)
        good.append(c)
    if good:
        try:
            ctx.add_cookies(good)
        except Exception:  # noqa: BLE001
            pass


def _launch(pw, visible):
    """visible=False -> a normal window parked off-screen (sites treat it like a real browser)."""
    os.makedirs(PROFILE_DIR, exist_ok=True)
    args = ["--no-first-run", "--disable-sync", "--no-default-browser-check",
            "--deny-permission-prompts",        # camera, mic, location, notifications: always denied
            "--disable-features=Translate,AutofillServerCommunication",
            "--disable-background-networking"]
    if not visible:
        args += ["--window-position=-32000,-32000", "--window-size=1400,900"]
    last = None
    for ch in BROWSER_CHANNELS:
        try:
            ctx = pw.chromium.launch_persistent_context(
                PROFILE_DIR, channel=ch, headless=False, args=args, viewport=None,
                accept_downloads=False,      # the hidden browser can never save files
                ignore_https_errors=False,   # refuse sites with invalid certificates
                permissions=[],              # grant nothing
                service_workers="block")
            _restore_login(ctx)
            return ctx
        except Exception as e:  # noqa: BLE001
            last = e
    raise RuntimeError(f"Could not start Microsoft Edge or Chrome: {last}")


def _is_login_url(u):
    u = u.lower()
    return "/login" in u or "microsoftonline" in u or "accounts.google" in u or "/saml" in u


# ---------- public API ----------
def sign_in(canvas_host, log):
    """Open a visible window; it closes itself once you are signed in."""
    if not valid_host(canvas_host):
        raise ValueError(f"Invalid Canvas address: {canvas_host!r}")
    with sync_playwright() as pw:
        ctx = _launch(pw, visible=True)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(f"https://{canvas_host}/courses", wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
            page.wait_for_timeout(2500)
            if _is_login_url(page.url) or canvas_host not in page.url:
                log("Sign in to Canvas in the window that opened. It closes by itself when you're in.")
                page.wait_for_url(lambda u: canvas_host in u and not _is_login_url(u), timeout=10 * 60 * 1000)
                page.wait_for_timeout(3000)
            _save_login(ctx, canvas_host)
            log("✔ Signed in. Your login is saved (encrypted) for next time.")
        finally:
            ctx.close()


def _scan(page, found):
    texts = [page.url] + [f.url for f in page.frames]
    try:
        texts.append(page.content())
    except Exception:  # noqa: BLE001
        pass
    for t in texts:
        for host, vid in PANOPTO_RE.findall(t):
            found.setdefault(vid.lower(), host.lower())


def _wait_and_scan(page, found, seconds):
    end = time.time() + seconds
    while time.time() < end:
        _scan(page, found)
        if found:
            return
        page.wait_for_timeout(1000)


def resolve(url, canvas_host, log):
    """
    Find the Panopto video(s) behind a Canvas page (or a Panopto link).
    Returns (viewer_urls, cookies) - cookies are scoped to Canvas/Panopto and kept in memory.
    """
    host = host_of(url)
    if host != canvas_host and not is_panopto_host(host):
        raise ValueError("Automatic sign-in only works for your Canvas site and Panopto links.")
    found = {}
    with sync_playwright() as pw:
        ctx = _launch(pw, visible=False)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            log("   Opening the page…")
            page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
            page.wait_for_timeout(2000)
            if _is_login_url(page.url) and not is_panopto_host(host_of(page.url)):
                raise NeedLogin()

            if is_panopto_host(host):
                _scan(page, found)
            else:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                log("   Looking for the video on the page…")
                _wait_and_scan(page, found, 15)
                if not found:
                    srcs = page.eval_on_selector_all("iframe", "els => els.map(e => e.src)")
                    for src in [s for s in srcs if "external_tools" in s and host_of(s) == canvas_host]:
                        log("   Opening the embedded video player…")
                        page.goto(src, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
                        _wait_and_scan(page, found, 15)
            if found:
                page.wait_for_timeout(3000)  # let Panopto finish its sign-in hand-off
            cookies = _scoped(ctx.cookies(), canvas_host)
            _save_login(ctx, canvas_host)
        finally:
            ctx.close()

    if not found:
        log("   No Panopto video found on the page - trying the link directly.")
        return [url], cookies
    log(f"   ✔ Found {len(found)} Panopto video(s).")
    return [f"https://{h}/Panopto/Pages/Viewer.aspx?id={v}" for v, h in found.items()], cookies


def add_cookies_to_jar(jar, cookies):
    """Put Playwright cookies straight into yt-dlp's cookie jar (no temp files)."""
    from http.cookiejar import Cookie
    for c in cookies:
        dom = c["domain"]
        exp = c.get("expires", -1)
        jar.set_cookie(Cookie(
            version=0, name=c["name"], value=c["value"], port=None, port_specified=False,
            domain=dom, domain_specified=True, domain_initial_dot=dom.startswith("."),
            path=c.get("path", "/"), path_specified=True, secure=bool(c.get("secure")),
            expires=int(exp) if exp and exp > 0 else None, discard=not (exp and exp > 0),
            comment=None, comment_url=None, rest={}))
