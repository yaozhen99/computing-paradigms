"""RoleScheduler: defines and iterates the role processing order within a drive round.

Default order: Coder -> Reviewer -> Tester -> Integrator.
Architect is not in the default loop; it is activated on-demand.
"""

from __future__ import annotations

from typing import Iterator


class RoleScheduler:
    """Defines and iterates the role processing order within a drive round."""

    DEFAULT_ORDER: list[str] = ["coder", "reviewer", "tester", "integrator"]

    def __init__(self, order: list[str] | None = None) -> None:
        """
        Args:
            order: Custom role order. Defaults to DEFAULT_ORDER.
        """
        self._order = order or list(self.DEFAULT_ORDER)

    @property
    def order(self) -> list[str]:
        """Return a copy of the current role order."""
        return list(self._order)

    def iter_round(self) -> Iterator[str]:
        """Yield role names in scheduling order for one round."""
        for role in self._order:
            yield role