"""Integration tests: full pipeline, convergence, metrics, bootstrap."""

from __future__ import annotations

import os
import tempfile

import pytest

from statekanban.core.errors import PermissionDeniedError
from statekanban.core.kanban import (
    Artifact,
    ArtifactType,
    IntentSignal,
    SignalType,
    StateKanban,
    ToolDef,
    VetoSignal,
    ViewportSpec,
    compute_checksum,
    make_signal_id,
    now_utc,
)
from statekanban.core.message_bus import MessageBus
from statekanban.core.process import ProcessManager
from statekanban.core.registry import ToolRegistry
from statekanban.core.valve import OutputValve
from statekanban.core.viewport import ViewportSlicer
from statekanban.config import Config


class TestFullWritePipeline:
    """TC-INT-001 ~ TC-INT-003: Full write pipeline integration."""

    @pytest.mark.asyncio
    async def test_valid_write_pipeline(self, tmp_dir):
        # TC-INT-001: ToolRegistry -> OutputValve -> filesystem
        kanban = StateKanban()
        registry = ToolRegistry(kanban)
        valve = OutputValve(kanban=kanban)

        # Register write_file tool
        async def write_impl(params: dict) -> dict:
            art = Artifact(
                seq_no=0,
                artifact_type=ArtifactType.CODE,
                path=params["path"],
                content=params["content"],
                checksum=compute_checksum(params["content"]),
                author_role=params.get("author_role", "coder"),
                created_at=now_utc(),
            )
            result = await valve.validate_and_write(art)
            return {"success": result.success, "path": result.artifact_path}

        tool_def = ToolDef(
            name="write_file",
            description="Write file",
            param_schema={},
            required_permissions={"coder", "integrator"},
        )
        registry.register(tool_def, write_impl)

        path = os.path.join(tmp_dir, "output.py")
        result = await registry.dispatch("write_file", "coder", {
            "path": path,
            "content": "x = 1",
            "author_role": "coder",
        })
        assert result.success is True
        assert os.path.exists(path)

    @pytest.mark.asyncio
    async def test_syntax_failure_pipeline(self, tmp_dir):
        # TC-INT-002: Invalid code -> no file written + ErrorSignal
        kanban = StateKanban()
        valve = OutputValve(kanban=kanban)

        path = os.path.join(tmp_dir, "bad.py")
        art = Artifact(
            seq_no=0,
            artifact_type=ArtifactType.CODE,
            path=path,
            content="def (",
            checksum=compute_checksum("def ("),
            author_role="coder",
            created_at=now_utc(),
        )
        result = await valve.validate_and_write(art)
        assert result.success is False
        assert not os.path.exists(path)
        # ErrorSignal should be in FluidZone
        errors = kanban.fluid.read_signals(signal_type=SignalType.ERROR)
        assert len(errors) > 0

    @pytest.mark.asyncio
    async def test_permission_denied_in_pipeline(self):
        # TC-INT-003: Unauthorized role + write_file
        kanban = StateKanban()
        registry = ToolRegistry(kanban)

        async def dummy_impl(params: dict) -> dict:
            return {"success": True}

        tool_def = ToolDef(
            name="write_file",
            description="Write file",
            param_schema={},
            required_permissions={"coder", "integrator"},
        )
        registry.register(tool_def, dummy_impl)

        with pytest.raises(PermissionDeniedError):
            await registry.dispatch("write_file", "reviewer", {"path": "x.py", "content": "x=1"})


class TestSnapshotIntegration:
    """TC-INT-004: PM state in snapshot round-trip."""

    def test_pm_state_round_trip(self):
        # TC-INT-004
        kanban = StateKanban()
        bus = MessageBus(kanban)
        pm = ProcessManager(kanban, bus)

        spec = ViewportSpec(
            role="coder",
            visible_signal_types=[SignalType.INTENT],
            visible_artifact_types=[ArtifactType.CODE],
            visible_target_patterns=["*"],
        )
        info = pm.create_process("coder", {"write_file"}, spec)
        pm.activate(info.process_id)

        # Save
        data = kanban.to_json()
        pm_state = pm.get_state_for_snapshot()

        # Restore kanban
        restored_kanban = StateKanban.from_json(data)
        restored_bus = MessageBus(restored_kanban)
        restored_pm = ProcessManager(restored_kanban, restored_bus)
        restored_pm.load_state_from_snapshot(pm_state)

        process = restored_pm.get_process(info.process_id)
        assert process is not None
        assert process.state.value == "active"


class TestConvergenceIntegration:
    """TC-INT-005: Collision -> convergence -> CrystalZone."""

    def test_collision_resolved_to_crystal(self):
        # TC-INT-005
        kanban = StateKanban()
        # Write intent
        kanban.fluid.write_signal(IntentSignal(
            signal_id=make_signal_id(),
            author_role="coder",
            target_id="artifact_A",
            payload={"action": "approve"},
            timestamp=now_utc(),
            round_number=0,
        ))
        # Write veto
        kanban.fluid.write_signal(VetoSignal(
            signal_id=make_signal_id(),
            author_role="reviewer",
            target_id="artifact_A",
            payload={"action": "reject"},
            timestamp=now_utc(),
            round_number=0,
            reason="needs improvement",
        ))

        # Run convergence -- with persistent collision, it will timeout
        result = kanban.run_convergence("artifact_A")
        # Since we don't resolve the collision, it should force-terminate
        assert result.forced_terminate is True
        assert result.converged is False

        # But if we clear veto and run again, it should converge
        kanban.fluid.clear_signals("artifact_A", round_number_ge=0)
        kanban.fluid.write_signal(IntentSignal(
            signal_id=make_signal_id(),
            author_role="coder",
            target_id="artifact_A",
            payload={"action": "approve"},
            timestamp=now_utc(),
            round_number=1,
        ))
        result2 = kanban.run_convergence("artifact_A")
        assert result2.converged is True

        # Now artifact can be appended to CrystalZone
        from statekanban.core.kanban import Artifact
        seq = kanban.crystal.append(Artifact(
            seq_no=0,
            artifact_type=ArtifactType.CODE,
            path="artifact_A.py",
            content="print('done')",
            checksum=compute_checksum("print('done')"),
            author_role="coder",
            created_at=now_utc(),
        ))
        assert seq == 1


class TestMetrics:
    """TC-INT-006 ~ TC-INT-008: Paper-defined metrics."""

    def test_convergence_rate(self):
        # TC-INT-006
        results = []
        for i in range(5):
            kanban = StateKanban()
            kanban.fluid.write_signal(IntentSignal(
                signal_id=make_signal_id(),
                author_role="coder",
                target_id=f"target_{i}",
                payload={},
                timestamp=now_utc(),
                round_number=0,
            ))
            if i < 3:  # 3 out of 5 converge (no veto)
                pass
            else:  # 2 out of 5 have veto
                kanban.fluid.write_signal(VetoSignal(
                    signal_id=make_signal_id(),
                    author_role="reviewer",
                    target_id=f"target_{i}",
                    payload={},
                    timestamp=now_utc(),
                    round_number=0,
                ))
            result = kanban.run_convergence(f"target_{i}")
            results.append(result)

        converged_count = sum(1 for r in results if r.converged)
        convergence_rate = converged_count / len(results)
        # 3 converged (no veto), 2 timed out (veto collision)
        assert convergence_rate == 0.6

    @pytest.mark.asyncio
    async def test_interception_rate(self, tmp_dir):
        # TC-INT-007
        kanban = StateKanban()
        valve = OutputValve(kanban=kanban)

        total_attempts = 4
        blocked = 0

        # Valid artifacts
        for i in range(2):
            art = Artifact(
                seq_no=0, artifact_type=ArtifactType.CODE,
                path=os.path.join(tmp_dir, f"valid_{i}.py"),
                content="x = 1",
                checksum=compute_checksum("x = 1"),
                author_role="coder", created_at=now_utc(),
            )
            result = await valve.validate_and_write(art)
            if not result.success:
                blocked += 1

        # Invalid artifacts
        for i in range(2):
            art = Artifact(
                seq_no=0, artifact_type=ArtifactType.CODE,
                path=os.path.join(tmp_dir, f"invalid_{i}.py"),
                content="def (",
                checksum=compute_checksum("def ("),
                author_role="coder", created_at=now_utc(),
            )
            result = await valve.validate_and_write(art)
            if not result.success:
                blocked += 1

        interception_rate = blocked / total_attempts
        # 2 valid passed, 2 invalid blocked
        assert interception_rate == 0.5

    def test_lossless_handoff(self):
        # TC-INT-008: claim_primary preserves viewport and state
        kanban = StateKanban()
        bus = MessageBus(kanban)
        pm = ProcessManager(kanban, bus)

        spec = ViewportSpec(
            role="coder",
            visible_signal_types=[SignalType.INTENT, SignalType.ERROR],
            visible_artifact_types=[ArtifactType.CODE, ArtifactType.CONFIG],
            visible_target_patterns=["*"],
            max_tokens=3000,
        )

        old_info = pm.create_process("coder", {"write_file"}, spec)
        pm.activate(old_info.process_id)

        # Manually register new coder process to bypass active-process check
        import uuid
        new_pid = str(uuid.uuid4())
        from statekanban.core.kanban import ProcessInfo, ProcessState
        new_spec = ViewportSpec(
            role="coder",
            visible_signal_types=[SignalType.INTENT],
            visible_artifact_types=[ArtifactType.CODE],
            visible_target_patterns=["*"],
            max_tokens=1000,
        )
        new_info = ProcessInfo(
            process_id=new_pid,
            role="coder",
            state=ProcessState.CREATED,
            tool_permits={"write_file", "read_file"},
            viewport_spec=new_spec,
        )
        pm._processes[new_pid] = new_info

        pm.claim_primary("coder", new_pid)

        # Verify lossless handoff: viewport spec from predecessor inherited
        assert new_info.viewport_spec.max_tokens == 3000
        assert SignalType.ERROR in new_info.viewport_spec.visible_signal_types
        assert new_info.state == ProcessState.ACTIVE


class TestBootstrap:
    """TC-INT-009: Full system bootstrap."""

    def test_full_bootstrap(self):
        # TC-INT-009
        from statekanban.cli.main import _bootstrap_system

        config = Config()
        components = _bootstrap_system(config)

        assert "kanban" in components
        assert "bus" in components
        assert "registry" in components
        assert "valve" in components
        assert "slicer" in components
        assert "pm" in components
        assert "adapter" in components

        # Verify component types
        assert isinstance(components["kanban"], StateKanban)
        assert isinstance(components["bus"], MessageBus)
        assert isinstance(components["registry"], ToolRegistry)
        assert isinstance(components["valve"], OutputValve)
        assert isinstance(components["slicer"], ViewportSlicer)
        assert isinstance(components["pm"], ProcessManager)

        # Verify tools registered
        tools = components["registry"].list_tools()
        assert "write_file" in tools
        assert "read_file" in tools
        assert "run_shell" in tools
        assert "call_llm" in tools
        assert "search_code" in tools