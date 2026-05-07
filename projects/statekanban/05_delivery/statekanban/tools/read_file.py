"""read_file tool implementation.

Accessible by all roles.
"""

from __future__ import annotations

from typing import Any


async def read_file(params: dict[str, Any]) -> dict[str, Any]:
    """Read file contents from the filesystem.

    Args:
        params: Must contain 'path'.

    Returns:
        Dict with 'success', 'content', and optional 'error'.
    """
    path = params.get("path", "")

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        return {
            "success": True,
            "path": path,
            "content": content,
        }

    except IsADirectoryError:
        return {
            "success": False,
            "error": f"Path is a directory, not a file: {path}",
        }
    except FileNotFoundError:
        return {
            "success": False,
            "error": f"File not found: {path}",
        }
    except PermissionError:
        return {
            "success": False,
            "error": f"Permission denied: {path}",
        }
    except Exception as exc:
        return {
            "success": False,
            "error": f"Failed to read file: {exc}",
        }
