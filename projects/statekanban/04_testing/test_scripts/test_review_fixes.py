"""Tests for Round 1 Review Fixes (R2).

TC-RR-001..005: TOCTOU fix (index-based replacement), error code
derivation (type-derived map), stale signal removal.
"""

from __future__ import annotations

import pytest

from statekanban.core.kanban import (
    ErrorSignal,
    IntentSignal,
    LLMMessage,
    LLMResponse,
    SignalType,
    StateKanban,
    VetoSignal,
    make_signal_id,
    now_utc,
)
from statekanban.core.valve import OutputValve

# ---------------------------------------------------------------------------
# TC-RR-001: TOCTOU -- same key written twice, no duplicates in backing list
# ---------------------------------------------------------------------------


class TestTOCTOU:
    """RR-001: Write same key (target,type,author) twice -> only latest in list."""

    def test_same_key_overwrite_no_duplicates(self, kanban):
        """TC-RR-001: Two signals with same (target,type,author) -> no duplicates."""
        sig1 = IntentSignal(
            signal_id=make_signal_id(),
            author_role="coder",
            target_id="task_root",
            payload={"version": 1},
            timestamp=now_utc(),
            round_number=1,
        )
        sig2 = IntentSignal(
            signal_id=make_signal_id(),
            author_role="coder",
            target_id="task_root",
            payload={"version": 2},
            timestamp=now_utc(),
            round_number=1,
        )

        kanban.fluid.write_signal(sig1)
        kanban.fluid.write_signal(sig2)

        # Only one signal should be in the backing list for this key
        signals = kanban.fluid.read_signals(
            target_id="task_root",
            signal_type=SignalType.INTENT,
            author_role="coder",
        )
        assert len(signals) == 1
        assert signals[0].payload["version"] == 2

    def test_rapid_overwrite_preserves_latest(self, kanban):
        """TC-RR-002: Read after overwrite returns only latest signal."""
        for i in range(10):
            sig = IntentSignal(
                signal_id=make_signal_id(),
                author_role="coder",
                target_id="task_root",
                payload={"version": i},
                timestamp=now_utc(),
                round_number=1,
            )
            kanban.fluid.write_signal(sig)

        signals = kanban.fluid.read_signals(
            target_id="task_root",
            signal_type=SignalType.INTENT,
            author_role="coder",
        )
        assert len(signals) == 1
        assert signals[0].payload["version"] == 9

    def test_different_authors_not_overwritten(self, kanban):
        """Same target+type but different author -> both signals exist."""
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

        signals = kanban.fluid.read_signals(
            target_id="task_root", signal_type=SignalType.INTENT
        )
        assert len(signals) == 2


# ---------------------------------------------------------------------------
# TC-RR-003: Error code derivation (type-derived map, not string matching)
# ---------------------------------------------------------------------------


class TestErrorCodeDerivation:
    """RR-002: OutputValve uses type-derived _VALIDATOR_ERROR_CODES dict."""

    def test_syntax_check_error_code_is_SK_OV_001(self, kanban):
        """TC-RR-003: Invalid syntax -> ErrorSignal with SK_OV_001."""
        from statekanban.core.errors import SyntaxCheckError

        error = SyntaxCheckError("invalid syntax")
        assert error.error_code == "SK_OV_001"

    def test_type_check_error_code_is_SK_OV_002(self):
        """Type check error -> SK_OV_002."""
        from statekanban.core.errors import TypeCheckError

        error = TypeCheckError("type mismatch")
        assert error.error_code == "SK_OV_002"

    def test_atomic_write_error_code_is_SK_OV_004(self):
        """TC-RR-004: I/O failure -> SK_OV_004."""
        from statekanban.core.errors import AtomicWriteError

        error = AtomicWriteError("permission denied")
        assert error.error_code == "SK_OV_004"

    def test_human_gate_rejected_error_code_is_SK_OV_005(self):
        """Human gate rejected -> SK_OV_005."""
        from statekanban.core.errors import HumanGateRejectedError

        error = HumanGateRejectedError("human rejected")
        assert error.error_code == "SK_OV_005"

    def test_error_codes_are_class_level_constants(self):
        """Error codes are defined at class level, not derived from class names."""
        from statekanban.core.errors import (
            SyntaxCheckError,
            TypeCheckError,
            TestExecutionError,
            AtomicWriteError,
            HumanGateRejectedError,
        )

        # Verify that error_code is a class attribute (not computed from __class__.__name__)
        assert SyntaxCheckError.error_code == "SK_OV_001"
        assert TypeCheckError.error_code == "SK_OV_002"
        assert TestExecutionError.error_code == "SK_OV_003"
        assert AtomicWriteError.error_code == "SK_OV_004"
        assert HumanGateRejectedError.error_code == "SK_OV_005"

    def test_valve_error_code_map_matches_class_constants(self, kanban):
        """TC-RR-003: OutputValve._VALIDATOR_ERROR_CODES matches error class constants."""
        valve = OutputValve(kanban=kanban)
        from statekanban.core.errors import (
            SyntaxCheckError,
            TypeCheckError,
            TestExecutionError,
            AtomicWriteError,
            HumanGateRejectedError,
        )

        assert (
            valve._VALIDATOR_ERROR_CODES["SyntaxValidator"]
            == SyntaxCheckError.error_code
        )
        assert (
            valve._VALIDATOR_ERROR_CODES["TypeValidator"] == TypeCheckError.error_code
        )
        assert (
            valve._VALIDATOR_ERROR_CODES["TestValidator"]
            == TestExecutionError.error_code
        )
        assert (
            valve._VALIDATOR_ERROR_CODES["AtomicWrite"] == AtomicWriteError.error_code
        )
        assert (
            valve._VALIDATOR_ERROR_CODES["HumanGate"]
            == HumanGateRejectedError.error_code
        )


# ---------------------------------------------------------------------------
# TC-RR-005: Stale signal removal
# ---------------------------------------------------------------------------


class TestStaleSignalRemoval:
    """RR-003: FluidZone.write_signal removes stale entry before adding new."""

    def test_overwrite_removes_stale_from_backing_list(self, kanban):
        """TC-RR-005: Overwriting same key removes old signal from list."""
        sig1 = IntentSignal(
            signal_id=make_signal_id(),
            author_role="coder",
            target_id="task_root",
            payload={"version": "old"},
            timestamp=now_utc(),
            round_number=1,
        )
        kanban.fluid.write_signal(sig1)

        # Verify first signal is in the list
        all_before = kanban.fluid.read_signals()
        assert len(all_before) == 1

        sig2 = IntentSignal(
            signal_id=make_signal_id(),
            author_role="coder",
            target_id="task_root",
            payload={"version": "new"},
            timestamp=now_utc(),
            round_number=1,
        )
        kanban.fluid.write_signal(sig2)

        # After overwrite, still only 1 signal in the list
        all_after = kanban.fluid.read_signals()
        assert len(all_after) == 1
        assert all_after[0].payload["version"] == "new"

    def test_overwrite_different_targets_preserves_others(self, kanban):
        """Overwriting one target does not affect other targets."""
        sig_a1 = IntentSignal(
            signal_id=make_signal_id(),
            author_role="coder",
            target_id="target_A",
            payload={},
            timestamp=now_utc(),
            round_number=1,
        )
        sig_b1 = IntentSignal(
            signal_id=make_signal_id(),
            author_role="coder",
            target_id="target_B",
            payload={},
            timestamp=now_utc(),
            round_number=1,
        )
        kanban.fluid.write_signal(sig_a1)
        kanban.fluid.write_signal(sig_b1)

        # Overwrite target_A
        sig_a2 = IntentSignal(
            signal_id=make_signal_id(),
            author_role="coder",
            target_id="target_A",
            payload={"updated": True},
            timestamp=now_utc(),
            round_number=2,
        )
        kanban.fluid.write_signal(sig_a2)

        # target_B should still be there
        signals_b = kanban.fluid.read_signals(target_id="target_B")
        assert len(signals_b) == 1

        # target_A should have the updated signal
        signals_a = kanban.fluid.read_signals(target_id="target_A")
        assert len(signals_a) == 1
        assert signals_a[0].payload.get("updated") is True
