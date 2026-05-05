"""Mock LLM adapter for testing.

Returns deterministic responses configurable per role.
"""

from __future__ import annotations

from typing import Any

from statekanban.adapters.base import LLMAdapter
from statekanban.core.kanban import LLMMessage, LLMResponse


class MockLLMAdapter(LLMAdapter):
    """Deterministic mock for testing."""

    def __init__(
        self,
        responses: dict[str, list[LLMResponse]] | None = None,
    ) -> None:
        """
        Args:
            responses: Map of role name to list of responses (cycled through).
        """
        self._responses: dict[str, list[LLMResponse]] = responses or {}
        self._call_counts: dict[str, int] = {}

    def set_response(self, role: str, responses: list[LLMResponse]) -> None:
        """Configure responses for a role."""
        self._responses[role] = responses
        self._call_counts[role] = 0

    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Return a deterministic mock response.

        Attempts to match the last user message's role context.
        Falls back to a default response if no role-specific responses are configured.
        """
        # Try to infer role from messages
        role = "default"
        for msg in reversed(messages):
            if msg.role == "user" and msg.content:
                # Simple heuristic: check for role indicators
                break

        # Get response for the role
        role_responses = self._responses.get(role, [])
        if not role_responses:
            # Try any available role
            for r, resps in self._responses.items():
                if resps:
                    role = r
                    role_responses = resps
                    break

        if not role_responses:
            return LLMResponse(
                content="Mock response: no configured responses",
                finish_reason="end_turn",
            )

        # Cycle through responses
        count = self._call_counts.get(role, 0)
        response = role_responses[count % len(role_responses)]
        self._call_counts[role] = count + 1

        return response
