"""Page structure dumper — detect chat input boxes and message containers.

Uses Playwright to evaluate JS on the page and find candidate elements
for chat interaction.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from lib.browser import get_page

logger = logging.getLogger(__name__)

_DUMP_SCRIPT = r"""
(() => {
  const result = { url: location.href, inputs: [], message_containers: [] };

  // --- Input boxes ---
  const inputSelectors = [
    'textarea',
    '[contenteditable="true"]',
    'input[type="text"]',
    '[role="textbox"]',
    '[data-placeholder]',
  ];
  const seen = new Set();
  for (const sel of inputSelectors) {
    for (const el of document.querySelectorAll(sel)) {
      const rect = el.getBoundingClientRect();
      if (rect.width < 10 || rect.height < 10) continue;
      const key = el.outerHTML.slice(0, 200);
      if (seen.has(key)) continue;
      seen.add(key);
      result.inputs.push({
        tag: el.tagName,
        id: el.id || null,
        className: (el.className && typeof el.className === 'string')
                   ? el.className.slice(0, 200) : null,
        placeholder: el.placeholder || el.getAttribute('data-placeholder') || null,
        contentEditable: el.contentEditable,
        role: el.getAttribute('role') || null,
        rect: { x: Math.round(rect.x), y: Math.round(rect.y),
                w: Math.round(rect.width), h: Math.round(rect.height) },
      });
    }
  }

  // --- Message containers ---
  const msgKeywords = /message|chat|conversation|assistant|user|reply|dialog/i;
  const msgSelectors = [
    '[role="log"]',
    '[aria-live="polite"]',
    '[aria-live="assertive"]',
  ];
  const msgSeen = new Set();

  for (const sel of msgSelectors) {
    for (const el of document.querySelectorAll(sel)) {
      const text = el.innerText?.slice(0, 100) || '';
      if (!text.trim()) continue;
      const key = el.outerHTML.slice(0, 200);
      if (msgSeen.has(key)) continue;
      msgSeen.add(key);
      result.message_containers.push({
        tag: el.tagName,
        id: el.id || null,
        className: (el.className && typeof el.className === 'string')
                   ? el.className.slice(0, 200) : null,
        role: el.getAttribute('role') || null,
        aria_live: el.getAttribute('aria-live') || null,
        child_count: el.children.length,
        text_preview: text.slice(0, 120),
      });
    }
  }

  for (const el of document.querySelectorAll('div, section, article')) {
    const cls = el.className;
    if (typeof cls !== 'string' || !msgKeywords.test(cls)) continue;
    const text = el.innerText?.slice(0, 100) || '';
    if (!text.trim() || text.length < 10) continue;
    const key = el.outerHTML.slice(0, 200);
    if (msgSeen.has(key)) continue;
    msgSeen.add(key);
    result.message_containers.push({
      tag: el.tagName,
      id: el.id || null,
      className: cls.slice(0, 200),
      role: el.getAttribute('role') || null,
      aria_live: el.getAttribute('aria-live') || null,
      child_count: el.children.length,
      text_preview: text.slice(0, 120),
    });
  }

  return result;
})()
"""


def dump() -> Dict[str, Any]:
    """Analyze the current page and return detected chat elements."""
    page = get_page()
    if page is None:
        return {
            "ok": False,
            "error": "No page available. Check CDP connection.",
        }

    try:
        result = page.evaluate(_DUMP_SCRIPT)
    except Exception as exc:
        logger.debug("Page evaluate failed: %s", exc)
        return {
            "ok": False,
            "error": "Failed to evaluate page DOM: %s" % exc,
        }

    result["ok"] = True
    return result