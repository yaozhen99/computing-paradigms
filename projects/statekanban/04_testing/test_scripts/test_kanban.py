"""
StateKanban Core Regression Tests -- R3
TC-REG-01 through TC-REG-12

Regression tests ensuring R1/R2 core functionality still works:
StateKanban, FluidZone, CrystalZone, AuditZone, ViewportSpec, OutputValve.
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
from statekanban.core.errors import (
    InvalidSignalError,
    SignalCollisionError,
    AppendOnlyViolationError,
    ArtifactConflictError,
)
from statekanban.core.valve import OutputValve
from statekanban.core.viewport import ViewportSlicer
from statekanban.core.message_bus import MessageBus
from statekanban.core.process import ProcessManager
from statekanban.core.registry import ToolRegistry


# ---------------------------------------------------------------------------
# TC-REG-01: FluidZone write_signal and read_signals
# ---------------------------------------------------------------------------

class TestFluidZoneRegression:

    def test_write_and_read_signal(self):
        """TC-REG-01: FluidZone write_signal / read_signals round-trip."""
        kanban = StateKanban()
        sig = IntentSignal(
            signal_id=make_signal_id(),
            author_role="user",
            target_id="task_root",
            payload={"intent": "test"},
            timestamp=now_utc(),
            round_number=0,
        )
        kanban.fluid.write_signal(sig)
        signals = list(kanban.fluid.read_signals())
        assert len(signals) == 1
        assert signals[0].signal_id == sig.signal_id

    def test_read_signals_with_type_filter(self):
        """FluidZone read_signals filters by signal type."""
        kanban = StateKanban()

        intent = IntentSignal(
            signal_id=make_signal_id(),
            author_role="user",
            target_id="task_root",
            payload={"intent": "test"},
            timestamp=now_utc(),
            round_number=0,
        )
        error = ErrorSignal(
            signal_id=make_signal_id(),
            author_role="coder",
            target_id="task_root",
            payload={"error": "something failed"},
            timestamp=now_utc(),
            round_number=1,
            error_code="SK_TEST_001",
        )
        kanban.fluid.write_signal(intent)
        kanban.fluid.write_signal(error)

        all_signals = list(kanban.fluid.read_signals())
        assert len(all_signals) == 2

        intent_signals = list(kanban.fluid.read_signals(signal_type=SignalType.INTENT))
        assert len(intent_signals) == 1
        assert intent_signals[0].signal_type == SignalType.INTENT

        error_signals = list(kanban.fluid.read_signals(signal_type=SignalType.ERROR))
        assert len(error_signals) == 1
        assert error_signals[0].signal_type == SignalType.ERROR

    def test_clear_signals(self):
        """FluidZone clear_signals removes signals for a target/round."""
        kanban = StateKanban()
        sig = IntentSignal(
            signal_id=make_signal_id(),
            author_role="user",
            target_id="task_root",
            payload={"intent": "test"},
            timestamp=now_utc(),
            round_number=0,
        )
        kanban.fluid.write_signal(sig)
        assert len(list(kanban.fluid.read_signals())) == 1

        kanban.fluid.clear_signals("task_root", round_number_ge=0)
        assert len(list(kanban.fluid.read_signals())) == 0


# ---------------------------------------------------------------------------
# TC-REG-02: CrystalZone write_artifact and read_artifacts
# ---------------------------------------------------------------------------

class TestCrystalZoneRegression:

    def test_write_and_read_artifact(self):
        """TC-REG-02: CrystalZone append / read_artifacts round-trip."""
        kanban = StateKanban()
        art = Artifact(
            seq_no=0,
            artifact_type=ArtifactType.CODE,
            path="test.py",
            content="x = 1",
            checksum=compute_checksum("x = 1"),
            author_role="coder",
            created_at=now_utc(),
        )
        kanban.crystal.append(art)
        artifacts = kanban.crystal.read_artifacts()
        assert len(artifacts) == 1
        assert artifacts[0].path == "test.py"


# ---------------------------------------------------------------------------
# TC-REG-03: AuditZone write and read
# ---------------------------------------------------------------------------

class TestAuditZoneRegression:

    def test_audit_write_and_read(self):
        """TC-REG-03: AuditZone log / read_entries round-trip."""
        kanban = StateKanban()
        kanban.audit.log(
            event_type="test_event",
            actor="tester",
            action="test_action",
            details={"key": "value"},
        )
        entries = kanban.audit.read_entries()
        assert len(entries) >= 1

    def test_audit_read_with_filter(self):
        """AuditZone read_entries filters by event_type."""
        kanban = StateKanban()
        kanban.audit.log(event_type="type_a", actor="alice", action="act", details={"x": 1})
        kanban.audit.log(event_type="type_b", actor="bob", action="act", details={"y": 2})

        a_entries = kanban.audit.read_entries(event_type="type_a")
        assert len(a_entries) >= 1
        for e in a_entries:
            assert e.event_type == "type_a"


# ---------------------------------------------------------------------------
# TC-REG-04: ViewportSpec and ViewportSlicer
# ---------------------------------------------------------------------------

class TestViewportRegression:

    def test_viewport_spec_registration(self):
        """TC-REG-04: ViewportSpec can be registered and retrieved."""
        kanban = StateKanban()
        spec = ViewportSpec(
            role="coder",
            visible_signal_types=[SignalType.INTENT, SignalType.ERROR],
            visible_artifact_types=[ArtifactType.CODE],
            visible_target_patterns=["*"],
            max_tokens=4000,
        )
        kanban.register_viewport(spec)
        retrieved = kanban.get_viewport_spec("coder")
        assert retrieved is not None
        assert retrieved.role == "coder"

    def test_viewport_slicer_filters_signals(self):
        """ViewportSlicer filters signals by role's visibility."""
        kanban = StateKanban()
        spec = ViewportSpec(
            role="coder",
            visible_signal_types=[SignalType.INTENT, SignalType.ERROR],
            visible_artifact_types=[ArtifactType.CODE],
            visible_target_patterns=["*"],
            max_tokens=4000,
        )
        kanban.register_viewport(spec)
        slicer = ViewportSlicer(kanban, {"coder": spec})

        # Add intent and veto
        intent = IntentSignal(
            signal_id=make_signal_id(),
            author_role="user",
            target_id="task_root",
            payload={"intent": "test"},
            timestamp=now_utc(),
            round_number=0,
        )
        veto = VetoSignal(
            signal_id=make_signal_id(),
            author_role="reviewer",
            target_id="task_root",
            payload={"action": "reject"},
            timestamp=now_utc(),
            round_number=1,
            reason="bug found",
        )
        kanban.fluid.write_signal(intent)
        kanban.fluid.write_signal(veto)

        slice_data = slicer.slice("coder")
        signal_types = [s.signal_type for s in slice_data.signals]
        # Coder should see INTENT but NOT VETO
        assert SignalType.INTENT in signal_types
        assert SignalType.VETO not in signal_types


# ---------------------------------------------------------------------------
# TC-REG-05: OutputValve validation
# ---------------------------------------------------------------------------

class TestValveRegression:

    @pytest.mark.asyncio
    async def test_valve_accepts_valid_artifact(self, tmp_path):
        """TC-REG-05: OutputValve accepts valid Python code."""
        kanban = StateKanban()
        valve = OutputValve(kanban=kanban)

        art = Artifact(
            seq_no=0,
            artifact_type=ArtifactType.CODE,
            path=str(tmp_path / "valid.py"),
            content="x = 1",
            checksum=compute_checksum("x = 1"),
            author_role="coder",
            created_at=now_utc(),
        )
        result = await valve.validate_and_write(art)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_valve_rejects_syntax_error(self, tmp_path):
        """OutputValve rejects code with syntax errors."""
        kanban = StateKanban()
        valve = OutputValve(kanban=kanban)

        art = Artifact(
            seq_no=0,
            artifact_type=ArtifactType.CODE,
            path=str(tmp_path / "bad.py"),
            content="def (",
            checksum=compute_checksum("def ("),
            author_role="coder",
            created_at=now_utc(),
        )
        result = await valve.validate_and_write(art)
        assert result.success is False


# ---------------------------------------------------------------------------
# TC-REG-06: ToolRegistry register and dispatch
# ---------------------------------------------------------------------------

class TestToolRegistryRegression:

    @pytest.mark.asyncio
    async def test_register_and_dispatch(self):
        """TC-REG-06: ToolRegistry can register and dispatch tools."""
        kanban = StateKanban()
        registry = ToolRegistry(kanban)

        async def echo(params):
            return {"echo": params}

        registry.register(
            ToolDef(
                name="echo_tool",
                description="Echo tool",
                param_schema={"type": "object"},
                required_permissions={"coder"},
                timeout_seconds=30.0,
            ),
            echo,
        )
        result = await registry.dispatch("echo_tool", "coder", {"msg": "hello"})
        assert result.success is True
        assert result.output["echo"]["msg"] == "hello"


# ---------------------------------------------------------------------------
# TC-REG-07: MessageBus
# ---------------------------------------------------------------------------

class TestMessageBusRegression:

    def test_message_bus_instantiation(self):
        """TC-REG-07: MessageBus can be instantiated with kanban."""
        kanban = StateKanban()
        bus = MessageBus(kanban)
        assert bus is not None


# ---------------------------------------------------------------------------
# TC-REG-08: ProcessManager
# ---------------------------------------------------------------------------

class TestProcessManagerRegression:

    def test_process_manager_instantiation(self):
        """TC-REG-08: ProcessManager can be instantiated."""
        kanban = StateKanban()
        bus = MessageBus(kanban)
        pm = ProcessManager(kanban, bus)
        assert pm is not None


# ---------------------------------------------------------------------------
# TC-REG-09: StateKanban to_json / from_json round-trip
# ---------------------------------------------------------------------------

class TestStateKanbanJsonRoundTrip:

    def test_to_json_and_from_json(self):
        """TC-REG-09: StateKanban to_json/from_json preserves state."""
        kanban = StateKanban()
        kanban.register_viewport(ViewportSpec(
            role="coder",
            visible_signal_types=[SignalType.INTENT],
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
            round_number=0,
        ))

        data = kanban.to_json()
        restored = StateKanban.from_json(data)

        orig_signals = list(kanban.fluid.read_signals())
        restored_signals = list(restored.fluid.read_signals())
        assert len(restored_signals) == len(orig_signals)


# ---------------------------------------------------------------------------
# TC-REG-10: Signal ID uniqueness
# ---------------------------------------------------------------------------

class TestSignalIdUniqueness:

    def test_make_signal_id_unique(self):
        """TC-REG-10: make_signal_id generates unique IDs."""
        ids = set()
        for _ in range(100):
            sid = make_signal_id()
            assert sid not in ids, f"Duplicate signal ID: {sid}"
            ids.add(sid)


# ---------------------------------------------------------------------------
# TC-REG-11: ArtifactType enum values
# ---------------------------------------------------------------------------

class TestArtifactTypeRegression:

    def test_artifact_type_values(self):
        """TC-REG-11: ArtifactType has expected values."""
        expected = {"CODE", "CONFIG", "DOC", "TEST"}
        actual = {t.name for t in ArtifactType}
        assert expected.issubset(actual), f"Missing ArtifactType values: {expected - actual}"


# ---------------------------------------------------------------------------
# TC-REG-12: SignalType enum values
# ---------------------------------------------------------------------------

class TestSignalTypeRegression:

    def test_signal_type_values(self):
        """TC-REG-12: SignalType has expected values."""
        expected = {"INTENT", "VETO", "ERROR"}
        actual = {t.name for t in SignalType}
        assert expected.issubset(actual), f"Missing SignalType values: {expected - actual}"