"""Tests for ViewportSlicer: filtering, priority, token budget."""

from __future__ import annotations

import pytest

from statekanban.core.errors import InvalidViewportSpecError, SliceOverflowError
from statekanban.core.kanban import (
    ArtifactType,
    SignalType,
    make_signal_id,
    now_utc,
    compute_checksum,
    Artifact,
    Signal,
    IntentSignal,
    VetoSignal,
    ViewportSpec,
)
from statekanban.core.viewport import ViewportSlicer


class TestViewportSlicerFilter:
    """TC-VS-001 ~ TC-VS-004: Filtering by spec."""

    def test_filter_signals_by_visible_types(self, kanban, slicer):
        # TC-VS-001: coder spec only allows INTENT and ERROR, not VETO
        kanban.fluid.write_signal(IntentSignal(
            signal_id=make_signal_id(), author_role="coder",
            target_id="A", payload={}, timestamp=now_utc(), round_number=0,
        ))
        kanban.fluid.write_signal(VetoSignal(
            signal_id=make_signal_id(), author_role="reviewer",
            target_id="A", payload={}, timestamp=now_utc(), round_number=0,
        ))
        slice = slicer.slice("coder")
        veto_in_slice = any(s.signal_type == SignalType.VETO for s in slice.signals)
        assert veto_in_slice is False

    def test_filter_artifacts_by_visible_types(self, kanban, slicer):
        # TC-VS-002: coder spec allows CODE and CONFIG, not DOC
        kanban.crystal.append(Artifact(
            seq_no=0, artifact_type=ArtifactType.CODE,
            path="x.py", content="x=1", checksum=compute_checksum("x=1"),
            author_role="coder", created_at=now_utc(),
        ))
        kanban.crystal.append(Artifact(
            seq_no=0, artifact_type=ArtifactType.DOC,
            path="x.md", content="# doc", checksum=compute_checksum("# doc"),
            author_role="coder", created_at=now_utc(),
        ))
        slice = slicer.slice("coder")
        doc_in_slice = any(a.artifact_type == ArtifactType.DOC for a in slice.artifacts)
        assert doc_in_slice is False

    def test_filter_by_target_patterns(self, kanban):
        # TC-VS-003
        spec = ViewportSpec(
            role="coder",
            visible_signal_types=[SignalType.INTENT],
            visible_artifact_types=[ArtifactType.CODE],
            visible_target_patterns=["artifact_*"],
            max_tokens=2000,
        )
        kanban.register_viewport(spec)
        slicer = ViewportSlicer(kanban, {"coder": spec})

        kanban.fluid.write_signal(IntentSignal(
            signal_id=make_signal_id(), author_role="coder",
            target_id="artifact_A", payload={}, timestamp=now_utc(), round_number=0,
        ))
        kanban.fluid.write_signal(IntentSignal(
            signal_id=make_signal_id(), author_role="coder",
            target_id="task_root", payload={}, timestamp=now_utc(), round_number=0,
        ))
        slice = slicer.slice("coder")
        # Only "artifact_*" matches; "task_root" does not
        targets = {s.target_id for s in slice.signals}
        assert "task_root" not in targets

    def test_empty_target_patterns_match_all(self, kanban):
        # TC-VS-004
        spec = ViewportSpec(
            role="coder",
            visible_signal_types=[SignalType.INTENT],
            visible_artifact_types=[ArtifactType.CODE],
            visible_target_patterns=[],  # empty -> match all
            max_tokens=2000,
        )
        kanban.register_viewport(spec)
        slicer = ViewportSlicer(kanban, {"coder": spec})

        kanban.fluid.write_signal(IntentSignal(
            signal_id=make_signal_id(), author_role="coder",
            target_id="anything", payload={}, timestamp=now_utc(), round_number=0,
        ))
        slice = slicer.slice("coder")
        assert len(slice.signals) == 1


class TestViewportSlicerPriority:
    """TC-VS-005 ~ TC-VS-006: Priority ordering."""

    def test_role_relevant_first(self, kanban, slicer):
        # TC-VS-005
        kanban.fluid.write_signal(IntentSignal(
            signal_id=make_signal_id(), author_role="other_role",
            target_id="A", payload={}, timestamp=now_utc(), round_number=0,
        ))
        kanban.fluid.write_signal(IntentSignal(
            signal_id=make_signal_id(), author_role="coder",
            target_id="coder_A", payload={}, timestamp=now_utc(), round_number=0,
        ))
        slice = slicer.slice("coder")
        if len(slice.signals) >= 2:
            # role-relevant (coder-authored or coder-targeted) should be first
            assert slice.signals[0].author_role == "coder" or \
                   slice.signals[0].target_id.startswith("coder")

    def test_own_artifacts_first(self, kanban, slicer):
        # TC-VS-006
        kanban.crystal.append(Artifact(
            seq_no=0, artifact_type=ArtifactType.CODE,
            path="other.py", content="x=1", checksum=compute_checksum("x=1"),
            author_role="reviewer", created_at=now_utc(),
        ))
        kanban.crystal.append(Artifact(
            seq_no=0, artifact_type=ArtifactType.CODE,
            path="my.py", content="y=2", checksum=compute_checksum("y=2"),
            author_role="coder", created_at=now_utc(),
        ))
        slice = slicer.slice("coder")
        if len(slice.artifacts) >= 2:
            assert slice.artifacts[0].author_role == "coder"


class TestViewportSlicerBudget:
    """TC-VS-007 ~ TC-VS-009: Token budget truncation."""

    def test_budget_respected(self, kanban):
        # TC-VS-007
        spec = ViewportSpec(
            role="coder",
            visible_signal_types=[SignalType.INTENT],
            visible_artifact_types=[ArtifactType.CODE],
            visible_target_patterns=["*"],
            max_tokens=100,
        )
        kanban.register_viewport(spec)
        slicer = ViewportSlicer(kanban, {"coder": spec})

        # Write signals with small payloads
        for i in range(3):
            kanban.fluid.write_signal(IntentSignal(
                signal_id=make_signal_id(), author_role="coder",
                target_id=f"A_{i}", payload={"data": "short"},
                timestamp=now_utc(), round_number=0,
            ))
        slice = slicer.slice("coder")
        assert slice.token_estimate <= 100

    def test_items_excluded_on_overflow(self, kanban):
        # TC-VS-008
        spec = ViewportSpec(
            role="coder",
            visible_signal_types=[SignalType.INTENT],
            visible_artifact_types=[ArtifactType.CODE],
            visible_target_patterns=["*"],
            max_tokens=200,  # moderate budget
        )
        kanban.register_viewport(spec)
        slicer = ViewportSlicer(kanban, {"coder": spec})

        # Write many signals to exceed budget
        for i in range(20):
            kanban.fluid.write_signal(IntentSignal(
                signal_id=make_signal_id(), author_role="coder",
                target_id=f"A_{i}", payload={"data": f"payload text that is somewhat long number {i}"},
                timestamp=now_utc(), round_number=0,
            ))
        slice = slicer.slice("coder")
        # Some items must be excluded since budget is moderate and there are many items
        assert slice.items_excluded > 0

    def test_slice_overflow_error(self, kanban):
        # TC-VS-009
        spec = ViewportSpec(
            role="coder",
            visible_signal_types=[SignalType.INTENT],
            visible_artifact_types=[ArtifactType.CODE],
            visible_target_patterns=["*"],
            max_tokens=1,  # Impossibly small budget
        )
        kanban.register_viewport(spec)
        slicer = ViewportSlicer(kanban, {"coder": spec})

        # Write a signal that exceeds 1 token budget
        kanban.fluid.write_signal(IntentSignal(
            signal_id=make_signal_id(), author_role="coder",
            target_id="A", payload={"data": "long"},
            timestamp=now_utc(), round_number=0,
        ))
        with pytest.raises(SliceOverflowError):
            slicer.slice("coder")


class TestViewportSlicerErrors:
    """TC-VS-010: InvalidViewportSpecError."""

    def test_no_spec_for_role(self, kanban, slicer):
        # TC-VS-010
        with pytest.raises(InvalidViewportSpecError):
            slicer.slice("nonexistent_role")


class TestViewportSlicerEstimateTokens:
    """TC-VS-011: Token estimation."""

    def test_estimate_tokens_heuristic(self, slicer):
        # TC-VS-011
        text = "hello world"  # 11 chars
        tokens = slicer.estimate_tokens(text)
        assert tokens == max(1, 11 // 4)

    def test_estimate_tokens_minimum(self, slicer):
        # Edge: very short text still returns at least 1
        assert slicer.estimate_tokens("") == 1


class TestViewportSlicerMetadata:
    """TC-VS-012: Slice log populated."""

    def test_slice_log_has_budget(self, kanban, slicer):
        # TC-VS-012
        slice = slicer.slice("coder")
        assert "budget" in slice.slice_log
        assert "total_signals_available" in slice.slice_log


class TestViewportIsolation:
    """TC-VS-011, TC-VS-012 (R2): Viewport isolation between roles."""

    def test_coder_cannot_see_veto_signals(self, kanban, slicer):
        """TC-VS-011: Coder viewport excludes Veto signals."""
        kanban.fluid.write_signal(IntentSignal(
            signal_id=make_signal_id(), author_role="coder",
            target_id="artifact_1", payload={}, timestamp=now_utc(), round_number=1,
        ))
        kanban.fluid.write_signal(VetoSignal(
            signal_id=make_signal_id(), author_role="reviewer",
            target_id="artifact_1", payload={}, timestamp=now_utc(), round_number=1,
            reason="missing error handling",
        ))
        coder_slice = slicer.slice("coder")
        veto_in_coder = any(s.signal_type == SignalType.VETO for s in coder_slice.signals)
        assert veto_in_coder is False, "Coder should not see Veto signals"

    def test_reviewer_can_see_veto_signals(self, kanban, slicer):
        """TC-VS-012: Reviewer viewport includes Veto signals."""
        kanban.fluid.write_signal(IntentSignal(
            signal_id=make_signal_id(), author_role="coder",
            target_id="artifact_1", payload={}, timestamp=now_utc(), round_number=1,
        ))
        kanban.fluid.write_signal(VetoSignal(
            signal_id=make_signal_id(), author_role="reviewer",
            target_id="artifact_1", payload={}, timestamp=now_utc(), round_number=1,
            reason="bad",
        ))
        reviewer_slice = slicer.slice("reviewer")
        veto_in_reviewer = any(s.signal_type == SignalType.VETO for s in reviewer_slice.signals)
        assert veto_in_reviewer is True, "Reviewer should see Veto signals"

    def test_coder_can_see_error_signals(self, kanban, slicer):
        """Coder can see Error signals (e.g., from valve failures)."""
        from statekanban.core.kanban import ErrorSignal
        kanban.fluid.write_signal(ErrorSignal(
            signal_id=make_signal_id(), author_role="OutputValve",
            target_id="output.py", payload={}, timestamp=now_utc(), round_number=1,
            error_code="SK_OV_001", error_detail="syntax error",
        ))
        coder_slice = slicer.slice("coder")
        error_in_coder = any(s.signal_type == SignalType.ERROR for s in coder_slice.signals)
        assert error_in_coder is True, "Coder should see Error signals"

    def test_tester_cannot_see_veto_signals(self, kanban, slicer):
        """Tester viewport excludes Veto signals."""
        kanban.fluid.write_signal(VetoSignal(
            signal_id=make_signal_id(), author_role="reviewer",
            target_id="artifact_1", payload={}, timestamp=now_utc(), round_number=1,
            reason="bad",
        ))
        tester_slice = slicer.slice("tester")
        veto_in_tester = any(s.signal_type == SignalType.VETO for s in tester_slice.signals)
        assert veto_in_tester is False, "Tester should not see Veto signals"