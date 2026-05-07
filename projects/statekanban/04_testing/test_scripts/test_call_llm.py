"""
StateKanban call_llm Tool Tests — R3
TC-CLL-01 through TC-CLL-07
"""

from __future__ import annotations

import json

import pytest

from statekanban.core.kanban import (
    LLMMessage,
    LLMResponse,
    StateKanban,
    ToolDef,
)
from statekanban.core.errors import ToolRegistryError
from statekanban.core.registry import ToolRegistry
from statekanban.adapters.mock_adapter import MockLLMAdapter
from statekanban.tools.call_llm import create_call_llm_tool

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def adapter():
    return MockLLMAdapter()


@pytest.fixture
def kanban():
    return StateKanban()


@pytest.fixture
def registry(kanban):
    return ToolRegistry(kanban)


@pytest.fixture
def call_llm_tool(adapter):
    return create_call_llm_tool(adapter)


# ---------------------------------------------------------------------------
# TC-CLL-01: Valid call returns structured result
# ---------------------------------------------------------------------------


class TestCallLLMSuccess:

    @pytest.mark.asyncio
    async def test_valid_call_returns_structured_result(self, call_llm_tool):
        """TC-CLL-01: Valid call returns success dict."""
        result = await call_llm_tool(
            {
                "messages": [{"role": "user", "content": "hello"}],
            }
        )
        assert result["success"] is True
        assert "output" in result
        assert "content" in result["output"]

    @pytest.mark.asyncio
    async def test_valid_call_with_llm_messages(self, call_llm_tool):
        """Valid call with LLMMessage objects."""
        result = await call_llm_tool(
            {
                "messages": [LLMMessage(role="user", content="write code")],
            }
        )
        assert result["success"] is True


# ---------------------------------------------------------------------------
# TC-CLL-02: Adapter exception returns error dict
# ---------------------------------------------------------------------------


class TestCallLLMError:

    @pytest.mark.asyncio
    async def test_adapter_exception_returns_error_dict(self):
        """TC-CLL-02: Adapter exception returns error dict."""

        class FailingAdapter:
            async def complete(self, messages, **kwargs):
                raise RuntimeError("LLM service unavailable")

        tool = create_call_llm_tool(FailingAdapter())
        result = await tool({"messages": [{"role": "user", "content": "test"}]})

        assert result["success"] is False
        assert "error" in result
        assert result["error_code"] == "SK_LLM_001"


# ---------------------------------------------------------------------------
# TC-CLL-03..04: Null bytes
# ---------------------------------------------------------------------------


class TestCallLLMNullBytes:

    @pytest.mark.asyncio
    async def test_null_bytes_in_message_content_rejected(self, call_llm_tool):
        """TC-CLL-03: Null bytes in message content rejected."""
        with pytest.raises(ToolRegistryError) as exc_info:
            await call_llm_tool(
                {
                    "messages": [{"role": "user", "content": "hello\x00world"}],
                }
            )
        assert exc_info.value.error_code == "SK_TR_004"

    @pytest.mark.asyncio
    async def test_null_bytes_in_nested_dict_rejected(self, call_llm_tool):
        """TC-CLL-04: Null bytes in nested structures rejected."""
        with pytest.raises(ToolRegistryError) as exc_info:
            await call_llm_tool(
                {
                    "messages": [{"role": "user", "content": "ok"}],
                    "extra_data": {"key": "val\x00ue"},
                }
            )
        assert exc_info.value.error_code == "SK_TR_004"


# ---------------------------------------------------------------------------
# TC-CLL-05: Audit log
# ---------------------------------------------------------------------------


class TestCallLLMAudit:

    @pytest.mark.asyncio
    async def test_audit_entry_created(self, adapter, kanban, registry):
        """TC-CLL-05: Each invocation produces audit log entry."""
        tool = create_call_llm_tool(adapter)
        registry.register(
            ToolDef(
                name="call_llm",
                description="Invoke LLM",
                param_schema={
                    "type": "object",
                    "properties": {"messages": {"type": "array"}},
                    "required": ["messages"],
                },
                required_permissions={"all_roles"},
                timeout_seconds=30.0,
            ),
            tool,
        )

        result = await registry.dispatch(
            tool_name="call_llm",
            caller_role="coder",
            params={"messages": [{"role": "user", "content": "test"}]},
        )
        assert result.success is True

        # Check audit zone has entries
        entries = kanban.audit.read_entries()
        assert len(entries) >= 1


# ---------------------------------------------------------------------------
# TC-CLL-06: Message conversion
# ---------------------------------------------------------------------------


class TestCallLLMMessageConversion:

    @pytest.mark.asyncio
    async def test_raw_dict_messages_converted(self, call_llm_tool):
        """TC-CLL-06: Raw dict messages are converted to LLMMessage."""
        result = await call_llm_tool(
            {
                "messages": [
                    {"role": "system", "content": "You are a coder."},
                    {"role": "user", "content": "Write a function"},
                ],
            }
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_mixed_message_types(self, call_llm_tool):
        """Mixed LLMMessage and dict messages are handled."""
        result = await call_llm_tool(
            {
                "messages": [
                    LLMMessage(role="system", content="You are a reviewer."),
                    {"role": "user", "content": "Review this code"},
                ],
            }
        )
        assert result["success"] is True


# ---------------------------------------------------------------------------
# TC-CLL-07: Factory
# ---------------------------------------------------------------------------


class TestCallLLMFactory:

    def test_create_returns_callable(self, adapter):
        """TC-CLL-07: create_call_llm_tool returns a callable."""
        tool = create_call_llm_tool(adapter)
        assert callable(tool)

    @pytest.mark.asyncio
    async def test_factory_tool_is_awaitable(self, adapter):
        """Returned callable is awaitable."""
        tool = create_call_llm_tool(adapter)
        result = await tool({"messages": [{"role": "user", "content": "test"}]})
        assert result["success"] is True
