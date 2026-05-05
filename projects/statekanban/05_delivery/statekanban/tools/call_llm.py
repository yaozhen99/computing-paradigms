"""call_llm tool implementation.

Accessible by all roles. Invokes LLM via adapter.
"""

from __future__ import annotations

from typing import Any

from statekanban.adapters.base import LLMAdapter
from statekanban.core.kanban import LLMMessage


def create_call_llm_tool(adapter: LLMAdapter) -> Any:
    """Create the call_llm tool implementation bound to an LLM adapter.

    Returns:
        Async callable that accepts params dict and returns result dict.
    """

    async def call_llm(params: dict[str, Any]) -> dict[str, Any]:
        """Invoke the LLM via the configured adapter.

        Args:
            params: Must contain 'messages' (list of message dicts).
                    May contain 'tools', 'max_tokens', 'temperature'.

        Returns:
            Dict with LLM response data.
        """
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

        response = await adapter.complete(
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        return {
            "success": True,
            "content": response.content,
            "tool_use_calls": response.tool_use_calls,
            "finish_reason": response.finish_reason,
            "usage": response.usage,
        }

    return call_llm
