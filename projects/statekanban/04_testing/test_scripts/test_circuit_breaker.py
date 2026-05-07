"""Tests for CircuitBreaker (R2).

TC-CB-001..005: should_break true/false, report, custom max, property.
"""

from __future__ import annotations

import pytest

from statekanban.engine.circuit_breaker import CircuitBreaker
from statekanban.engine.result import EngineResult


# ---------------------------------------------------------------------------
# TC-CB-001: should_break True (round >= max)
# ---------------------------------------------------------------------------

class TestCircuitBreakerShouldBreak:
    """TC-CB-001."""

    def test_should_break_at_max_rounds(self, breaker):
        assert breaker.should_break(10) is True

    def test_should_break_above_max_rounds(self, breaker):
        assert breaker.should_break(11) is True

    def test_should_break_at_round_10(self, breaker):
        assert breaker.should_break(10) is True


# ---------------------------------------------------------------------------
# TC-CB-002: should_break False (round < max)
# ---------------------------------------------------------------------------

class TestCircuitBreakerShouldNotBreak:
    """TC-CB-002."""

    def test_should_not_break_below_max(self, breaker):
        assert breaker.should_break(5) is False

    def test_should_not_break_at_round_1(self, breaker):
        assert breaker.should_break(1) is False

    def test_should_not_break_at_round_0(self, breaker):
        assert breaker.should_break(0) is False

    def test_should_not_break_at_round_9(self, breaker):
        assert breaker.should_break(9) is False


# ---------------------------------------------------------------------------
# TC-CB-003: report
# ---------------------------------------------------------------------------

class TestCircuitBreakerReport:
    """TC-CB-003."""

    def test_report_returns_engine_result(self, breaker):
        result = breaker.report(10)
        assert isinstance(result, EngineResult)
        assert result.converged is False
        assert result.forced_terminate is True
        assert result.total_rounds == 10

    def test_report_has_empty_signal_summary(self, breaker):
        result = breaker.report(10)
        assert result.signal_summary == {}

    def test_report_has_zero_error_count(self, breaker):
        result = breaker.report(10)
        assert result.error_count == 0


# ---------------------------------------------------------------------------
# TC-CB-004: Custom max_rounds
# ---------------------------------------------------------------------------

class TestCircuitBreakerCustomMax:
    """TC-CB-004."""

    def test_custom_max_rounds_3(self, breaker_3):
        assert breaker_3.should_break(2) is False
        assert breaker_3.should_break(3) is True

    def test_custom_max_rounds_1(self):
        cb = CircuitBreaker(max_rounds=1)
        assert cb.should_break(0) is False
        assert cb.should_break(1) is True

    def test_custom_max_rounds_report(self, breaker_3):
        result = breaker_3.report(3)
        assert result.total_rounds == 3
        assert result.forced_terminate is True


# ---------------------------------------------------------------------------
# TC-CB-005: max_rounds property
# ---------------------------------------------------------------------------

class TestCircuitBreakerProperty:
    """TC-CB-005."""

    def test_max_rounds_property_default(self, breaker):
        assert breaker.max_rounds == 10

    def test_max_rounds_property_custom(self, breaker_3):
        assert breaker_3.max_rounds == 3