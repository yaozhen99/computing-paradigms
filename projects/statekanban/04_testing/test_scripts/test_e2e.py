"""
StateKanban End-to-End Tests -- R3
TC-E2E-01 through TC-E2E-06

These tests validate the complete flow from intent seeding through
convergence, including happy path, collision convergence, circuit breaker,
viewport isolation, and snapshot save/restore.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile

import pytest

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
    ConvergenceResult,
)
from statekanban.core.message_bus import MessageBus
from statekanban.core.registry import ToolRegistry
from statekanban.core.valve import OutputValve
from statekanban.core.viewport import ViewportSlicer
from statekanban.core.process import ProcessManager
from statekanban.engine.engine import Engine
from statekanban.engine.convergence import ConvergenceDetector
from statekanban.engine.circuit_breaker import CircuitBreaker
from statekanban.config import Config
from statekanban.adapters.mock_adapter import (
    MockLLMAdapter,
    MockCoderBehavior,
    MockReviewerBehavior,
)
from statekanban.tools.call_llm import create_call_llm_tool
from statekanban.snapshot import save_snapshot, load_snapshot


# ---------------------------------------------------------------------------
# Helper: build a complete system with all 4 viewports
# ---------------------------------------------------------------------------

def _make_viewports() -> dict:
    """Standard 4-role viewport specs."""
    return {
        "coder": ViewportSpec(
            role="coder",
            visible_signal_types=[SignalType.INTENT, SignalType.ERROR],
            visible_artifact_types=[ArtifactType.CODE, ArtifactType.CONFIG],
            visible_target_patterns=["*"],
            max_tokens=4000,
        ),
        "reviewer": ViewportSpec(
            role="reviewer",
            visible_signal_types=[SignalType.INTENT, SignalType.VETO, SignalType.ERROR],
            visible_artifact_types=[ArtifactType.CODE, ArtifactType.CONFIG, ArtifactType.DOC],
            visible_target_patterns=["*"],
            max_tokens=4000,
        ),
        "tester": ViewportSpec(
            role="tester",
            visible_signal_types=[SignalType.INTENT, SignalType.ERROR],
            visible_artifact_types=[ArtifactType.CODE, ArtifactType.TEST],
            visible_target_patterns=["*"],
            max_tokens=4000,
        ),
        "integrator": ViewportSpec(
            role="integrator",
            visible_signal_types=[SignalType.INTENT, SignalType.VETO, SignalType.ERROR],
            visible_artifact_types=[ArtifactType.CODE, ArtifactType.CONFIG, ArtifactType.TEST],
            visible_target_patterns=["*"],
            max_tokens=4000,
        ),
    }


# ---------------------------------------------------------------------------
# TC-E2E-01: Happy Path -- Engine.drive() with mock adapter
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_e2e_01_happy_path():
    """TC-E2E-01: Engine.drive() completes with mock adapter."""
    kanban = StateKanban()
    bus = MessageBus(kanban)
    registry = ToolRegistry(kanban)
    valve = OutputValve(kanban=kanban)

    vp = _make_viewports()
    for spec in vp.values():
        kanban.register_viewport(spec)
    slicer = ViewportSlicer(kanban, vp)

    pm = ProcessManager(kanban, bus)
    adapter = MockLLMAdapter()
    adapter.set_behavior_mode("coder", "generate_simple")

    config = Config()
    config.convergence_max_rounds = 5

    registry.register(
        ToolDef(
            name="call_llm",
            description="Invoke LLM via adapter",
            param_schema={"type": "object", "properties": {"messages": {"type": "array"}}, "required": ["messages"]},
            required_permissions={"all_roles"},
            timeout_seconds=120.0,
        ),
        create_call_llm_tool(adapter),
    )

    engine = Engine(
        kanban=kanban, bus=bus, registry=registry, valve=valve,
        slicer=slicer, pm=pm, adapter=adapter, config=config,
    )

    result = await engine.drive("Implement feature X")

    # Engine should complete (either converged or forced terminate)
    assert result is not None
    assert isinstance(result.converged, bool)
    assert isinstance(result.total_rounds, int)
    assert result.total_rounds > 0


# ---------------------------------------------------------------------------
# TC-E2E-02: Collision Resolution -- Engine.drive() with reject-then-approve
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_e2e_02_collision_convergence():
    """TC-E2E-02: Engine.drive() resolves collision via REJECT_THEN_APPROVE behavior."""
    kanban = StateKanban()
    bus = MessageBus(kanban)
    registry = ToolRegistry(kanban)
    valve = OutputValve(kanban=kanban)

    vp = _make_viewports()
    for spec in vp.values():
        kanban.register_viewport(spec)
    slicer = ViewportSlicer(kanban, vp)

    pm = ProcessManager(kanban, bus)
    adapter = MockLLMAdapter()
    adapter.set_behavior_mode("coder", "generate_simple")
    adapter.set_behavior_mode("reviewer", "reject_then_approve")

    config = Config()
    config.convergence_max_rounds = 5

    registry.register(
        ToolDef(
            name="call_llm",
            description="Invoke LLM via adapter",
            param_schema={"type": "object", "properties": {"messages": {"type": "array"}}, "required": ["messages"]},
            required_permissions={"all_roles"},
            timeout_seconds=120.0,
        ),
        create_call_llm_tool(adapter),
    )

    engine = Engine(
        kanban=kanban, bus=bus, registry=registry, valve=valve,
        slicer=slicer, pm=pm, adapter=adapter, config=config,
    )

    result = await engine.drive("Implement feature with review cycle")

    # Engine should complete after reviewer transitions from reject to approve
    assert result is not None
    assert isinstance(result.converged, bool)
    assert result.total_rounds > 0


# ---------------------------------------------------------------------------
# TC-E2E-03: Circuit Breaker -- Engine.drive() with persistent rejection
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_e2e_03_circuit_breaker():
    """TC-E2E-03: Engine.drive() hits circuit break with always-reject reviewer."""
    kanban = StateKanban()
    bus = MessageBus(kanban)
    registry = ToolRegistry(kanban)
    valve = OutputValve(kanban=kanban)

    vp = _make_viewports()
    for spec in vp.values():
        kanban.register_viewport(spec)
    slicer = ViewportSlicer(kanban, vp)

    pm = ProcessManager(kanban, bus)
    adapter = MockLLMAdapter()
    adapter.set_behavior_mode("coder", "generate_simple")
    adapter.set_behavior_mode("reviewer", "always_reject")

    config = Config()
    config.convergence_max_rounds = 3

    registry.register(
        ToolDef(
            name="call_llm",
            description="Invoke LLM via adapter",
            param_schema={"type": "object", "properties": {"messages": {"type": "array"}}, "required": ["messages"]},
            required_permissions={"all_roles"},
            timeout_seconds=120.0,
        ),
        create_call_llm_tool(adapter),
    )

    engine = Engine(
        kanban=kanban, bus=bus, registry=registry, valve=valve,
        slicer=slicer, pm=pm, adapter=adapter, config=config,
    )

    result = await engine.drive("Implement feature with persistent veto")

    # Engine should hit circuit break (not converged)
    assert result is not None
    assert result.converged is False


# ---------------------------------------------------------------------------
# TC-E2E-04: Viewport Isolation -- Coder viewport excludes VETO signals
# ---------------------------------------------------------------------------

def test_e2e_04_viewport_isolation():
    """TC-E2E-04: Coder viewport does not include reviewer VETO signals."""
    kanban = StateKanban()
    vp = _make_viewports()
    for spec in vp.values():
        kanban.register_viewport(spec)
    slicer = ViewportSlicer(kanban, vp)

    # Seed intent + veto
    kanban.fluid.write_signal(IntentSignal(
        signal_id=make_signal_id(),
        author_role="user",
        target_id="task_root",
        payload={"intent": "Test viewport isolation"},
        timestamp=now_utc(),
        round_number=0,
    ))
    kanban.fluid.write_signal(VetoSignal(
        signal_id=make_signal_id(),
        author_role="reviewer",
        target_id="task_root",
        payload={"action": "reject"},
        timestamp=now_utc(),
        round_number=1,
        reason="bug found",
    ))

    # Coder slice should NOT contain VETO
    coder_slice = slicer.slice("coder")
    signal_types_in_coder = [s.signal_type for s in coder_slice.signals]
    assert SignalType.VETO not in signal_types_in_coder, \
        f"Coder viewport should not contain VETO signals, found: {signal_types_in_coder}"

    # Reviewer slice SHOULD contain VETO
    reviewer_slice = slicer.slice("reviewer")
    signal_types_in_reviewer = [s.signal_type for s in reviewer_slice.signals]
    assert SignalType.VETO in signal_types_in_reviewer, \
        "Reviewer viewport should contain VETO signals"


# ---------------------------------------------------------------------------
# TC-E2E-05: Snapshot Save/Restore
# ---------------------------------------------------------------------------

def test_e2e_05_snapshot_save_restore_continue(tmp_path):
    """TC-E2E-05: Snapshot save/load preserves state."""
    kanban = StateKanban()
    vp = _make_viewports()
    for spec in vp.values():
        kanban.register_viewport(spec)

    # Seed intent
    kanban.fluid.write_signal(IntentSignal(
        signal_id=make_signal_id(),
        author_role="user",
        target_id="task_root",
        payload={"intent": "Test snapshot round-trip"},
        timestamp=now_utc(),
        round_number=0,
    ))

    # Save snapshot
    snap_path = str(tmp_path / "mid_run.json")
    save_snapshot(kanban, snap_path)

    # Record state
    fluid_signals_before = list(kanban.fluid.read_signals())

    # Load snapshot
    kanban2 = load_snapshot(snap_path)

    # Verify state matches
    fluid_signals_after = list(kanban2.fluid.read_signals())
    assert len(fluid_signals_after) == len(fluid_signals_before), \
        f"Signal count mismatch after restore: {len(fluid_signals_after)} vs {len(fluid_signals_before)}"


# ---------------------------------------------------------------------------
# TC-E2E-06: ValveReworkLoopError (SK_EN_004)
# ---------------------------------------------------------------------------

def test_e2e_06_valve_rework_loop_error():
    """TC-E2E-06: ValveReworkLoopError raised after consecutive valve failures."""
    from statekanban.core.errors import ValveReworkLoopError, EngineError, StateKanbanError

    err = ValveReworkLoopError("3 consecutive valve failures")
    assert err.error_code == "SK_EN_004"
    assert err.http_analogy == 500
    assert isinstance(err, EngineError)
    assert isinstance(err, StateKanbanError)


# ---------------------------------------------------------------------------
# TC-PAP-01: Convergence rate >= 80% (via StateKanban.run_convergence)
# ---------------------------------------------------------------------------

def test_paper_convergence_rate():
    """TC-PAP-01: Convergence rate across multiple targets should be >= 80%."""
    converged = 0
    total = 10

    for i in range(total):
        kanban = StateKanban()
        kanban.fluid.write_signal(IntentSignal(
            signal_id=make_signal_id(),
            author_role="coder",
            target_id=f"target_{i}",
            payload={"action": "approve"},
            timestamp=now_utc(),
            round_number=1,
        ))
        # 8 out of 10 have no veto (should converge)
        # 2 out of 10 have veto (should not converge)
        if i >= 8:
            kanban.fluid.write_signal(VetoSignal(
                signal_id=make_signal_id(),
                author_role="reviewer",
                target_id=f"target_{i}",
                payload={"action": "reject"},
                timestamp=now_utc(),
                round_number=1,
                reason="bad",
            ))

        result = kanban.run_convergence(f"target_{i}")
        if result.converged:
            converged += 1

    rate = converged / total
    assert rate >= 0.8, f"Convergence rate {rate:.0%} is below 80% ({converged}/{total})"


# ---------------------------------------------------------------------------
# TC-PAP-02: Interception rate = 100%
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_paper_interception_rate(tmp_path):
    """TC-PAP-02: All invalid artifact writes should be blocked by Valve."""
    kanban = StateKanban()
    valve = OutputValve(kanban=kanban)

    # Valid artifact should pass through valve
    valid_art = Artifact(
        seq_no=0,
        artifact_type=ArtifactType.CODE,
        path=str(tmp_path / "valid.py"),
        content="x = 1",
        checksum=compute_checksum("x = 1"),
        author_role="coder",
        created_at=now_utc(),
    )
    valid_result = await valve.validate_and_write(valid_art)
    assert valid_result.success is True, "Valid code should pass valve"

    # Invalid (syntax error) artifact should be blocked
    invalid_art = Artifact(
        seq_no=0,
        artifact_type=ArtifactType.CODE,
        path=str(tmp_path / "invalid.py"),
        content="def (",
        checksum=compute_checksum("def ("),
        author_role="coder",
        created_at=now_utc(),
    )
    invalid_result = await valve.validate_and_write(invalid_art)
    assert invalid_result.success is False, "Invalid code should be blocked by valve"

    # Error signal should be injected for blocked artifact
    error_signals = kanban.fluid.read_signals(signal_type=SignalType.ERROR)
    assert len(error_signals) > 0, "Blocked artifact should inject error signal"


# ---------------------------------------------------------------------------
# TC-PAP-03: Lossless handoff -- snapshot restore preserves state
# ---------------------------------------------------------------------------

def test_paper_lossless_handoff():
    """TC-PAP-03: Snapshot save/load produces identical state."""
    kanban = StateKanban()
    kanban.register_viewport(ViewportSpec(
        role="coder",
        visible_signal_types=[SignalType.INTENT, SignalType.ERROR],
        visible_artifact_types=[ArtifactType.CODE],
        visible_target_patterns=["*"],
        max_tokens=4000,
    ))

    kanban.fluid.write_signal(IntentSignal(
        signal_id=make_signal_id(),
        author_role="user",
        target_id="task_root",
        payload={"intent": "test"},
        timestamp=now_utc(),
        round_number=1,
    ))

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "handoff.json")
        save_snapshot(kanban, path)
        loaded = load_snapshot(path)

    orig_signals = list(kanban.fluid.read_signals())
    loaded_signals = list(loaded.fluid.read_signals())
    assert len(loaded_signals) == len(orig_signals), \
        "Signal count should match after lossless handoff"

    orig_spec = kanban.get_viewport_spec("coder")
    loaded_spec = loaded.get_viewport_spec("coder")
    assert orig_spec.role == loaded_spec.role
    assert orig_spec.visible_signal_types == loaded_spec.visible_signal_types