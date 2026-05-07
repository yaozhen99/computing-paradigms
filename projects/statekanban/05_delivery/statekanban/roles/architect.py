"""Architect role: designs and validates architecture decisions."""

from __future__ import annotations

from typing import Any

from statekanban.roles.base import ProcessRole


class Architect(ProcessRole):
    """Architect process role: designs and validates architecture decisions."""

    async def execute(self, intent: str) -> dict[str, Any]:
        """Execute architecture design task.

        Reads viewport, calls LLM for architecture analysis.
        """
        viewport = await self.read_viewport()

        llm_result = await self.call_tool(
            "call_llm",
            {
                "messages": [
                    {
                        "role": "user",
                        "content": f"Architecture task: {intent}\n\nContext: {viewport}",
                    },
                ],
            },
        )

        return {
            "role": self.role,
            "intent": intent,
            "viewport_signals": len(viewport.signals),
            "viewport_artifacts": len(viewport.artifacts),
            "llm_result": (
                llm_result.output if hasattr(llm_result, "output") else str(llm_result)
            ),
        }
