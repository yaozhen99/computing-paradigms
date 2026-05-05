"""ProcessRole abstract base class.

Each process = role + viewport + tool permit.
Processes are stateless: each invocation rebuilds context from viewport.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from statekanban.core.kanban import ProcessInfo
from statekanban.core.message_bus import MessageBus
from statekanban.core.registry import ToolRegistry
from statekanban.core.viewport import ViewportSlicer, ViewportSlice


class ProcessRole(ABC):
    """Abstract base class for process roles."""

    def __init__(
        self,
        process_info: ProcessInfo,
        slicer: ViewportSlicer,
        bus: MessageBus,
        registry: ToolRegistry,
    ) -> None:
        self._process_info = process_info
        self._slicer = slicer
        self._bus = bus
        self._registry = registry

    @property
    def process_id(self) -> str:
        return self._process_info.process_id

    @property
    def role(self) -> str:
        return self._process_info.role

    @abstractmethod
    async def execute(self, intent: str) -> dict[str, Any]:
        """Execute the role's primary task.

        Args:
            intent: Task intent description.

        Returns:
            Dict with execution results.
        """
        ...

    async def read_viewport(self) -> ViewportSlice:
        """Read the current viewport for this role."""
        return self._slicer.slice(self.role)

    async def call_tool(self, tool_name: str, params: dict[str, Any]) -> Any:
        """Call a tool through the registry with permission check."""
        result = await self._registry.dispatch(tool_name, self.role, params)
        return result

    async def publish_signal(self, signal: Any) -> None:
        """Publish a signal via the message bus."""
        await self._bus.publish(signal)
