"""Snapshot serialization and deserialization.

save_snapshot: Serialize StateKanban to JSON and write to file.
load_snapshot: Load and validate a snapshot from file.
list_snapshots: List all snapshot files in a directory.
delete_snapshot: Delete a snapshot file.

Also provides SnapshotManager class for stateful snapshot management.

REQ-604: save_snapshot can route through OutputValve for sandboxed writes.
load_snapshot validates path against project_root to prevent traversal.

NFR-003 compliance: This module is application-layer, not in core/.
It imports from core/ but performs I/O itself.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from statekanban.core.errors import (
    SnapshotIntegrityError,
    SnapshotPathViolationError,
    SnapshotWriteError,
)
from statekanban.core.kanban import StateKanban

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level functions
# ---------------------------------------------------------------------------


def save_snapshot(
    kanban: StateKanban,
    path: str,
    valve: Any | None = None,
    project_root: str = "",
) -> None:
    """Atomically persist StateKanban to a JSON file.

    REQ-604: When valve is provided, routes the write through
    OutputValve for sandboxed path validation and atomic write.
    Otherwise falls back to direct atomic write (backward compat).

    Algorithm (direct mode):
        1. kanban.to_json() -> dict (includes SHA-256 checksum)
        2. json.dumps() -> string
        3. Write to temp file in same directory
        4. os.replace(temp, path) -- atomic rename
        5. Clean up temp file on failure

    Args:
        kanban: StateKanban instance to persist.
        path: Target file path. Parent directories created if needed.
        valve: Optional OutputValve instance for sandboxed writes (REQ-604).
        project_root: Project space root for path validation when valve is used.

    Raises:
        SnapshotWriteError: SK_SN_002 -- write failed (IO, permissions, etc.).
        ValvePathViolationError: SK_VS_005 -- path escapes sandbox (via valve).
    """
    if valve is not None:
        _save_snapshot_via_valve(kanban, path, valve)
    else:
        _save_snapshot_atomic(kanban, path)


def load_snapshot(
    path: str,
    project_root: str = "",
) -> StateKanban:
    """Load StateKanban from a snapshot file.

    REQ-604: When project_root is provided, validates that the
    resolved path stays within project_root. Prevents path traversal
    attacks (e.g., loading snapshots from outside the project space).

    Algorithm:
        1. Resolve and validate path (if project_root set)
        2. Read and parse JSON
        3. StateKanban.from_json(data) -- verifies SHA-256 checksum
        4. Return reconstructed StateKanban

    Args:
        path: Snapshot file path.
        project_root: Project space root for path validation (REQ-604).
            Empty string means no path validation (backward compat).

    Returns:
        Fully reconstructed StateKanban instance.

    Raises:
        FileNotFoundError: path does not exist.
        SnapshotIntegrityError: SK_SN_001 -- corrupt/invalid file or checksum mismatch.
        SnapshotPathViolationError: SK_SN_003 -- path escapes project_root.
    """
    # REQ-604: Path validation against project_root
    resolved_path = _validate_snapshot_path(path, project_root)
    return _load_snapshot_from_file(resolved_path)


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

    def __init__(
        self,
        base_dir: str = ".statekanban/snapshots",
        project_root: str = "",  # REQ-503: deprecated, use config
        config: Any | None = None,  # REQ-603: preferred
    ) -> None:
        """
        Args:
            base_dir: Directory where snapshots are stored (relative to project_root).
            project_root: Project space root (deprecated, use config).
            config: Config instance for path resolution (REQ-603).
        """
        self._base_dir = base_dir
        self._config = config
        # Backward compat: if config not provided, use project_root
        if config is not None:
            self._project_root = config.project_root
        else:
            self._project_root = project_root

    def save_snapshot(
        self,
        kanban: StateKanban,
        path: str,
        valve: Any | None = None,
    ) -> None:
        """Atomically persist StateKanban to a JSON file.

        REQ-604: When valve is provided, routes through OutputValve.

        Args:
            kanban: StateKanban instance to persist.
            path: Target file path (relative to base_dir or absolute).
            valve: Optional OutputValve instance for sandboxed writes (REQ-604).

        Raises:
            SnapshotWriteError: SK_SN_002 -- write failed.
            ValvePathViolationError: SK_VS_005 -- path escapes sandbox (via valve).
        """
        full_path = self._resolve_path(path)
        self._ensure_gitignore()
        if valve is not None:
            _save_snapshot_via_valve(kanban, full_path, valve)
        else:
            _save_snapshot_atomic(kanban, full_path)

    def load_snapshot(self, path: str) -> StateKanban:
        """Load StateKanban from a snapshot file.

        REQ-604: Path is validated against project_root when configured.

        Args:
            path: Snapshot file path (relative to base_dir or absolute).

        Returns:
            Fully reconstructed StateKanban instance.

        Raises:
            FileNotFoundError: path does not exist.
            SnapshotIntegrityError: SK_SN_001 -- corrupt/invalid file or checksum mismatch.
            SnapshotPathViolationError: SK_SN_003 -- path escapes project_root.
        """
        full_path = self._resolve_path(path)
        # REQ-604: Validate resolved path against project_root
        validated_path = _validate_snapshot_path(
            full_path,
            self._project_root,
        )
        return _load_snapshot_from_file(validated_path)

    def list_snapshots(self) -> list[str]:
        """List all snapshot files in the base directory.

        Returns:
            List of snapshot filenames (not full paths), sorted by name.
        """
        resolved_base = self._resolve_path("")
        return list_snapshots(resolved_base)

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
        """Resolve a path relative to project_root + base_dir if not absolute.

        REQ-603: When config is provided, uses config.resolve_path()
        which includes traversal guard. Otherwise falls back to
        legacy project_root/CWD resolution with a basic traversal
        guard when project_root is set.
        """
        if os.path.isabs(path):
            return path

        if self._config is not None:
            # REQ-603: Use config.resolve_path() with traversal guard
            effective_path = os.path.join(self._base_dir, path)
            return self._config.resolve_path(effective_path)

        # Legacy fallback (R5 compat)
        base = self._project_root if self._project_root else os.getcwd()
        effective_base = os.path.join(base, self._base_dir)
        result = os.path.join(effective_base, path)

        # M-2 fix: Traversal guard in legacy path
        # When project_root is set, verify the resolved path stays within it.
        if self._project_root:
            abs_result = os.path.abspath(result)
            abs_root = os.path.abspath(self._project_root)
            if not Path(abs_result).is_relative_to(Path(abs_root)):
                from statekanban.core.errors import PathEscapeError

                raise PathEscapeError(
                    attempted_path=path,
                    project_root=abs_root,
                )

        return result

    def _ensure_gitignore(self) -> None:
        """Create .gitignore in .statekanban/ if it doesn't exist (AC-603.5).

        Content is '*' to prevent snapshots from being tracked by git.
        Called lazily on first save_snapshot().
        """
        if self._config is not None:
            statekanban_dir = self._config.resolve_path(".statekanban")
        else:
            base = self._project_root if self._project_root else os.getcwd()
            statekanban_dir = os.path.join(base, ".statekanban")

        gitignore_path = os.path.join(statekanban_dir, ".gitignore")

        if not os.path.exists(gitignore_path):
            try:
                os.makedirs(statekanban_dir, exist_ok=True)
                with open(gitignore_path, "w", encoding="utf-8") as f:
                    f.write("*\n")
            except OSError:
                logger.debug("Failed to create .gitignore in %s", statekanban_dir)


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
        raise SnapshotIntegrityError(f"Snapshot file is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise SnapshotIntegrityError(f"Failed to read snapshot file: {exc}") from exc

    return StateKanban.from_json(data)


def _validate_snapshot_path(path: str, project_root: str) -> str:
    """Validate that a snapshot path stays within project_root.

    REQ-604: When project_root is set, resolves the path and checks
    that it stays within the sandbox. Prevents path traversal attacks.

    Args:
        path: The snapshot file path.
        project_root: Project space root. Empty string means no validation.

    Returns:
        The resolved absolute path.

    Raises:
        SnapshotPathViolationError: SK_SN_003 if path escapes project_root.
    """
    if not project_root:
        # No sandbox configured -- return as-is (backward compat)
        return path

    # Resolve absolute path
    if os.path.isabs(path):
        abs_path = os.path.realpath(path)
    else:
        abs_path = os.path.realpath(os.path.join(project_root, path))

    abs_root = os.path.realpath(project_root)

    if not Path(abs_path).is_relative_to(Path(abs_root)):
        raise SnapshotPathViolationError(
            attempted_path=path,
            project_root=abs_root,
        )

    return abs_path


def _save_snapshot_via_valve(
    kanban: StateKanban, path: str, valve: Any
) -> None:
    """Save snapshot through OutputValve for sandboxed writes (REQ-604).

    Creates an Artifact and submits it through valve.validate_and_write().
    This ensures the write path is validated by the valve's path sandbox.

    Args:
        kanban: StateKanban instance to persist.
        path: Target file path.
        valve: OutputValve instance.

    Raises:
        SnapshotWriteError: SK_SN_002 if valve write fails.
    """
    import asyncio

    from statekanban.core.kanban import (
        Artifact,
        ArtifactType,
        compute_checksum,
        make_signal_id,
        now_utc,
    )

    try:
        data = kanban.to_json()
        json_str = json.dumps(data, indent=2, default=str, ensure_ascii=False)

        artifact = Artifact(
            seq_no=0,
            artifact_type=ArtifactType.CONFIG,
            path=path,
            content=json_str,
            checksum=compute_checksum(json_str),
            author_role="system",
            created_at=now_utc(),
        )

        # valve.validate_and_write is async -- run it in a fresh event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            # We're inside an async context -- can't use asyncio.run()
            # Schedule and wait using a thread
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                valve_result = pool.submit(
                    asyncio.run, valve.validate_and_write(artifact)
                ).result()
        else:
            valve_result = asyncio.run(valve.validate_and_write(artifact))

        if not valve_result.success:
            raise SnapshotWriteError(
                f"Valve rejected snapshot write to {path}: {valve_result.error}"
            )

    except SnapshotWriteError:
        raise
    except Exception as exc:
        raise SnapshotWriteError(
            f"Failed to save snapshot through valve: {exc}"
        ) from exc
