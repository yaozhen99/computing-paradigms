"""LLM Adapter abstract base class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from statekanban.core.kanban import LLMMessage, LLMResponse


class LLMAdapter(ABC):
    """Abstract base for LLM backends."""

    @abstractmethod
    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Send a completion request to the LLM.

        Args:
            messages: Conversation messages (single-turn for stateless mode).
            tools: Tool definitions for tool_use.
            max_tokens: Maximum output tokens.
            temperature: Sampling temperature.

        Returns:
            LLMResponse with content and/or tool_use calls.

        Raises:
            LLMRateLimitError: API rate limit hit.
            LLMAuthError: Authentication failure.
            LLMResponseParseError: Malformed API response.
        """
        ...
