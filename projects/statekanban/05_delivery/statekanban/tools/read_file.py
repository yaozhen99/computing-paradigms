"""read_file tool implementation.

Accessible by all roles.

REQ-605/C-2: Path sandbox added. When config is provided,
resolves path via config.resolve_path() which includes traversal
guard and null-byte check. Without config, falls back to direct
read (backward compat) with a warning log.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


async def read_file(
    params: dict[str, Any],
    config: Any | None = None,
) -> dict[str, Any]:
    """Read file contents from the filesystem.

    When config is provided, the path is resolved via
    config.resolve_path() which enforces sandbox boundaries
    (project_root) and null-byte detection. Without config,
    falls back to direct open (backward compat) with a
    warning about unvalidated path access.

    Args:
        params: Must contain 'path'.
        config: Config instance for sandboxed path resolution.
                When provided, config.resolve_path() is called
                before opening the file.

    Returns:
        Dict with 'success', 'content', and optional 'error'.
    """
    path = params.get("path", "")

    # Null-byte check (always, even without config)
    if "\x00" in path:
        return {
            "success": False,
            "error": f"Path contains null byte: {path!r}",
            "error_code": "SK_TR_005",
        }

    # Path sandbox resolution
    if config is not None:
        try:
            resolved_path = config.resolve_path(path)
        except Exception as exc:
            # PathEscapeError or ValueError from config.resolve_path
            exc_name = type(exc).__name__
            error_code = getattr(exc, "error_code", "SK_TR_005")
            return {
                "success": False,
                "error": f"Path violation: {exc_name}: {exc}",
                "error_code": error_code,
            }
        # Symlink normalization: os.path.realpath() after resolve
        resolved_path = os.path.realpath(resolved_path)
        # Verify resolved path is still within project_root
        project_root = os.path.realpath(config.project_root)
        if not Path(resolved_path).is_relative_to(Path(project_root)):
            return {
                "success": False,
                "error": (
                    f"Path violation: resolved path '{resolved_path}' "
                    f"escapes project root '{project_root}'"
                ),
                "error_code": "SK_TR_005",
            }
    else:
        # Backward compat: no config, direct read
        logger.warning(
            "read_file called without config -- path not sandboxed: %s", path
        )
        resolved_path = path

    try:
        with open(resolved_path, "r", encoding="utf-8") as f:
            content = f.read()

        return {
            "success": True,
            "path": path,
            "resolved_path": resolved_path,
            "content": content,
        }

    except IsADirectoryError:
        return {
            "success": False,
            "error": f"Path is a directory, not a file: {path}",
            "error_code": "SK_TR_005",
        }
    except FileNotFoundError:
        return {
            "success": False,
            "error": f"File not found: {path}",
            "error_code": "SK_TR_005",
        }
    except PermissionError:
        return {
            "success": False,
            "error": f"Permission denied: {path}",
            "error_code": "SK_TR_005",
        }
    except Exception as exc:
        return {
            "success": False,
            "error": f"Failed to read file: {exc}",
            "error_code": "SK_TR_005",
        }
