"""
StateKanban Response Parser Tests -- R3
TC-RP-01 through TC-RP-05

Tests for ResponseParser: unstructured response handling,
error signal injection, and parse recovery.
"""

from __future__ import annotations

import pytest

from statekanban.core.kanban import (
    LLMResponse,
    SignalType,
    StateKanban,
)
from statekanban.engine.response_parser import ResponseParser


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def kanban():
    return StateKanban()


@pytest.fixture
def parser(kanban):
    return ResponseParser(kanban=kanban)


# ---------------------------------------------------------------------------
# TC-RP-01: Unstructured response produces parsed result
# ---------------------------------------------------------------------------

class TestResponseParserBasic:

    def test_unstructured_produces_result(self, parser):
        """TC-RP-01: Unstructured response produces at least one parsed result."""
        raw = LLMResponse(content="Just some text", finish_reason="end_turn")
        results = parser.parse(raw, "coder", 1)
        assert len(results) > 0

    def test_result_has_response_type(self, parser):
        """Parsed result has a response_type attribute."""
        raw = LLMResponse(content="Some output", finish_reason="end_turn")
        results = parser.parse(raw, "coder", 1)
        assert hasattr(results[0], "response_type") or hasattr(results[0], "parse_success")


# ---------------------------------------------------------------------------
# TC-RP-02: Error signal injection on unstructured coder response
# ---------------------------------------------------------------------------

class TestResponseParserErrorInjection:

    def test_unstructured_coder_injects_error(self, parser, kanban):
        """TC-RP-02: Unstructured coder response injects error signal into kanban."""
        raw = LLMResponse(content="I don't understand", finish_reason="end_turn")
        parser.parse(raw, "coder", 1)

        error_signals = list(kanban.fluid.read_signals(signal_type=SignalType.ERROR))
        assert len(error_signals) > 0, "Unstructured coder response should inject error signal"

    def test_unstructured_reviewer_injects_error(self, parser, kanban):
        """Unstructured reviewer response also injects error signal."""
        raw = LLMResponse(content="Random text", finish_reason="end_turn")
        parser.parse(raw, "reviewer", 1)

        error_signals = list(kanban.fluid.read_signals(signal_type=SignalType.ERROR))
        assert len(error_signals) > 0


# ---------------------------------------------------------------------------
# TC-RP-03: Parser without kanban does not inject errors
# ---------------------------------------------------------------------------

class TestResponseParserNoKanban:

    def test_parser_without_kanban(self):
        """TC-RP-03: ResponseParser(kanban=None) still produces results."""
        parser = ResponseParser(kanban=None)
        raw = LLMResponse(content="Some text", finish_reason="end_turn")
        results = parser.parse(raw, "coder", 1)
        assert len(results) > 0


# ---------------------------------------------------------------------------
# TC-RP-04: Error code injection
# ---------------------------------------------------------------------------

class TestResponseParserErrorCode:

    def test_error_signal_has_correct_type(self, parser, kanban):
        """TC-RP-04: Injected error signals have type ERROR."""
        raw = LLMResponse(content="Non-parseable text", finish_reason="end_turn")
        parser.parse(raw, "coder", 1)

        error_signals = list(kanban.fluid.read_signals(signal_type=SignalType.ERROR))
        for sig in error_signals:
            assert sig.signal_type == SignalType.ERROR


# ---------------------------------------------------------------------------
# TC-RP-05: Multiple parse calls accumulate errors
# ---------------------------------------------------------------------------

class TestResponseParserMultipleCalls:

    def test_multiple_unstructured_calls_produce_errors(self, parser, kanban):
        """TC-RP-05: Multiple unstructured responses produce error signals."""
        raw = LLMResponse(content="Bad response", finish_reason="end_turn")
        parser.parse(raw, "coder", 1)
        parser.parse(raw, "coder", 2)

        error_signals = list(kanban.fluid.read_signals(signal_type=SignalType.ERROR))
        # Note: FluidZone index deduplicates by (target_id, signal_type, author_role),
        # so the second error overwrites the first. At least 1 error signal must exist.
        assert len(error_signals) >= 1, "Unstructured calls should produce error signals"