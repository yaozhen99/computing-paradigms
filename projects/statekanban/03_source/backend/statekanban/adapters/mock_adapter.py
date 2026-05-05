"""Mock LLM adapter for testing.

Returns deterministic responses configurable per role.
Enhanced with structured JSON support for drive loop testing.
"""

from __future__ import annotations

import json
from typing import Any

from statekanban.adapters.base import LLMAdapter
from statekanban.core.kanban import LLMMessage, LLMResponse


class MockLLMAdapter(LLMAdapter):
    """Enhanced deterministic mock for drive loop testing.

    Supports two modes:
    1. Legacy mode: pre-configured LLMResponse objects per role.
    2. Structured mode: returns JSON strings that ResponseParser can parse.
    """

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
        self._structured_mode: bool = False
        self._structured_responses: dict[str, list[dict[str, Any]]] = {}

    def set_response(self, role: str, responses: list[LLMResponse]) -> None:
        """Configure responses for a role."""
        self._responses[role] = responses
        self._call_counts[role] = 0

    def set_structured_response(
        self,
        role: str,
        response_type: Any,  # ParsedResponseType
        target_id: str = "task_root",
        payload: dict[str, Any] | None = None,
        reason: str = "",
        artifact_path: str = "",
        artifact_content: str = "",
    ) -> None:
        """Configure a structured JSON response for a role.

        When structured_mode is enabled, complete() returns LLMResponse
        with content containing a JSON string that ResponseParser can parse.
        """
        self._structured_mode = True

        # Build the structured JSON object
        response_obj: dict[str, Any] = {
            "type": response_type.value if hasattr(response_type, "value") else str(response_type),
            "target_id": target_id,
            "payload": payload or {},
        }

        if response_type.value == "veto" if hasattr(response_type, "value") else response_type == "veto":
            response_obj["reason"] = reason
        elif response_type.value == "artifact" if hasattr(response_type, "value") else response_type == "artifact":
            response_obj["artifact_path"] = artifact_path
            response_obj["artifact_content"] = artifact_content
            response_obj["artifact_type"] = "code"

        if role not in self._structured_responses:
            self._structured_responses[role] = []
        self._structured_responses[role].append(response_obj)

    @property
    def structured_mode(self) -> bool:
        """Whether structured JSON mode is enabled."""
        return self._structured_mode

    @structured_mode.setter
    def structured_mode(self, value: bool) -> None:
        """Enable or disable structured JSON mode."""
        self._structured_mode = value

    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Return a deterministic mock response.

        In structured mode, returns JSON strings that ResponseParser can parse.
        In legacy mode, cycles through pre-configured LLMResponse objects.
        """
        # Try to infer role from messages
        role = "default"
        for msg in reversed(messages):
            if msg.role == "user" and msg.content:
                # Check if content starts with "Role:" (Engine convention)
                if msg.content.startswith("Role:"):
                    role = msg.content.split("\n")[0].replace("Role:", "").strip()
                    break

        # Structured mode
        if self._structured_mode:
            return self._get_structured_response(role)

        # Legacy mode
        return self._get_legacy_response(role)

    def _get_structured_response(self, role: str) -> LLMResponse:
        """Get a structured JSON response for a role."""
        role_responses = self._structured_responses.get(role, [])

        if not role_responses:
            # Try any available role
            for r, resps in self._structured_responses.items():
                if resps:
                    role = r
                    role_responses = resps
                    break

        if not role_responses:
            return LLMResponse(
                content='{"type": "intent", "target_id": "task_root", "payload": {}}',
                finish_reason="end_turn",
            )

        # Cycle through responses
        count = self._call_counts.get(role, 0)
        response_obj = role_responses[count % len(role_responses)]
        self._call_counts[role] = count + 1

        return LLMResponse(
            content=json.dumps(response_obj),
            finish_reason="end_turn",
        )

    def _get_legacy_response(self, role: str) -> LLMResponse:
        """Get a legacy pre-configured response for a role."""
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