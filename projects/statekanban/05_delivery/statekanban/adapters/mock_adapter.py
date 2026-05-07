"""Mock LLM adapter for testing.

Returns deterministic responses configurable per role.
Enhanced with structured JSON support and behavior modes for drive loop testing.

REQ-001: structured_mode -- returns structured JSON (thought/action/observation).
REQ-002: behavior_mode -- returns responses per a behavior definition (input->output mapping).
Backward compatible: existing mock_mode unchanged.
"""

from __future__ import annotations

import json
import logging
from enum import Enum
from typing import Any

from statekanban.adapters.base import LLMAdapter
from statekanban.core.kanban import LLMMessage, LLMResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# REQ-002: Behavior enums
# ---------------------------------------------------------------------------


class MockReviewerBehavior(Enum):
    """Predefined reviewer behaviors for one-click scenario setup."""

    ALWAYS_APPROVE = "always_approve"
    ALWAYS_REJECT = "always_reject"
    REJECT_THEN_APPROVE = "reject_then_approve"


class MockCoderBehavior(Enum):
    """Predefined coder behaviors for one-click scenario setup."""

    GENERATE_SIMPLE = "generate_simple"
    GENERATE_WITH_BUG = "generate_with_bug"


class MockLLMAdapter(LLMAdapter):
    """Enhanced deterministic mock for drive loop testing.

    Supports three modes (priority chain):
        1. behavior_mode  -- if set, drives responses via behavior definition
        2. structured_mode -- if True, returns JSON strings from _structured_responses
        3. legacy_mode     -- default, returns LLMResponse objects per role

    Priority: behavior_mode > structured_mode > legacy_mode
    """

    def __init__(
        self,
        responses: dict[str, list[LLMResponse]] | None = None,
        structured_mode: bool = False,
    ) -> None:
        """
        Args:
            responses: Map of role name to list of responses (cycled through).
            structured_mode: If True, complete() returns JSON strings
                             from _structured_responses. If False (default),
                             returns legacy LLMResponse objects.
        """
        self._responses: dict[str, list[LLMResponse]] = responses or {}
        self._call_counts: dict[str, int] = {}
        self._structured_mode: bool = structured_mode
        self._structured_responses: dict[str, list[dict[str, Any]]] = {}

        # REQ-504: Dual-parameter behavior mode state
        self._reviewer_behavior: MockReviewerBehavior = (
            MockReviewerBehavior.ALWAYS_APPROVE
        )
        self._coder_behavior: MockCoderBehavior = MockCoderBehavior.GENERATE_SIMPLE
        self._behavior_mode_active: bool = (
            False  # True after set_behavior_mode() called
        )
        self._behavior_state: dict[str, int] = {}  # per-role call counts

    # ─── REQ-001: structured_mode ──────────────────────────────

    @property
    def structured_mode(self) -> bool:
        """Whether structured JSON mode is enabled."""
        return self._structured_mode

    @structured_mode.setter
    def structured_mode(self, value: bool) -> None:
        """Toggle structured mode."""
        self._structured_mode = value

    def set_response(self, role: str, responses: list[LLMResponse]) -> None:
        """Configure responses for a role (legacy mode)."""
        self._responses[role] = responses
        self._call_counts[role] = 0

    def set_structured_response(
        self,
        role: str,
        response_type: Any,  # ParsedResponseType or str
        target_id: str = "task_root",
        payload: dict[str, Any] | None = None,
        reason: str = "",
        artifact_path: str = "",
        artifact_content: str = "",
        artifact_type: str = "code",
    ) -> None:
        """Configure a structured JSON response for a role.

        When structured_mode is enabled, complete() returns LLMResponse
        with content containing a JSON string that ResponseParser can parse.
        """
        self._structured_mode = True

        # Build the structured JSON object
        type_str = (
            response_type.value
            if hasattr(response_type, "value")
            else str(response_type)
        )
        response_obj: dict[str, Any] = {
            "type": type_str,
            "target_id": target_id,
            "payload": payload or {},
        }

        if type_str == "veto":
            response_obj["reason"] = reason
        elif type_str == "artifact":
            response_obj["artifact_path"] = artifact_path
            response_obj["artifact_content"] = artifact_content
            response_obj["artifact_type"] = artifact_type

        if role not in self._structured_responses:
            self._structured_responses[role] = []
        self._structured_responses[role].append(response_obj)

    # ─── REQ-504: Dual-keyword behavior_mode ───────────────────

    def set_behavior_mode(
        self,
        *,
        reviewer_behavior: MockReviewerBehavior | None = None,
        coder_behavior: MockCoderBehavior | None = None,
    ) -> None:
        """Configure behavior mode for mock responses (REQ-504 dual-keyword signature).

        Auto-enables structured_mode. Simultaneously configures reviewer
        and coder behaviors. Also auto-configures tester and integrator roles.

        Args:
            reviewer_behavior: How the reviewer role should behave.
            coder_behavior: How the coder role should behave.

        Raises:
            TypeError: If called with positional args (old convention).
        """
        if reviewer_behavior is not None:
            self._reviewer_behavior = reviewer_behavior
        if coder_behavior is not None:
            self._coder_behavior = coder_behavior
        self._behavior_mode_active = True
        self._behavior_state.clear()
        self._apply_behavior_mode()

    def _apply_behavior_mode(self) -> None:
        """Pre-configure structured responses for all roles based on behavior modes.

        REQ-504: Simultaneously configures reviewer, coder, tester, and integrator.
        """
        self._structured_responses.clear()

        # --- Reviewer ---
        if self._reviewer_behavior == MockReviewerBehavior.ALWAYS_APPROVE:
            self.set_structured_response(
                role="reviewer",
                response_type="intent",
                target_id="task_root",
                payload={"approved": True},
            )
        elif self._reviewer_behavior == MockReviewerBehavior.ALWAYS_REJECT:
            self.set_structured_response(
                role="reviewer",
                response_type="veto",
                target_id="task_root",
                reason="Quality gate: always reject",
            )
        elif self._reviewer_behavior == MockReviewerBehavior.REJECT_THEN_APPROVE:
            self.set_structured_response(
                role="reviewer",
                response_type="veto",
                target_id="task_root",
                reason="Quality gate: needs rework",
            )
            self.set_structured_response(
                role="reviewer",
                response_type="intent",
                target_id="task_root",
                payload={"approved": True},
            )

        # --- Coder ---
        if self._coder_behavior == MockCoderBehavior.GENERATE_SIMPLE:
            self.set_structured_response(
                role="coder",
                response_type="artifact",
                target_id="task_root",
                artifact_path="output.py",
                artifact_content='def hello():\n    return "hello world"\n',
                artifact_type="code",
            )
        elif self._coder_behavior == MockCoderBehavior.GENERATE_WITH_BUG:
            self.set_structured_response(
                role="coder",
                response_type="artifact",
                target_id="task_root",
                artifact_path="output.py",
                artifact_content="def hello():\n    return undefined_var\n",
                artifact_type="code",
            )

        # --- Tester (auto-configured) ---
        self.set_structured_response(
            role="tester",
            response_type="intent",
            target_id="task_root",
            payload={"action": "test_passed", "coverage": "100%"},
        )

        # --- Integrator (auto-configured) ---
        self.set_structured_response(
            role="integrator",
            response_type="intent",
            target_id="task_root",
            payload={"action": "integrate", "files": ["output.py"]},
        )

    @property
    def behavior_mode(self) -> tuple[MockReviewerBehavior, MockCoderBehavior]:
        """Current behavior mode as (reviewer_behavior, coder_behavior)."""  # REQ-504
        return (self._reviewer_behavior, self._coder_behavior)

    # ─── Core method (unchanged signature) ─────────────────────

    async def complete(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Return LLMResponse based on active mode.

        Priority chain:
        1. If behavior_mode is set -> use behavior-driven response
        2. If structured_mode is True -> use _get_structured_response()
        3. Otherwise -> use _get_legacy_response()

        Returns:
            LLMResponse with content = JSON string (modes 1-2)
            or plain text (mode 3).
        """
        # Try to infer role from messages
        role = "default"
        for msg in reversed(messages):
            if msg.role == "user" and msg.content:
                # Check if content starts with "Role:" (Engine convention)
                if msg.content.startswith("Role:"):
                    role = msg.content.split("\n")[0].replace("Role:", "").strip()
                    break

        # REQ-504: behavior_mode takes highest priority
        if self._behavior_mode_active:
            return self._get_behavior_response(role)

        # REQ-001: structured_mode
        if self._structured_mode:
            return self._get_structured_response(role)

        # Legacy mode
        return self._get_legacy_response(role)

    # ─── Private: behavior-driven response ─────────────────────

    def _get_behavior_response(self, role: str) -> LLMResponse:
        """Get a behavior-driven response for a role.

        For REJECT_THEN_APPROVE: first call returns veto, subsequent calls return approve.
        Other behaviors use the pre-configured structured responses.
        """
        if (
            self._reviewer_behavior == MockReviewerBehavior.REJECT_THEN_APPROVE
            and role == "reviewer"
        ):
            call_count = self._behavior_state.get(role, 0)
            self._behavior_state[role] = call_count + 1

            if call_count == 0:
                # First call: return veto
                return LLMResponse(
                    content=json.dumps(
                        {
                            "type": "veto",
                            "target_id": "task_root",
                            "reason": "Quality gate: needs rework",
                        }
                    ),
                    finish_reason="end_turn",
                )
            else:
                # Subsequent calls: return approve
                return LLMResponse(
                    content=json.dumps(
                        {
                            "type": "intent",
                            "target_id": "task_root",
                            "payload": {"approved": True},
                        }
                    ),
                    finish_reason="end_turn",
                )

        # For other behavior modes, use the structured responses
        return self._get_structured_response(role)

    # ─── Private: structured response ──────────────────────────

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

    # ─── Private: legacy response ──────────────────────────────

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

    def reset(self) -> None:
        """Reset all internal state."""
        self._call_counts.clear()
        self._behavior_state.clear()
