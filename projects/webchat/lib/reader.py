"""Message reader — extract chat messages via "dimensionality reduction".

Instead of parsing DOM structure (fragile, platform-specific class names),
we dump the page to pure text and parse the text stream. This is the
"降维提取" approach: freeze the page, strip all HTML/CSS/JS, then
extract meaning from the raw text.

Platform adapters are now optional enhancements, not requirements.
"""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

from lib.browser import get_page

logger = logging.getLogger(__name__)

_LOGS_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")


def _save_snapshot(text: str, prefix: str = "page") -> str:
    """Save a text snapshot to logs/ directory, return the file path."""
    os.makedirs(_LOGS_DIR, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(_LOGS_DIR, f"{prefix}_{ts}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def _extract_messages_from_text(text: str) -> List[Dict[str, str]]:
    """Parse chat messages from pure page text.

    Strategy: AI markers ("已思考", "Thinking" etc.) anchor the structure.
    Each AI block starts at its marker. The block's content ends where
    a short standalone line appears — that short line is the next user
    message. This produces alternating user→assistant pairs.
    """
    messages: List[Dict[str, str]] = []

    ai_markers = [
        r"已思考[（(]",
        r"思考过程",
        r"[Tt]hinking",
        r"已深度思考",
    ]
    ai_pattern = "|".join(ai_markers)

    lines = text.split("\n")

    # Identify all AI marker line indices
    ai_line_indices = []
    for i, line in enumerate(lines):
        if re.search(ai_pattern, line.strip()):
            ai_line_indices.append(i)

    if not ai_line_indices:
        content = text.strip()
        if content:
            messages.append({"role": "user", "content": content})
        return messages

    # For each AI block, find where its content actually ends.
    # The content ends at the last long line (> 40 chars) or the last
    # line before a short standalone line that looks like a user prompt.
    # Then the short line(s) between this block's end and the next
    # AI marker are the user message for the next round.
    block_ranges = []  # (ai_start, content_end) pairs
    for block_idx, ai_start in enumerate(ai_line_indices):
        # Scan forward from AI marker to find where AI content ends
        content_end = ai_start
        for i in range(ai_start + 1, len(lines)):
            stripped = lines[i].strip()
            if not stripped:
                continue
            # If we hit another AI marker, this block ends here
            if re.search(ai_pattern, stripped):
                break
            # Short standalone line (< 40 chars) after AI content
            # is likely a user message, not part of the AI reply.
            # But we need to check: is this line followed by more
            # AI content, or by another AI marker?
            if len(stripped) <= 40:
                # Check if the next non-empty line is an AI marker
                next_is_ai = False
                for j in range(i + 1, len(lines)):
                    next_stripped = lines[j].strip()
                    if not next_stripped:
                        continue
                    if re.search(ai_pattern, next_stripped):
                        next_is_ai = True
                    break
                if next_is_ai:
                    # This short line is a user message before the
                    # next AI reply — AI content ends before it.
                    break
            content_end = i

        block_ranges.append((ai_start, content_end))

    # Now extract messages from the blocks
    for block_idx, (ai_start, content_end) in enumerate(block_ranges):
        # User message: lines between previous block's content_end
        # and this block's ai_start
        prev_content_end = block_ranges[block_idx - 1][1] if block_idx > 0 else -1
        user_lines = []
        for i in range(prev_content_end + 1, ai_start):
            stripped = lines[i].strip()
            if stripped and not re.search(ai_pattern, stripped):
                user_lines.append(stripped)
        if user_lines:
            messages.append({"role": "user", "content": "\n".join(user_lines)})

        # AI reply: lines from ai_start to content_end
        ai_lines = []
        for i in range(ai_start, content_end + 1):
            stripped = lines[i].strip()
            if stripped:
                ai_lines.append(stripped)
        if ai_lines:
            messages.append({"role": "assistant", "content": "\n".join(ai_lines)})

    return messages


def _extract_chat_region(text: str) -> str:
    """Try to isolate the chat/conversation region from full page text.

    Sidebar noise (history list, navigation) appears before the actual
    conversation. The key insight: only lines *immediately before* the
    first AI marker are real user messages; everything earlier is sidebar.

    Strategy:
    1. Find all AI marker lines ("已思考", "Thinking", etc.)
    2. From the first AI marker, scan backwards collecting short lines
       (user messages) until hitting a long line or a gap — that's the
       sidebar boundary.
    3. The chat region runs from that boundary to the end of the text
       (after the last AI marker, there may be footer noise like
       "深度思考 智能搜索" and repeated sidebar links).
    """
    lines = text.split("\n")

    ai_markers = ["已思考", "思考过程", "Thinking", "已深度思考"]
    ai_line_indices = []
    for i, line in enumerate(lines):
        if any(m in line for m in ai_markers):
            ai_line_indices.append(i)

    if not ai_line_indices:
        return text

    # --- Find chat start: scan backwards from first AI marker ---
    # Sidebar = many consecutive short lines (history titles, account info).
    # The real user message is the last meaningful line before the AI marker.
    # Strategy: scan backwards, skip known UI noise, take at most 1-2 lines
    # that look like a genuine user prompt.
    first_ai = ai_line_indices[0]
    chat_start = first_ai

    # UI noise patterns near the input area (not real user messages).
    ui_noise = ["@", "快速模式", "深度思考", "智能搜索", "联网搜索",
                "DeepThink", "Search", "开启新对话", "置顶"]

    # Scan backwards from first AI marker. Collect user message lines,
    # but stop if we see too many consecutive non-empty lines (sidebar).
    user_lines_found = 0
    for i in range(first_ai - 1, -1, -1):
        stripped = lines[i].strip()
        if not stripped:
            chat_start = i + 1
            break
        if any(noise in stripped for noise in ui_noise):
            chat_start = i + 1
            break
        user_lines_found += 1
        if user_lines_found > 2:
            # More than 2 lines before first AI marker = sidebar spill
            chat_start = first_ai
            break
        chat_start = i

    # --- Find chat end: scan forward from last AI marker ---
    # Footer noise patterns (DeepSeek: "深度思考 智能搜索 由 AI 生成")
    footer_markers = ["内容由 AI 生成", "内容来自 AI", "AI-generated",
                      "深度思考", "智能搜索"]
    last_ai = ai_line_indices[-1]
    chat_end = len(lines)

    # After the last AI marker's content, look for footer markers
    # and repeated sidebar links (same titles as the top).
    for i in range(last_ai + 1, len(lines)):
        stripped = lines[i].strip()
        if any(m in stripped for m in footer_markers):
            chat_end = i
            break

    return "\n".join(lines[chat_start:chat_end])


def read_messages(
    last: bool = False,
    since: float = 0.0,
    save_snapshot: bool = True,
) -> Dict[str, Any]:
    """Read messages from the current chat page using dimensionality reduction.

    1. Dump page to pure text (inner_text)
    2. Save snapshot to logs/ (offline, safe from anti-debugging)
    3. Extract chat region
    4. Parse messages from text stream
    """
    page = get_page()
    if page is None:
        return {
            "ok": False,
            "error": "No page available. Check CDP connection.",
            "messages": [],
        }

    # Step 1: Dump page to pure text
    try:
        full_text = page.inner_text("body")
    except Exception as exc:
        logger.debug("Page inner_text failed: %s", exc)
        return {
            "ok": False,
            "error": "Failed to read page: %s" % exc,
            "messages": [],
        }

    # Step 2: Save snapshot
    snapshot_path = ""
    if save_snapshot:
        try:
            snapshot_path = _save_snapshot(full_text)
        except OSError:
            pass

    # Step 3: Extract chat region
    chat_text = _extract_chat_region(full_text)

    # Step 4: Parse messages
    messages = _extract_messages_from_text(chat_text)

    if last and messages:
        messages = messages[-1:]

    result: Dict[str, Any] = {
        "ok": True,
        "messages": messages,
        "count": len(messages),
    }
    if snapshot_path:
        result["snapshot"] = snapshot_path

    return result