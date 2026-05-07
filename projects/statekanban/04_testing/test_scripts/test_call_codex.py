"""
StateKanban call_codex Tool Tests -- R3
TC-CCX-01 through TC-CCX-05

Tests for call_codex tool: null bytes rejection, error handling,
factory, async interface, and graceful failure.
"""

from __future__ import annotations

import pytest

from statekanban.adapters.codex_adapter import CodexAdapter
from statekanban.tools.call_codex import create_call_codex_tool

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def adapter():
    return CodexAdapter()


@pytest.fixture
def call_codex_tool(adapter):
    return create_call_codex_tool(adapter)


# ---------------------------------------------------------------------------
# TC-CCX-01: Null bytes rejection
# ---------------------------------------------------------------------------


class TestCallCodexNullBytes:

    @pytest.mark.asyncio
    async def test_null_bytes_in_prompt_returns_error(self, call_codex_tool):
        """TC-CCX-01: Null bytes in prompt returns SK_TR_004 error dict."""
        result = await call_codex_tool(
            {
                "prompt": "bad\x00prompt",
                "output_path": "",
            }
        )
        assert result["success"] is False
        assert result["error_code"] == "SK_TR_004"


# ---------------------------------------------------------------------------
# TC-CCX-02: Codex not available (raises exception)
# ---------------------------------------------------------------------------


class TestCallCodexError:

    @pytest.mark.asyncio
    async def test_codex_not_available_raises(self, call_codex_tool):
        """TC-CCX-02: When codex is not available, an exception is raised."""
        from statekanban.core.errors import CodexNotAvailableError

        with pytest.raises(CodexNotAvailableError):
            await call_codex_tool(
                {
                    "prompt": "write a function",
                    "output_path": "output.py",
                }
            )


# ---------------------------------------------------------------------------
# TC-CCX-03: Factory
# ---------------------------------------------------------------------------


class TestCallCodexFactory:

    def test_create_returns_callable(self, adapter):
        """TC-CCX-03: create_call_codex_tool returns a callable."""
        tool = create_call_codex_tool(adapter)
        assert callable(tool)


# ---------------------------------------------------------------------------
# TC-CCX-04: Async interface
# ---------------------------------------------------------------------------


class TestCallCodexAsync:

    def test_tool_is_awaitable(self, adapter):
        """TC-CCX-04: Returned callable is awaitable."""
        tool = create_call_codex_tool(adapter)
        import asyncio

        # The tool should return a coroutine when called
        coro = tool({"prompt": "test", "output_path": ""})
        assert asyncio.iscoroutine(coro)
        # Clean up the coroutine to avoid RuntimeWarning
        coro.close()


# ---------------------------------------------------------------------------
# TC-CCX-05: Valid prompt with null bytes detection
# ---------------------------------------------------------------------------


class TestCallCodexNullBytesValidation:

    @pytest.mark.asyncio
    async def test_null_bytes_in_context_file_rejected(self, call_codex_tool):
        """TC-CCX-05: Null bytes in context_files are also rejected."""
        result = await call_codex_tool(
            {
                "prompt": "write code",
                "context_files": ["bad\x00path.py"],
                "output_path": "output.py",
            }
        )
        assert result["success"] is False
        assert result["error_code"] == "SK_TR_004"

    @pytest.mark.asyncio
    async def test_clean_prompt_does_not_trigger_null_bytes(self, call_codex_tool):
        """Clean prompt doesn't trigger SK_TR_004 (may fail for other reasons)."""
        from statekanban.core.errors import CodexNotAvailableError

        try:
            result = await call_codex_tool(
                {
                    "prompt": "write a hello world function",
                    "output_path": "hello.py",
                }
            )
            # If it succeeds or returns a different error, that's fine
            # Just ensure it's not SK_TR_004
            if not result["success"]:
                assert result.get("error_code") != "SK_TR_004"
        except CodexNotAvailableError:
            # Codex not available is expected in test environment
            pass
