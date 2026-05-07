"""Tests for CrystalZone and AuditZone."""

from __future__ import annotations

import pytest

from statekanban.core.errors import ArtifactConflictError
from statekanban.core.kanban import (
    Artifact,
    ArtifactType,
    AuditEntry,
    CrystalZone,
    AuditZone,
    compute_checksum,
    make_signal_id,
    now_utc,
)


class TestCrystalZoneAppend:
    """TC-CZ-001 ~ TC-CZ-004: CrystalZone append operations."""

    def test_auto_assign_seq_no(self, crystal, make_artifact):
        # TC-CZ-001
        art = make_artifact(seq_no=0)
        assigned = crystal.append(art)
        assert assigned == 1

    def test_multiple_auto_assign(self, crystal, make_artifact):
        # TC-CZ-002
        a1 = crystal.append(make_artifact(seq_no=0))
        a2 = crystal.append(make_artifact(seq_no=0))
        a3 = crystal.append(make_artifact(seq_no=0))
        assert [a1, a2, a3] == [1, 2, 3]

    def test_explicit_seq_no(self, crystal, make_artifact):
        # TC-CZ-003
        assigned = crystal.append(make_artifact(seq_no=5))
        assert assigned == 5

    def test_duplicate_seq_no_raises(self, crystal, make_artifact):
        # TC-CZ-004
        crystal.append(make_artifact(seq_no=1))
        with pytest.raises(ArtifactConflictError):
            crystal.append(make_artifact(seq_no=1))


class TestCrystalZoneRead:
    """TC-CZ-005 ~ TC-CZ-011: CrystalZone read operations."""

    def test_read_by_seq_no(self, crystal, make_artifact):
        # TC-CZ-005
        crystal.append(make_artifact(content="hello", seq_no=0))
        art = crystal.read_artifact(1)
        assert art is not None
        assert art.content == "hello"

    def test_read_nonexistent_seq_no(self, crystal):
        # TC-CZ-006
        assert crystal.read_artifact(999) is None

    def test_read_all_artifacts(self, crystal, make_artifact):
        # TC-CZ-007
        crystal.append(make_artifact(content="a", seq_no=0))
        crystal.append(make_artifact(content="b", seq_no=0))
        arts = crystal.read_artifacts()
        assert len(arts) == 2

    def test_filter_by_artifact_type(self, crystal, make_artifact):
        # TC-CZ-008
        crystal.append(make_artifact(artifact_type=ArtifactType.CODE, seq_no=0))
        crystal.append(make_artifact(artifact_type=ArtifactType.CONFIG, seq_no=0))
        code_arts = crystal.read_artifacts(artifact_type=ArtifactType.CODE)
        assert all(a.artifact_type == ArtifactType.CODE for a in code_arts)

    def test_filter_by_author_role(self, crystal, make_artifact):
        # TC-CZ-009
        crystal.append(make_artifact(author_role="coder", seq_no=0))
        crystal.append(make_artifact(author_role="reviewer", seq_no=0))
        coder_arts = crystal.read_artifacts(author_role="coder")
        assert all(a.author_role == "coder" for a in coder_arts)

    def test_latest_seq_no_empty(self, crystal):
        # TC-CZ-010
        assert crystal.latest_seq_no() == 0

    def test_latest_seq_no_after_appends(self, crystal, make_artifact):
        # TC-CZ-011
        crystal.append(make_artifact(seq_no=0))
        crystal.append(make_artifact(seq_no=0))
        crystal.append(make_artifact(seq_no=0))
        assert crystal.latest_seq_no() == 3


class TestCrystalZoneImmutable:
    """TC-CZ-012 ~ TC-CZ-013: Append-only invariant."""

    def test_no_update_method(self):
        # TC-CZ-012
        assert not hasattr(CrystalZone, "update")

    def test_no_delete_method(self):
        # TC-CZ-013
        assert not hasattr(CrystalZone, "delete")


class TestAuditZone:
    """TC-AZ-001 ~ TC-AZ-007: AuditZone operations."""

    def test_log_entry(self, audit):
        # TC-AZ-001
        entry_id = audit.log("tool_call", "ToolRegistry", "dispatch", {"tool": "x"})
        assert entry_id == 1

    def test_multiple_log_entries(self, audit):
        # TC-AZ-002
        id1 = audit.log("event_a", "actor1", "act", {})
        id2 = audit.log("event_b", "actor2", "act", {})
        id3 = audit.log("event_c", "actor3", "act", {})
        assert [id1, id2, id3] == [1, 2, 3]

    def test_read_all_entries(self, audit):
        # TC-AZ-003
        audit.log("event1", "actor1", "act1", {})
        audit.log("event2", "actor2", "act2", {})
        entries = audit.read_entries()
        assert len(entries) == 2

    def test_filter_by_event_type(self, audit):
        # TC-AZ-004
        audit.log("tool_call", "TR", "dispatch", {})
        audit.log("signal_write", "Coder", "write", {})
        entries = audit.read_entries(event_type="tool_call")
        assert len(entries) == 1
        assert entries[0].event_type == "tool_call"

    def test_filter_by_actor(self, audit):
        # TC-AZ-005
        audit.log("event", "ToolRegistry", "act", {})
        audit.log("event", "Coder", "act", {})
        entries = audit.read_entries(actor="ToolRegistry")
        assert len(entries) == 1

    def test_filter_by_since_entry_id(self, audit):
        # TC-AZ-006
        audit.log("e1", "a", "act", {})
        audit.log("e2", "a", "act", {})
        audit.log("e3", "a", "act", {})
        entries = audit.read_entries(since_entry_id=2)
        assert all(e.entry_id > 2 for e in entries)

    def test_read_empty_zone(self, audit):
        # TC-AZ-007
        entries = audit.read_entries()
        assert entries == []
