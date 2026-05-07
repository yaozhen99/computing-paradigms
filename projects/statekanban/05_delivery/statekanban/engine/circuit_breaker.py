"""CircuitBreaker: prevents infinite drive loops by enforcing a maximum round count.

Once the circuit breaker fires, the Engine stops the drive loop and reports
to the user. No automatic retry after circuit break.
"""

from __future__ import annotations

from statekanban.core.kanban import StateKanban
from statekanban.engine.result import EngineResult


class CircuitBreaker:
    """Prevents infinite drive loops by enforcing a maximum round count."""

    def __init__(self, max_rounds: int = 10) -> None:
        """
        Args:
            max_rounds: Maximum number of rounds before circuit break.
        """
        self._max_rounds = max_rounds

    def should_break(self, current_round: int) -> bool:
        """Check if the drive loop should terminate.

        Returns:
            True if current_round >= max_rounds.
        """
        return current_round >= self._max_rounds

    def report(self, current_round: int) -> EngineResult:
        """Generate an EngineResult for circuit break termination.

        Args:
            current_round: The round at which the break occurred.

        Returns:
            EngineResult with converged=False, forced_terminate=True.
        """
        return EngineResult(
            converged=False,
            forced_terminate=True,
            total_rounds=current_round,
            signal_summary={},
            error_count=0,
            duration_seconds=0.0,
        )

    @property
    def max_rounds(self) -> int:
        return self._max_rounds