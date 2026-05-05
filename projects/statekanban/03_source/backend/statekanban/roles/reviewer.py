"""Reviewer role: reviews and approves/rejects artifacts."""

from __future__ import annotations

from typing import Any

from statekanban.roles.base import ProcessRole


class Reviewer(ProcessRole):
    """Reviewer process role: reviews and approves/rejects artifacts."""

    async def execute(self, intent: str) -> dict[str, Any]:
        """Execute review task.

        Reads viewport, calls LLM for review, produces Intent or Veto signal.
        """
        viewport = await self.read_viewport()

        llm_result = await self.call_tool("call_llm", {
            "messages": [
                {"role": "user", "content": f"Review task: {intent}\n\nContext: {viewport}"},
            ],
        })

        return {
            "role": self.role,
            "intent": intent,
            "viewport_signals": len(viewport.signals),
            "llm_result": llm_result.output if hasattr(llm_result, "output") else str(llm_result),
        }
