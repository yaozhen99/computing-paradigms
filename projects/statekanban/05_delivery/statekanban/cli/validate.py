"""CLI path validation for --project-root argument.

Validation chain (in order, AC-605.7):
1. Null byte detection
2. Path normalization (relative -> absolute)
3. Existence check
4. Directory check

Each step produces a specific error code and message.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import NoReturn


class PathValidationError(Exception):
    """Base error for CLI path validation failures."""

    exit_code: int = 1

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message: str = message


class NullByteError(PathValidationError):
    """Path contains null byte (AC-605.1)."""

    exit_code: int = 2

    def __init__(self, path: str) -> None:
        self.path: str = path
        super().__init__(f"Path validation error [null byte]: {path!r}")


class PathNotExistError(PathValidationError):
    """Project root path does not exist (AC-605.3)."""

    exit_code: int = 3

    def __init__(self, path: str) -> None:
        self.path: str = path
        super().__init__(f"Path validation error [not exist]: {path!r}")


class PathNotDirectoryError(PathValidationError):
    """Project root path is not a directory (AC-605.4)."""

    exit_code: int = 4

    def __init__(self, path: str) -> None:
        self.path: str = path
        super().__init__(f"Path validation error [not directory]: {path!r}")


def validate_project_root(path_str: str) -> Path:
    """Validate and normalize --project-root argument.

    Validation chain (AC-605.7):
    1. Null byte detection -- fail fast before any path operations
    2. Relative -> absolute conversion (via Path.resolve())
    3. Existence check
    4. Directory check

    Args:
        path_str: Raw --project-root argument value.

    Returns:
        Validated absolute Path.

    Raises:
        NullByteError: If path_str contains null bytes.
        PathNotExistError: If path does not exist.
        PathNotDirectoryError: If path is not a directory.
    """
    # Step 1: Null byte detection (AC-605.1)
    if "\x00" in path_str:
        raise NullByteError(path_str)

    # Step 2: Normalize to absolute path (AC-605.2)
    abs_path: Path = Path(path_str).resolve()

    # Step 3: Existence check (AC-605.3)
    if not abs_path.exists():
        raise PathNotExistError(str(abs_path))

    # Step 4: Directory check (AC-605.4)
    if not abs_path.is_dir():
        raise PathNotDirectoryError(str(abs_path))

    return abs_path
