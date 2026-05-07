"""ConvergenceDetector: determines whether signals for a target have converged.

A target is considered converged when:
- There exists at least one IntentSignal for this target in current_round
- There are zero VetoSignal entries for this target in current_round
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from statekanban.core.kanban import SignalType, StateKanban


@dataclass(frozen=True)
class ConvergenceCheckResult:
    """Result of checking convergence for a target at a given round."""

    target_id: str
    round_number: int
    converged: bool
    intent_count: int
    veto_count: int


class ConvergenceDetector:
    """Determines whether signals for a target have converged."""

    def __init__(self, kanban: StateKanban) -> None:
        """
        Args:
            kanban: StateKanban instance for reading signals.
        """
        self._kanban = kanban

    def check(self, target_id: str, current_round: int) -> ConvergenceCheckResult:
        """Check convergence for a target at the given round.

        A target is converged when:
        - There are IntentSignals in current_round for this target
        - There are no VetoSignal entries in current_round for this target

        Args:
            target_id: The target to check.
            current_round: The current round number.

        Returns:
            ConvergenceCheckResult with convergence status and signal counts.
        """
        current_signals = self._kanban.fluid.read_signals(target_id=target_id)
        round_signals = [s for s in current_signals if s.round_number == current_round]

        intent_count = sum(
            1 for s in round_signals if s.signal_type == SignalType.INTENT
        )
        veto_count = sum(
            1 for s in round_signals if s.signal_type == SignalType.VETO
        )

        converged = intent_count > 0 and veto_count == 0

        return ConvergenceCheckResult(
            target_id=target_id,
            round_number=current_round,
            converged=converged,
            intent_count=intent_count,
            veto_count=veto_count,
        )

    def check_all_pending(self, current_round: int) -> dict[str, ConvergenceCheckResult]:
        """Check convergence for all targets that have signals in the current round.

        Returns:
            Dict mapping target_id to ConvergenceCheckResult.
        """
        all_signals = self._kanban.fluid.read_signals()
        # Find unique target_ids with signals in the current round
        target_ids: set[str] = set()
        for sig in all_signals:
            if sig.round_number == current_round:
                target_ids.add(sig.target_id)

        results: dict[str, ConvergenceCheckResult] = {}
        for tid in sorted(target_ids):
            results[tid] = self.check(tid, current_round)

        return results