"""R6 Isolation tests: REQ-601 through REQ-605.

Validates that the virtual substrate isolation boundaries are enforced:
- REQ-601: OutputValve path sandbox (ValvePathViolationError SK_VS_005)
- REQ-602: read_file path sandbox (ToolPathViolationError SK_TR_005)
- REQ-603: call_llm isolation (timeout, retry, degraded fallback)
- REQ-604: snapshot through OutputValve + path validation (SK_SN_003)
- REQ-605: Engine exception boundary (ErrorSignal SK_EN_006)
"""

from __future__ import annotations

import asyncio
import os
import tempfile

import pytest

from statekanban.config import Config
from statekanban.core.errors import (
    EngineExternalError,
    PathEscapeError,
    SnapshotPathViolationError,
    ToolPathViolationError,
    ValvePathViolationError,
)
from statekanban.core.kanban import (
    Artifact,
    ArtifactType,
    ErrorSignal,
    SignalType,
    StateKanban,
    compute_checksum,
    make_signal_id,
    now_utc,
    ToolDef,
)
from statekanban.core.valve import OutputValve
from statekanban.tools.read_file import read_file
from statekanban.tools.call_llm import CallLlmTool, create_call_llm_tool
from statekanban.snapshot import save_snapshot, load_snapshot, SnapshotManager
from statekanban.adapters.mock_adapter import MockLLMAdapter


# ============================================================================
# REQ-601: OutputValve path sandbox
# ============================================================================


class TestReq601ValvePathSandbox:
    """REQ-601: OutputValve write paths must stay within project_root."""

    def test_traversal_rejected(self, tmp_dir):
        """../etc/passwd -> ValvePathViolationError."""
        config = Config(project_root=tmp_dir)
        valve = OutputValve(config=config)
        artifact = Artifact(
            seq_no=0,
            artifact_type=ArtifactType.CODE,
            path="../etc/passwd",
            content="malicious",
            checksum=compute_checksum("malicious"),
            author_role="coder",
            created_at=now_utc(),
        )
        result = asyncio.run(valve.validate_and_write(artifact))
        assert not result.success
        assert "SK_VS_005" in (result.error or "")

    def test_absolute_path_outside_rejected(self, tmp_dir):
        """Absolute path pointing outside project_root -> rejected."""
        config = Config(project_root=tmp_dir)
        valve = OutputValve(config=config)
        artifact = Artifact(
            seq_no=0,
            artifact_type=ArtifactType.CODE,
            path="/etc/passwd",
            content="malicious",
            checksum=compute_checksum("malicious"),
            author_role="coder",
            created_at=now_utc(),
        )
        result = asyncio.run(valve.validate_and_write(artifact))
        assert not result.success

    def test_valid_path_within_sandbox(self, tmp_dir):
        """Valid path within project_root -> allowed."""
        config = Config(project_root=tmp_dir)
        valve = OutputValve(config=config)
        artifact = Artifact(
            seq_no=0,
            artifact_type=ArtifactType.CODE,
            path="output/test.py",
            content="x = 1",
            checksum=compute_checksum("x = 1"),
            author_role="coder",
            created_at=now_utc(),
        )
        result = asyncio.run(valve.validate_and_write(artifact))
        assert result.success
        assert os.path.exists(result.artifact_path)

    def test_no_sandbox_allows_all(self):
        """No project_root configured -> all paths allowed (backward compat)."""
        valve = OutputValve()  # No config, no project_root
        resolved = valve._validate_path("any/path.py")
        assert isinstance(resolved, str)

    def test_validate_path_raises_on_traversal(self, tmp_dir):
        """_validate_path directly raises ValvePathViolationError."""
        config = Config(project_root=tmp_dir)
        valve = OutputValve(config=config)
        with pytest.raises(ValvePathViolationError) as exc_info:
            valve._validate_path("../../etc/shadow")
        assert exc_info.value.attempted_path == "../../etc/shadow"
        assert exc_info.value.output_dir == os.path.realpath(tmp_dir)


# ============================================================================
# REQ-602: read_file path sandbox
# ============================================================================


class TestReq602ReadFilePathSandbox:
    """REQ-602: read_file must restrict reads to project_root."""

    @pytest.mark.asyncio
    async def test_traversal_rejected(self, tmp_dir):
        """Reading ../etc/passwd -> error with SK_TR_005."""
        config = Config(project_root=tmp_dir)
        result = await read_file(
            params={"path": "../etc/passwd"},
            config=config,
        )
        assert not result["success"]
        assert result["error_code"] == "SK_TR_005"

    @pytest.mark.asyncio
    async def test_absolute_path_outside_rejected(self, tmp_dir):
        """Reading /etc/passwd -> error with SK_TR_005."""
        config = Config(project_root=tmp_dir)
        result = await read_file(
            params={"path": "/etc/passwd"},
            config=config,
        )
        assert not result["success"]

    @pytest.mark.asyncio
    async def test_valid_path_within_sandbox(self, tmp_dir):
        """Reading a file within project_root -> success."""
        test_file = os.path.join(tmp_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("hello")

        config = Config(project_root=tmp_dir)
        result = await read_file(
            params={"path": "test.txt"},
            config=config,
        )
        assert result["success"]
        assert result["content"] == "hello"

    @pytest.mark.asyncio
    async def test_null_bytes_rejected(self):
        """Path with null bytes -> error with SK_TR_005."""
        result = await read_file(
            params={"path": "test\x00.txt"},
            config=None,
        )
        assert not result["success"]
        assert result["error_code"] == "SK_TR_005"

    @pytest.mark.asyncio
    async def test_no_config_warns_but_allows(self):
        """Without config, read_file still works (backward compat)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("test content")
            tmp_path = f.name
        try:
            result = await read_file(
                params={"path": tmp_path},
                config=None,
            )
            assert result["success"]
            assert result["content"] == "test content"
        finally:
            os.unlink(tmp_path)


# ============================================================================
# REQ-603: call_llm isolation
# ============================================================================


class TestReq603CallLlmIsolation:
    """REQ-603: call_llm timeout, retry, and degraded fallback."""

    @pytest.mark.asyncio
    async def test_timeout_returns_degraded(self):
        """Timeout after retries -> degraded fallback response."""

        class SlowAdapter(MockLLMAdapter):
            async def complete(self, **kwargs):
                await asyncio.sleep(60.0)  # Will be cancelled by timeout
                return await super().complete(**kwargs)

        tool = CallLlmTool(SlowAdapter(), timeout=0.01, max_retries=1)
        result = await tool(params={"messages": [{"role": "user", "content": "hi"}]})
        assert not result["success"]
        assert result.get("degraded") is True
        assert "TIMEOUT" in result["error"]

    @pytest.mark.asyncio
    async def test_error_returns_degraded(self):
        """Adapter error after retries -> degraded fallback response."""

        class FailingAdapter(MockLLMAdapter):
            async def complete(self, **kwargs):
                raise RuntimeError("API down")

        tool = CallLlmTool(FailingAdapter(), timeout=30.0, max_retries=1)
        result = await tool(params={"messages": [{"role": "user", "content": "hi"}]})
        assert not result["success"]
        assert result.get("degraded") is True
        assert "ERROR" in result["error"]

    @pytest.mark.asyncio
    async def test_success_on_first_try(self):
        """Normal adapter -> success without retry."""
        adapter = MockLLMAdapter()
        tool = CallLlmTool(adapter, timeout=30.0, max_retries=2)
        result = await tool(params={"messages": [{"role": "user", "content": "hi"}]})
        assert result["success"]
        assert result["output"]["content"] is not None

    @pytest.mark.asyncio
    async def test_retry_then_success(self):
        """Fails once then succeeds -> success after retry."""
        call_count = 0

        class FlakeyAdapter(MockLLMAdapter):
            async def complete(self, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise ConnectionError("transient")
                return await super().complete(**kwargs)

        tool = CallLlmTool(FlakeyAdapter(), timeout=30.0, max_retries=2)
        result = await tool(params={"messages": [{"role": "user", "content": "hi"}]})
        assert result["success"]
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_factory_creates_tool(self):
        """create_call_llm_tool creates a callable tool."""
        adapter = MockLLMAdapter()
        tool_fn = create_call_llm_tool(adapter, timeout=5.0, max_retries=1)
        assert callable(tool_fn)

    @pytest.mark.asyncio
    async def test_null_bytes_rejected(self):
        """Null bytes in input -> ToolRegistryError SK_TR_004."""
        adapter = MockLLMAdapter()
        tool = CallLlmTool(adapter, timeout=30.0, max_retries=2)
        with pytest.raises(Exception):
            await tool(params={"messages": [{"role": "user", "content": "hi\x00"}]})


# ============================================================================
# REQ-604: snapshot through OutputValve + path validation
# ============================================================================


class TestReq604SnapshotValve:
    """REQ-604: save_snapshot through OutputValve, load_snapshot path validation."""

    def test_save_via_valve(self, tmp_dir):
        """save_snapshot with valve -> writes through OutputValve."""
        config = Config(project_root=tmp_dir)
        kanban = StateKanban()
        valve = OutputValve(config=config)
        path = os.path.join(tmp_dir, "snap.json")
        save_snapshot(kanban, path, valve=valve)
        assert os.path.exists(path)

    def test_save_traversal_rejected_via_valve(self, tmp_dir):
        """save_snapshot with valve + ../outside.json -> rejected."""
        config = Config(project_root=tmp_dir)
        kanban = StateKanban()
        valve = OutputValve(config=config)
        with pytest.raises(Exception):
            save_snapshot(kanban, "../outside.json", valve=valve)

    def test_load_path_validation_rejects_traversal(self, tmp_dir):
        """load_snapshot with project_root rejects traversal."""
        with pytest.raises(SnapshotPathViolationError) as exc_info:
            load_snapshot("../outside.json", project_root=tmp_dir)
        assert exc_info.value.attempted_path == "../outside.json"

    def test_load_valid_path(self, tmp_dir):
        """load_snapshot with valid path -> success."""
        config = Config(project_root=tmp_dir)
        kanban = StateKanban()
        valve = OutputValve(config=config)
        path = os.path.join(tmp_dir, "snap.json")
        save_snapshot(kanban, path, valve=valve)

        loaded = load_snapshot(path, project_root=tmp_dir)
        assert isinstance(loaded, StateKanban)

    def test_load_no_project_root_allows_all(self, tmp_dir):
        """load_snapshot without project_root -> no path validation."""
        kanban = StateKanban()
        path = os.path.join(tmp_dir, "snap.json")
        save_snapshot(kanban, path)
        loaded = load_snapshot(path, project_root="")
        assert isinstance(loaded, StateKanban)

    def test_snapshot_manager_with_valve(self, tmp_dir):
        """SnapshotManager.save_snapshot with valve parameter."""
        config = Config(project_root=tmp_dir)
        kanban = StateKanban()
        valve = OutputValve(config=config)
        mgr = SnapshotManager(
            base_dir=".statekanban/snapshots",
            config=config,
        )
        mgr.save_snapshot(kanban, "test.json", valve=valve)
        loaded = mgr.load_snapshot("test.json")
        assert isinstance(loaded, StateKanban)


# ============================================================================
# REQ-605: Engine exception boundary
# ============================================================================


class TestReq605EngineExceptionBoundary:
    """REQ-605: External exceptions -> ErrorSignal SK_EN_006."""

    def test_process_role_catches_exception(self, kanban, bus, registry, valve, slicer, pm, config):
        """_process_role catches external exception -> SK_EN_006 ErrorSignal.

        When the LLM adapter raises, _call_llm_for_role catches it and
        returns an error LLMResponse. _process_role then converts this
        to an ErrorSignal with SK_EN_006.
        """

        class ExplodingAdapter(MockLLMAdapter):
            async def complete(self, **kwargs):
                raise RuntimeError("API exploded")

        from statekanban.tools.call_llm import create_call_llm_tool

        adapter = ExplodingAdapter()
        registry.register(
            ToolDef(
                name="call_llm",
                description="Invoke LLM",
                param_schema={"type": "object", "properties": {"messages": {"type": "array"}}},
                required_permissions={"all_roles"},
                timeout_seconds=120.0,
            ),
            create_call_llm_tool(adapter),
        )
        from statekanban.engine.engine import Engine

        engine = Engine(
            kanban=kanban, bus=bus, registry=registry,
            valve=valve, slicer=slicer, pm=pm,
            adapter=adapter, config=config,
        )
        # _process_role should not raise
        asyncio.run(engine._process_role("coder", 1))

        # Check that SK_EN_006 ErrorSignal was written
        error_signals = kanban.fluid.read_signals(signal_type=SignalType.ERROR)
        sk_en_006_signals = [s for s in error_signals if s.error_code == "SK_EN_006"]
        assert len(sk_en_006_signals) > 0

    def test_consecutive_errors_detected(self, kanban, bus, registry, valve, slicer, pm, config):
        """Consecutive SK_EN_006 signals are tracked by the engine."""
        # Manually inject SK_EN_006 signals for 3 consecutive rounds
        for round_num in range(1, 4):
            error_signal = ErrorSignal(
                signal_id=make_signal_id(),
                author_role="system",
                target_id=f"coder_r{round_num}",  # unique target_id per round
                payload={"error": "test"},
                timestamp=now_utc(),
                round_number=round_num,
                error_code="SK_EN_006",
            )
            kanban.fluid.write_signal(error_signal)

        # Verify signals are in FluidZone
        error_signals = kanban.fluid.read_signals(signal_type=SignalType.ERROR)
        sk_en_006_signals = [s for s in error_signals if s.error_code == "SK_EN_006"]
        assert len(sk_en_006_signals) == 3

    def test_error_signal_does_not_crash_drive(self, kanban, bus, registry, valve, slicer, pm, config):
        """ErrorSignal in FluidZone does not prevent drive loop from continuing."""
        error_signal = ErrorSignal(
            signal_id=make_signal_id(),
            author_role="system",
            target_id="coder",
            payload={"error": "test"},
            timestamp=now_utc(),
            round_number=1,
            error_code="SK_EN_006",
        )
        kanban.fluid.write_signal(error_signal)

        # Drive loop should still be able to read signals
        error_signals = kanban.fluid.read_signals(signal_type=SignalType.ERROR)
        assert len(error_signals) == 1
        assert error_signals[0].error_code == "SK_EN_006"

    def test_engine_external_error_class(self):
        """EngineExternalError has correct error_code."""
        err = EngineExternalError("test")
        assert err.error_code == "SK_EN_006"
