"""Tests for CodexAdapter (R3).

TC-CX-01..05: null bytes guard, timeout error, response format,
async interface, SK_CX_003 error code.
"""

from __future__ import annotations

import pytest

from statekanban.adapters.codex_adapter import CodexAdapter
from statekanban.core.kanban import LLMMessage
from statekanban.core.errors import (
    ToolRegistryError,
    CodexAdapterError,
    CodexTimeoutError,
)


# ---------------------------------------------------------------------------
# TC-CX-01..02: Null bytes guard
# ---------------------------------------------------------------------------

class TestCodexAdapterNullBytes:

    @pytest.mark.asyncio
    async def test_null_bytes_in_user_message_raises(self):
        """TC-CX-01: Null bytes in user message content raises SK_TR_004."""
        adapter = CodexAdapter()
        with pytest.raises(ToolRegistryError) as exc_info:
            await adapter.complete(
                messages=[LLMMessage(role="user", content="bad\x00content")]
            )
        assert exc_info.value.error_code == "SK_TR_004"

    @pytest.mark.asyncio
    async def test_null_bytes_in_system_message_raises(self):
        """TC-CX-02: Null bytes in system message raises SK_TR_004."""
        adapter = CodexAdapter()
        with pytest.raises(ToolRegistryError) as exc_info:
            await adapter.complete(
                messages=[
                    LLMMessage(role="system", content="system\x00prompt"),
                    LLMMessage(role="user", content="hello"),
                ]
            )
        assert exc_info.value.error_code == "SK_TR_004"

    @pytest.mark.asyncio
    async def test_clean_messages_do_not_raise(self):
        """Clean messages pass null bytes check (may fail at codex execution)."""
        adapter = CodexAdapter()
        # This should not raise ToolRegistryError -- may raise CodexNotAvailableError
        # if codex CLI is not installed, which is expected in test environment.
        try:
            await adapter.complete(
                messages=[LLMMessage(role="user", content="hello world")]
            )
        except ToolRegistryError:
            pytest.fail("Clean messages should not raise ToolRegistryError")
        except CodexAdapterError:
            pass  # Codex not available in test environment is acceptable


# ---------------------------------------------------------------------------
# TC-CX-03: CodexTimeoutError
# ---------------------------------------------------------------------------

class TestCodexTimeoutError:

    def test_error_code_is_sk_cx_003(self):
        """TC-CX-03: CodexTimeoutError has SK_CX_003."""
        err = CodexTimeoutError("timeout")
        assert err.error_code == "SK_CX_003"

    def test_http_analogy_is_408(self):
        err = CodexTimeoutError("timeout")
        assert err.http_analogy == 408

    def test_inherits_from_codex_adapter_error(self):
        err = CodexTimeoutError("timeout")
        assert isinstance(err, CodexAdapterError)


# ---------------------------------------------------------------------------
# TC-CX-04: Async interface
# ---------------------------------------------------------------------------

class TestCodexAdapterAsync:

    def test_complete_is_coroutine_function(self):
        """TC-CX-04: CodexAdapter.complete is an async method."""
        adapter = CodexAdapter()
        import asyncio
        assert asyncio.iscoroutinefunction(adapter.complete)


# ---------------------------------------------------------------------------
# TC-CX-05: CodexAdapter configuration
# ---------------------------------------------------------------------------

class TestCodexAdapterConfig:

    def test_default_init(self):
        """CodexAdapter can be created with defaults."""
        adapter = CodexAdapter()
        assert adapter is not None

    def test_custom_init(self):
        """CodexAdapter accepts custom cli_path and timeout."""
        adapter = CodexAdapter(cli_path="/custom/codex", timeout=60.0)
        assert adapter._cli_path == "/custom/codex"
        assert adapter._timeout == 60.0