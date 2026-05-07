"""Tests for ConvergenceDetector (R2).

TC-CD-001..006: Converged, not converged (veto), not converged (no intent),
check_all_pending, empty FluidZone, prior veto resolved.
"""

from __future__ import annotations

import pytest

from statekanban.core.kanban import (
    IntentSignal,
    SignalType,
    StateKanban,
    VetoSignal,
    make_signal_id,
    now_utc,
)
from statekanban.engine.convergence import ConvergenceCheckResult, ConvergenceDetector

# ---------------------------------------------------------------------------
# TC-CD-001: Converged (intent present, no veto in current round)
# ---------------------------------------------------------------------------


class TestConvergenceConverged:
    """TC-CD-001."""

    def test_converged_when_intent_no_veto(self, kanban, convergence_detector):
        sig = IntentSignal(
            signal_id=make_signal_id(),
            author_role="coder",
            target_id="task_root",
            payload={"action": "approve"},
            timestamp=now_utc(),
            round_number=2,
        )
        kanban.fluid.write_signal(sig)

        result = convergence_detector.check("task_root", 2)
        assert result.converged is True
        assert result.intent_count == 1
        assert result.veto_count == 0

    def test_converged_multiple_intents(self, kanban, convergence_detector):
        sig1 = IntentSignal(
            signal_id=make_signal_id(),
            author_role="coder",
            target_id="task_root",
            payload={},
            timestamp=now_utc(),
            round_number=1,
        )
        sig2 = IntentSignal(
            signal_id=make_signal_id(),
            author_role="reviewer",
            target_id="task_root",
            payload={},
            timestamp=now_utc(),
            round_number=1,
        )
        kanban.fluid.write_signal(sig1)
        kanban.fluid.write_signal(sig2)

        result = convergence_detector.check("task_root", 1)
        assert result.converged is True
        assert result.intent_count == 2
        assert result.veto_count == 0


# ---------------------------------------------------------------------------
# TC-CD-002: Not converged (veto in current round)
# ---------------------------------------------------------------------------


class TestConvergenceNotConvergedVeto:
    """TC-CD-002."""

    def test_not_converged_when_veto_exists(self, kanban, convergence_detector):
        intent = IntentSignal(
            signal_id=make_signal_id(),
            author_role="coder",
            target_id="task_root",
            payload={},
            timestamp=now_utc(),
            round_number=2,
        )
        veto = VetoSignal(
            signal_id=make_signal_id(),
            author_role="reviewer",
            target_id="task_root",
            payload={},
            timestamp=now_utc(),
            round_number=2,
            reason="bad",
        )
        kanban.fluid.write_signal(intent)
        kanban.fluid.write_signal(veto)

        result = convergence_detector.check("task_root", 2)
        assert result.converged is False
        assert result.intent_count == 1
        assert result.veto_count == 1


# ---------------------------------------------------------------------------
# TC-CD-003: Not converged (no intent in current round)
# ---------------------------------------------------------------------------


class TestConvergenceNotConvergedNoIntent:
    """TC-CD-003."""

    def test_not_converged_when_no_intent(self, kanban, convergence_detector):
        # Only a veto signal, no intent
        veto = VetoSignal(
            signal_id=make_signal_id(),
            author_role="reviewer",
            target_id="task_root",
            payload={},
            timestamp=now_utc(),
            round_number=2,
            reason="bad",
        )
        kanban.fluid.write_signal(veto)

        result = convergence_detector.check("task_root", 2)
        assert result.converged is False
        assert result.intent_count == 0
        assert result.veto_count == 1

    def test_not_converged_when_no_signals_at_all(self, kanban, convergence_detector):
        result = convergence_detector.check("nonexistent", 1)
        assert result.converged is False
        assert result.intent_count == 0


# ---------------------------------------------------------------------------
# TC-CD-004: check_all_pending with multiple targets
# ---------------------------------------------------------------------------


class TestConvergenceCheckAllPending:
    """TC-CD-004."""

    def test_multiple_targets_mixed(self, kanban, convergence_detector):
        # Target A: converged
        sig_a = IntentSignal(
            signal_id=make_signal_id(),
            author_role="coder",
            target_id="target_A",
            payload={},
            timestamp=now_utc(),
            round_number=1,
        )
        kanban.fluid.write_signal(sig_a)

        # Target B: not converged (has veto)
        sig_b_intent = IntentSignal(
            signal_id=make_signal_id(),
            author_role="coder",
            target_id="target_B",
            payload={},
            timestamp=now_utc(),
            round_number=1,
        )
        sig_b_veto = VetoSignal(
            signal_id=make_signal_id(),
            author_role="reviewer",
            target_id="target_B",
            payload={},
            timestamp=now_utc(),
            round_number=1,
            reason="bad",
        )
        kanban.fluid.write_signal(sig_b_intent)
        kanban.fluid.write_signal(sig_b_veto)

        results = convergence_detector.check_all_pending(1)
        assert "target_A" in results
        assert "target_B" in results
        assert results["target_A"].converged is True
        assert results["target_B"].converged is False


# ---------------------------------------------------------------------------
# TC-CD-005: Empty FluidZone
# ---------------------------------------------------------------------------


class TestConvergenceEmpty:
    """TC-CD-005."""

    def test_empty_fluid_zone(self, kanban, convergence_detector):
        results = convergence_detector.check_all_pending(1)
        assert results == {}


# ---------------------------------------------------------------------------
# TC-CD-006: Prior veto resolved
# ---------------------------------------------------------------------------


class TestConvergencePriorVetoResolved:
    """TC-CD-006: Veto in round 1, but not in round 2 -> converged."""

    def test_prior_veto_resolved(self, kanban, convergence_detector):
        # Round 1: intent + veto
        intent1 = IntentSignal(
            signal_id=make_signal_id(),
            author_role="coder",
            target_id="task_root",
            payload={},
            timestamp=now_utc(),
            round_number=1,
        )
        veto1 = VetoSignal(
            signal_id=make_signal_id(),
            author_role="reviewer",
            target_id="task_root",
            payload={},
            timestamp=now_utc(),
            round_number=1,
            reason="bad",
        )
        kanban.fluid.write_signal(intent1)
        kanban.fluid.write_signal(veto1)

        # Round 1 not converged
        result_r1 = convergence_detector.check("task_root", 1)
        assert result_r1.converged is False

        # Round 2: only intent, no veto -> converged
        intent2 = IntentSignal(
            signal_id=make_signal_id(),
            author_role="coder",
            target_id="task_root",
            payload={},
            timestamp=now_utc(),
            round_number=2,
        )
        kanban.fluid.write_signal(intent2)

        result_r2 = convergence_detector.check("task_root", 2)
        assert result_r2.converged is True
        assert result_r2.veto_count == 0


# ---------------------------------------------------------------------------
# ConvergenceCheckResult dataclass contract
# ---------------------------------------------------------------------------


class TestConvergenceCheckResultContract:
    """Verify all fields of ConvergenceCheckResult are populated."""

    def test_result_fields(self, kanban, convergence_detector):
        sig = IntentSignal(
            signal_id=make_signal_id(),
            author_role="coder",
            target_id="t1",
            payload={},
            timestamp=now_utc(),
            round_number=1,
        )
        kanban.fluid.write_signal(sig)

        result = convergence_detector.check("t1", 1)
        assert result.target_id == "t1"
        assert result.round_number == 1
        assert isinstance(result.converged, bool)
        assert isinstance(result.intent_count, int)
        assert isinstance(result.veto_count, int)
