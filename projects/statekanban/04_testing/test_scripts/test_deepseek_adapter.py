"""Tests for DeepSeekAdapter (R7, REQ-702).

AC-702.1: Inherits LLMAdapter, complete() signature consistent
AC-702.2: LLMAuthError when env var not set
AC-702.3: OpenAI mode normal call (mock openai SDK)
AC-702.4: Anthropic mode normal call (mock anthropic SDK)
AC-702.5: Invalid api_mode raises ValueError
AC-702.6: model parameter override
AC-702.7: OpenAI mode message conversion
AC-702.8: Anthropic mode message conversion
AC-702.9: OpenAI mode RateLimitError retry
AC-702.10: Anthropic mode RateLimitError retry
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
from statekanban.adapters.deepseek_adapter import DeepSeekAdapter
from statekanban.core.errors import (
    LLMAuthError,
    LLMRateLimitError,
    LLMResponseParseError,
)
from statekanban.core.kanban import LLMMessage, LLMResponse


# ---------------------------------------------------------------------------
# Helpers: mock SDK modules
# ---------------------------------------------------------------------------


class _MockOpenAIRateLimitError(Exception):
    pass


class _MockOpenAIAuthenticationError(Exception):
    pass


class _MockAnthropicRateLimitError(Exception):
    pass


class _MockAnthropicAuthenticationError(Exception):
    pass


def _build_mock_openai_module(client):
    """Build a fake ``openai`` module that returns *client* from AsyncOpenAI."""
    mod = ModuleType("openai")
    mod.AsyncOpenAI = MagicMock(return_value=client)
    mod.RateLimitError = _MockOpenAIRateLimitError
    mod.AuthenticationError = _MockOpenAIAuthenticationError
    return mod


def _build_mock_anthropic_module(client):
    """Build a fake ``anthropic`` module that returns *client* from AsyncAnthropic."""
    mod = ModuleType("anthropic")
    mod.AsyncAnthropic = MagicMock(return_value=client)
    mod.RateLimitError = _MockAnthropicRateLimitError
    mod.AuthenticationError = _MockAnthropicAuthenticationError
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


def _make_anthropic_response(
    content="hello",
    stop_reason="end_turn",
    input_tokens=10,
    output_tokens=20,
    tool_use_blocks=None,
):
    """Build a mock Anthropic API response object."""
    content_blocks = []
    if content is not None:
        content_blocks.append(SimpleNamespace(type="text", text=content))
    if tool_use_blocks:
        for tb in tool_use_blocks:
            content_blocks.append(SimpleNamespace(**tb))

    usage = SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens)
    return SimpleNamespace(
        content=content_blocks,
        usage=usage,
        stop_reason=stop_reason,
        model_dump=MagicMock(
            return_value={"content": [{"type": "text", "text": content}]}
        ),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def clean_env(monkeypatch):
    """Remove DeepSeek env vars to ensure clean state."""
    for key in ("DEEPSEEK_API_KEY", "DEEPSEEK_API_MODE", "DEEPSEEK_MODEL"):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def adapter_openai(clean_env):
    """DeepSeekAdapter in OpenAI mode with API key."""
    return DeepSeekAdapter(api_key="test-key", api_mode="openai")


@pytest.fixture
def adapter_anthropic(clean_env):
    """DeepSeekAdapter in Anthropic mode with API key."""
    return DeepSeekAdapter(api_key="test-key", api_mode="anthropic")


# ---------------------------------------------------------------------------
# AC-702.1: Inherits LLMAdapter, complete() signature consistent
# ---------------------------------------------------------------------------


class TestDeepSeekAdapterInheritance:

    def test_inherits_llm_adapter(self):
        """AC-702.1: DeepSeekAdapter is subclass of LLMAdapter."""
        assert issubclass(DeepSeekAdapter, LLMAdapter)

    def test_complete_is_coroutine_function(self):
        """AC-702.1: complete() is an async method (signature consistent)."""
        adapter = DeepSeekAdapter(api_key="test", api_mode="openai")
        assert inspect.iscoroutinefunction(adapter.complete)

    def test_complete_signature_params(self):
        """AC-702.1: complete() accepts the base class parameters."""
        sig = inspect.signature(DeepSeekAdapter.complete)
        params = list(sig.parameters.keys())
        assert "messages" in params
        assert "tools" in params
        assert "max_tokens" in params
        assert "temperature" in params


# ---------------------------------------------------------------------------
# AC-702.2: LLMAuthError when env var not set
# ---------------------------------------------------------------------------


class TestDeepSeekAdapterAuthError:

    @pytest.mark.asyncio
    async def test_no_api_key_raises_auth_error(self, clean_env):
        """AC-702.2: LLMAuthError when DEEPSEEK_API_KEY not set."""
        adapter = DeepSeekAdapter(api_mode="openai")
        with pytest.raises(LLMAuthError) as exc_info:
            await adapter.complete([LLMMessage(role="user", content="hello")])
        assert "DEEPSEEK_API_KEY" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_empty_api_key_raises_auth_error(self, clean_env):
        """AC-702.2: LLMAuthError when api_key is empty string."""
        adapter = DeepSeekAdapter(api_key="", api_mode="openai")
        with pytest.raises(LLMAuthError):
            await adapter.complete([LLMMessage(role="user", content="hello")])

    @pytest.mark.asyncio
    async def test_anthropic_mode_no_key_raises_auth_error(self, clean_env):
        """AC-702.2: LLMAuthError in Anthropic mode when key not set."""
        adapter = DeepSeekAdapter(api_mode="anthropic")
        with pytest.raises(LLMAuthError):
            await adapter.complete([LLMMessage(role="user", content="hello")])


# ---------------------------------------------------------------------------
# AC-702.3: OpenAI mode normal call (mock openai SDK)
# ---------------------------------------------------------------------------


class TestDeepSeekAdapterOpenAINormal:

    @pytest.mark.asyncio
    async def test_openai_mode_returns_llm_response(self, adapter_openai):
        """AC-702.3: OpenAI mode complete() returns LLMResponse."""
        mock_response = _make_openai_response(content="deepseek response")
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai = _build_mock_openai_module(mock_client)

        with patch.dict(sys.modules, {"openai": mock_openai}):
            with patch(
                "statekanban.adapters.deepseek_adapter.asyncio.sleep",
                new_callable=AsyncMock,
            ):
                result = await adapter_openai.complete(
                    [LLMMessage(role="user", content="hello")]
                )

        assert isinstance(result, LLMResponse)
        assert result.content == "deepseek response"
        assert result.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_openai_mode_usage_parsed(self, adapter_openai):
        """AC-702.3: OpenAI mode usage is correctly parsed."""
        mock_response = _make_openai_response(
            content="output", prompt_tokens=30, completion_tokens=60
        )
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai = _build_mock_openai_module(mock_client)

        with patch.dict(sys.modules, {"openai": mock_openai}):
            with patch(
                "statekanban.adapters.deepseek_adapter.asyncio.sleep",
                new_callable=AsyncMock,
            ):
                result = await adapter_openai.complete(
                    [LLMMessage(role="user", content="hello")]
                )

        assert result.usage["input_tokens"] == 30
        assert result.usage["output_tokens"] == 60


# ---------------------------------------------------------------------------
# AC-702.4: Anthropic mode normal call (mock anthropic SDK)
# ---------------------------------------------------------------------------


class TestDeepSeekAdapterAnthropicNormal:

    @pytest.mark.asyncio
    async def test_anthropic_mode_returns_llm_response(self, adapter_anthropic):
        """AC-702.4: Anthropic mode complete() returns LLMResponse."""
        mock_response = _make_anthropic_response(
            content="deepseek anthropic response", stop_reason="end_turn"
        )
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic = _build_mock_anthropic_module(mock_client)

        with patch.dict(sys.modules, {"anthropic": mock_anthropic}):
            with patch(
                "statekanban.adapters.deepseek_adapter.asyncio.sleep",
                new_callable=AsyncMock,
            ):
                result = await adapter_anthropic.complete(
                    [LLMMessage(role="user", content="hello")]
                )

        assert isinstance(result, LLMResponse)
        assert result.content == "deepseek anthropic response"
        assert result.finish_reason == "end_turn"

    @pytest.mark.asyncio
    async def test_anthropic_mode_usage_parsed(self, adapter_anthropic):
        """AC-702.4: Anthropic mode usage is correctly parsed."""
        mock_response = _make_anthropic_response(
            content="output", input_tokens=25, output_tokens=50
        )
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic = _build_mock_anthropic_module(mock_client)

        with patch.dict(sys.modules, {"anthropic": mock_anthropic}):
            with patch(
                "statekanban.adapters.deepseek_adapter.asyncio.sleep",
                new_callable=AsyncMock,
            ):
                result = await adapter_anthropic.complete(
                    [LLMMessage(role="user", content="hello")]
                )

        assert result.usage["input_tokens"] == 25
        assert result.usage["output_tokens"] == 50

    @pytest.mark.asyncio
    async def test_anthropic_mode_tool_use_parsed(self, adapter_anthropic):
        """AC-702.4: Anthropic mode tool_use blocks are parsed."""
        tool_blocks = [
            {
                "type": "tool_use",
                "id": "tu1",
                "name": "read_file",
                "input": {"path": "/tmp/x.py"},
            },
        ]
        mock_response = _make_anthropic_response(
            content="using tool", tool_use_blocks=tool_blocks
        )
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_anthropic = _build_mock_anthropic_module(mock_client)

        with patch.dict(sys.modules, {"anthropic": mock_anthropic}):
            with patch(
                "statekanban.adapters.deepseek_adapter.asyncio.sleep",
                new_callable=AsyncMock,
            ):
                result = await adapter_anthropic.complete(
                    [LLMMessage(role="user", content="read the file")]
                )

        assert len(result.tool_use_calls) == 1
        assert result.tool_use_calls[0]["name"] == "read_file"
        assert result.tool_use_calls[0]["id"] == "tu1"


# ---------------------------------------------------------------------------
# AC-702.5: Invalid api_mode raises ValueError
# ---------------------------------------------------------------------------


class TestDeepSeekAdapterInvalidMode:

    def test_invalid_api_mode_raises_value_error(self, clean_env):
        """AC-702.5: Invalid api_mode raises ValueError at construction."""
        with pytest.raises(ValueError) as exc_info:
            DeepSeekAdapter(api_key="test", api_mode="invalid_mode")
        assert "invalid_mode" in str(exc_info.value).lower()

    def test_empty_api_mode_uses_default(self, clean_env):
        """Default api_mode is 'openai' when not specified."""
        adapter = DeepSeekAdapter(api_key="test")
        assert adapter._api_mode == "openai"

    def test_env_api_mode_anthropic(self, monkeypatch, clean_env):
        """DEEPSEEK_API_MODE env var sets mode."""
        monkeypatch.setenv("DEEPSEEK_API_MODE", "anthropic")
        adapter = DeepSeekAdapter(api_key="test")
        assert adapter._api_mode == "anthropic"

    def test_env_api_mode_invalid_raises(self, monkeypatch, clean_env):
        """Invalid DEEPSEEK_API_MODE env var raises ValueError."""
        monkeypatch.setenv("DEEPSEEK_API_MODE", "bad")
        with pytest.raises(ValueError):
            DeepSeekAdapter(api_key="test")


# ---------------------------------------------------------------------------
# AC-702.6: model parameter override
# ---------------------------------------------------------------------------


class TestDeepSeekAdapterModelOverride:

    def test_explicit_model_overrides_env(self, monkeypatch, clean_env):
        """AC-702.6: Explicit model param overrides env var."""
        monkeypatch.setenv("DEEPSEEK_MODEL", "env-model")
        adapter = DeepSeekAdapter(api_key="test", model="deepseek-v4-pro")
        assert adapter._model == "deepseek-v4-pro"

    def test_env_model_overrides_default(self, monkeypatch, clean_env):
        """AC-702.6: DEEPSEEK_MODEL env var overrides default."""
        monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
        adapter = DeepSeekAdapter(api_key="test")
        assert adapter._model == "deepseek-v4-pro"

    def test_model_default_is_deepseek_v4_flash(self, clean_env):
        """AC-702.6: Default model is 'deepseek-v4-flash'."""
        adapter = DeepSeekAdapter(api_key="test")
        assert adapter._model == "deepseek-v4-flash"


# ---------------------------------------------------------------------------
# AC-702.7: OpenAI mode message conversion
# ---------------------------------------------------------------------------


class TestDeepSeekAdapterOpenAIMessageConversion:

    def test_simple_message_conversion(self):
        """AC-702.7: Simple messages convert to OpenAI format."""
        messages = [
            LLMMessage(role="system", content="You are helpful."),
            LLMMessage(role="user", content="Hello"),
        ]
        result = DeepSeekAdapter._convert_messages_openai(messages)
        assert len(result) == 2
        assert result[0] == {"role": "system", "content": "You are helpful."}
        assert result[1] == {"role": "user", "content": "Hello"}

    def test_tool_use_appended_to_content(self):
        """AC-702.7: tool_use JSON-serialized and appended to content."""
        messages = [
            LLMMessage(
                role="assistant",
                content="result",
                tool_use={"name": "read_file", "input": {"path": "/tmp/test.py"}},
            ),
        ]
        result = DeepSeekAdapter._convert_messages_openai(messages)
        assert len(result) == 1
        assert "[tool_use:" in result[0]["content"]
        assert "read_file" in result[0]["content"]

    def test_tool_result_appended_to_content(self):
        """AC-702.7: tool_result JSON-serialized and appended to content."""
        messages = [
            LLMMessage(
                role="user",
                content="",
                tool_result={"tool_use_id": "t1", "content": "file content"},
            ),
        ]
        result = DeepSeekAdapter._convert_messages_openai(messages)
        assert "[tool_result:" in result[0]["content"]

    def test_none_content_treated_as_empty(self):
        """AC-702.7: None content treated as empty string."""
        messages = [LLMMessage(role="user", content=None)]
        result = DeepSeekAdapter._convert_messages_openai(messages)
        assert result[0]["content"] == ""


# ---------------------------------------------------------------------------
# AC-702.8: Anthropic mode message conversion
# ---------------------------------------------------------------------------


class TestDeepSeekAdapterAnthropicMessageConversion:

    def test_simple_text_message(self):
        """AC-702.8: Simple text messages convert to Anthropic format."""
        messages = [
            LLMMessage(role="user", content="Hello"),
        ]
        result = DeepSeekAdapter._convert_messages_anthropic(messages)
        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "Hello"

    def test_tool_use_converts_to_content_block(self):
        """AC-702.8: tool_use converts to Anthropic content block."""
        messages = [
            LLMMessage(
                role="assistant",
                content=None,
                tool_use={"name": "read_file", "input": {"path": "/tmp/x.py"}},
            ),
        ]
        result = DeepSeekAdapter._convert_messages_anthropic(messages)
        assert len(result) == 1
        content = result[0]["content"]
        assert isinstance(content, list)
        assert content[0]["type"] == "tool_use"
        assert content[0]["name"] == "read_file"

    def test_tool_result_converts_to_content_block(self):
        """AC-702.8: tool_result converts to Anthropic content block."""
        messages = [
            LLMMessage(
                role="user",
                content=None,
                tool_result={"tool_use_id": "t1", "content": "file content"},
            ),
        ]
        result = DeepSeekAdapter._convert_messages_anthropic(messages)
        content = result[0]["content"]
        assert isinstance(content, list)
        assert content[0]["type"] == "tool_result"
        assert content[0]["tool_use_id"] == "t1"

    def test_text_with_no_tool_fields(self):
        """AC-702.8: Plain text message without tool fields."""
        messages = [
            LLMMessage(role="user", content="just text"),
        ]
        result = DeepSeekAdapter._convert_messages_anthropic(messages)
        assert result[0]["content"] == "just text"


# ---------------------------------------------------------------------------
# AC-702.9: OpenAI mode RateLimitError retry
# ---------------------------------------------------------------------------


class TestDeepSeekAdapterOpenAIRateLimit:

    @pytest.mark.asyncio
    async def test_rate_limit_retries_then_raises(self, adapter_openai):
        """AC-702.9: OpenAI RateLimitError triggers retry, then LLMRateLimitError."""
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=_MockOpenAIRateLimitError("rate limited")
        )
        mock_openai = _build_mock_openai_module(mock_client)

        with patch.dict(sys.modules, {"openai": mock_openai}):
            with patch(
                "statekanban.adapters.deepseek_adapter.asyncio.sleep",
                new_callable=AsyncMock,
            ):
                with pytest.raises(LLMRateLimitError):
                    await adapter_openai.complete(
                        [LLMMessage(role="user", content="hello")]
                    )

    @pytest.mark.asyncio
    async def test_rate_limit_recover_after_retry(self, adapter_openai):
        """AC-702.9: OpenAI RateLimitError can recover on later attempt."""
        mock_response = _make_openai_response(content="recovered")
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[
                _MockOpenAIRateLimitError("rl"),
                mock_response,
            ]
        )
        mock_openai = _build_mock_openai_module(mock_client)

        with patch.dict(sys.modules, {"openai": mock_openai}):
            with patch(
                "statekanban.adapters.deepseek_adapter.asyncio.sleep",
                new_callable=AsyncMock,
            ):
                result = await adapter_openai.complete(
                    [LLMMessage(role="user", content="hello")]
                )

        assert result.content == "recovered"

    @pytest.mark.asyncio
    async def test_openai_auth_error_no_retry(self, adapter_openai):
        """OpenAI AuthenticationError is not retried."""
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=_MockOpenAIAuthenticationError("bad key")
        )
        mock_openai = _build_mock_openai_module(mock_client)

        with patch.dict(sys.modules, {"openai": mock_openai}):
            with patch(
                "statekanban.adapters.deepseek_adapter.asyncio.sleep",
                new_callable=AsyncMock,
            ):
                with pytest.raises(LLMAuthError):
                    await adapter_openai.complete(
                        [LLMMessage(role="user", content="hello")]
                    )


# ---------------------------------------------------------------------------
# AC-702.10: Anthropic mode RateLimitError retry
# ---------------------------------------------------------------------------


class TestDeepSeekAdapterAnthropicRateLimit:

    @pytest.mark.asyncio
    async def test_rate_limit_retries_then_raises(self, adapter_anthropic):
        """AC-702.10: Anthropic RateLimitError triggers retry, then LLMRateLimitError."""
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            side_effect=_MockAnthropicRateLimitError("rate limited")
        )
        mock_anthropic = _build_mock_anthropic_module(mock_client)

        with patch.dict(sys.modules, {"anthropic": mock_anthropic}):
            with patch(
                "statekanban.adapters.deepseek_adapter.asyncio.sleep",
                new_callable=AsyncMock,
            ):
                with pytest.raises(LLMRateLimitError):
                    await adapter_anthropic.complete(
                        [LLMMessage(role="user", content="hello")]
                    )

    @pytest.mark.asyncio
    async def test_rate_limit_recover_after_retry(self, adapter_anthropic):
        """AC-702.10: Anthropic RateLimitError can recover on later attempt."""
        mock_response = _make_anthropic_response(content="recovered")
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            side_effect=[
                _MockAnthropicRateLimitError("rl"),
                mock_response,
            ]
        )
        mock_anthropic = _build_mock_anthropic_module(mock_client)

        with patch.dict(sys.modules, {"anthropic": mock_anthropic}):
            with patch(
                "statekanban.adapters.deepseek_adapter.asyncio.sleep",
                new_callable=AsyncMock,
            ):
                result = await adapter_anthropic.complete(
                    [LLMMessage(role="user", content="hello")]
                )

        assert result.content == "recovered"

    @pytest.mark.asyncio
    async def test_anthropic_auth_error_no_retry(self, adapter_anthropic):
        """Anthropic AuthenticationError is not retried."""
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            side_effect=_MockAnthropicAuthenticationError("bad key")
        )
        mock_anthropic = _build_mock_anthropic_module(mock_client)

        with patch.dict(sys.modules, {"anthropic": mock_anthropic}):
            with patch(
                "statekanban.adapters.deepseek_adapter.asyncio.sleep",
                new_callable=AsyncMock,
            ):
                with pytest.raises(LLMAuthError):
                    await adapter_anthropic.complete(
                        [LLMMessage(role="user", content="hello")]
                    )


# ---------------------------------------------------------------------------
# OpenAI mode other exception handling
# ---------------------------------------------------------------------------


class TestDeepSeekAdapterOpenAIOtherException:

    @pytest.mark.asyncio
    async def test_other_exception_retries_then_raises(self, adapter_openai):
        """Non-RateLimit exceptions retry, then LLMResponseParseError."""
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=RuntimeError("unexpected error")
        )
        mock_openai = _build_mock_openai_module(mock_client)

        with patch.dict(sys.modules, {"openai": mock_openai}):
            with patch(
                "statekanban.adapters.deepseek_adapter.asyncio.sleep",
                new_callable=AsyncMock,
            ):
                with pytest.raises(LLMResponseParseError) as exc_info:
                    await adapter_openai.complete(
                        [LLMMessage(role="user", content="hello")]
                    )

        assert "unexpected error" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Anthropic mode other exception handling
# ---------------------------------------------------------------------------


class TestDeepSeekAdapterAnthropicOtherException:

    @pytest.mark.asyncio
    async def test_other_exception_retries_then_raises(self, adapter_anthropic):
        """Non-RateLimit exceptions retry, then LLMResponseParseError."""
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            side_effect=RuntimeError("anthropic unexpected")
        )
        mock_anthropic = _build_mock_anthropic_module(mock_client)

        with patch.dict(sys.modules, {"anthropic": mock_anthropic}):
            with patch(
                "statekanban.adapters.deepseek_adapter.asyncio.sleep",
                new_callable=AsyncMock,
            ):
                with pytest.raises(LLMResponseParseError) as exc_info:
                    await adapter_anthropic.complete(
                        [LLMMessage(role="user", content="hello")]
                    )

        assert "anthropic unexpected" in str(exc_info.value)


# ---------------------------------------------------------------------------
# OpenAI mode response parsing
# ---------------------------------------------------------------------------


class TestDeepSeekAdapterOpenAIResponseParsing:

    def test_parse_valid_response(self):
        """OpenAI response parsed correctly."""
        response = _make_openai_response(
            content="parsed output",
            finish_reason="stop",
            prompt_tokens=5,
            completion_tokens=10,
        )
        result = DeepSeekAdapter._parse_response_openai(response)
        assert isinstance(result, LLMResponse)
        assert result.content == "parsed output"
        assert result.finish_reason == "stop"

    def test_parse_response_no_usage(self):
        """OpenAI response without usage attribute parsed correctly."""
        message = SimpleNamespace(content="hello")
        choice = SimpleNamespace(message=message, finish_reason="stop")
        # Build response without .usage attribute at all
        resp_cls = type("Resp", (), {
            "choices": [choice],
            "model_dump": MagicMock(return_value={}),
        })
        response = resp_cls()
        result = DeepSeekAdapter._parse_response_openai(response)
        assert result.usage == {}

    def test_parse_invalid_response_raises(self):
        """Invalid OpenAI response raises LLMResponseParseError."""
        response = SimpleNamespace()  # no choices
        with pytest.raises(LLMResponseParseError):
            DeepSeekAdapter._parse_response_openai(response)


# ---------------------------------------------------------------------------
# Anthropic mode response parsing
# ---------------------------------------------------------------------------


class TestDeepSeekAdapterAnthropicResponseParsing:

    def test_parse_valid_response(self):
        """Anthropic response parsed correctly."""
        response = _make_anthropic_response(
            content="parsed output",
            stop_reason="end_turn",
            input_tokens=15,
            output_tokens=25,
        )
        result = DeepSeekAdapter._parse_response_anthropic(response)
        assert isinstance(result, LLMResponse)
        assert result.content == "parsed output"
        assert result.finish_reason == "end_turn"

    def test_parse_response_no_usage(self):
        """Anthropic response without usage attribute parsed correctly."""
        text_block = SimpleNamespace(type="text", text="hello")
        # Build response without .usage attribute at all
        resp_cls = type("Resp", (), {
            "content": [text_block],
            "stop_reason": "stop",
            "model_dump": MagicMock(return_value={}),
        })
        response = resp_cls()
        result = DeepSeekAdapter._parse_response_anthropic(response)
        assert result.usage == {}

    def test_parse_empty_content_response(self):
        """Anthropic response with empty content list."""
        response = SimpleNamespace(
            content=[],
            usage=SimpleNamespace(input_tokens=5, output_tokens=0),
            stop_reason="stop",
            model_dump=MagicMock(return_value={}),
        )
        result = DeepSeekAdapter._parse_response_anthropic(response)
        assert isinstance(result, LLMResponse)
        assert result.content is None


# ---------------------------------------------------------------------------
# Null bytes guard (both modes)
# ---------------------------------------------------------------------------


class TestDeepSeekAdapterNullBytes:

    @pytest.mark.asyncio
    async def test_null_bytes_in_message_openai_mode(self, adapter_openai):
        """Null bytes in message content raises LLMResponseParseError (OpenAI)."""
        with pytest.raises(LLMResponseParseError) as exc_info:
            await adapter_openai.complete(
                [LLMMessage(role="user", content="bad\x00content")]
            )
        assert "Null bytes" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_null_bytes_in_message_anthropic_mode(self, adapter_anthropic):
        """Null bytes in message content raises LLMResponseParseError (Anthropic)."""
        with pytest.raises(LLMResponseParseError) as exc_info:
            await adapter_anthropic.complete(
                [LLMMessage(role="user", content="bad\x00content")]
            )
        assert "Null bytes" in str(exc_info.value)


# ---------------------------------------------------------------------------
# CLI integration: _create_adapter branches
# ---------------------------------------------------------------------------


class TestDeepSeekAdapterCLIIntegration:

    def test_create_adapter_deepseek(self):
        """_create_adapter returns DeepSeekAdapter for 'deepseek'."""
        from statekanban.cli.main import _create_adapter

        args = SimpleNamespace(
            adapter="deepseek",
            model=None,
            structured=False,
            behavior=False,
        )
        adapter = _create_adapter(args)
        assert isinstance(adapter, DeepSeekAdapter)
        assert adapter._api_mode == "openai"  # default

    def test_create_adapter_deepseek_with_model(self):
        """_create_adapter passes --model to DeepSeekAdapter."""
        from statekanban.cli.main import _create_adapter

        args = SimpleNamespace(
            adapter="deepseek",
            model="deepseek-v4-pro",
            structured=False,
            behavior=False,
        )
        adapter = _create_adapter(args)
        assert isinstance(adapter, DeepSeekAdapter)
        assert adapter._model == "deepseek-v4-pro"


# ---------------------------------------------------------------------------
# IflytekAdapter CLI integration
# ---------------------------------------------------------------------------


class TestIflytekAdapterCLIIntegration:

    def test_create_adapter_iflytek(self):
        """_create_adapter returns IflytekAdapter for 'iflytek'."""
        from statekanban.cli.main import _create_adapter
        from statekanban.adapters.iflytek_adapter import IflytekAdapter

        args = SimpleNamespace(
            adapter="iflytek",
            model=None,
            structured=False,
            behavior=False,
        )
        adapter = _create_adapter(args)
        assert isinstance(adapter, IflytekAdapter)

    def test_create_adapter_iflytek_with_model(self):
        """_create_adapter passes --model to IflytekAdapter."""
        from statekanban.cli.main import _create_adapter
        from statekanban.adapters.iflytek_adapter import IflytekAdapter

        args = SimpleNamespace(
            adapter="iflytek",
            model="4.0Ultra",
            structured=False,
            behavior=False,
        )
        adapter = _create_adapter(args)
        assert isinstance(adapter, IflytekAdapter)
        assert adapter._model == "4.0Ultra"
