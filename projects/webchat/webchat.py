#!/usr/bin/env python3
"""webchat — AI agent web chat interaction tool.

Lets an AI agent (Hermes) read and send messages in web chat interfaces
like DeepSeek, ChatGPT, and ChatGLM via CDP (Chrome DevTools Protocol).

Usage:
    python webchat.py connect              # Check CDP connection
    python webchat.py dump                 # Detect chat elements on page
    python webchat.py read                 # Read all messages
    python webchat.py read --last          # Read last message only
    python webchat.py read --since 5       # Read messages from last 5 seconds
    python webchat.py send "Hello"         # Type and send a message
    python webchat.py send "Hi" --fast     # Send without humanized typing
    python webchat.py wait                 # Wait for AI reply to complete
    python webchat.py wait --timeout 60    # Wait with custom timeout
    python webchat.py chat "Hello"         # Send + wait for reply
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import os
import sys
import time

# Fix Windows GBK console — force UTF-8 for all output
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Add project root to path so lib/ and adapters/ are importable
_PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)

from lib.browser import connect as browser_connect, cleanup as browser_cleanup
from lib.dumper import dump as page_dump
from lib.reader import read_messages
from lib.writer import send_message
from lib.detector import wait_for_reply

logger = logging.getLogger("webchat")


def _output(data: dict) -> None:
    """Print structured output."""
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_connect(args: argparse.Namespace) -> int:
    """Check CDP connection to browser."""
    result = browser_connect()
    if result.get("ok"):
        print("OK|已连接，当前页面: %s" % result.get("url", "unknown"))
        if args.verbose:
            _output(result)
    else:
        print("FAIL|%s" % result.get("error", "连接失败"))
    return 0 if result.get("ok") else 1


def cmd_dump(args: argparse.Namespace) -> int:
    """Detect chat elements on the current page."""
    result = page_dump()
    _output(result)
    return 0 if result.get("ok") else 1


def cmd_read(args: argparse.Namespace) -> int:
    """Read messages from the current chat page."""
    result = read_messages(last=args.last, since=args.since or 0)
    _output(result)
    return 0 if result.get("ok") else 1


def cmd_send(args: argparse.Namespace) -> int:
    """Send a message to the chat."""
    result = send_message(text=args.text, humanize=not args.fast)
    if result.get("ok"):
        print("OK|已发送")
        if args.verbose:
            _output(result)
    else:
        print("FAIL|%s" % result.get("error", "发送失败"))
    return 0 if result.get("ok") else 1


def cmd_wait(args: argparse.Namespace) -> int:
    """Wait for AI reply to complete."""
    result = wait_for_reply(timeout=args.timeout)
    if result.get("ok"):
        _output({
            "ok": True,
            "reply": result.get("reply", ""),
            "role": result.get("role", "assistant"),
            "duration_seconds": result.get("duration_seconds", 0),
        })
    else:
        status = result.get("status", "UNKNOWN")
        if status == "TIMEOUT":
            print("TIMEOUT|等待超时%d秒" % args.timeout)
        _output(result)
    return 0 if result.get("ok") else 1


def cmd_chat(args: argparse.Namespace) -> int:
    """Send a message and wait for the reply (one-shot conversation)."""
    # Send
    send_result = send_message(text=args.text, humanize=not args.fast)
    if not send_result.get("ok"):
        print("FAIL|%s" % send_result.get("error", "发送失败"))
        return 1

    # Wait
    wait_result = wait_for_reply(timeout=args.timeout)
    _output({
        "ok": wait_result.get("ok", False),
        "sent": args.text,
        "reply": wait_result.get("reply", ""),
        "role": wait_result.get("role", "assistant"),
        "duration_seconds": wait_result.get("duration_seconds", 0),
        "incomplete": wait_result.get("incomplete", False),
    })
    return 0 if wait_result.get("ok") else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AI agent web chat interaction tool",
        prog="webchat",
    )
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Verbose output (show full JSON)")
    parser.add_argument("--log-level", default="WARNING",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Log level")

    sub = parser.add_subparsers(dest="command", help="Command to execute")

    # connect
    p_connect = sub.add_parser("connect", help="Check CDP connection")
    p_connect.set_defaults(func=cmd_connect)

    # dump
    p_dump = sub.add_parser("dump", help="Detect chat elements on page")
    p_dump.set_defaults(func=cmd_dump)

    # read
    p_read = sub.add_parser("read", help="Read chat messages")
    p_read.add_argument("--last", action="store_true",
                        help="Only read the last message")
    p_read.add_argument("--since", type=float, default=0,
                        help="Read messages from last N seconds")
    p_read.set_defaults(func=cmd_read)

    # send
    p_send = sub.add_parser("send", help="Send a message")
    p_send.add_argument("text", help="Message text to send")
    p_send.add_argument("--fast", action="store_true",
                        help="Skip humanized typing (instant fill)")
    p_send.set_defaults(func=cmd_send)

    # wait
    p_wait = sub.add_parser("wait", help="Wait for AI reply")
    p_wait.add_argument("--timeout", type=float, default=120,
                        help="Timeout in seconds (default: 120)")
    p_wait.set_defaults(func=cmd_wait)

    # chat (send + wait)
    p_chat = sub.add_parser("chat", help="Send message and wait for reply")
    p_chat.add_argument("text", help="Message text to send")
    p_chat.add_argument("--fast", action="store_true",
                        help="Skip humanized typing")
    p_chat.add_argument("--timeout", type=float, default=120,
                        help="Timeout in seconds (default: 120)")
    p_chat.set_defaults(func=cmd_chat)

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if not args.command:
        parser.print_help()
        return 1

    result = args.func(args)

    browser_cleanup()
    return result


if __name__ == "__main__":
    sys.exit(main())
