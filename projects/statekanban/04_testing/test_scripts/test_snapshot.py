"""Tests for Snapshot: save, load, integrity, round-trip."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from statekanban.core.errors import SnapshotIntegrityError, SnapshotWriteError
from statekanban.core.kanban import (
    ArtifactType,
    IntentSignal,
    SignalType,
    StateKanban,
    make_signal_id,
    now_utc,
)
from statekanban.snapshot import save_snapshot, load_snapshot


class TestSnapshotSave:
    """TC-SN-001 ~ TC-SN-002: Snapshot save."""

    def test_save_to_valid_path(self, kanban, tmp_dir):
        # TC-SN-001
        path = os.path.join(tmp_dir, "snapshot.json")
        save_snapshot(kanban, path)
        assert os.path.exists(path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "data" in data
        assert "checksum" in data

    def test_creates_parent_directories(self, kanban, tmp_dir):
        # TC-SN-002
        path = os.path.join(tmp_dir, "sub", "dir", "snapshot.json")
        save_snapshot(kanban, path)
        assert os.path.exists(path)


class TestSnapshotLoad:
    """TC-SN-003 ~ TC-SN-006: Snapshot load."""

    def test_load_valid_snapshot(self, kanban, tmp_dir):
        # TC-SN-003
        path = os.path.join(tmp_dir, "snapshot.json")
        save_snapshot(kanban, path)
        loaded = load_snapshot(path)
        assert loaded is not None
        assert isinstance(loaded, StateKanban)

    def test_file_not_found(self):
        # TC-SN-004
        with pytest.raises(FileNotFoundError):
            load_snapshot("/nonexistent/path/snapshot.json")

    def test_invalid_json_raises_integrity_error(self, tmp_dir):
        # TC-SN-005
        path = os.path.join(tmp_dir, "bad_snapshot.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write("NOT VALID JSON {{{")
        with pytest.raises(SnapshotIntegrityError):
            load_snapshot(path)

    def test_checksum_mismatch_raises_integrity_error(self, kanban, tmp_dir):
        # TC-SN-006
        data = kanban.to_json()
        # Tamper the data but keep the old checksum
        data["data"]["fluid"] = ["TAMPERED"]
        path = os.path.join(tmp_dir, "tampered.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        with pytest.raises(SnapshotIntegrityError):
            load_snapshot(path)


class TestSnapshotRoundTrip:
    """TC-SN-007: Full round-trip."""

    def test_full_round_trip_preserves_data(self, tmp_dir):
        # TC-SN-007
        from statekanban.core.kanban import ViewportSpec, Artifact, compute_checksum
        kanban = StateKanban()
        # Populate kanban
        kanban.fluid.write_signal(IntentSignal(
            signal_id=make_signal_id(),
            author_role="coder",
            target_id="A",
            payload={"action": "approve"},
            timestamp=now_utc(),
            round_number=0,
        ))
        kanban.audit.log("test_event", "tester", "test_action", {"key": "val"})
        kanban.register_viewport(ViewportSpec(
            role="coder",
            visible_signal_types=[SignalType.INTENT],
            visible_artifact_types=[ArtifactType.CODE],
            visible_target_patterns=["*"],
        ))
        kanban.crystal.append(Artifact(
            seq_no=0, artifact_type=ArtifactType.CODE,
            path="test.py", content="print('hello')",
            checksum=compute_checksum("print('hello')"),
            author_role="coder", created_at=now_utc(),
        ))

        path = os.path.join(tmp_dir, "roundtrip.json")
        save_snapshot(kanban, path)
        loaded = load_snapshot(path)

        # Verify all zones preserved
        assert len(loaded.fluid.read_signals()) == len(kanban.fluid.read_signals())
        assert loaded.crystal.latest_seq_no() == kanban.crystal.latest_seq_no()
        assert len(loaded.audit.read_entries()) == len(kanban.audit.read_entries())
        assert loaded.get_viewport_spec("coder") is not None