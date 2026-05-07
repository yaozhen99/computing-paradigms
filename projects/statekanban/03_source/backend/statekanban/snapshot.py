"""Snapshot serialization and deserialization.

save_snapshot: Serialize StateKanban to JSON and write to file.
load_snapshot: Load and validate a snapshot from file.
list_snapshots: List all snapshot files in a directory.
delete_snapshot: Delete a snapshot file.

Also provides SnapshotManager class for stateful snapshot management.

NFR-003 compliance: This module is application-layer, not in core/.
It imports from core/ but performs I/O itself.
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any

from statekanban.core.errors import SnapshotIntegrityError, SnapshotWriteError
from statekanban.core.kanban import StateKanban


# ---------------------------------------------------------------------------
# Module-level functions
# ---------------------------------------------------------------------------

def save_snapshot(kanban: StateKanban, path: str) -> None:
    """Atomically persist StateKanban to a JSON file.

    Algorithm:
        1. kanban.to_json() -> dict (includes SHA-256 checksum)
        2. json.dumps() -> string
        3. Write to temp file in same directory
        4. os.replace(temp, path) -- atomic rename
        5. Clean up temp file on failure

    Args:
        kanban: StateKanban instance to persist.
        path: Target file path. Parent directories created if needed.

    Raises:
        SnapshotWriteError: SK_SN_002 -- write failed (IO, permissions, etc.).
    """
    _save_snapshot_atomic(kanban, path)


def load_snapshot(path: str) -> StateKanban:
    """Load StateKanban from a snapshot file.

    Algorithm:
        1. Read and parse JSON
        2. StateKanban.from_json(data) -- verifies SHA-256 checksum
        3. Return reconstructed StateKanban

    Args:
        path: Snapshot file path.

    Returns:
        Fully reconstructed StateKanban instance.

    Raises:
        FileNotFoundError: path does not exist.
        SnapshotIntegrityError: SK_SN_001 -- corrupt/invalid file or checksum mismatch.
    """
    return _load_snapshot_from_file(path)


def list_snapshots(base_dir: str = ".statekanban/snapshots") -> list[str]:
    """List all snapshot files in a directory.

    Args:
        base_dir: Directory to scan for snapshot files.

    Returns:
        List of snapshot filenames, sorted by name.
    """
    if not os.path.exists(base_dir):
        return []
    entries: list[str] = []
    try:
        for name in os.listdir(base_dir):
            if name.endswith(".json"):
                entries.append(name)
    except OSError:
        return []
    return sorted(entries)


def delete_snapshot(path: str) -> None:
    """Delete a snapshot file.

    Args:
        path: Snapshot file path.

    Raises:
        FileNotFoundError: path does not exist.
        OSError: Deletion failed.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Snapshot file not found: {path}")
    os.remove(path)


# ---------------------------------------------------------------------------
# SnapshotManager class
# ---------------------------------------------------------------------------

class SnapshotManager:
    """Manager for StateKanban snapshot operations.

    Provides a class-based interface for save, load, list, and delete
    operations on StateKanban snapshot files.

    Usage:
        mgr = SnapshotManager(base_dir=".statekanban/snapshots")
        mgr.save_snapshot(kanban, "my_snapshot.json")
        kanban2 = mgr.load_snapshot("my_snapshot.json")
        names = mgr.list_snapshots()
        mgr.delete_snapshot("my_snapshot.json")
    """

    def __init__(self, base_dir: str = ".statekanban/snapshots") -> None:
        """
        Args:
            base_dir: Directory where snapshots are stored.
        """
        self._base_dir = base_dir

    def save_snapshot(self, kanban: StateKanban, path: str) -> None:
        """Atomically persist StateKanban to a JSON file.

        Args:
            kanban: StateKanban instance to persist.
            path: Target file path (relative to base_dir or absolute).

        Raises:
            SnapshotWriteError: SK_SN_002 -- write failed.
        """
        full_path = self._resolve_path(path)
        _save_snapshot_atomic(kanban, full_path)

    def load_snapshot(self, path: str) -> StateKanban:
        """Load StateKanban from a snapshot file.

        Args:
            path: Snapshot file path (relative to base_dir or absolute).

        Returns:
            Fully reconstructed StateKanban instance.

        Raises:
            FileNotFoundError: path does not exist.
            SnapshotIntegrityError: SK_SN_001 -- corrupt/invalid file or checksum mismatch.
        """
        full_path = self._resolve_path(path)
        return _load_snapshot_from_file(full_path)

    def list_snapshots(self) -> list[str]:
        """List all snapshot files in the base directory.

        Returns:
            List of snapshot filenames (not full paths), sorted by name.
        """
        return list_snapshots(self._base_dir)

    def delete_snapshot(self, path: str) -> None:
        """Delete a snapshot file.

        Args:
            path: Snapshot file path (relative to base_dir or absolute).

        Raises:
            FileNotFoundError: path does not exist.
            OSError: Deletion failed.
        """
        full_path = self._resolve_path(path)
        delete_snapshot(full_path)

    def _resolve_path(self, path: str) -> str:
        """Resolve a path relative to base_dir if not absolute."""
        if os.path.isabs(path):
            return path
        return os.path.join(self._base_dir, path)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _save_snapshot_atomic(kanban: StateKanban, path: str) -> None:
    """Atomic write of StateKanban to a JSON file.

    Uses tempfile.mkstemp + os.replace for atomic semantics.
    """
    try:
        data = kanban.to_json()
        json_str = json.dumps(data, indent=2, default=str, ensure_ascii=False)

        # Ensure parent directory exists
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        # Atomic write via temp file
        fd, tmp_path = tempfile.mkstemp(
            dir=parent or None,
            prefix=".statekanban_snapshot_",
            suffix=".json",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(json_str)
            os.replace(tmp_path, path)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    except SnapshotWriteError:
        raise
    except OSError as exc:
        raise SnapshotWriteError(f"Failed to write snapshot to {path}: {exc}") from exc
    except Exception as exc:
        raise SnapshotWriteError(f"Failed to serialize snapshot: {exc}") from exc


def _load_snapshot_from_file(path: str) -> StateKanban:
    """Load and validate a snapshot from a file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Snapshot file not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise SnapshotIntegrityError(
            f"Snapshot file is not valid JSON: {exc}"
        ) from exc
    except OSError as exc:
        raise SnapshotIntegrityError(
            f"Failed to read snapshot file: {exc}"
        ) from exc

    return StateKanban.from_json(data)
