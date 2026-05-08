"""Iflytek MaaS adapter via OpenAI-compatible API.

Connects to iFlytek's MaaS platform using the OpenAI SDK,
since iFlytek exposes an OpenAI-compatible chat completions endpoint.

Environment variables:
  IFLYTEK_API_KEY: API key for iFlytek MaaS.
  IFLYTEK_BASE_URL: OpenAI-compatible endpoint URL.
  IFLYTEK_MODEL: Model name (default: "4.0Ultra").
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


class IflytekAdapter(LLMAdapter):
    """Iflytek MaaS adapter via OpenAI-compatible API.

    Uses the openai AsyncOpenAI client to call iFlytek's
    OpenAI-compatible chat completions endpoint.

    Constructor parameter priority:
      explicit arg > environment variable > default
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("IFLYTEK_API_KEY", "")
        _base_url = base_url or os.environ.get("IFLYTEK_BASE_URL", "")
        self._base_url = _base_url if _base_url else None
        self._model = model or os.environ.get("IFLYTEK_MODEL", "4.0Ultra")
        self._client: Any = None  # lazy-init openai.AsyncOpenAI

    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Send a completion request to the iFlytek MaaS API."""
        # Pre-check: API key
        if not self._api_key:
            raise LLMAuthError("IFLYTEK_API_KEY not set")

        # Pre-check: null bytes in message content
        for msg in messages:
            if msg.content and "\x00" in msg.content:
                raise LLMResponseParseError("Null bytes in message content")

        # Lazy-init SDK import and client
        try:
            import openai
        except ImportError:
            raise LLMAuthError("openai package not installed. Run: pip install openai")

        if self._client is None:
            self._client = openai.AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
            )

        # Log warning if tools are passed (not supported)
        if tools:
            logger.warning(
                "IflytekAdapter does not support tool_use; %d tools ignored",
                len(tools),
            )

        # Convert messages
        api_messages = self._convert_messages(messages)

        # API call with retry
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self._client.chat.completions.create(
                    model=self._model,
                    messages=api_messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                return self._parse_response(response)
            except openai.RateLimitError:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)
                    continue
                raise LLMRateLimitError("iFlytek API rate limit hit")
            except openai.AuthenticationError:
                raise LLMAuthError("iFlytek API authentication failed")
            except Exception as exc:
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                raise LLMResponseParseError(f"iFlytek API call failed: {exc}") from exc

    @staticmethod
    def _convert_messages(messages: list[LLMMessage]) -> list[dict[str, Any]]:
        """Convert LLMMessage list to OpenAI API format.

        IflytekAdapter does not support tool_use/tool_result.
        If a message contains tool_use or tool_result, they are
        JSON-serialized and appended to the content string.
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
    def _parse_response(response: Any) -> LLMResponse:
        """Parse OpenAI API response into LLMResponse.

        Raises:
            LLMResponseParseError: If response structure is unexpected.
        """
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
                f"Failed to parse Iflytek response: {exc}"
            ) from exc
