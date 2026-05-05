#!/usr/bin/env python3
r"""webchat-new -- Open a new chat session on the current browser tab.

Thin wrapper over Playwright CDP. Uses the same browser connection as webchat.
Platform-specific navigation:
  - DeepSeek: https://chat.deepseek.com/
  - ChatGPT:  https://chatgpt.com/
  - Others:   navigate to site root

Usage (from WSL):
    /mnt/c/Python312/python.exe 'C:\tower-of-babel\hermes\hertes\scripts\webchat_new.py'
"""

from __future__ import annotations

import io
import sys

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

_PROJECT_DIR = r"C:\tower-of-babel\projects\webchat"
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)

from lib.browser import get_page, cleanup
from urllib.parse import urlparse

PLATFORM_MAP = {
    "deepseek.com": "https://chat.deepseek.com/",
    "chatgpt.com": "https://chatgpt.com/",
    "chatglm.cn": "https://chatglm.cn/",
}


def main() -> int:
    page = get_page()
    if not page:
        print("FAIL|无法连接浏览器")
        return 1

    current_url = page.url

    # Determine target URL based on current platform
    target = None
    for domain, url in PLATFORM_MAP.items():
        if domain in current_url:
            target = url
            break
    if target is None:
        parsed = urlparse(current_url)
        target = f"{parsed.scheme}://{parsed.netloc}/"

    # Navigate to new chat
    page.goto(target, wait_until="networkidle", timeout=10000)
    print(f"OK|新对话已创建，当前页面: {page.url}")

    cleanup()
    return 0


if __name__ == "__main__":
    sys.exit(main())
