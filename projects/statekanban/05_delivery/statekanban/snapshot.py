"""Snapshot serialization and deserialization.

save_snapshot: Serialize StateKanban to JSON and write to file.
load_snapshot: Load and validate a snapshot from file.
"""

from __future__ import annotations

import json
import os

from statekanban.core.errors import SnapshotIntegrityError, SnapshotWriteError
from statekanban.core.kanban import StateKanban


def save_snapshot(kanban: StateKanban, path: str) -> None:
    """Serialize kanban to JSON and write to file.

    Args:
        kanban: The kanban instance to snapshot.
        path: File path for the snapshot JSON.

    Raises:
        SnapshotWriteError: File write failed.
    """
    try:
        data = kanban.to_json()
        json_str = json.dumps(data, indent=2, default=str, ensure_ascii=False)

        # Ensure parent directory exists
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        # Atomic write via temp file
        import tempfile
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


def load_snapshot(path: str) -> StateKanban:
    """Load and validate a snapshot from file.

    Args:
        path: Path to the snapshot JSON.

    Returns:
        Reconstructed StateKanban instance.

    Raises:
        SnapshotIntegrityError: Checksum validation failed.
        FileNotFoundError: Snapshot file does not exist.
    """
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
