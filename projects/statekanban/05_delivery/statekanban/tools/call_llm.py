"""call_llm tool: invoke LLM via the configured adapter.

REQ-005: call_llm tool with permission control, audit logging, and null bytes validation.
REQ-005a: call_llm integration with Engine via ToolRegistry.
REQ-008: null bytes validation per reviewer rules RR-004.
REQ-603: timeout isolation, retry cap, and degraded fallback.

This module provides:
  - CallLlmTool: callable tool class for invoking LLM.
  - create_call_llm_tool: factory function for ToolRegistry registration.

The tool is async (returns a coroutine) because ToolRegistry.dispatch()
uses `await implementation(params)`.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
from typing import Any, Callable

from statekanban.adapters.base import LLMAdapter
from statekanban.core.errors import ToolRegistryError
from statekanban.core.kanban import LLMMessage

logger = logging.getLogger(__name__)


class CallLlmTool:
    """Tool that invokes the LLM adapter.

    Permission control: all roles can call this tool.
    Audit logging: every invocation is logged with timestamp, role, and prompt summary.
    Null bytes validation: inputs containing null bytes are rejected (RR-004).
    REQ-603: timeout isolation (default 30s), retry cap (default 2),
    and degraded fallback on exhaustion.
    """

    def __init__(
        self,
        adapter: LLMAdapter,
        timeout: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        """
        Args:
            adapter: An LLM adapter instance with an async complete() method.
            timeout: Maximum seconds per LLM call (REQ-603). Default 30.0.
            max_retries: Maximum retry attempts after initial failure (REQ-603). Default 2.
        """
        self._adapter = adapter
        self._timeout = timeout
        self._max_retries = max_retries

    async def __call__(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute the call_llm tool (async).

        REQ-603: Wraps the adapter call with asyncio.wait_for timeout
        and retry logic. On exhaustion, returns a degraded fallback
        response instead of raising.

        Args:
            params: Dict with keys:
                - messages: list of message dicts (required)
                - max_tokens: int (optional)
                - temperature: float (optional)

        Returns:
            On success:
                {"success": True, "output": {"content": str, "finish_reason": str}}

            On timeout/error (after retries exhausted):
                Degraded fallback response (REQ-603).

        Raises:
            ToolRegistryError: SK_TR_004 if null bytes detected in input.
        """
        # --- Null bytes validation (REQ-008, RR-004) ---
        _validate_no_null_bytes(params)

        raw_messages = params.get("messages", [])
        tools = params.get("tools")
        max_tokens = params.get("max_tokens", 4096)
        temperature = params.get("temperature", 0.0)

        # Convert raw message dicts to LLMMessage objects
        messages: list[LLMMessage] = []
        for msg in raw_messages:
            if isinstance(msg, LLMMessage):
                messages.append(msg)
            elif isinstance(msg, dict):
                messages.append(
                    LLMMessage(
                        role=msg.get("role", "user"),
                        content=msg.get("content"),
                        tool_use=msg.get("tool_use"),
                        tool_result=msg.get("tool_result"),
                    )
                )

        # --- Audit logging ---
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        prompt_len = sum(len(m.content) for m in messages if m.content)
        logger.info(
            "call_llm invoked: prompt_len=%d, timestamp=%s",
            prompt_len,
            timestamp,
        )

        # REQ-603: Retry loop with timeout
        last_error: str = ""
        for attempt in range(self._max_retries + 1):
            try:
                response = await asyncio.wait_for(
                    self._adapter.complete(
                        messages=messages,
                        tools=tools,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    ),
                    timeout=self._timeout,
                )

                logger.info(
                    "call_llm completed: response_len=%d",
                    len(response.content) if response.content else 0,
                )

                return {
                    "success": True,
                    "output": {
                        "content": response.content,
                        "finish_reason": response.finish_reason,
                    },
                }

            except asyncio.TimeoutError:
                last_error = f"LLM_TIMEOUT after {self._timeout}s (attempt {attempt + 1})"
                logger.warning("call_llm timeout: %s", last_error)
                if attempt == self._max_retries:
                    return self._fallback_response("LLM_TIMEOUT")

            except Exception as exc:
                last_error = f"LLM_ERROR: {exc} (attempt {attempt + 1})"
                logger.error("call_llm error: %s", last_error)
                if attempt == self._max_retries:
                    return self._fallback_response("LLM_ERROR")

        # Should not reach here, but safety net
        return self._fallback_response("LLM_ERROR")

    def _fallback_response(self, reason: str) -> dict[str, Any]:
        """Degraded fallback response (REQ-603).

        Returns a valid intent signal that lets the drive loop continue
        rather than crashing. The degraded signal is a legitimate internal
        signal that the Engine can process normally.

        Args:
            reason: "LLM_TIMEOUT" or "LLM_ERROR".

        Returns:
            Dict with success=False and degraded intent payload.
        """
        return {
            "success": False,
            "error": reason,
            "error_code": "SK_LLM_001",
            "degraded": True,
            "output": {
                "content": "",
                "finish_reason": "degraded",
            },
        }


def create_call_llm_tool(
    adapter: LLMAdapter,
    timeout: float = 30.0,
    max_retries: int = 2,
) -> Callable[[dict[str, Any]], Any]:
    """Factory function to create a call_llm tool callable.

    Used for ToolRegistry registration.

    Args:
        adapter: An LLM adapter instance with an async complete() method.
        timeout: Maximum seconds per LLM call (REQ-603). Default 30.0.
        max_retries: Maximum retry attempts after initial failure (REQ-603). Default 2.

    Returns:
        An async callable that accepts params dict and returns result dict.
    """
    tool = CallLlmTool(adapter, timeout=timeout, max_retries=max_retries)
    return tool


# ---------------------------------------------------------------------------
# Null bytes validation helpers (REQ-008, RR-004)
# ---------------------------------------------------------------------------


def _validate_no_null_bytes(params: dict[str, Any]) -> None:
    """Validate that params contain no null bytes.

    Checks all string values in the params dict recursively.

    Raises:
        ToolRegistryError: SK_TR_004 if null bytes detected.
    """
    _check_dict_for_null_bytes(params, "params")


def _check_dict_for_null_bytes(d: dict[str, Any], path: str) -> None:
    """Recursively check a dict for null bytes in string values."""
    for key, value in d.items():
        current_path = f"{path}.{key}" if path else key
        if isinstance(value, str):
            if "\x00" in value:
                raise ToolRegistryError(
                    f"Null bytes detected in tool input at {current_path}",
                    error_code="SK_TR_004",
                )
        elif isinstance(value, dict):
            _check_dict_for_null_bytes(value, current_path)
        elif isinstance(value, list):
            _check_list_for_null_bytes(value, current_path)


def _check_list_for_null_bytes(lst: list[Any], path: str) -> None:
    """Recursively check a list for null bytes in string values."""
    for i, value in enumerate(lst):
        current_path = f"{path}[{i}]"
        if isinstance(value, str):
            if "\x00" in value:
                raise ToolRegistryError(
                    f"Null bytes detected in tool input at {current_path}",
                    error_code="SK_TR_004",
                )
        elif isinstance(value, dict):
            _check_dict_for_null_bytes(value, current_path)
        elif isinstance(value, list):
            _check_list_for_null_bytes(value, current_path)
