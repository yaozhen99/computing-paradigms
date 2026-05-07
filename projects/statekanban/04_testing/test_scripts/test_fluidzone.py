"""Tests for FluidZone: signal write, read, collision, clear."""

from __future__ import annotations

import pytest

from statekanban.core.errors import InvalidSignalError
from statekanban.core.kanban import (
    IntentSignal,
    SignalType,
    make_signal_id,
    now_utc,
)


class TestFluidZoneWrite:
    """TC-FZ-001 ~ TC-FZ-007: Signal write and validation."""

    def test_write_intent_signal(self, fluid, make_intent):
        # TC-FZ-001
        s = make_intent()
        fluid.write_signal(s)
        signals = fluid.read_signals()
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.INTENT

    def test_write_veto_signal_with_reason(self, fluid, make_veto):
        # TC-FZ-002
        s = make_veto(reason="critical bug")
        fluid.write_signal(s)
        signals = fluid.read_signals()
        assert len(signals) == 1
        assert signals[0].reason == "critical bug"

    def test_write_error_signal(self, fluid, make_error_signal):
        # TC-FZ-003
        s = make_error_signal()
        fluid.write_signal(s)
        signals = fluid.read_signals()
        assert len(signals) == 1
        assert signals[0].error_code == "SK_OV_001"

    def test_empty_signal_id_rejected(self, fluid):
        # TC-FZ-004
        with pytest.raises(InvalidSignalError):
            fluid.write_signal(IntentSignal(
                signal_id="",
                author_role="coder",
                target_id="t",
                payload={},
                timestamp=now_utc(),
                round_number=0,
            ))

    def test_empty_author_role_rejected(self, fluid):
        # TC-FZ-005
        with pytest.raises(InvalidSignalError):
            fluid.write_signal(IntentSignal(
                signal_id=make_signal_id(),
                author_role="",
                target_id="t",
                payload={},
                timestamp=now_utc(),
                round_number=0,
            ))

    def test_empty_target_id_rejected(self, fluid):
        # TC-FZ-006
        with pytest.raises(InvalidSignalError):
            fluid.write_signal(IntentSignal(
                signal_id=make_signal_id(),
                author_role="coder",
                target_id="",
                payload={},
                timestamp=now_utc(),
                round_number=0,
            ))

    def test_invalid_signal_type_rejected(self):
        # TC-FZ-007
        with pytest.raises(ValueError):
            SignalType("UNKNOWN_TYPE")


class TestFluidZoneRead:
    """TC-FZ-008 ~ TC-FZ-013: Signal read and filtering."""

    def test_read_all_signals(self, fluid, make_intent, make_veto):
        # TC-FZ-008
        fluid.write_signal(make_intent(target_id="A"))
        fluid.write_signal(make_veto(target_id="A"))
        signals = fluid.read_signals()
        assert len(signals) == 2

    def test_read_by_target_id(self, fluid, make_intent):
        # TC-FZ-009
        fluid.write_signal(make_intent(target_id="A"))
        fluid.write_signal(make_intent(target_id="B"))
        signals = fluid.read_signals(target_id="A")
        assert len(signals) == 1
        assert signals[0].target_id == "A"

    def test_read_by_signal_type(self, fluid, make_intent, make_veto):
        # TC-FZ-010
        fluid.write_signal(make_intent(target_id="A"))
        fluid.write_signal(make_veto(target_id="A"))
        signals = fluid.read_signals(signal_type=SignalType.VETO)
        assert all(s.signal_type == SignalType.VETO for s in signals)

    def test_read_by_author_role(self, fluid, make_intent):
        # TC-FZ-011
        fluid.write_signal(make_intent(author_role="coder"))
        fluid.write_signal(make_intent(author_role="reviewer"))
        signals = fluid.read_signals(author_role="coder")
        assert all(s.author_role == "coder" for s in signals)

    def test_read_with_combined_filters(self, fluid, make_intent, make_veto):
        # TC-FZ-012
        fluid.write_signal(make_intent(target_id="A", author_role="coder"))
        fluid.write_signal(make_veto(target_id="A", author_role="reviewer"))
        fluid.write_signal(make_intent(target_id="B", author_role="coder"))
        signals = fluid.read_signals(target_id="A", signal_type=SignalType.INTENT)
        assert len(signals) == 1

    def test_read_empty_zone(self, fluid):
        # TC-FZ-013
        signals = fluid.read_signals()
        assert signals == []


class TestFluidZoneCollision:
    """TC-FZ-014 ~ TC-FZ-017: Collision detection."""

    def test_no_collision_intent_only(self, fluid, make_intent):
        # TC-FZ-014
        fluid.write_signal(make_intent(target_id="A"))
        result = fluid.detect_collision("A")
        assert result.has_collision is False
        assert result.is_resolved is True

    def test_intent_veto_collision(self, fluid, make_intent, make_veto):
        # TC-FZ-015
        fluid.write_signal(make_intent(target_id="A"))
        fluid.write_signal(make_veto(target_id="A"))
        result = fluid.detect_collision("A")
        assert result.has_collision is True
        assert result.is_resolved is False

    def test_no_signals_for_target(self, fluid):
        # TC-FZ-016
        result = fluid.detect_collision("nonexistent")
        assert result.has_collision is False
        assert result.is_resolved is True

    def test_veto_only_no_collision(self, fluid, make_veto):
        # TC-FZ-017
        fluid.write_signal(make_veto(target_id="A"))
        result = fluid.detect_collision("A")
        assert result.has_collision is False


class TestFluidZoneClear:
    """TC-FZ-018 ~ TC-FZ-019: Signal clearing."""

    def test_clear_by_round(self, fluid, make_intent):
        # TC-FZ-018
        # Use different author_roles so the TOCTOU-fix (index overwrite)
        # does not collapse signals into one entry.
        fluid.write_signal(make_intent(target_id="A", round_number=0, author_role="coder"))
        fluid.write_signal(make_intent(target_id="A", round_number=1, author_role="reviewer"))
        fluid.write_signal(make_intent(target_id="A", round_number=2, author_role="tester"))
        fluid.clear_signals("A", round_number_ge=2)
        signals = fluid.read_signals(target_id="A")
        rounds = {s.round_number for s in signals}
        assert 2 not in rounds
        assert 0 in rounds and 1 in rounds

    def test_clear_rebuilds_index(self, fluid, make_intent, make_veto):
        # TC-FZ-019
        fluid.write_signal(make_intent(target_id="A", round_number=0))
        fluid.write_signal(make_veto(target_id="A", round_number=1))
        fluid.write_signal(make_intent(target_id="B", round_number=1))
        fluid.clear_signals("A", round_number_ge=1)
        signals_a = fluid.read_signals(target_id="A")
        assert len(signals_a) == 1


class TestFluidZoneOverwrite:
    """TC-FZ-020: Same key overwritten in index."""

    def test_same_key_overwrites_index(self, fluid, make_intent):
        # TC-FZ-020: Same (target_id, signal_type, author_role) overwrites in index
        # After TOCTOU fix (RR-001), the stale entry is removed from the backing
        # list, so only the latest signal remains.
        sid1 = make_signal_id()
        sid2 = make_signal_id()
        s1 = make_intent(target_id="A", author_role="coder", signal_id=sid1)
        s2 = make_intent(target_id="A", author_role="coder", signal_id=sid2)
        fluid.write_signal(s1)
        fluid.write_signal(s2)
        # Only the latest signal should be in the list (stale removed)
        signals = fluid.read_signals(target_id="A")
        assert len(signals) == 1
        # The remaining one is the latest write
        assert signals[0].signal_id == sid2