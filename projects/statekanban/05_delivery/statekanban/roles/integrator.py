"""Integrator role: integrates validated artifacts."""

from __future__ import annotations

from typing import Any

from statekanban.roles.base import ProcessRole


class Integrator(ProcessRole):
    """Integrator process role: integrates validated artifacts."""

    async def execute(self, intent: str) -> dict[str, Any]:
        """Execute integration task.

        Reads viewport, integrates artifacts, performs final validation.
        """
        viewport = await self.read_viewport()

        llm_result = await self.call_tool(
            "call_llm",
            {
                "messages": [
                    {
                        "role": "user",
                        "content": f"Integration task: {intent}\n\nContext: {viewport}",
                    },
                ],
            },
        )

        return {
            "role": self.role,
            "intent": intent,
            "viewport_artifacts": len(viewport.artifacts),
            "llm_result": (
                llm_result.output if hasattr(llm_result, "output") else str(llm_result)
            ),
        }
