"""ResultSummarizer: produces end-of-loop EngineResult summaries.

Reads final state from StateKanban and ProcessManager to build
a comprehensive result summary after the drive loop completes.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any

from statekanban.core.kanban import ArtifactType, SignalType, StateKanban
from statekanban.core.process import ProcessManager


@dataclass(frozen=True)
class EngineResult:
    """Summary of a completed drive loop execution."""

    converged: bool
    forced_terminate: bool
    total_rounds: int
    artifact_files: list[str] = field(default_factory=list)
    signal_summary: dict[str, int] = field(default_factory=dict)
    error_count: int = 0
    duration_seconds: float = 0.0


class ResultSummarizer:
    """Produces end-of-loop EngineResult summaries."""

    def __init__(self, kanban: StateKanban, pm: ProcessManager) -> None:
        """
        Args:
            kanban: StateKanban instance for reading final state.
            pm: ProcessManager instance for process state.
        """
        self._kanban = kanban
        self._pm = pm

    def summarize(
        self,
        total_rounds: int,
        converged: bool,
        forced_terminate: bool = False,
        start_time: datetime.datetime | None = None,
    ) -> EngineResult:
        """Generate a summary of the drive loop execution.

        Args:
            total_rounds: Number of rounds completed.
            converged: Whether convergence was achieved.
            forced_terminate: Whether circuit breaker fired.
            start_time: When the drive loop started (for duration calc).

        Returns:
            EngineResult with signal counts, artifact files, and timing.
        """
        # Count signals by type
        intent_count = len(
            self._kanban.fluid.read_signals(signal_type=SignalType.INTENT)
        )
        veto_count = len(self._kanban.fluid.read_signals(signal_type=SignalType.VETO))
        error_count = len(self._kanban.fluid.read_signals(signal_type=SignalType.ERROR))

        signal_summary: dict[str, int] = {
            "intent": intent_count,
            "veto": veto_count,
            "error": error_count,
        }

        # Collect artifact file paths
        artifact_files: list[str] = []
        for artifact_type in ArtifactType:
            artifacts = self._kanban.crystal.read_artifacts(artifact_type=artifact_type)
            for art in artifacts:
                if art.path:
                    artifact_files.append(art.path)

        # Calculate duration
        duration_seconds = 0.0
        if start_time is not None:
            duration_seconds = (
                datetime.datetime.now(tz=datetime.timezone.utc) - start_time
            ).total_seconds()

        return EngineResult(
            converged=converged,
            forced_terminate=forced_terminate,
            total_rounds=total_rounds,
            artifact_files=artifact_files,
            signal_summary=signal_summary,
            error_count=error_count,
            duration_seconds=duration_seconds,
        )
