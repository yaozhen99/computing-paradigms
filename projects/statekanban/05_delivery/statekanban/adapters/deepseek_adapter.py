"""DeepSeek dual-mode adapter (OpenAI + Anthropic API).

DeepSeek exposes both OpenAI-compatible and Anthropic-compatible
API endpoints. This adapter selects the protocol at construction
time via ``api_mode`` and cannot switch at runtime.

Environment variables:
  DEEPSEEK_API_KEY: DeepSeek API key.
  DEEPSEEK_API_MODE: "openai" or "anthropic" (default: "openai").
  DEEPSEEK_MODEL: Model name (default: "deepseek-v4-flash").

DeepSeek model names:
  - "deepseek-v4-flash" (default, non-thinking)
  - "deepseek-v4-pro" (thinking mode)

Deprecated (2026-07-24):
  - "deepseek-chat" -> use "deepseek-v4-flash"
  - "deepseek-reasoner" -> use "deepseek-v4-pro"
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from statekanban.adapters.base import LLMAdapter
from statekanban.core.errors import (
    LLMAuthError,
    LLMRateLimitError,
    LLMResponseParseError,
)
from statekanban.core.kanban import LLMMessage, LLMResponse

logger = logging.getLogger(__name__)

_OPENAI_BASE_URL = "https://api.deepseek.com"
_ANTHROPIC_BASE_URL = "https://api.deepseek.com/anthropic"


class DeepSeekAdapter(LLMAdapter):
    """DeepSeek dual-mode adapter (OpenAI + Anthropic API).

    Supports two API protocols via ``api_mode``:
      - "openai": Uses openai.AsyncOpenAI with DeepSeek's OpenAI-compatible
        endpoint.
      - "anthropic": Uses anthropic.AsyncAnthropic with DeepSeek's
        Anthropic-compatible endpoint.

    The ``api_mode`` is fixed at construction time and cannot be changed
    at runtime.

    Constructor parameter priority:
      explicit arg > environment variable > default
    """

    def __init__(
        self,
        api_key: str | None = None,
        api_mode: str | None = None,
        model: str | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self._api_mode = api_mode or os.environ.get("DEEPSEEK_API_MODE", "openai")
        self._model = model or os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")

        if self._api_mode not in ("openai", "anthropic"):
            raise ValueError(
                f"Invalid api_mode: {self._api_mode!r}. "
                "Must be 'openai' or 'anthropic'."
            )

        self._openai_client: Any = None  # lazy-init openai.AsyncOpenAI
        self._anthropic_client: Any = None  # lazy-init anthropic.AsyncAnthropic

    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Send a completion request to DeepSeek API."""
        # Pre-check: API key
        if not self._api_key:
            raise LLMAuthError("DEEPSEEK_API_KEY not set")

        # Pre-check: null bytes in message content
        for msg in messages:
            if msg.content and "\x00" in msg.content:
                raise LLMResponseParseError("Null bytes in message content")

        # Dispatch by api_mode
        if self._api_mode == "openai":
            return await self._complete_openai(messages, tools, max_tokens, temperature)
        else:
            return await self._complete_anthropic(
                messages, tools, max_tokens, temperature
            )

    async def _complete_openai(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None,
        max_tokens: int,
        temperature: float,
    ) -> LLMResponse:
        """Complete using OpenAI-compatible endpoint."""
        try:
            import openai
        except ImportError:
            raise LLMAuthError("openai package not installed. Run: pip install openai")

        # Lazy-init client
        if self._openai_client is None:
            self._openai_client = openai.AsyncOpenAI(
                api_key=self._api_key,
                base_url=_OPENAI_BASE_URL,
            )

        # Log warning if tools are passed (OpenAI mode does not support)
        if tools:
            logger.warning("DeepSeekAdapter (openai mode) does not support tool_use")

        api_messages = self._convert_messages_openai(messages)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self._openai_client.chat.completions.create(
                    model=self._model,
                    messages=api_messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                return self._parse_response_openai(response)
            except openai.RateLimitError:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)
                    continue
                raise LLMRateLimitError("DeepSeek API rate limit hit")
            except openai.AuthenticationError:
                raise LLMAuthError("DeepSeek API authentication failed")
            except Exception as exc:
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                raise LLMResponseParseError(f"DeepSeek API call failed: {exc}") from exc

    async def _complete_anthropic(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None,
        max_tokens: int,
        temperature: float,
    ) -> LLMResponse:
        """Complete using Anthropic-compatible endpoint."""
        try:
            import anthropic
        except ImportError:
            raise LLMAuthError(
                "anthropic package not installed. Run: pip install anthropic"
            )

        # Lazy-init client
        if self._anthropic_client is None:
            self._anthropic_client = anthropic.AsyncAnthropic(
                api_key=self._api_key,
                base_url=_ANTHROPIC_BASE_URL,
            )

        api_messages = self._convert_messages_anthropic(messages)

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": api_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self._anthropic_client.messages.create(**kwargs)
                return self._parse_response_anthropic(response)
            except anthropic.RateLimitError:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)
                    continue
                raise LLMRateLimitError("DeepSeek API rate limit hit")
            except anthropic.AuthenticationError:
                raise LLMAuthError("DeepSeek API authentication failed")
            except Exception as exc:
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                raise LLMResponseParseError(f"DeepSeek API call failed: {exc}") from exc

    @staticmethod
    def _convert_messages_openai(
        messages: list[LLMMessage],
    ) -> list[dict[str, Any]]:
        """Convert LLMMessage list to OpenAI API format.

        Tool_use/tool_result are JSON-serialized and appended
        to content, matching IflytekAdapter convention.
        """
        api_messages: list[dict[str, Any]] = []
        for msg in messages:
            api_msg: dict[str, Any] = {"role": msg.role}
            content = msg.content or ""
            if msg.tool_use is not None:
                content += f"\n[tool_use: {json.dumps(msg.tool_use)}]"
            if msg.tool_result is not None:
                content += f"\n[tool_result: {json.dumps(msg.tool_result)}]"
            api_msg["content"] = content
            api_messages.append(api_msg)
        return api_messages

    @staticmethod
    def _convert_messages_anthropic(
        messages: list[LLMMessage],
    ) -> list[dict[str, Any]]:
        """Convert LLMMessage list to Anthropic API format.

        Supports tool_use/tool_result content blocks,
        matching AnthropicMessagesAdapter convention.
        """
        api_messages: list[dict[str, Any]] = []
        for msg in messages:
            api_msg: dict[str, Any] = {"role": msg.role}
            if msg.tool_use is not None or msg.tool_result is not None:
                blocks: list[dict[str, Any]] = []
                if msg.content is not None:
                    blocks.append({"type": "text", "text": msg.content})
                if msg.tool_use is not None:
                    blocks.append({"type": "tool_use", **msg.tool_use})
                if msg.tool_result is not None:
                    blocks.append({"type": "tool_result", **msg.tool_result})
                api_msg["content"] = blocks
            elif msg.content is not None:
                api_msg["content"] = msg.content
            if "content" not in api_msg:
                api_msg["content"] = ""
            api_messages.append(api_msg)
        return api_messages

    @staticmethod
    def _parse_response_openai(response: Any) -> LLMResponse:
        """Parse OpenAI-format response into LLMResponse."""
        try:
            choice = response.choices[0]
            content = choice.message.content if choice.message else None
            finish_reason = choice.finish_reason or ""
            usage = {}
            if hasattr(response, "usage") and response.usage:
                usage = {
                    "input_tokens": getattr(response.usage, "prompt_tokens", 0),
                    "output_tokens": getattr(response.usage, "completion_tokens", 0),
                }
            return LLMResponse(
                content=content,
                finish_reason=finish_reason,
                usage=usage,
                raw=response.model_dump() if hasattr(response, "model_dump") else {},
            )
        except Exception as exc:
            raise LLMResponseParseError(
                f"Failed to parse DeepSeek OpenAI response: {exc}"
            ) from exc

    @staticmethod
    def _parse_response_anthropic(response: Any) -> LLMResponse:
        """Parse Anthropic-format response into LLMResponse."""
        try:
            content = None
            tool_use_calls: list[dict[str, Any]] = []

            if hasattr(response, "content"):
                for block in response.content:
                    if block.type == "text":
                        content = block.text
                    elif block.type == "tool_use":
                        tool_use_calls.append(
                            {
                                "id": block.id,
                                "name": block.name,
                                "input": block.input,
                            }
                        )

            usage = {}
            if hasattr(response, "usage"):
                usage = {
                    "input_tokens": getattr(response.usage, "input_tokens", 0),
                    "output_tokens": getattr(response.usage, "output_tokens", 0),
                }

            finish_reason = ""
            if hasattr(response, "stop_reason"):
                finish_reason = response.stop_reason or ""

            return LLMResponse(
                content=content,
                tool_use_calls=tool_use_calls,
                finish_reason=finish_reason,
                usage=usage,
                raw=response.model_dump() if hasattr(response, "model_dump") else {},
            )
        except Exception as exc:
            raise LLMResponseParseError(
                f"Failed to parse DeepSeek Anthropic response: {exc}"
            ) from exc
