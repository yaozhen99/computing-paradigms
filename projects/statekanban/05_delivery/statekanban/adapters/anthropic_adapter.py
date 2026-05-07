"""Anthropic Messages API adapter.

Direct API call via the anthropic SDK. Supports tool_use and streaming.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from statekanban.adapters.base import LLMAdapter
from statekanban.core.errors import (
    LLMAuthError,
    LLMRateLimitError,
    LLMResponseParseError,
)
from statekanban.core.kanban import LLMMessage, LLMResponse


class AnthropicMessagesAdapter(LLMAdapter):
    """Direct Anthropic Messages API adapter."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-20250514",
    ) -> None:
        """
        Args:
            api_key: Anthropic API key. If None, reads ANTHROPIC_API_KEY env var.
            model: Model identifier.
        """
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._model = model

    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Send a completion request to the Anthropic Messages API."""
        if not self._api_key:
            raise LLMAuthError("ANTHROPIC_API_KEY not set")

        try:
            import anthropic
        except ImportError:
            raise LLMAuthError(
                "anthropic package not installed. Run: pip install anthropic"
            )

        client = anthropic.AsyncAnthropic(api_key=self._api_key)

        # Convert messages to Anthropic format
        api_messages = self._convert_messages(messages)

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
                response = await client.messages.create(**kwargs)
                return self._parse_response(response)
            except anthropic.RateLimitError:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)
                    continue
                raise LLMRateLimitError("Anthropic API rate limit hit")
            except anthropic.AuthenticationError:
                raise LLMAuthError("Anthropic API authentication failed")
            except Exception as exc:
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                raise LLMResponseParseError(f"API call failed: {exc}") from exc

        raise LLMRateLimitError("Max retries exceeded")

    @staticmethod
    def _convert_messages(messages: list[LLMMessage]) -> list[dict[str, Any]]:
        """Convert LLMMessage list to Anthropic API format."""
        api_messages: list[dict[str, Any]] = []
        for msg in messages:
            api_msg: dict[str, Any] = {"role": msg.role}
            if msg.content is not None:
                api_msg["content"] = msg.content
            if msg.tool_use is not None:
                api_msg["content"] = [
                    {"type": "tool_use", **msg.tool_use},
                ]
            if msg.tool_result is not None:
                api_msg["content"] = [
                    {"type": "tool_result", **msg.tool_result},
                ]
            api_messages.append(api_msg)
        return api_messages

    @staticmethod
    def _parse_response(response: Any) -> LLMResponse:
        """Parse Anthropic API response into LLMResponse."""
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
            raise LLMResponseParseError(f"Failed to parse response: {exc}") from exc
