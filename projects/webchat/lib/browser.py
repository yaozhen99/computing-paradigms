"""Browser connection management via Playwright + CDP.

Connects to an already-running Edge/Chrome instance that was launched with
--remote-debugging-port=9333.  Shares the user's login state.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
import urllib.error
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

CDP_PORT = int(os.environ.get("WEBCAT_CDP_PORT", "9333"))
# Try IPv4 first, then IPv6 loopback — proxy/VPN services may occupy 0.0.0.0
# on common ports while Edge falls back to [::1].
CDP_HOSTS = ["127.0.0.1", "::1"]

# Module-level Playwright instance — lazy init, reused across calls.
_pw = None
_browser = None
_page = None
_detected_host: Optional[str] = None


def _detect_cdp_host() -> str:
    """Probe CDP hosts and return the first one that responds."""
    for host in CDP_HOSTS:
        url = f"http://{host}:{CDP_PORT}/json/version"
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if resp.status == 200:
                    return host
        except (urllib.error.URLError, OSError, TimeoutError):
            continue
    return CDP_HOSTS[0]


def _cdp_host() -> str:
    """Return the active CDP host, detecting on first call."""
    global _detected_host
    if _detected_host is None:
        _detected_host = _detect_cdp_host()
        logger.debug("CDP host detected: %s", _detected_host)
    return _detected_host


def _version_url() -> str:
    return f"http://{_cdp_host()}:{CDP_PORT}/json/version"


def _list_url() -> str:
    return f"http://{_cdp_host()}:{CDP_PORT}/json"


def check_port() -> bool:
    """Return True if the CDP debug port is reachable."""
    try:
        with urllib.request.urlopen(_version_url(), timeout=3) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError, TimeoutError):
        return False


def get_version() -> Optional[Dict[str, Any]]:
    """Return browser version info from CDP, or None if unreachable."""
    try:
        with urllib.request.urlopen(_version_url(), timeout=3) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        logger.debug("CDP version fetch failed: %s", exc)
        return None


def get_pages() -> list[Dict[str, Any]]:
    """Return list of open pages/tabs from CDP."""
    try:
        with urllib.request.urlopen(_list_url(), timeout=3) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        logger.debug("CDP page list fetch failed: %s", exc)
        return []


def get_page():
    """Return a Playwright Page connected to the browser via CDP.

    Lazily initializes Playwright and connects.  Reuses the same connection
    across calls within the same process.
    """
    global _pw, _browser, _page

    if _page and not _page.is_closed():
        return _page

    from playwright.sync_api import sync_playwright

    if _pw is None:
        _pw = sync_playwright().start()

    if _browser is None or not _browser.is_connected():
        _browser = _pw.chromium.connect_over_cdp(
            f"http://{_cdp_host()}:{CDP_PORT}"
        )

    # Get the first non-chrome page
    contexts = _browser.contexts
    if not contexts:
        return None

    for ctx in contexts:
        for p in ctx.pages:
            if not p.url.startswith("chrome"):
                _page = p
                return _page

    # Fallback: any page
    for ctx in contexts:
        if ctx.pages:
            _page = ctx.pages[0]
            return _page

    return None


def reset_connection():
    """Reset the cached Playwright connection (use after browser restart)."""
    global _pw, _browser, _page, _detected_host
    if _browser:
        try:
            _browser.close()
        except Exception:
            pass
    _browser = None
    _page = None
    _detected_host = None


def connect() -> Dict[str, Any]:
    """Attempt to connect to the browser via CDP.

    Returns a result dict with 'ok' bool and descriptive info.
    """
    if not check_port():
        return {
            "ok": False,
            "error": (
                "CDP port %d not reachable. "
                "Launch Edge with: "
                "msedge --remote-debugging-port=%d"
            ) % (CDP_PORT, CDP_PORT),
        }

    version = get_version()
    pages = get_pages()

    if not pages:
        return {
            "ok": True,
            "browser": version.get("Browser", "unknown") if version else "unknown",
            "url": "(no open pages)",
            "pages": 0,
        }

    first_page = None
    for p in pages:
        if p.get("url") and not p["url"].startswith("chrome"):
            first_page = p
            break
    if first_page is None:
        first_page = pages[0]

    return {
        "ok": True,
        "browser": version.get("Browser", "unknown") if version else "unknown",
        "url": first_page.get("url", ""),
        "title": first_page.get("title", ""),
        "pages": len(pages),
    }


def cleanup():
    """Clean up Playwright resources on process exit."""
    global _pw, _browser, _page
    if _browser:
        try:
            _browser.close()
        except Exception:
            pass
    if _pw:
        try:
            _pw.stop()
        except Exception:
            pass
    _browser = None
    _page = None
    _pw = None
