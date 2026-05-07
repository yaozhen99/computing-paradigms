"""Tests for SignalRouter (R2).

TC-SR-001..008: Intent from user->coder, Intent from coder->reviewer,
Veto from reviewer->coder, Error from OutputValve->coder,
Error from ResponseParser->coder, Error from ToolRegistry->coder,
Intent from reviewer->None, unknown->None.
"""

from __future__ import annotations

import pytest

from statekanban.core.kanban import (
    ErrorSignal,
    IntentSignal,
    Signal,
    SignalType,
    StateKanban,
    VetoSignal,
    ViewportSpec,
    make_signal_id,
    now_utc,
)
from statekanban.core.message_bus import MessageBus
from statekanban.core.process import ProcessManager
from statekanban.engine.router import SignalRouter


# ---------------------------------------------------------------------------
# TC-SR-001: IntentSignal from "user" -> "coder"
# ---------------------------------------------------------------------------

class TestRouterIntentFromUser:
    """TC-SR-001."""

    def test_user_intent_routes_to_coder(self, router):
        sig = IntentSignal(
            signal_id=make_signal_id(),
            author_role="user",
            target_id="task_root",
            payload={"intent": "do something"},
            timestamp=now_utc(),
            round_number=0,
        )
        assert router.route(sig) == "coder"


# ---------------------------------------------------------------------------
# TC-SR-002: IntentSignal from "coder" -> "reviewer"
# ---------------------------------------------------------------------------

class TestRouterIntentFromCoder:
    """TC-SR-002."""

    def test_coder_intent_routes_to_reviewer(self, router):
        sig = IntentSignal(
            signal_id=make_signal_id(),
            author_role="coder",
            target_id="task_root",
            payload={"action": "approve"},
            timestamp=now_utc(),
            round_number=1,
        )
        assert router.route(sig) == "reviewer"


# ---------------------------------------------------------------------------
# TC-SR-003: VetoSignal from "reviewer" -> "coder"
# ---------------------------------------------------------------------------

class TestRouterVetoFromReviewer:
    """TC-SR-003."""

    def test_reviewer_veto_routes_to_coder(self, router):
        sig = VetoSignal(
            signal_id=make_signal_id(),
            author_role="reviewer",
            target_id="task_root",
            payload={"action": "reject"},
            timestamp=now_utc(),
            round_number=1,
            reason="bad code",
        )
        assert router.route(sig) == "coder"


# ---------------------------------------------------------------------------
# TC-SR-004: ErrorSignal from "OutputValve" -> "coder"
# ---------------------------------------------------------------------------

class TestRouterErrorFromValve:
    """TC-SR-004."""

    def test_valve_error_routes_to_coder(self, router):
        sig = ErrorSignal(
            signal_id=make_signal_id(),
            author_role="OutputValve",
            target_id="output.py",
            payload={},
            timestamp=now_utc(),
            round_number=1,
            error_code="SK_OV_001",
            error_detail="syntax error",
        )
        assert router.route(sig) == "coder"


# ---------------------------------------------------------------------------
# TC-SR-005: ErrorSignal from "ResponseParser" -> "coder"
# ---------------------------------------------------------------------------

class TestRouterErrorFromParser:
    """TC-SR-005."""

    def test_parser_error_routes_to_coder(self, router):
        sig = ErrorSignal(
            signal_id=make_signal_id(),
            author_role="ResponseParser",
            target_id="parse_failure",
            payload={},
            timestamp=now_utc(),
            round_number=1,
            error_code="SK_EN_003",
            error_detail="parse failure",
        )
        assert router.route(sig) == "coder"


# ---------------------------------------------------------------------------
# TC-SR-006: ErrorSignal from "ToolRegistry" -> "coder"
# ---------------------------------------------------------------------------

class TestRouterErrorFromToolRegistry:
    """TC-SR-006."""

    def test_toolregistry_error_routes_to_coder(self, router):
        sig = ErrorSignal(
            signal_id=make_signal_id(),
            author_role="ToolRegistry",
            target_id="call_codex",
            payload={},
            timestamp=now_utc(),
            round_number=1,
            error_code="SK_TR_001",
            error_detail="permission denied",
        )
        assert router.route(sig) == "coder"


# ---------------------------------------------------------------------------
# TC-SR-007: IntentSignal from "reviewer" -> None
# ---------------------------------------------------------------------------

class TestRouterIntentFromReviewer:
    """TC-SR-007."""

    def test_reviewer_intent_routes_to_none(self, router):
        sig = IntentSignal(
            signal_id=make_signal_id(),
            author_role="reviewer",
            target_id="task_root",
            payload={"action": "approve"},
            timestamp=now_utc(),
            round_number=1,
        )
        assert router.route(sig) is None


# ---------------------------------------------------------------------------
# TC-SR-008: Unknown combinations -> None
# ---------------------------------------------------------------------------

class TestRouterUnknownCombinations:
    """TC-SR-008."""

    def test_veto_from_coder_routes_to_none(self, router):
        sig = VetoSignal(
            signal_id=make_signal_id(),
            author_role="coder",
            target_id="task_root",
            payload={},
            timestamp=now_utc(),
            round_number=1,
            reason="self-reject",
        )
        assert router.route(sig) is None

    def test_error_from_unknown_role_routes_to_none(self, router):
        sig = ErrorSignal(
            signal_id=make_signal_id(),
            author_role="unknown_module",
            target_id="task_root",
            payload={},
            timestamp=now_utc(),
            round_number=1,
            error_code="SK_ERR_000",
            error_detail="unknown",
        )
        assert router.route(sig) is None

    def test_intent_from_tester_routes_to_none(self, router):
        sig = IntentSignal(
            signal_id=make_signal_id(),
            author_role="tester",
            target_id="task_root",
            payload={},
            timestamp=now_utc(),
            round_number=1,
        )
        assert router.route(sig) is None


# ---------------------------------------------------------------------------
# get_pending_targets
# ---------------------------------------------------------------------------

class TestRouterGetPendingTargets:
    """get_pending_targets returns list."""

    def test_get_pending_targets_returns_list(self, router):
        result = router.get_pending_targets()
        assert isinstance(result, list)