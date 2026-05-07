"""
StateKanban Snapshot Module Tests — R3
TC-SNP-01 through TC-SNP-14
"""

from __future__ import annotations

import json
import os
import stat
import sys
import tempfile

import pytest

from statekanban.core.kanban import (
    Artifact,
    ArtifactType,
    IntentSignal,
    SignalType,
    StateKanban,
    ViewportSpec,
    make_signal_id,
    now_utc,
    compute_checksum,
)
from statekanban.snapshot import (
    SnapshotManager,
    save_snapshot,
    load_snapshot,
    list_snapshots,
    delete_snapshot,
    SnapshotIntegrityError,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_kanban_with_data():
    """Create a StateKanban with some signals."""
    kanban = StateKanban()
    kanban.register_viewport(ViewportSpec(
        role="coder",
        visible_signal_types=[SignalType.INTENT, SignalType.ERROR],
        visible_artifact_types=[ArtifactType.CODE],
        visible_target_patterns=["*"],
        max_tokens=4000,
    ))

    sig = IntentSignal(
        signal_id=make_signal_id(),
        author_role="user",
        target_id="task_root",
        payload={"intent": "Test intent"},
        timestamp=now_utc(),
        round_number=0,
    )
    kanban.fluid.write_signal(sig)
    return kanban


# ---------------------------------------------------------------------------
# TC-SNP-01: Save to valid path creates file
# ---------------------------------------------------------------------------

def test_save_snapshot_creates_file(tmp_path):
    """TC-SNP-01: save_snapshot writes file to valid path."""
    kanban = _make_kanban_with_data()
    path = str(tmp_path / "test_save.json")

    save_snapshot(kanban, path)

    assert os.path.exists(path), "Snapshot file should exist"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "state" in data or "checksum" in data, "Snapshot should contain state data"


# ---------------------------------------------------------------------------
# TC-SNP-02: Creates parent directories
# ---------------------------------------------------------------------------

def test_save_snapshot_creates_parent_dirs(tmp_path):
    """TC-SNP-02: save_snapshot creates missing parent directories."""
    kanban = _make_kanban_with_data()
    path = str(tmp_path / "nested" / "dir" / "test.json")

    save_snapshot(kanban, path)

    assert os.path.exists(path), "Snapshot file should exist with nested dirs"


# ---------------------------------------------------------------------------
# TC-SNP-03: Atomic write (no partial files left)
# ---------------------------------------------------------------------------

def test_save_snapshot_atomic(tmp_path):
    """TC-SNP-03: save_snapshot uses atomic write (no leftover .tmp files)."""
    kanban = _make_kanban_with_data()
    path = str(tmp_path / "atomic_test.json")

    save_snapshot(kanban, path)

    # No .tmp files should be left
    tmp_files = [f for f in os.listdir(str(tmp_path)) if f.endswith(".tmp")]
    assert len(tmp_files) == 0, f"Leftover .tmp files: {tmp_files}"
    # Target file should be complete and valid JSON
    assert os.path.exists(path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data is not None


# ---------------------------------------------------------------------------
# TC-SNP-04: Load valid snapshot
# ---------------------------------------------------------------------------

def test_load_snapshot_valid(tmp_path):
    """TC-SNP-04: load_snapshot reconstructs StateKanban from file."""
    kanban = _make_kanban_with_data()
    path = str(tmp_path / "load_test.json")
    save_snapshot(kanban, path)

    loaded = load_snapshot(path)

    assert isinstance(loaded, StateKanban), "Loaded object should be StateKanban"
    # Check signals are preserved
    loaded_signals = list(loaded.fluid.read_signals())
    original_signals = list(kanban.fluid.read_signals())
    assert len(loaded_signals) == len(original_signals), \
        f"Signal count mismatch: {len(loaded_signals)} vs {len(original_signals)}"


# ---------------------------------------------------------------------------
# TC-SNP-05: Load missing file raises FileNotFoundError
# ---------------------------------------------------------------------------

def test_load_snapshot_missing_file(tmp_path):
    """TC-SNP-05: load_snapshot raises FileNotFoundError for missing file."""
    path = str(tmp_path / "nonexistent.json")

    with pytest.raises(FileNotFoundError):
        load_snapshot(path)


# ---------------------------------------------------------------------------
# TC-SNP-06: Load invalid JSON raises SnapshotIntegrityError
# ---------------------------------------------------------------------------

def test_load_snapshot_invalid_json(tmp_path):
    """TC-SNP-06: load_snapshot raises SnapshotIntegrityError for invalid JSON."""
    path = str(tmp_path / "bad.json")
    with open(path, "w", encoding="utf-8") as f:
        f.write("{invalid json content")

    with pytest.raises(SnapshotIntegrityError):
        load_snapshot(path)


# ---------------------------------------------------------------------------
# TC-SNP-07: Checksum mismatch raises SnapshotIntegrityError
# ---------------------------------------------------------------------------

def test_load_snapshot_checksum_mismatch(tmp_path):
    """TC-SNP-07: load_snapshot raises SnapshotIntegrityError for tampered content."""
    kanban = _make_kanban_with_data()
    path = str(tmp_path / "tampered.json")
    save_snapshot(kanban, path)

    # Tamper with the data content without updating checksum
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Modify data (the actual state payload is under "data" key)
    if "data" in data:
        data["data"]["tampered_key"] = True
    else:
        data["tampered_key"] = True

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    with pytest.raises(SnapshotIntegrityError):
        load_snapshot(path)


# ---------------------------------------------------------------------------
# TC-SNP-08: Full save->load round-trip
# ---------------------------------------------------------------------------

def test_snapshot_round_trip(tmp_path):
    """TC-SNP-08: Full save->load round-trip preserves all zones."""
    kanban = _make_kanban_with_data()
    # Add another signal
    sig2 = IntentSignal(
        signal_id=make_signal_id(),
        author_role="coder",
        target_id="task_A",
        payload={"intent": "Another intent"},
        timestamp=now_utc(),
        round_number=1,
    )
    kanban.fluid.write_signal(sig2)

    path = str(tmp_path / "roundtrip.json")
    save_snapshot(kanban, path)

    loaded = load_snapshot(path)

    # Verify fluid zone
    orig_signals = list(kanban.fluid.read_signals())
    loaded_signals = list(loaded.fluid.read_signals())
    assert len(loaded_signals) == len(orig_signals), "Signal count should match"

    # Verify viewport specs are preserved
    orig_spec = kanban.get_viewport_spec("coder")
    loaded_spec = loaded.get_viewport_spec("coder")
    assert orig_spec is not None
    assert loaded_spec is not None
    assert orig_spec.role == loaded_spec.role
    assert orig_spec.visible_signal_types == loaded_spec.visible_signal_types


# ---------------------------------------------------------------------------
# TC-SNP-09: list_snapshots returns sorted filenames
# ---------------------------------------------------------------------------

def test_list_snapshots_sorted(tmp_path):
    """TC-SNP-09: list_snapshots returns sorted .json filenames."""
    kanban = _make_kanban_with_data()

    # Create snapshots with names that sort interestingly
    for name in ["c.json", "a.json", "b.json"]:
        save_snapshot(kanban, str(tmp_path / name))

    result = list_snapshots(str(tmp_path))

    assert len(result) == 3
    # Should be sorted
    assert result == sorted(result)


# ---------------------------------------------------------------------------
# TC-SNP-10: list_snapshots on missing dir returns empty
# ---------------------------------------------------------------------------

def test_list_snapshots_missing_dir(tmp_path):
    """TC-SNP-10: list_snapshots on missing directory returns empty list."""
    missing = str(tmp_path / "no_such_dir")
    result = list_snapshots(missing)
    assert result == []


# ---------------------------------------------------------------------------
# TC-SNP-11: delete_snapshot removes file
# ---------------------------------------------------------------------------

def test_delete_snapshot(tmp_path):
    """TC-SNP-11: delete_snapshot removes the file."""
    kanban = _make_kanban_with_data()
    path = str(tmp_path / "to_delete.json")
    save_snapshot(kanban, path)
    assert os.path.exists(path)

    delete_snapshot(path)

    assert not os.path.exists(path), "File should be deleted"


# ---------------------------------------------------------------------------
# TC-SNP-12: delete_snapshot on missing file raises
# ---------------------------------------------------------------------------

def test_delete_snapshot_missing(tmp_path):
    """TC-SNP-12: delete_snapshot on missing file raises FileNotFoundError."""
    path = str(tmp_path / "nonexistent.json")

    with pytest.raises(FileNotFoundError):
        delete_snapshot(path)


# ---------------------------------------------------------------------------
# TC-SNP-13: SnapshotManager save/load round-trip
# ---------------------------------------------------------------------------

def test_snapshot_manager_round_trip(tmp_path):
    """TC-SNP-13: SnapshotManager.save_snapshot + load_snapshot round-trip."""
    kanban = _make_kanban_with_data()
    manager = SnapshotManager(base_dir=str(tmp_path))
    name = "manager_test"
    path = str(tmp_path / f"{name}.json")

    manager.save_snapshot(kanban, path)

    loaded = manager.load_snapshot(path)

    assert isinstance(loaded, StateKanban)
    orig_signals = list(kanban.fluid.read_signals())
    loaded_signals = list(loaded.fluid.read_signals())
    assert len(loaded_signals) == len(orig_signals)


# ---------------------------------------------------------------------------
# TC-SNP-14: Null bytes in snapshot path rejected
# ---------------------------------------------------------------------------

def test_snapshot_null_bytes_path(tmp_path):
    """TC-SNP-14: Null bytes in snapshot path should raise an error."""
    from statekanban.core.errors import SnapshotWriteError
    kanban = _make_kanban_with_data()
    bad_path = str(tmp_path / "test\x00bad.json")

    with pytest.raises((SnapshotWriteError, ValueError, TypeError, OSError)):
        save_snapshot(kanban, bad_path)
