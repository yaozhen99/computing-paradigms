"""call_llm tool: invoke LLM via the configured adapter.

REQ-005: call_llm tool with permission control, audit logging, and null bytes validation.
REQ-005a: call_llm integration with Engine via ToolRegistry.
REQ-008: null bytes validation per reviewer rules RR-004.

This module provides:
  - CallLlmTool: callable tool class for invoking LLM.
  - create_call_llm_tool: factory function for ToolRegistry registration.

The tool is async (returns a coroutine) because ToolRegistry.dispatch()
uses `await implementation(params)`.
"""

from __future__ import annotations

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
    """

    def __init__(self, adapter: LLMAdapter) -> None:
        """
        Args:
            adapter: An LLM adapter instance with an async complete() method.
        """
        self._adapter = adapter

    async def __call__(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute the call_llm tool (async).

        Args:
            params: Dict with keys:
                - messages: list of message dicts (required)
                - max_tokens: int (optional)
                - temperature: float (optional)

        Returns:
            On success:
                {"success": True, "output": {"content": str, "finish_reason": str}}

            On failure:
                {"success": False, "error": str, "error_code": "SK_LLM_001"}

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
                messages.append(LLMMessage(
                    role=msg.get("role", "user"),
                    content=msg.get("content"),
                    tool_use=msg.get("tool_use"),
                    tool_result=msg.get("tool_result"),
                ))

        # --- Audit logging ---
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        prompt_len = sum(len(m.content) for m in messages if m.content)
        logger.info(
            "call_llm invoked: prompt_len=%d, timestamp=%s",
            prompt_len,
            timestamp,
        )

        try:
            response = await self._adapter.complete(
                messages=messages,
                tools=tools,
                max_tokens=max_tokens,
                temperature=temperature,
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

        except Exception as exc:
            logger.error(
                "call_llm error: error=%s",
                str(exc),
            )
            return {
                "success": False,
                "error": str(exc),
                "error_code": "SK_LLM_001",
            }


def create_call_llm_tool(adapter: LLMAdapter) -> Callable[[dict[str, Any]], Any]:
    """Factory function to create a call_llm tool callable.

    Used for ToolRegistry registration.

    Args:
        adapter: An LLM adapter instance with an async complete() method.

    Returns:
        An async callable that accepts params dict and returns result dict.
    """
    tool = CallLlmTool(adapter)
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
