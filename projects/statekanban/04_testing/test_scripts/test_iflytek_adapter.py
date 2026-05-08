"""Tests for IflytekAdapter (R7, REQ-701).

AC-701.1: Inherits LLMAdapter, complete() signature consistent
AC-701.2: LLMAuthError when env var not set
AC-701.3: Normal call returns valid LLMResponse (mock openai SDK)
AC-701.4: RateLimitError triggers retry, then LLMRateLimitError
AC-701.5: Other exceptions retry then LLMResponseParseError
AC-701.6: Constructor parameter priority (explicit > env > default)
AC-701.7: Message format conversion correct
AC-701.8: Response parsing correct
"""

from __future__ import annotations

import asyncio
import inspect
import json
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from statekanban.adapters.base import LLMAdapter
from statekanban.adapters.iflytek_adapter import IflytekAdapter
from statekanban.core.errors import (
    LLMAuthError,
    LLMRateLimitError,
    LLMResponseParseError,
)
from statekanban.core.kanban import LLMMessage, LLMResponse


# ---------------------------------------------------------------------------
# Helpers: mock openai SDK module
# ---------------------------------------------------------------------------


class _MockRateLimitError(Exception):
    pass


class _MockAuthenticationError(Exception):
    pass


def _build_mock_openai_module(client):
    """Build a fake ``openai`` module that returns *client* from AsyncOpenAI."""
    mod = ModuleType("openai")
    mod.AsyncOpenAI = MagicMock(return_value=client)
    mod.RateLimitError = _MockRateLimitError
    mod.AuthenticationError = _MockAuthenticationError
    return mod


def _make_openai_response(
    content="hello",
    finish_reason="stop",
    prompt_tokens=10,
    completion_tokens=20,
):
    """Build a mock OpenAI API response object."""
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message, finish_reason=finish_reason)
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
    )
    return SimpleNamespace(
        choices=[choice],
        usage=usage,
        model_dump=MagicMock(
            return_value={"choices": [{"message": {"content": content}}]}
        ),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def clean_env(monkeypatch):
    """Remove iFlytek env vars to ensure clean state."""
    for key in ("IFLYTEK_API_KEY", "IFLYTEK_BASE_URL", "IFLYTEK_MODEL"):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def adapter_with_key(clean_env):
    """IflytekAdapter with API key set."""
    return IflytekAdapter(
        api_key="test-key", base_url="https://test.example.com/v1"
    )


# ---------------------------------------------------------------------------
# AC-701.1: Inherits LLMAdapter, complete() signature consistent
# ---------------------------------------------------------------------------


class TestIflytekAdapterInheritance:

    def test_inherits_llm_adapter(self):
        """AC-701.1: IflytekAdapter is subclass of LLMAdapter."""
        assert issubclass(IflytekAdapter, LLMAdapter)

    def test_complete_is_coroutine_function(self):
        """AC-701.1: complete() is an async method (signature consistent)."""
        adapter = IflytekAdapter(api_key="test")
        assert inspect.iscoroutinefunction(adapter.complete)

    def test_complete_signature_params(self):
        """AC-701.1: complete() accepts the base class parameters."""
        sig = inspect.signature(IflytekAdapter.complete)
        params = list(sig.parameters.keys())
        assert "messages" in params
        assert "tools" in params
        assert "max_tokens" in params
        assert "temperature" in params


# ---------------------------------------------------------------------------
# AC-701.2: LLMAuthError when env var not set
# ---------------------------------------------------------------------------


class TestIflytekAdapterAuthError:

    @pytest.mark.asyncio
    async def test_no_api_key_raises_auth_error(self, clean_env):
        """AC-701.2: LLMAuthError when IFLYTEK_API_KEY not set."""
        adapter = IflytekAdapter()
        with pytest.raises(LLMAuthError) as exc_info:
            await adapter.complete([LLMMessage(role="user", content="hello")])
        assert "IFLYTEK_API_KEY" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_empty_api_key_raises_auth_error(self, clean_env):
        """AC-701.2: LLMAuthError when api_key is empty string."""
        adapter = IflytekAdapter(api_key="")
        with pytest.raises(LLMAuthError):
            await adapter.complete([LLMMessage(role="user", content="hello")])


# ---------------------------------------------------------------------------
# AC-701.3: Normal call returns valid LLMResponse (mock openai SDK)
# ---------------------------------------------------------------------------


class TestIflytekAdapterNormalCall:

    @pytest.mark.asyncio
    async def test_normal_call_returns_llm_response(self, adapter_with_key):
        """AC-701.3: complete() returns LLMResponse on success."""
        mock_response = _make_openai_response(content="test output")
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai = _build_mock_openai_module(mock_client)

        with patch.dict(sys.modules, {"openai": mock_openai}):
            with patch(
                "statekanban.adapters.iflytek_adapter.asyncio.sleep",
                new_callable=AsyncMock,
            ):
                result = await adapter_with_key.complete(
                    [LLMMessage(role="user", content="hello")]
                )

        assert isinstance(result, LLMResponse)
        assert result.content == "test output"
        assert result.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_normal_call_usage_parsed(self, adapter_with_key):
        """AC-701.3: Usage is correctly parsed from response."""
        mock_response = _make_openai_response(
            content="output", prompt_tokens=50, completion_tokens=100
        )
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai = _build_mock_openai_module(mock_client)

        with patch.dict(sys.modules, {"openai": mock_openai}):
            with patch(
                "statekanban.adapters.iflytek_adapter.asyncio.sleep",
                new_callable=AsyncMock,
            ):
                result = await adapter_with_key.complete(
                    [LLMMessage(role="user", content="hello")]
                )

        assert result.usage["input_tokens"] == 50
        assert result.usage["output_tokens"] == 100


# ---------------------------------------------------------------------------
# AC-701.4: RateLimitError triggers retry, then LLMRateLimitError
# ---------------------------------------------------------------------------


class TestIflytekAdapterRateLimit:

    @pytest.mark.asyncio
    async def test_rate_limit_retries_then_raises(self, adapter_with_key):
        """AC-701.4: RateLimitError triggers retry, ultimately LLMRateLimitError."""
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=_MockRateLimitError("rate limited")
        )
        mock_openai = _build_mock_openai_module(mock_client)

        with patch.dict(sys.modules, {"openai": mock_openai}):
            with patch(
                "statekanban.adapters.iflytek_adapter.asyncio.sleep",
                new_callable=AsyncMock,
            ):
                with pytest.raises(LLMRateLimitError) as exc_info:
                    await adapter_with_key.complete(
                        [LLMMessage(role="user", content="hello")]
                    )

        assert "rate limit" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_rate_limit_retries_3_times(self, adapter_with_key):
        """AC-701.4: RateLimitError retries 3 times total, can recover."""
        mock_response = _make_openai_response(content="recovered")
        mock_client = AsyncMock()
        # Fail twice with RateLimitError, then succeed
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[
                _MockRateLimitError("rl"),
                _MockRateLimitError("rl"),
                mock_response,
            ]
        )
        mock_openai = _build_mock_openai_module(mock_client)

        with patch.dict(sys.modules, {"openai": mock_openai}):
            with patch(
                "statekanban.adapters.iflytek_adapter.asyncio.sleep",
                new_callable=AsyncMock,
            ):
                result = await adapter_with_key.complete(
                    [LLMMessage(role="user", content="hello")]
                )

        assert result.content == "recovered"


# ---------------------------------------------------------------------------
# AC-701.5: Other exceptions retry then LLMResponseParseError
# ---------------------------------------------------------------------------


class TestIflytekAdapterOtherException:

    @pytest.mark.asyncio
    async def test_other_exception_retries_then_raises(self, adapter_with_key):
        """AC-701.5: Non-RateLimit exceptions retry, then LLMResponseParseError."""
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=RuntimeError("unexpected")
        )
        mock_openai = _build_mock_openai_module(mock_client)

        with patch.dict(sys.modules, {"openai": mock_openai}):
            with patch(
                "statekanban.adapters.iflytek_adapter.asyncio.sleep",
                new_callable=AsyncMock,
            ):
                with pytest.raises(LLMResponseParseError) as exc_info:
                    await adapter_with_key.complete(
                        [LLMMessage(role="user", content="hello")]
                    )

        assert "unexpected" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_auth_error_no_retry(self, adapter_with_key):
        """openai.AuthenticationError is not retried, raises LLMAuthError immediately."""
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=_MockAuthenticationError("bad key")
        )
        mock_openai = _build_mock_openai_module(mock_client)

        with patch.dict(sys.modules, {"openai": mock_openai}):
            with patch(
                "statekanban.adapters.iflytek_adapter.asyncio.sleep",
                new_callable=AsyncMock,
            ):
                with pytest.raises(LLMAuthError) as exc_info:
                    await adapter_with_key.complete(
                        [LLMMessage(role="user", content="hello")]
                    )

        assert "authentication" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# AC-701.6: Constructor parameter priority
# ---------------------------------------------------------------------------


class TestIflytekAdapterParamPriority:

    def test_explicit_params_override_env(self, monkeypatch, clean_env):
        """AC-701.6: Explicit constructor args take priority over env vars."""
        monkeypatch.setenv("IFLYTEK_API_KEY", "env-key")
        monkeypatch.setenv("IFLYTEK_BASE_URL", "https://env.example.com")
        monkeypatch.setenv("IFLYTEK_MODEL", "env-model")

        adapter = IflytekAdapter(
            api_key="explicit-key",
            base_url="https://explicit.example.com",
            model="explicit-model",
        )
        assert adapter._api_key == "explicit-key"
        assert adapter._base_url == "https://explicit.example.com"
        assert adapter._model == "explicit-model"

    def test_env_vars_override_defaults(self, monkeypatch, clean_env):
        """AC-701.6: Env vars take priority over defaults."""
        monkeypatch.setenv("IFLYTEK_API_KEY", "env-key")
        monkeypatch.setenv("IFLYTEK_BASE_URL", "https://env.example.com")
        monkeypatch.setenv("IFLYTEK_MODEL", "env-model")

        adapter = IflytekAdapter()
        assert adapter._api_key == "env-key"
        assert adapter._base_url == "https://env.example.com"
        assert adapter._model == "env-model"

    def test_model_default_is_4_ultra(self, clean_env):
        """AC-701.6: Default model is '4.0Ultra'."""
        adapter = IflytekAdapter()
        assert adapter._model == "4.0Ultra"

    def test_api_key_default_is_empty(self, clean_env):
        """AC-701.6: Default api_key is empty string."""
        adapter = IflytekAdapter()
        assert adapter._api_key == ""


# ---------------------------------------------------------------------------
# AC-701.7: Message format conversion correct
# ---------------------------------------------------------------------------


class TestIflytekAdapterMessageConversion:

    def test_simple_message_conversion(self):
        """AC-701.7: Simple messages convert to OpenAI format."""
        messages = [
            LLMMessage(role="system", content="You are helpful."),
            LLMMessage(role="user", content="Hello"),
        ]
        result = IflytekAdapter._convert_messages(messages)
        assert len(result) == 2
        assert result[0] == {"role": "system", "content": "You are helpful."}
        assert result[1] == {"role": "user", "content": "Hello"}

    def test_tool_use_appended_to_content(self):
        """AC-701.7: tool_use is JSON-serialized and appended to content."""
        messages = [
            LLMMessage(
                role="assistant",
                content="result",
                tool_use={"name": "read_file", "input": {"path": "/tmp/test.py"}},
            ),
        ]
        result = IflytekAdapter._convert_messages(messages)
        assert len(result) == 1
        assert result[0]["role"] == "assistant"
        assert "result" in result[0]["content"]
        assert "[tool_use:" in result[0]["content"]
        assert "read_file" in result[0]["content"]

    def test_tool_result_appended_to_content(self):
        """AC-701.7: tool_result is JSON-serialized and appended to content."""
        messages = [
            LLMMessage(
                role="user",
                content="",
                tool_result={"tool_use_id": "t1", "content": "file content"},
            ),
        ]
        result = IflytekAdapter._convert_messages(messages)
        assert len(result) == 1
        assert "[tool_result:" in result[0]["content"]
        assert "file content" in result[0]["content"]

    def test_none_content_becomes_empty_string(self):
        """AC-701.7: None content is treated as empty string."""
        messages = [LLMMessage(role="user", content=None)]
        result = IflytekAdapter._convert_messages(messages)
        assert result[0]["content"] == ""


# ---------------------------------------------------------------------------
# AC-701.8: Response parsing correct
# ---------------------------------------------------------------------------


class TestIflytekAdapterResponseParsing:

    def test_parse_valid_response(self):
        """AC-701.8: Valid OpenAI response parsed correctly."""
        response = _make_openai_response(
            content="Hello world",
            finish_reason="stop",
            prompt_tokens=5,
            completion_tokens=10,
        )
        result = IflytekAdapter._parse_response(response)
        assert isinstance(result, LLMResponse)
        assert result.content == "Hello world"
        assert result.finish_reason == "stop"
        assert result.usage["input_tokens"] == 5
        assert result.usage["output_tokens"] == 10

    def test_parse_response_with_null_content(self):
        """AC-701.8: Response with None content parsed correctly."""
        response = _make_openai_response(content=None)
        result = IflytekAdapter._parse_response(response)
        assert result.content is None

    def test_parse_response_with_no_usage(self):
        """AC-701.8: Response without usage field parsed correctly."""
        message = SimpleNamespace(content="hello")
        choice = SimpleNamespace(message=message, finish_reason="stop")
        # Build response without .usage attribute
        resp_cls = type("Resp", (), {
            "choices": [choice],
            "model_dump": MagicMock(return_value={}),
        })
        response = resp_cls()
        result = IflytekAdapter._parse_response(response)
        assert result.usage == {}

    def test_parse_invalid_response_raises(self):
        """AC-701.8: Invalid response raises LLMResponseParseError."""
        response = SimpleNamespace()  # no choices attribute
        with pytest.raises(LLMResponseParseError):
            IflytekAdapter._parse_response(response)


# ---------------------------------------------------------------------------
# Additional: Null bytes guard
# ---------------------------------------------------------------------------


class TestIflytekAdapterNullBytes:

    @pytest.mark.asyncio
    async def test_null_bytes_in_message_raises(self, adapter_with_key):
        """Null bytes in message content raises LLMResponseParseError."""
        with pytest.raises(LLMResponseParseError) as exc_info:
            await adapter_with_key.complete(
                [LLMMessage(role="user", content="bad\x00content")]
            )
        assert "Null bytes" in str(exc_info.value)
