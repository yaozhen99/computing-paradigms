"""ViewportSlicer: context engineering for LLM calls.

Slices the StateKanban into role-specific views based on ViewportSpec,
applying filters, priority ordering, and token budget truncation.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import Any

from statekanban.core.errors import InvalidViewportSpecError, SliceOverflowError
from statekanban.core.kanban import (
    Artifact,
    ArtifactType,
    Signal,
    SignalType,
    StateKanban,
    ViewportSpec,
)


# ---------------------------------------------------------------------------
# ViewportSlice result
# ---------------------------------------------------------------------------

@dataclass
class ViewportSlice:
    """Result of a viewport slicing operation."""

    role: str
    signals: list[Signal]
    artifacts: list[Artifact]
    token_estimate: int
    items_included: int
    items_excluded: int
    slice_log: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# ViewportSlicer
# ---------------------------------------------------------------------------

class ViewportSlicer:
    """Context engineering: slice the kanban into role-specific views."""

    # Heuristic: ~4 characters per token
    CHARS_PER_TOKEN = 4

    def __init__(self, kanban: StateKanban, specs: dict[str, ViewportSpec]) -> None:
        """
        Args:
            kanban: The source kanban to slice.
            specs: Map of role name to ViewportSpec.
        """
        self._kanban = kanban
        self._specs = dict(specs)

    def slice(self, role: str) -> ViewportSlice:
        """Generate a viewport slice for a role.

        Applies the ViewportSpec filters, orders by priority,
        and truncates to fit within the token budget.

        Args:
            role: The role name whose spec to use.

        Returns:
            ViewportSlice containing the filtered context and metadata.

        Raises:
            InvalidViewportSpecError: No spec registered for role.
        """
        spec = self._specs.get(role) or self._kanban.get_viewport_spec(role)
        if spec is None:
            raise InvalidViewportSpecError(f"No viewport spec registered for role: {role}")

        # Filter signals
        all_signals = self._kanban.fluid.read_signals()
        filtered_signals = self._filter_signals(all_signals, spec)

        # Filter artifacts
        all_artifacts = self._kanban.crystal.read_artifacts()
        filtered_artifacts = self._filter_artifacts(all_artifacts, spec)

        # Order by priority
        ordered_signals = self._order_by_priority(filtered_signals, spec)
        ordered_artifacts = self._order_by_priority_artifacts(filtered_artifacts, spec)

        # Apply token budget
        budget = spec.max_tokens
        included_signals: list[Signal] = []
        included_artifacts: list[Artifact] = []
        total_tokens = 0
        items_included = 0
        items_excluded = 0

        # Priority 1: role_relevant signals
        for sig in ordered_signals:
            est = self.estimate_tokens(str(sig.to_dict()))
            if total_tokens + est <= budget:
                included_signals.append(sig)
                total_tokens += est
                items_included += 1
            else:
                items_excluded += 1

        # Priority 2: dependency-chain upstream (artifacts)
        for art in ordered_artifacts:
            est = self.estimate_tokens(str(art.to_dict()))
            if total_tokens + est <= budget:
                included_artifacts.append(art)
                total_tokens += est
                items_included += 1
            else:
                items_excluded += 1

        # Check if we have at least something
        if items_included == 0 and (ordered_signals or ordered_artifacts):
            # Try to include at least one item
            raise SliceOverflowError(
                f"Cannot fit any items within token budget ({budget}) for role: {role}"
            )

        return ViewportSlice(
            role=role,
            signals=included_signals,
            artifacts=included_artifacts,
            token_estimate=total_tokens,
            items_included=items_included,
            items_excluded=items_excluded,
            slice_log={
                "budget": budget,
                "total_signals_available": len(ordered_signals),
                "total_artifacts_available": len(ordered_artifacts),
            },
        )

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for a string.

        Uses a heuristic of 4 characters per token.
        """
        return max(1, len(text) // self.CHARS_PER_TOKEN)

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _filter_signals(
        self, signals: list[Signal], spec: ViewportSpec
    ) -> list[Signal]:
        """Filter signals by signal type and target patterns."""
        result: list[Signal] = []
        for sig in signals:
            if sig.signal_type not in spec.visible_signal_types:
                continue
            if not self._matches_target_patterns(sig.target_id, spec.visible_target_patterns):
                continue
            result.append(sig)
        return result

    def _filter_artifacts(
        self, artifacts: list[Artifact], spec: ViewportSpec
    ) -> list[Artifact]:
        """Filter artifacts by artifact type."""
        result: list[Artifact] = []
        for art in artifacts:
            if art.artifact_type not in spec.visible_artifact_types:
                continue
            result.append(art)
        return result

    @staticmethod
    def _matches_target_patterns(target_id: str, patterns: list[str]) -> bool:
        """Check if a target_id matches any of the given glob patterns."""
        if not patterns:
            return True
        for pattern in patterns:
            if fnmatch.fnmatch(target_id, pattern):
                return True
        return False

    def _order_by_priority(
        self, signals: list[Signal], spec: ViewportSpec
    ) -> list[Signal]:
        """Order signals by priority.

        Priority order from spec:
        1. role_relevant -- signals from this role or targeting this role
        2. dependency_upstream -- signals from upstream dependencies
        3. global_summary -- all other signals
        """
        role_relevant: list[Signal] = []
        dependency_upstream: list[Signal] = []
        global_summary: list[Signal] = []

        for sig in signals:
            if sig.author_role == spec.role or sig.target_id.startswith(spec.role):
                role_relevant.append(sig)
            elif sig.signal_type == SignalType.INTENT:
                dependency_upstream.append(sig)
            else:
                global_summary.append(sig)

        ordered: list[Signal] = []
        for priority in spec.priority_order:
            if priority == "role_relevant":
                ordered.extend(role_relevant)
            elif priority == "dependency_upstream":
                ordered.extend(dependency_upstream)
            elif priority == "global_summary":
                ordered.extend(global_summary)

        return ordered

    @staticmethod
    def _order_by_priority_artifacts(
        artifacts: list[Artifact], spec: ViewportSpec
    ) -> list[Artifact]:
        """Order artifacts -- authored by this role first, then others."""
        own: list[Artifact] = []
        other: list[Artifact] = []
        for art in artifacts:
            if art.author_role == spec.role:
                own.append(art)
            else:
                other.append(art)
        return own + other
