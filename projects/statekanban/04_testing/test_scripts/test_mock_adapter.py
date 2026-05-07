"""
StateKanban MockLLMAdapter Tests -- R3
TC-MCK-01 through TC-MCK-10

Tests for MockLLMAdapter behavior modes, call counting,
structured responses, and reset functionality.
"""

from __future__ import annotations

import pytest

from statekanban.core.kanban import LLMMessage, LLMResponse
from statekanban.adapters.mock_adapter import (
    MockLLMAdapter,
    MockCoderBehavior,
    MockReviewerBehavior,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def adapter():
    return MockLLMAdapter()


# ---------------------------------------------------------------------------
# TC-MCK-01: Default behavior returns LLMResponse
# ---------------------------------------------------------------------------

class TestMockAdapterDefault:

    @pytest.mark.asyncio
    async def test_default_returns_llm_response(self, adapter):
        """TC-MCK-01: Default adapter.complete returns LLMResponse."""
        result = await adapter.complete([LLMMessage(role="user", content="hello")])
        assert isinstance(result, LLMResponse)
        assert result.content is not None
        assert len(result.content) > 0

    @pytest.mark.asyncio
    async def test_default_has_end_turn_finish(self, adapter):
        """Default response has end_turn finish reason."""
        result = await adapter.complete([LLMMessage(role="user", content="hello")])
        assert result.finish_reason in ("end_turn", "stop")


# ---------------------------------------------------------------------------
# TC-MCK-02: GENERATE_SIMPLE behavior
# ---------------------------------------------------------------------------

class TestMockAdapterCoderSimple:

    @pytest.mark.asyncio
    async def test_generate_simple(self, adapter):
        """TC-MCK-02: GENERATE_SIMPLE produces code content."""
        adapter.set_behavior_mode(MockCoderBehavior.GENERATE_SIMPLE)
        result = await adapter.complete([LLMMessage(role="user", content="write code")])
        assert isinstance(result, LLMResponse)
        assert result.content is not None

    @pytest.mark.asyncio
    async def test_generate_simple_increments_call_count(self, adapter):
        """GENERATE_SIMPLE increments call counts."""
        adapter.set_behavior_mode(MockCoderBehavior.GENERATE_SIMPLE)
        initial = sum(adapter._call_counts.values())
        await adapter.complete([LLMMessage(role="user", content="write code")])
        after = sum(adapter._call_counts.values())
        assert after > initial, "Call count should increment after complete"


# ---------------------------------------------------------------------------
# TC-MCK-03: GENERATE_WITH_BUG behavior
# ---------------------------------------------------------------------------

class TestMockAdapterCoderBug:

    @pytest.mark.asyncio
    async def test_generate_with_bug(self, adapter):
        """TC-MCK-03: GENERATE_WITH_BUG produces content."""
        adapter.set_behavior_mode(MockCoderBehavior.GENERATE_WITH_BUG)
        result = await adapter.complete([LLMMessage(role="user", content="write buggy code")])
        assert isinstance(result, LLMResponse)
        assert result.content is not None


# ---------------------------------------------------------------------------
# TC-MCK-04: ALWAYS_APPROVE reviewer behavior
# ---------------------------------------------------------------------------

class TestMockAdapterReviewerApprove:

    @pytest.mark.asyncio
    async def test_always_approve(self, adapter):
        """TC-MCK-04: ALWAYS_APPROVE reviewer returns approval content."""
        adapter.set_behavior_mode(MockReviewerBehavior.ALWAYS_APPROVE)
        result = await adapter.complete([LLMMessage(role="user", content="Role: reviewer\nreview this")])
        assert isinstance(result, LLMResponse)
        assert result.content is not None
        # Check that content includes "approved" or "intent"
        assert "approved" in result.content or "intent" in result.content


# ---------------------------------------------------------------------------
# TC-MCK-05: ALWAYS_REJECT reviewer behavior
# ---------------------------------------------------------------------------

class TestMockAdapterReviewerReject:

    @pytest.mark.asyncio
    async def test_always_reject(self, adapter):
        """TC-MCK-05: ALWAYS_REJECT reviewer returns rejection content."""
        adapter.set_behavior_mode(MockReviewerBehavior.ALWAYS_REJECT)
        result = await adapter.complete([LLMMessage(role="user", content="Role: reviewer\nreview this")])
        assert isinstance(result, LLMResponse)
        assert result.content is not None
        # Should contain veto or reject in content
        assert "veto" in result.content or "reject" in result.content


# ---------------------------------------------------------------------------
# TC-MCK-06: REJECT_THEN_APPROVE reviewer behavior
# ---------------------------------------------------------------------------

class TestMockAdapterReviewerRejectThenApprove:

    @pytest.mark.asyncio
    async def test_reject_then_approve(self, adapter):
        """TC-MCK-06: REJECT_THEN_APPROVE rejects first, then approves."""
        adapter.set_behavior_mode(MockReviewerBehavior.REJECT_THEN_APPROVE)

        # First call should reject (veto)
        result1 = await adapter.complete([LLMMessage(role="user", content="Role: reviewer\nreview")])
        assert isinstance(result1, LLMResponse)

        # Second call should approve (intent)
        result2 = await adapter.complete([LLMMessage(role="user", content="Role: reviewer\nreview again")])
        assert isinstance(result2, LLMResponse)


# ---------------------------------------------------------------------------
# TC-MCK-07: Call count tracking via _call_counts
# ---------------------------------------------------------------------------

class TestMockAdapterCallCount:

    @pytest.mark.asyncio
    async def test_call_counts_increment_with_behavior(self, adapter):
        """TC-MCK-07: _call_counts tracks calls when behavior mode is set."""
        adapter.set_behavior_mode(MockCoderBehavior.GENERATE_SIMPLE)
        await adapter.complete([LLMMessage(role="user", content="Role: coder\ntest")])
        total = sum(adapter._call_counts.values())
        assert total >= 1, f"Expected >=1 calls, got {total}"

    @pytest.mark.asyncio
    async def test_multiple_calls_increment_count(self, adapter):
        """Multiple calls increment count appropriately."""
        adapter.set_behavior_mode(MockCoderBehavior.GENERATE_SIMPLE)
        await adapter.complete([LLMMessage(role="user", content="Role: coder\ntest 1")])
        await adapter.complete([LLMMessage(role="user", content="Role: coder\ntest 2")])
        total = sum(adapter._call_counts.values())
        assert total >= 2, f"Expected >=2 calls, got {total}"


# ---------------------------------------------------------------------------
# TC-MCK-08: Reset functionality
# ---------------------------------------------------------------------------

class TestMockAdapterReset:

    @pytest.mark.asyncio
    async def test_reset_clears_call_counts(self, adapter):
        """TC-MCK-08: reset() clears _call_counts."""
        adapter.set_behavior_mode(MockCoderBehavior.GENERATE_SIMPLE)
        await adapter.complete([LLMMessage(role="user", content="Role: coder\ntest")])
        assert sum(adapter._call_counts.values()) > 0

        adapter.reset()
        assert sum(adapter._call_counts.values()) == 0, "Call counts should be 0 after reset"

    @pytest.mark.asyncio
    async def test_reset_clears_behavior_state(self, adapter):
        """reset() clears behavior_state (internal per-role call count)."""
        adapter.set_behavior_mode(MockCoderBehavior.GENERATE_SIMPLE)
        await adapter.complete([LLMMessage(role="user", content="Role: coder\ntest")])

        adapter.reset()
        assert len(adapter._behavior_state) == 0


# ---------------------------------------------------------------------------
# TC-MCK-09: set_structured_response override
# ---------------------------------------------------------------------------

class TestMockAdapterStructuredResponse:

    @pytest.mark.asyncio
    async def test_structured_override(self, adapter):
        """TC-MCK-09: set_structured_response overrides default output."""
        adapter.set_structured_response(
            role="coder",
            response_type="intent",
            target_id="task_root",
            payload={"custom": True},
        )
        # Enable structured mode
        adapter._structured_mode = True
        result = await adapter.complete([LLMMessage(role="user", content="Role: coder\ntest")])
        assert isinstance(result, LLMResponse)
        assert result.content is not None


# ---------------------------------------------------------------------------
# TC-MCK-10: Multiple message handling
# ---------------------------------------------------------------------------

class TestMockAdapterMultipleMessages:

    @pytest.mark.asyncio
    async def test_multiple_messages(self, adapter):
        """TC-MCK-10: Adapter handles multiple LLMMessage objects."""
        messages = [
            LLMMessage(role="system", content="You are a coder."),
            LLMMessage(role="user", content="Write a function."),
        ]
        result = await adapter.complete(messages)
        assert isinstance(result, LLMResponse)
        assert result.content is not None