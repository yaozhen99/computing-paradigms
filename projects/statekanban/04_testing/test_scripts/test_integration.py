"""
StateKanban Integration Tests -- R3
TC-INT-01 through TC-INT-07

Tests for multi-component interactions: Engine+Adapter, Engine+Registry,
ConvergenceDetector, CircuitBreaker, ResponseParser, and full pipeline.
"""

from __future__ import annotations

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
    LLMResponse,
)
from statekanban.core.message_bus import MessageBus
from statekanban.core.registry import ToolRegistry
from statekanban.core.valve import OutputValve
from statekanban.core.viewport import ViewportSlicer
from statekanban.core.process import ProcessManager
from statekanban.engine.engine import Engine
from statekanban.engine.response_parser import ResponseParser
from statekanban.engine.convergence import ConvergenceDetector
from statekanban.engine.circuit_breaker import CircuitBreaker
from statekanban.config import Config
from statekanban.adapters.mock_adapter import (
    MockLLMAdapter,
    MockCoderBehavior,
    MockReviewerBehavior,
)
from statekanban.tools.call_llm import create_call_llm_tool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_engine(
    coder_behavior=MockCoderBehavior.GENERATE_SIMPLE,
    reviewer_behavior=MockReviewerBehavior.ALWAYS_APPROVE,
    max_rounds=5,
) -> Engine:
    """Build a configured Engine with all dependencies."""
    k = StateKanban()
    b = MessageBus(k)
    r = ToolRegistry(k)
    v = OutputValve(kanban=k)

    specs = {
        "coder": ViewportSpec(
            role="coder",
            visible_signal_types=[SignalType.INTENT, SignalType.ERROR],
            visible_artifact_types=[ArtifactType.CODE],
            visible_target_patterns=["*"],
            max_tokens=4000,
        ),
        "reviewer": ViewportSpec(
            role="reviewer",
            visible_signal_types=[SignalType.INTENT, SignalType.VETO, SignalType.ERROR],
            visible_artifact_types=[ArtifactType.CODE],
            visible_target_patterns=["*"],
            max_tokens=4000,
        ),
    }
    for spec in specs.values():
        k.register_viewport(spec)
    s = ViewportSlicer(k, specs)

    p = ProcessManager(k, b)
    a = MockLLMAdapter()
    if coder_behavior is not None:
        a.set_behavior_mode(coder_behavior)
    if reviewer_behavior is not None:
        a.set_behavior_mode(reviewer_behavior)

    c = Config()
    c.convergence_max_rounds = max_rounds

    e = Engine(
        kanban=k,
        bus=b,
        registry=r,
        valve=v,
        slicer=s,
        pm=p,
        adapter=a,
        config=c,
    )

    r.register(
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
        create_call_llm_tool(a),
    )

    return e


# ---------------------------------------------------------------------------
# TC-INT-01: Engine + Adapter integration
# ---------------------------------------------------------------------------

class TestEngineAdapterIntegration:

    @pytest.mark.asyncio
    async def test_engine_calls_adapter(self):
        """TC-INT-01: Engine.drive() invokes the LLM adapter."""
        engine = _build_engine()
        kanban = engine._kanban

        result = await engine.drive("Write a hello function")

        # Adapter should have been called
        adapter = engine._adapter
        total_calls = sum(adapter._call_counts.values())
        assert total_calls > 0, "Adapter should have been called during engine drive"


# ---------------------------------------------------------------------------
# TC-INT-02: Engine + Registry integration
# ---------------------------------------------------------------------------

class TestEngineRegistryIntegration:

    @pytest.mark.asyncio
    async def test_engine_uses_registry_for_llm(self):
        """TC-INT-02: When use_registry_for_llm=True, engine dispatches through registry."""
        engine = _build_engine()
        kanban = engine._kanban

        await engine.drive("Test registry dispatch")

        # Audit zone should have tool_call entries
        entries = kanban.audit.read_entries(event_type="tool_call")
        assert len(entries) > 0, "Registry dispatch should produce audit entries"


# ---------------------------------------------------------------------------
# TC-INT-03: ConvergenceDetector
# ---------------------------------------------------------------------------

class TestConvergenceDetectorIntegration:

    def test_convergence_detector_instantiation(self):
        """TC-INT-03: ConvergenceDetector can be instantiated with kanban."""
        kanban = StateKanban()
        cd = ConvergenceDetector(kanban=kanban)
        assert cd is not None

    def test_convergence_detected_with_intent_only(self):
        """Intent without veto means convergence on a target."""
        kanban = StateKanban()
        cd = ConvergenceDetector(kanban=kanban)

        kanban.fluid.write_signal(IntentSignal(
            signal_id=make_signal_id(),
            author_role="coder",
            target_id="target_X",
            payload={"action": "approve"},
            timestamp=now_utc(),
            round_number=1,  # Must match the check round
        ))

        result = cd.check("target_X", current_round=1)
        assert result.converged is True


# ---------------------------------------------------------------------------
# TC-INT-04: CircuitBreaker
# ---------------------------------------------------------------------------

class TestCircuitBreakerIntegration:

    def test_circuit_breaker_instantiation(self):
        """TC-INT-04: CircuitBreaker can be instantiated."""
        cb = CircuitBreaker()
        assert cb is not None

    @pytest.mark.asyncio
    async def test_circuit_breaker_trips_on_persistent_failure(self):
        """Circuit breaker trips after persistent failures."""
        engine = _build_engine(
            coder_behavior=MockCoderBehavior.GENERATE_SIMPLE,
            reviewer_behavior=MockReviewerBehavior.ALWAYS_REJECT,
            max_rounds=3,
        )
        result = await engine.drive("Write code that keeps getting rejected")
        assert result is not None
        assert result.forced_terminate is True, \
            "Engine should force-terminate when circuit breaker trips"


# ---------------------------------------------------------------------------
# TC-INT-05: ResponseParser
# ---------------------------------------------------------------------------

class TestResponseParserIntegration:

    def test_parser_handles_unstructured_response(self):
        """TC-INT-05: ResponseParser handles unstructured LLM response."""
        kanban = StateKanban()
        parser = ResponseParser(kanban=kanban)

        raw = LLMResponse(content="Just plain text", finish_reason="end_turn")
        results = parser.parse(raw, "coder", 1)

        assert len(results) > 0, "Parser should produce at least one result"

    def test_parser_injects_error_on_unstructured(self):
        """Unstructured response from coder injects error signal into kanban."""
        kanban = StateKanban()
        parser = ResponseParser(kanban=kanban)

        raw = LLMResponse(content="Just plain text", finish_reason="end_turn")
        parser.parse(raw, "coder", 1)

        error_signals = list(kanban.fluid.read_signals(signal_type=SignalType.ERROR))
        assert len(error_signals) > 0, "Unstructured response should inject error signal"


# ---------------------------------------------------------------------------
# TC-INT-06: Full pipeline (seed -> process -> valve)
# ---------------------------------------------------------------------------

class TestFullPipelineIntegration:

    @pytest.mark.asyncio
    async def test_seed_and_process_role(self):
        """TC-INT-06: _seed_intent + _process_role produces signals."""
        engine = _build_engine()
        kanban = engine._kanban

        await engine._seed_intent("Write a function")
        signals_before = list(kanban.fluid.read_signals())

        # Intent should be seeded
        assert len(signals_before) > 0, "Intent should be seeded"

    @pytest.mark.asyncio
    async def test_process_role_updates_fluid(self):
        """Processing a role adds signals to fluid zone."""
        engine = _build_engine()
        kanban = engine._kanban

        await engine._seed_intent("Write a function")
        await engine._process_role("coder", 1)

        # After processing, fluid zone should have signals
        signals = list(kanban.fluid.read_signals())
        assert len(signals) > 0


# ---------------------------------------------------------------------------
# TC-INT-07: Valve + Artifact interaction
# ---------------------------------------------------------------------------

class TestValveArtifactIntegration:

    @pytest.mark.asyncio
    async def test_valve_blocks_invalid_artifact(self, tmp_path):
        """TC-INT-07: Valve blocks artifacts with invalid syntax."""
        kanban = StateKanban()
        valve = OutputValve(kanban=kanban)

        # Valid Python artifact
        valid_art = Artifact(
            seq_no=0,
            artifact_type=ArtifactType.CODE,
            path=str(tmp_path / "valid.py"),
            content="x = 1",
            checksum=compute_checksum("x = 1"),
            author_role="coder",
            created_at=now_utc(),
        )
        result = await valve.validate_and_write(valid_art)
        assert result.success is True

        # Invalid Python artifact (syntax error)
        invalid_art = Artifact(
            seq_no=0,
            artifact_type=ArtifactType.CODE,
            path=str(tmp_path / "invalid.py"),
            content="def (",
            checksum=compute_checksum("def ("),
            author_role="coder",
            created_at=now_utc(),
        )
        result = await valve.validate_and_write(invalid_art)
        assert result.success is False

    @pytest.mark.asyncio
    async def test_valve_error_injects_signal(self, tmp_path):
        """Blocked artifact injects error signal into kanban."""
        kanban = StateKanban()
        valve = OutputValve(kanban=kanban)

        invalid_art = Artifact(
            seq_no=0,
            artifact_type=ArtifactType.CODE,
            path=str(tmp_path / "bad.py"),
            content="def (",
            checksum=compute_checksum("def ("),
            author_role="coder",
            created_at=now_utc(),
        )
        await valve.validate_and_write(invalid_art)

        error_signals = kanban.fluid.read_signals(signal_type=SignalType.ERROR)
        assert len(error_signals) > 0, "Valve should inject error signal on rejection"