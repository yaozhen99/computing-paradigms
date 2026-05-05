"""Tests for StateKanban facade: convergence, serialization, viewport registration."""

from __future__ import annotations

import json

import pytest

from statekanban.core.errors import SnapshotIntegrityError, ConvergenceTimeoutError
from statekanban.core.kanban import (
    ArtifactType,
    IntentSignal,
    SignalType,
    StateKanban,
    VetoSignal,
    ViewportSpec,
    make_signal_id,
    now_utc,
)


class TestStateKanbanConvergence:
    """TC-SK-001 ~ TC-SK-004: Convergence loop."""

    def test_immediate_agreement(self, kanban, make_intent):
        # TC-SK-001: Only INTENT, no VETO -> immediate convergence
        kanban.fluid.write_signal(make_intent(target_id="A"))
        result = kanban.run_convergence("A")
        assert result.converged is True
        assert result.rounds == 1
        assert result.forced_terminate is False

    def test_collision_resolved(self, kanban, make_intent, make_veto):
        # TC-SK-002: INTENT+VETO collision that gets resolved
        # After first collision round, clear the veto and run again
        kanban.fluid.write_signal(make_intent(target_id="A"))
        kanban.fluid.write_signal(make_veto(target_id="A"))
        # Simulate resolution: clear veto signals
        kanban.fluid.clear_signals("A", round_number_ge=0)
        # Re-add only intent
        kanban.fluid.write_signal(make_intent(target_id="A"))
        result = kanban.run_convergence("A")
        assert result.converged is True

    def test_forced_terminate_at_max_rounds(self, kanban, make_intent, make_veto):
        # TC-SK-003: Persistent INTENT+VETO -> forced terminate at 10 rounds
        kanban.fluid.write_signal(make_intent(target_id="A"))
        kanban.fluid.write_signal(make_veto(target_id="A"))
        result = kanban.run_convergence("A")
        assert result.converged is False
        assert result.forced_terminate is True
        assert result.rounds == 10

    def test_convergence_result_fields(self, kanban, make_intent):
        # TC-SK-004: All ConvergenceResult fields populated
        kanban.fluid.write_signal(make_intent(target_id="A"))
        result = kanban.run_convergence("A")
        assert result.target_id == "A"
        assert result.rounds >= 1
        assert isinstance(result.converged, bool)
        assert isinstance(result.forced_terminate, bool)
        assert isinstance(result.final_signals, list)


class TestStateKanbanViewport:
    """TC-SK-005 ~ TC-SK-006: Viewport registration."""

    def test_register_and_retrieve_viewport(self, kanban, coder_spec):
        # TC-SK-005
        kanban.register_viewport(coder_spec)
        spec = kanban.get_viewport_spec("coder")
        assert spec is not None
        assert spec.role == "coder"

    def test_retrieve_nonexistent_viewport(self, kanban):
        # TC-SK-006
        assert kanban.get_viewport_spec("nonexistent") is None


class TestStateKanbanSerialization:
    """TC-SK-007 ~ TC-SK-009: to_json / from_json."""

    def test_round_trip(self, kanban, make_intent, make_artifact):
        # TC-SK-007
        kanban.fluid.write_signal(make_intent(target_id="A"))
        kanban.crystal.append(make_artifact())
        kanban.register_viewport(ViewportSpec(
            role="coder",
            visible_signal_types=[SignalType.INTENT],
            visible_artifact_types=[ArtifactType.CODE],
            visible_target_patterns=["*"],
        ))
        kanban.audit.log("test", "tester", "act", {})

        data = kanban.to_json()
        restored = StateKanban.from_json(data)

        assert len(restored.fluid.read_signals()) == 1
        assert restored.crystal.latest_seq_no() == 1
        assert len(restored.audit.read_entries()) == 1
        assert restored.get_viewport_spec("coder") is not None

    def test_checksum_validation_pass(self, kanban):
        # TC-SK-008
        data = kanban.to_json()
        restored = StateKanban.from_json(data)
        assert restored is not None

    def test_checksum_validation_fail(self, kanban):
        # TC-SK-009
        data = kanban.to_json()
        # Tamper with the data but keep original checksum
        data["data"]["fluid"] = ["TAMPERED"]
        with pytest.raises(SnapshotIntegrityError):
            StateKanban.from_json(data)

    def test_from_json_without_checksum(self):
        # Edge case: data without checksum field should still reconstruct
        data = {
            "data": {
                "fluid": [],
                "crystal": {"artifacts": [], "next_seq_no": 1},
                "audit": {"entries": [], "next_entry_id": 1},
                "viewport_specs": {},
            },
        }
        kanban = StateKanban.from_json(data)
        assert kanban is not None