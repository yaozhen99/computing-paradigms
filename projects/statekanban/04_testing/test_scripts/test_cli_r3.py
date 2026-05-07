"""
StateKanban CLI Snapshot Subcommand Tests -- R3
TC-CLI-01 through TC-CLI-06

Tests for CLI snapshot save, load, list, and delete subcommands.
"""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from statekanban.cli.main import build_parser, cmd_snapshot
from statekanban.core.kanban import (
    IntentSignal,
    SignalType,
    StateKanban,
    ViewportSpec,
    ArtifactType,
    make_signal_id,
    now_utc,
)
from statekanban.snapshot import save_snapshot

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_kanban_with_data():
    """Create a StateKanban with some data."""
    kanban = StateKanban()
    kanban.register_viewport(
        ViewportSpec(
            role="coder",
            visible_signal_types=[SignalType.INTENT, SignalType.ERROR],
            visible_artifact_types=[ArtifactType.CODE],
            visible_target_patterns=["*"],
            max_tokens=4000,
        )
    )
    sig = IntentSignal(
        signal_id=make_signal_id(),
        author_role="user",
        target_id="task_root",
        payload={"intent": "CLI test intent"},
        timestamp=now_utc(),
        round_number=0,
    )
    kanban.fluid.write_signal(sig)
    return kanban


# ---------------------------------------------------------------------------
# TC-CLI-01: snapshot save creates file
# ---------------------------------------------------------------------------


class TestCLISnapshotSave:

    def test_snapshot_save_creates_file(self, tmp_path):
        """TC-CLI-01: snapshot save creates a snapshot file."""
        kanban = _make_kanban_with_data()
        snap_path = str(tmp_path / "cli_save.json")
        save_snapshot(kanban, snap_path)
        assert os.path.exists(snap_path), "Snapshot file should be created"


# ---------------------------------------------------------------------------
# TC-CLI-02: snapshot load restores state
# ---------------------------------------------------------------------------


class TestCLISnapshotLoad:

    def test_snapshot_load_restores_state(self, tmp_path):
        """TC-CLI-02: snapshot load restores kanban state."""
        from statekanban.snapshot import load_snapshot

        kanban = _make_kanban_with_data()
        snap_path = str(tmp_path / "cli_load.json")
        save_snapshot(kanban, snap_path)

        loaded = load_snapshot(snap_path)
        assert isinstance(loaded, StateKanban)

        orig_signals = list(kanban.fluid.read_signals())
        loaded_signals = list(loaded.fluid.read_signals())
        assert len(loaded_signals) == len(orig_signals)


# ---------------------------------------------------------------------------
# TC-CLI-03: snapshot list returns filenames
# ---------------------------------------------------------------------------


class TestCLISnapshotList:

    def test_snapshot_list_returns_filenames(self, tmp_path):
        """TC-CLI-03: snapshot list returns sorted filenames."""
        from statekanban.snapshot import list_snapshots

        kanban = _make_kanban_with_data()
        for name in ["b.json", "a.json", "c.json"]:
            save_snapshot(kanban, str(tmp_path / name))

        result = list_snapshots(str(tmp_path))
        assert len(result) == 3
        assert result == sorted(result)


# ---------------------------------------------------------------------------
# TC-CLI-04: snapshot delete removes file
# ---------------------------------------------------------------------------


class TestCLISnapshotDelete:

    def test_snapshot_delete_removes_file(self, tmp_path):
        """TC-CLI-04: snapshot delete removes the snapshot file."""
        from statekanban.snapshot import delete_snapshot

        kanban = _make_kanban_with_data()
        snap_path = str(tmp_path / "cli_delete.json")
        save_snapshot(kanban, snap_path)
        assert os.path.exists(snap_path)

        delete_snapshot(snap_path)
        assert not os.path.exists(snap_path)


# ---------------------------------------------------------------------------
# TC-CLI-05: CLI parser has snapshot subcommand
# ---------------------------------------------------------------------------


class TestCLIParserSnapshot:

    def test_parser_has_snapshot_subcommand(self):
        """TC-CLI-05: CLI parser accepts snapshot subcommand."""
        parser = build_parser()
        # Try parsing with snapshot subcommand
        args = parser.parse_args(["snapshot", "save", "test.json"])
        assert args.command == "snapshot"

    def test_parser_snapshot_save_args(self):
        """CLI parser recognizes snapshot save with path argument."""
        parser = build_parser()
        args = parser.parse_args(["snapshot", "save", "my_snapshot.json"])
        assert (
            hasattr(args, "subcommand")
            or hasattr(args, "path")
            or hasattr(args, "name")
        )


# ---------------------------------------------------------------------------
# TC-CLI-06: snapshot list on missing directory
# ---------------------------------------------------------------------------


class TestCLISnapshotListEdgeCases:

    def test_snapshot_list_missing_dir(self, tmp_path):
        """TC-CLI-06: snapshot list on missing directory returns empty list."""
        from statekanban.snapshot import list_snapshots

        missing_dir = str(tmp_path / "no_such_dir")
        result = list_snapshots(missing_dir)
        assert result == []
