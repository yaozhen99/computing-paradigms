"""
StateKanban Test Fixtures -- R6
Shared fixtures for all test modules (R1, R2, R3, R4, R5, R6).
"""

from __future__ import annotations

import os
import tempfile

import pytest


# ---------------------------------------------------------------------------
# Business code hotfix: snapshot.py missing 'import tempfile'
# The backend code in 05_delivery/statekanban/snapshot.py uses
# tempfile.mkstemp but forgot to import tempfile at module level.
# This patch injects the module until the backend is fixed.
# ---------------------------------------------------------------------------
import statekanban.snapshot as _snapshot_mod
if not hasattr(_snapshot_mod, 'tempfile') or _snapshot_mod.tempfile is None:
    _snapshot_mod.tempfile = tempfile


def pytest_addoption(parser):
    """Add --run-live flag for real API smoke tests."""
    parser.addoption(
        "--run-live",
        action="store_true",
        default=False,
        help="Run live API smoke tests (requires ANTHROPIC_API_KEY)",
    )


def pytest_configure(config):
    """Register the live_api marker."""
    config.addinivalue_line(
        "markers",
        "live_api: marks tests as live API smoke tests (deselect with '-m \"not live_api\"')",
    )


def pytest_collection_modifyitems(config, items):
    """Skip live_api tests unless --run-live is passed."""
    if config.getoption("--run-live"):
        return
    skip_live = pytest.mark.skip(reason="need --run-live option to run")
    for item in items:
        if "live_api" in item.keywords:
            item.add_marker(skip_live)


from statekanban.core.kanban import (
    Artifact,
    ArtifactType,
    IntentSignal,
    VetoSignal,
    ErrorSignal,
    SignalType,
    StateKanban,
    ViewportSpec,
    make_signal_id,
    now_utc,
    compute_checksum,
    ToolDef,
    LLMMessage,
)
from statekanban.core.message_bus import MessageBus
from statekanban.core.registry import ToolRegistry
from statekanban.core.valve import OutputValve
from statekanban.core.viewport import ViewportSlicer
from statekanban.core.process import ProcessManager
from statekanban.engine.engine import Engine
from statekanban.engine.convergence import ConvergenceDetector
from statekanban.engine.circuit_breaker import CircuitBreaker
from statekanban.engine.response_parser import ResponseParser
from statekanban.engine.result import ResultSummarizer
from statekanban.engine.router import SignalRouter
from statekanban.engine.scheduler import RoleScheduler
from statekanban.config import Config
from statekanban.adapters.mock_adapter import (
    MockLLMAdapter,
    MockCoderBehavior,
    MockReviewerBehavior,
)
from statekanban.tools.call_llm import create_call_llm_tool

# ---------------------------------------------------------------------------
# Core fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def kanban():
    """Fresh StateKanban instance with standard viewports."""
    k = StateKanban()
    k.register_viewport(
        ViewportSpec(
            role="coder",
            visible_signal_types=[SignalType.INTENT, SignalType.ERROR],
            visible_artifact_types=[ArtifactType.CODE, ArtifactType.CONFIG],
            visible_target_patterns=["*"],
            max_tokens=4000,
        )
    )
    k.register_viewport(
        ViewportSpec(
            role="reviewer",
            visible_signal_types=[SignalType.INTENT, SignalType.VETO, SignalType.ERROR],
            visible_artifact_types=[
                ArtifactType.CODE,
                ArtifactType.CONFIG,
                ArtifactType.DOC,
            ],
            visible_target_patterns=["*"],
            max_tokens=4000,
        )
    )
    k.register_viewport(
        ViewportSpec(
            role="tester",
            visible_signal_types=[SignalType.INTENT, SignalType.ERROR],
            visible_artifact_types=[ArtifactType.CODE, ArtifactType.TEST],
            visible_target_patterns=["*"],
            max_tokens=4000,
        )
    )
    k.register_viewport(
        ViewportSpec(
            role="integrator",
            visible_signal_types=[SignalType.INTENT, SignalType.VETO, SignalType.ERROR],
            visible_artifact_types=[
                ArtifactType.CODE,
                ArtifactType.CONFIG,
                ArtifactType.TEST,
            ],
            visible_target_patterns=["*"],
            max_tokens=4000,
        )
    )
    return k


@pytest.fixture
def bus(kanban):
    return MessageBus(kanban)


@pytest.fixture
def registry(kanban):
    return ToolRegistry(kanban)


@pytest.fixture
def valve(kanban):
    return OutputValve(kanban=kanban)


@pytest.fixture
def slicer(kanban):
    specs = {
        "coder": kanban.get_viewport_spec("coder"),
        "reviewer": kanban.get_viewport_spec("reviewer"),
        "tester": kanban.get_viewport_spec("tester"),
        "integrator": kanban.get_viewport_spec("integrator"),
    }
    return ViewportSlicer(kanban, specs)


@pytest.fixture
def pm(kanban, bus):
    return ProcessManager(kanban, bus)


@pytest.fixture
def adapter():
    return MockLLMAdapter()


@pytest.fixture
def config():
    c = Config()
    c.convergence_max_rounds = 5
    return c


@pytest.fixture
def engine(kanban, bus, registry, valve, slicer, pm, adapter, config):
    """Engine with call_llm tool registered."""
    registry.register(
        ToolDef(
            name="call_llm",
            description="Invoke LLM via adapter",
            param_schema={
                "type": "object",
                "properties": {"messages": {"type": "array"}},
                "required": ["messages"],
            },
            required_permissions={"all_roles"},
            timeout_seconds=120.0,
        ),
        create_call_llm_tool(adapter),
    )
    return Engine(
        kanban=kanban,
        bus=bus,
        registry=registry,
        valve=valve,
        slicer=slicer,
        pm=pm,
        adapter=adapter,
        config=config,
    )


# ---------------------------------------------------------------------------
# R1/R2 engine component fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def breaker():
    """CircuitBreaker with default max_rounds=10."""
    return CircuitBreaker()


@pytest.fixture
def breaker_3():
    """CircuitBreaker with custom max_rounds=3."""
    return CircuitBreaker(max_rounds=3)


@pytest.fixture
def convergence_detector(kanban):
    """ConvergenceDetector bound to the kanban fixture."""
    return ConvergenceDetector(kanban=kanban)


@pytest.fixture
def parser(kanban):
    """ResponseParser bound to the kanban fixture."""
    return ResponseParser(kanban=kanban)


@pytest.fixture
def summarizer(kanban, pm):
    """ResultSummarizer bound to kanban and process manager."""
    return ResultSummarizer(kanban=kanban, pm=pm)


@pytest.fixture
def router(pm):
    """SignalRouter bound to process manager."""
    return SignalRouter(pm=pm)


@pytest.fixture
def scheduler():
    """RoleScheduler with default order."""
    return RoleScheduler()


@pytest.fixture
def fluid(kanban):
    """FluidZone from the kanban fixture."""
    return kanban.fluid


@pytest.fixture
def crystal():
    """Fresh CrystalZone instance."""
    from statekanban.core.kanban import CrystalZone

    return CrystalZone()


@pytest.fixture
def audit():
    """Fresh AuditZone instance."""
    from statekanban.core.kanban import AuditZone

    return AuditZone()


@pytest.fixture
def tmp_dir():
    """Temporary directory for file-based tests."""
    with tempfile.TemporaryDirectory() as d:
        yield d


# ---------------------------------------------------------------------------
# Signal factory fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def make_intent():
    """Factory for creating IntentSignal instances."""

    def _make(
        role=None,
        target="task_root",
        payload=None,
        round_num=0,
        target_id=None,
        author_role=None,
        signal_id=None,
        reason=None,
        round_number=None,
    ):
        # R1/R2 compat: target_id -> target, author_role -> role, round_number -> round_num
        effective_target = target_id if target_id is not None else target
        effective_role = author_role if author_role is not None else (role or "user")
        effective_sid = signal_id or make_signal_id()
        effective_round = round_number if round_number is not None else round_num
        return IntentSignal(
            signal_id=effective_sid,
            author_role=effective_role,
            target_id=effective_target,
            payload=payload or {"intent": "test intent"},
            timestamp=now_utc(),
            round_number=effective_round,
        )

    return _make


@pytest.fixture
def make_veto():
    """Factory for creating VetoSignal instances."""

    def _make(
        role=None,
        target="task_root",
        reason="rejected",
        round_num=1,
        target_id=None,
        author_role=None,
        round_number=None,
    ):
        # R1/R2 compat: target_id -> target, author_role -> role, round_number -> round_num
        effective_target = target_id if target_id is not None else target
        effective_role = (
            author_role if author_role is not None else (role or "reviewer")
        )
        effective_round = round_number if round_number is not None else round_num
        return VetoSignal(
            signal_id=make_signal_id(),
            author_role=effective_role,
            target_id=effective_target,
            payload={"action": "reject"},
            timestamp=now_utc(),
            round_number=effective_round,
            reason=reason,
        )

    return _make


@pytest.fixture
def make_error():
    """Factory for creating ErrorSignal instances."""

    def _make(role="coder", target="task_root", error_code="SK_TEST_001", round_num=1):
        return ErrorSignal(
            signal_id=make_signal_id(),
            author_role=role,
            target_id=target,
            payload={"error": "test error"},
            timestamp=now_utc(),
            round_number=round_num,
            error_code=error_code,
        )

    return _make


@pytest.fixture
def make_error_signal():
    """Factory for creating ErrorSignal instances (R1/R2 compat, error_code=SK_OV_001)."""

    def _make(
        role="coder",
        target="task_root",
        error_code="SK_OV_001",
        round_num=1,
        round_number=None,
    ):
        effective_round = round_number if round_number is not None else round_num
        return ErrorSignal(
            signal_id=make_signal_id(),
            author_role=role,
            target_id=target,
            payload={"error": "test error"},
            timestamp=now_utc(),
            round_number=effective_round,
            error_code=error_code,
        )

    return _make


# ---------------------------------------------------------------------------
# Artifact factory fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def make_code_artifact():
    """Factory for creating Artifact instances."""

    def _make(content="x = 1", path="test.py", role="coder"):
        return Artifact(
            seq_no=0,
            artifact_type=ArtifactType.CODE,
            path=path,
            content=content,
            checksum=compute_checksum(content),
            author_role=role,
            created_at=now_utc(),
        )

    return _make


@pytest.fixture
def make_artifact():
    """Factory for creating Artifact instances for CrystalZone (R1/R2 compat)."""

    def _make(
        content="x = 1",
        path="test.py",
        role="coder",
        artifact_type=ArtifactType.CODE,
        seq_no=-1,
        author_role=None,
    ):
        effective_role = author_role if author_role is not None else role
        return Artifact(
            seq_no=seq_no,
            artifact_type=artifact_type,
            path=path,
            content=content,
            checksum=compute_checksum(content),
            author_role=effective_role,
            created_at=now_utc(),
        )

    return _make
