"""Coder role: generates code artifacts via LLM."""

from __future__ import annotations

from typing import Any

from statekanban.roles.base import ProcessRole


class Coder(ProcessRole):
    """Coder process role: generates code artifacts."""

    async def execute(self, intent: str) -> dict[str, Any]:
        """Execute code generation task.

        Reads viewport, calls LLM, and writes artifacts.
        """
        # Read viewport for context
        viewport = await self.read_viewport()

        # Call LLM with context
        llm_result = await self.call_tool("call_llm", {
            "messages": [
                {"role": "user", "content": f"Task: {intent}\n\nContext: {viewport}"},
            ],
        })

        return {
            "role": self.role,
            "intent": intent,
            "viewport_signals": len(viewport.signals),
            "viewport_artifacts": len(viewport.artifacts),
            "llm_result": llm_result.output if hasattr(llm_result, "output") else str(llm_result),
        }
