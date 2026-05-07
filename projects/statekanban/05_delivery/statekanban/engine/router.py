"""SignalRouter: routes signals to the appropriate processing role.

Routing rules:
- IntentSignal from "user" -> "coder"
- IntentSignal from "coder" -> "reviewer"
- VetoSignal from "reviewer" -> "coder" (rework)
- ErrorSignal from "OutputValve" -> "coder" (rework)
- ErrorSignal from "ResponseParser" -> "coder" (retry)
- Other -> None (no specific route; picked up by scheduler)
"""

from __future__ import annotations

from statekanban.core.kanban import Signal, SignalType, StateKanban
from statekanban.core.process import ProcessManager


class SignalRouter:
    """Routes signals to the appropriate processing role."""

    def __init__(self, pm: ProcessManager) -> None:
        """
        Args:
            pm: ProcessManager for role lookup.
        """
        self._pm = pm

    def route(self, signal: Signal) -> str | None:
        """Determine which role should process a signal.

        Routing rules:
        - IntentSignal from "user" -> "coder"
        - IntentSignal from "coder" -> "reviewer"
        - VetoSignal from "reviewer" -> "coder" (rework)
        - ErrorSignal from "OutputValve" -> "coder" (rework)
        - ErrorSignal from "ResponseParser" -> "coder" (retry)
        - Other -> None

        Args:
            signal: The signal to route.

        Returns:
            Role name that should process this signal, or None.
        """
        if signal.signal_type == SignalType.INTENT:
            if signal.author_role == "user":
                return "coder"
            if signal.author_role == "coder":
                return "reviewer"
            return None

        if signal.signal_type == SignalType.VETO:
            if signal.author_role == "reviewer":
                return "coder"
            return None

        if signal.signal_type == SignalType.ERROR:
            if signal.author_role in ("OutputValve", "ResponseParser", "ToolRegistry"):
                return "coder"
            return None

        return None

    def get_pending_targets(self) -> list[str]:
        """Get all target_ids that have unprocessed signals.

        Returns:
            List of target_ids with pending signals.
        """
        processes = self._pm.list_processes()
        active_roles = set(p.role for p in processes)
        # For now, return all targets that have signals
        # The scheduler will pick up roles that have work to do
        return []
