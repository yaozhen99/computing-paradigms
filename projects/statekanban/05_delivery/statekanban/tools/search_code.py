"""search_code tool implementation.

Accessible by all roles. Searches the codebase for patterns.
"""

from __future__ import annotations

import asyncio
import fnmatch
import os
from typing import Any


async def search_code(params: dict[str, Any]) -> dict[str, Any]:
    """Search the codebase for a pattern.

    Args:
        params: Must contain 'pattern' (glob or text pattern).
                May contain 'path' (root directory, default: '.').
                May contain 'file_glob' (file name filter, default: '*.py').
                May contain 'max_results' (default: 50).

    Returns:
        Dict with 'success', 'matches', and 'total_matches'.
    """
    pattern = params.get("pattern", "")
    root_path = params.get("path", ".")
    file_glob = params.get("file_glob", "*.py")
    max_results = params.get("max_results", 50)

    if not pattern:
        return {
            "success": False,
            "error": "No search pattern specified",
        }

    matches: list[dict[str, Any]] = []

    try:
        for dirpath, dirnames, filenames in os.walk(root_path):
            # Skip hidden and common non-source directories
            dirnames[:] = [
                d
                for d in dirnames
                if not d.startswith(".")
                and d not in ("__pycache__", "node_modules", ".git", ".venv")
            ]

            for filename in filenames:
                if not fnmatch.fnmatch(filename, file_glob):
                    continue

                filepath = os.path.join(dirpath, filename)
                try:
                    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                        for line_no, line in enumerate(f, 1):
                            if pattern.lower() in line.lower():
                                matches.append(
                                    {
                                        "file": filepath,
                                        "line": line_no,
                                        "content": line.rstrip(),
                                    }
                                )
                                if len(matches) >= max_results:
                                    break
                    if len(matches) >= max_results:
                        break
                except (OSError, PermissionError):
                    continue

            if len(matches) >= max_results:
                break

        return {
            "success": True,
            "matches": matches,
            "total_matches": len(matches),
        }

    except Exception as exc:
        return {
            "success": False,
            "error": f"Search failed: {exc}",
        }
