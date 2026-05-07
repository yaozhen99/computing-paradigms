"""Tests for RoleScheduler (R2).

TC-RS-001..004: Default order, custom order, copy safety, iter_round.
"""

from __future__ import annotations

import pytest

from statekanban.engine.scheduler import RoleScheduler


# ---------------------------------------------------------------------------
# TC-RS-001: Default order
# ---------------------------------------------------------------------------

class TestSchedulerDefault:
    """TC-RS-001."""

    def test_default_order(self, scheduler):
        assert scheduler.order == ["coder", "reviewer", "tester", "integrator"]

    def test_default_order_is_copy(self, scheduler):
        order = scheduler.order
        order.append("extra")
        assert scheduler.order == ["coder", "reviewer", "tester", "integrator"]


# ---------------------------------------------------------------------------
# TC-RS-002: Custom order
# ---------------------------------------------------------------------------

class TestSchedulerCustom:
    """TC-RS-002."""

    def test_custom_order(self):
        s = RoleScheduler(order=["coder", "reviewer"])
        assert s.order == ["coder", "reviewer"]

    def test_custom_order_single(self):
        s = RoleScheduler(order=["coder"])
        assert s.order == ["coder"]


# ---------------------------------------------------------------------------
# TC-RS-003: order property returns copy
# ---------------------------------------------------------------------------

class TestSchedulerCopy:
    """TC-RS-003."""

    def test_modifying_returned_list_does_not_affect_internal(self, scheduler):
        order = scheduler.order
        order[0] = "hacked"
        assert scheduler.order[0] == "coder"


# ---------------------------------------------------------------------------
# TC-RS-004: iter_round yields all roles
# ---------------------------------------------------------------------------

class TestSchedulerIterRound:
    """TC-RS-004."""

    def test_iter_round_yields_default_order(self, scheduler):
        roles = list(scheduler.iter_round())
        assert roles == ["coder", "reviewer", "tester", "integrator"]

    def test_iter_round_custom_order(self):
        s = RoleScheduler(order=["coder", "architect"])
        roles = list(s.iter_round())
        assert roles == ["coder", "architect"]

    def test_iter_round_returns_iterator(self, scheduler):
        result = scheduler.iter_round()
        assert hasattr(result, "__next__")

    def test_iter_round_multiple_iterations(self, scheduler):
        # Each call should produce a fresh iterator
        r1 = list(scheduler.iter_round())
        r2 = list(scheduler.iter_round())
        assert r1 == r2