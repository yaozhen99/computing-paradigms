"""webchat API — AI agent entry point.

Provides a run() function that any AI agent (Claude Code, Hermes, etc.)
can call directly without going through the CLI.

Usage from Python:
    from webchat_api import run

    result = run("connect")
    result = run("read", last=True)
    result = run("send", text="Hello", humanize=True)
    result = run("wait", timeout=60)
    result = run("chat", text="1+1=?", humanize=True, timeout=120)

All commands return a dict with at least an "ok" key (bool).
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict

# Ensure project root is on sys.path so "lib" is importable
_PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)

from lib.browser import connect as browser_connect, cleanup as browser_cleanup
from lib.dumper import dump as page_dump
from lib.reader import read_messages
from lib.writer import send_message
from lib.detector import wait_for_reply


def run(command: str, **params: Any) -> Dict[str, Any]:
    """Execute a webchat command and return a result dict.

    Commands:
        connect  — Check CDP connection to browser.
                   No params.
                   Returns: {ok, browser, url, title, pages} or {ok, error}

        dump     — Detect chat elements on current page.
                   No params.
                   Returns: {ok, url, inputs, message_containers} or {ok, error}

        read     — Read messages from current chat page.
                   Params: last (bool, default False) — only last message
                           since (float, default 0) — messages from last N seconds
                   Returns: {ok, messages, count, snapshot?} or {ok, error}

        send     — Type and send a message.
                   Params: text (str, required) — message to send
                           humanize (bool, default True) — humanized typing
                   Returns: {ok, sent, humanized} or {ok, error}

        wait     — Wait for AI reply to complete.
                   Params: timeout (float, default 120) — max wait seconds
                   Returns: {ok, reply, role, duration_seconds} or {ok, error, status}

        chat     — Send a message and wait for reply (one-shot).
                   Params: text (str, required) — message to send
                           humanize (bool, default True) — humanized typing
                           timeout (float, default 120) — max wait seconds
                   Returns: {ok, sent, reply, role, duration_seconds, incomplete?}

    Returns:
        Dict with "ok" (bool) and command-specific fields.
    """
    if command == "connect":
        return browser_connect()

    if command == "dump":
        return page_dump()

    if command == "read":
        return read_messages(
            last=params.get("last", False),
            since=params.get("since", 0.0),
            save_snapshot=params.get("save_snapshot", True),
        )

    if command == "send":
        text = params.get("text", "")
        if not text:
            return {"ok": False, "error": "Missing required param: text"}
        return send_message(
            text=text,
            humanize=params.get("humanize", True),
        )

    if command == "wait":
        return wait_for_reply(timeout=params.get("timeout", 120.0))

    if command == "chat":
        text = params.get("text", "")
        if not text:
            return {"ok": False, "error": "Missing required param: text"}

        send_result = send_message(
            text=text,
            humanize=params.get("humanize", True),
        )
        if not send_result.get("ok"):
            return send_result

        wait_result = wait_for_reply(timeout=params.get("timeout", 120.0))
        return {
            "ok": wait_result.get("ok", False),
            "sent": text,
            "reply": wait_result.get("reply", ""),
            "role": wait_result.get("role", "assistant"),
            "duration_seconds": wait_result.get("duration_seconds", 0),
            "incomplete": wait_result.get("incomplete", False),
        }

    return {"ok": False, "error": "Unknown command: %s" % command}
