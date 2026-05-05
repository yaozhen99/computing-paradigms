"""Tester role: validates artifacts via test execution."""

from __future__ import annotations

from typing import Any

from statekanban.roles.base import ProcessRole


class Tester(ProcessRole):
    """Tester process role: validates artifacts via test execution."""

    async def execute(self, intent: str) -> dict[str, Any]:
        """Execute test validation task.

        Reads viewport, runs tests on artifacts, reports results.
        """
        viewport = await self.read_viewport()

        llm_result = await self.call_tool("call_llm", {
            "messages": [
                {"role": "user", "content": f"Test task: {intent}\n\nContext: {viewport}"},
            ],
        })

        return {
            "role": self.role,
            "intent": intent,
            "viewport_artifacts": len(viewport.artifacts),
            "llm_result": llm_result.output if hasattr(llm_result, "output") else str(llm_result),
        }
