"""Humanized message writer — types text into chat input with realistic timing.

Uses Playwright for reliable page interaction.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Any, Dict

from lib.browser import get_page

logger = logging.getLogger(__name__)

# Typing speed parameters (milliseconds)
_CHAR_DELAY_MIN = 40
_CHAR_DELAY_MAX = 120
_PUNCTUATION_PAUSE_MIN = 200
_PUNCTUATION_PAUSE_MAX = 500
_THINKING_PAUSE_PROB = 0.03
_THINKING_PAUSE_MIN = 500
_THINKING_PAUSE_MAX = 1500
_PRE_SEND_PAUSE_MIN = 300
_PRE_SEND_PAUSE_MAX = 800

_PUNCTUATION_CHARS = frozenset("。，！？、；：""''…—,.!?;:\"'-")

# Selectors for finding the input element, in priority order.
_INPUT_SELECTORS = [
    'textarea',
    '[contenteditable="true"]',
    '[role="textbox"]',
    'input[type="text"]',
]

# Selectors for finding a send button.
_SEND_BUTTON_SELECTORS = [
    'button[aria-label*="Send"]',
    'button[aria-label*="send"]',
    'button[data-testid*="send"]',
    'button[type="submit"]',
]


def _ms(min_ms: float, max_ms: float) -> float:
    """Random delay in milliseconds, returned as seconds for time.sleep()."""
    return random.uniform(min_ms, max_ms) / 1000.0


def _find_input(page):
    """Find the chat input element on the page."""
    for sel in _INPUT_SELECTORS:
        el = page.query_selector(sel)
        if el and el.is_visible():
            return el
    return None


def _find_send_button(page):
    """Find a send button on the page."""
    for sel in _SEND_BUTTON_SELECTORS:
        el = page.query_selector(sel)
        if el and el.is_visible():
            return el
    return None


def send_message(
    text: str,
    humanize: bool = True,
) -> Dict[str, Any]:
    """Type a message into the chat input and send it.

    Args:
        text: The message text to send.
        humanize: If True, type with human-like timing. If False, fill instantly.

    Returns:
        Result dict with 'ok' and descriptive info.
    """
    if not text:
        return {"ok": False, "error": "Empty message"}

    if len(text) > 4000:
        return {"ok": False, "error": "Message too long (max 4000 chars)"}

    page = get_page()
    if page is None:
        return {"ok": False, "error": "No page available. Check CDP connection."}

    # Find and focus the input element
    input_el = _find_input(page)
    if input_el is None:
        return {"ok": False, "error": "No input element found. Run 'dump' first."}

    input_el.click()
    time.sleep(0.1)

    tag = input_el.evaluate("el => el.tagName")

    if humanize:
        # Type character by character with humanized timing
        for char in text:
            input_el.type(char, delay=0)

            time.sleep(_ms(_CHAR_DELAY_MIN, _CHAR_DELAY_MAX))

            if char in _PUNCTUATION_CHARS:
                time.sleep(_ms(_PUNCTUATION_PAUSE_MIN, _PUNCTUATION_PAUSE_MAX))

            if random.random() < _THINKING_PAUSE_PROB:
                time.sleep(_ms(_THINKING_PAUSE_MIN, _THINKING_PAUSE_MAX))

        time.sleep(_ms(_PRE_SEND_PAUSE_MIN, _PRE_SEND_PAUSE_MAX))
    else:
        # Instant fill
        if tag == "TEXTAREA" or tag == "INPUT":
            input_el.fill(text)
        else:
            # contenteditable — use keyboard type
            input_el.type(text)

    # Send: try Enter key first
    input_el.press("Enter")

    # Also try clicking a send button (some sites need both)
    send_btn = _find_send_button(page)
    if send_btn:
        try:
            send_btn.click()
        except Exception:
            pass

    return {"ok": True, "sent": text, "humanized": humanize}
