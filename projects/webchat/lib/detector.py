"""Reply completion detector — wait for AI to finish generating.

Uses dimensionality reduction: instead of querying DOM elements (fragile),
we dump page text and check if content is stable. When the text stops
changing, the reply is done.

Also checks for "stop generating" buttons via Playwright selectors as a
fast-path signal, but the primary mechanism is content stability.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Dict, Optional

from lib.browser import get_page
from lib.reader import _extract_chat_region, _extract_messages_from_text

logger = logging.getLogger(__name__)

# Selectors for "stop generating" buttons — used as a fast-path signal.
_STOP_SELECTORS = [
    'button[aria-label*="Stop"]',
    'button[aria-label*="stop"]',
    'button[aria-label*="Cancel"]',
    'button[aria-label*="cancel"]',
    'button[data-testid*="stop"]',
]

_STABILITY_SECONDS = 2.0
_POLL_INTERVAL = 0.8


def _is_generating(page) -> bool:
    """Quick check: is a 'stop generating' button visible?"""
    for sel in _STOP_SELECTORS:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                return True
        except Exception:
            pass
    return False


def _text_hash(page) -> str:
    """Hash the page's visible text content."""
    try:
        text = page.inner_text("body")
    except Exception:
        return ""
    return hashlib.md5(text.encode("utf-8", errors="replace")).hexdigest()


def _get_last_reply(page) -> Dict[str, str]:
    """Extract the last AI reply from the page text."""
    try:
        text = page.inner_text("body")
    except Exception:
        return {"role": "none", "content": ""}

    chat_text = _extract_chat_region(text)
    messages = _extract_messages_from_text(chat_text)

    # Find the last assistant message
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            return {"role": "assistant", "content": msg.get("content", "")}

    # No assistant message found
    if messages:
        last = messages[-1]
        return {"role": last.get("role", "unknown"), "content": last.get("content", "")}
    return {"role": "none", "content": ""}


def wait_for_reply(
    timeout: float = 120.0,
    stability_seconds: float = _STABILITY_SECONDS,
) -> Dict[str, Any]:
    """Wait for the AI to finish generating its reply.

    Uses content stability (text hash unchanged for N seconds) as the
    primary completion signal. Falls back to timeout.
    """
    page = get_page()
    if page is None:
        return {
            "ok": False,
            "error": "No page available. Check CDP connection.",
            "reply": "",
            "duration_seconds": 0,
        }

    start_time = time.time()
    last_hash: Optional[str] = None
    stable_since: Optional[float] = None

    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout:
            reply = _get_last_reply(page)
            return {
                "ok": False,
                "status": "TIMEOUT",
                "error": "Wait timed out after %.0f seconds" % timeout,
                "reply": reply.get("content", ""),
                "duration_seconds": round(elapsed, 1),
                "incomplete": True,
            }

        # Fast path: check for stop button
        if _is_generating(page):
            last_hash = None
            stable_since = None
            time.sleep(_POLL_INTERVAL)
            continue

        # Content stability check
        current_hash = _text_hash(page)
        if current_hash == last_hash and last_hash is not None:
            if stable_since is None:
                stable_since = time.time()
            elif time.time() - stable_since >= stability_seconds:
                reply = _get_last_reply(page)
                return {
                    "ok": True,
                    "status": "COMPLETE",
                    "reply": reply.get("content", ""),
                    "role": reply.get("role", "assistant"),
                    "duration_seconds": round(time.time() - start_time, 1),
                }
        else:
            last_hash = current_hash
            stable_since = None

        time.sleep(_POLL_INTERVAL)