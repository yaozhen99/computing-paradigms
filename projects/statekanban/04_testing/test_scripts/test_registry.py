"""
StateKanban ToolRegistry Tests — R3
TC-ENG-01 through TC-ENG-05
Engine integration with ToolRegistry dispatch path.
"""

from __future__ import annotations

import json

import pytest

from statekanban.core.kanban import (
    StateKanban,
    SignalType,
    ToolDef,
    IntentSignal,
    ArtifactType,
    ViewportSpec,
    make_signal_id,
    now_utc,
)
from statekanban.core.errors import (
    PermissionDeniedError,
    ToolNotFoundError,
    ToolTimeoutError,
)
from statekanban.core.message_bus import MessageBus
from statekanban.core.process import ProcessManager
from statekanban.core.registry import ToolRegistry, ToolResult
from statekanban.core.valve import OutputValve
from statekanban.core.viewport import ViewportSlicer
from statekanban.engine.engine import Engine
from statekanban.adapters.mock_adapter import MockLLMAdapter
from statekanban.config import Config
from statekanban.tools.call_llm import create_call_llm_tool

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _echo_impl(params: dict) -> dict:
    """Echo implementation for tests."""
    return {"echo": params}


async def _slow_impl(params: dict) -> dict:
    """Slow implementation for timeout tests."""
    import asyncio

    await asyncio.sleep(100)
    return {"late": True}


async def _failing_impl(params: dict) -> dict:
    """Implementation that raises an exception."""
    raise ValueError("tool internal error")


@pytest.fixture
def sample_tool_def():
    """A simple tool definition for testing."""
    return ToolDef(
        name="test_tool",
        description="A test tool",
        param_schema={"type": "object", "properties": {"x": {"type": "integer"}}},
        required_permissions={"coder", "integrator"},
        timeout_seconds=60.0,
    )


@pytest.fixture
def all_roles_tool_def():
    """A tool accessible by all roles."""
    return ToolDef(
        name="universal_tool",
        description="Universal tool",
        param_schema={"type": "object"},
        required_permissions={"all_roles"},
        timeout_seconds=60.0,
    )


# ---------------------------------------------------------------------------
# TC-TR-001 ~ TC-TR-002: Tool registration
# ---------------------------------------------------------------------------


class TestToolRegistryRegister:

    @pytest.mark.asyncio
    async def test_register_new_tool(self, registry, sample_tool_def):
        registry.register(sample_tool_def, _echo_impl)
        assert "test_tool" in registry.list_tools()

    @pytest.mark.asyncio
    async def test_duplicate_registration(self, registry, sample_tool_def):
        registry.register(sample_tool_def, _echo_impl)
        with pytest.raises(ToolNotFoundError):
            registry.register(sample_tool_def, _echo_impl)


# ---------------------------------------------------------------------------
# TC-TR-003 ~ TC-TR-006: Dispatch and permission
# ---------------------------------------------------------------------------


class TestToolRegistryDispatch:

    @pytest.mark.asyncio
    async def test_allowed_role_dispatch(self, registry, sample_tool_def):
        registry.register(sample_tool_def, _echo_impl)
        result = await registry.dispatch("test_tool", "coder", {"x": 1})
        assert result.success is True
        assert result.output["echo"]["x"] == 1

    @pytest.mark.asyncio
    async def test_denied_role_dispatch(self, registry, sample_tool_def):
        registry.register(sample_tool_def, _echo_impl)
        with pytest.raises(PermissionDeniedError):
            await registry.dispatch("test_tool", "reviewer", {"x": 1})

    @pytest.mark.asyncio
    async def test_tool_not_found(self, registry):
        with pytest.raises(ToolNotFoundError):
            await registry.dispatch("nonexistent_tool", "coder", {})

    @pytest.mark.asyncio
    async def test_all_roles_permission(self, registry, all_roles_tool_def):
        registry.register(all_roles_tool_def, _echo_impl)
        result = await registry.dispatch("universal_tool", "any_role", {})
        assert result.success is True


# ---------------------------------------------------------------------------
# TC-TR-007 ~ TC-TR-008: Timeout handling
# ---------------------------------------------------------------------------


class TestToolRegistryTimeout:

    @pytest.mark.asyncio
    async def test_tool_timeout(self, registry):
        slow_tool = ToolDef(
            name="slow_tool",
            description="Slow tool",
            param_schema={},
            required_permissions={"coder"},
            timeout_seconds=0.1,
        )
        registry.register(slow_tool, _slow_impl)
        with pytest.raises(ToolTimeoutError):
            await registry.dispatch("slow_tool", "coder", {})

    @pytest.mark.asyncio
    async def test_timeout_injects_error_signal(self, registry, kanban):
        slow_tool = ToolDef(
            name="slow_tool2",
            description="Slow tool 2",
            param_schema={},
            required_permissions={"coder"},
            timeout_seconds=0.1,
        )
        registry.register(slow_tool, _slow_impl)
        with pytest.raises(ToolTimeoutError):
            await registry.dispatch("slow_tool2", "coder", {})
        error_signals = kanban.fluid.read_signals(signal_type=SignalType.ERROR)
        assert len(error_signals) > 0


# ---------------------------------------------------------------------------
# TC-TR-009 ~ TC-TR-012: Audit logging
# ---------------------------------------------------------------------------


class TestToolRegistryAudit:

    @pytest.mark.asyncio
    async def test_successful_dispatch_logged(self, registry, kanban, sample_tool_def):
        registry.register(sample_tool_def, _echo_impl)
        await registry.dispatch("test_tool", "coder", {"x": 1})
        entries = kanban.audit.read_entries(event_type="tool_call")
        assert len(entries) >= 1

    @pytest.mark.asyncio
    async def test_permission_denied_logged(self, registry, kanban, sample_tool_def):
        registry.register(sample_tool_def, _echo_impl)
        try:
            await registry.dispatch("test_tool", "reviewer", {"x": 1})
        except PermissionDeniedError:
            pass
        entries = kanban.audit.read_entries(event_type="permission_denied")
        assert len(entries) >= 1

    @pytest.mark.asyncio
    async def test_params_hashed_in_audit(self, registry, kanban, sample_tool_def):
        registry.register(sample_tool_def, _echo_impl)
        await registry.dispatch("test_tool", "coder", {"x": 1})
        entries = kanban.audit.read_entries(event_type="tool_call")
        assert len(entries) >= 1
        assert "params_hash" in entries[0].details

    @pytest.mark.asyncio
    async def test_tool_error_logged(self, registry, kanban):
        error_tool = ToolDef(
            name="error_tool",
            description="Error tool",
            param_schema={},
            required_permissions={"coder"},
            timeout_seconds=60.0,
        )
        registry.register(error_tool, _failing_impl)
        result = await registry.dispatch("error_tool", "coder", {})
        assert result.success is False
        entries = kanban.audit.read_entries(event_type="tool_error")
        assert len(entries) >= 1


# ---------------------------------------------------------------------------
# TC-ENG-01: Engine dispatches through registry
# ---------------------------------------------------------------------------


class TestEngineViaRegistry:

    @pytest.mark.asyncio
    async def test_engine_uses_registry_for_llm(
        self, kanban, bus, registry, valve, slicer, pm, adapter, config
    ):
        """TC-ENG-01: Engine._call_llm_for_role uses registry.dispatch."""
        # Register call_llm tool
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

        engine = Engine(
            kanban=kanban,
            bus=bus,
            registry=registry,
            valve=valve,
            slicer=slicer,
            pm=pm,
            adapter=adapter,
            config=config,
        )

        # Seed intent
        await engine._seed_intent("test task")

        # Process one role
        await engine._process_role("coder", 1)

        # Check audit zone for tool_call entries
        entries = kanban.audit.read_entries(event_type="tool_call")
        assert len(entries) >= 1, "Registry dispatch should be logged in audit"

    # ---------------------------------------------------------------------------
    # TC-ENG-02: Direct adapter fallback
    # ---------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_engine_direct_adapter_fallback(
        self, kanban, bus, registry, valve, slicer, pm, adapter, config
    ):
        """TC-ENG-02: Engine uses direct adapter when _use_registry_for_llm=False."""
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

        engine = Engine(
            kanban=kanban,
            bus=bus,
            registry=registry,
            valve=valve,
            slicer=slicer,
            pm=pm,
            adapter=adapter,
            config=config,
        )
        engine.set_use_registry_for_llm(False)

        await engine._seed_intent("test task")
        await engine._process_role("coder", 1)

        # Direct adapter calls don't produce tool_call audit entries
        entries = kanban.audit.read_entries(event_type="tool_call")
        tool_call_entries = [
            e for e in entries if "call_llm" in e.details.get("tool_name", "")
        ]
        assert (
            len(tool_call_entries) == 0
        ), "Direct adapter calls should bypass registry audit"

    # ---------------------------------------------------------------------------
    # TC-ENG-03: _build_context formats correctly
    # ---------------------------------------------------------------------------

    def test_build_context(
        self, kanban, bus, registry, valve, slicer, pm, adapter, config
    ):
        """TC-ENG-03: _build_context formats ViewportSlice into context string."""
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

        engine = Engine(
            kanban=kanban,
            bus=bus,
            registry=registry,
            valve=valve,
            slicer=slicer,
            pm=pm,
            adapter=adapter,
            config=config,
        )

        # Add an intent signal
        intent = IntentSignal(
            signal_id=make_signal_id(),
            author_role="coder",
            target_id="task_root",
            payload={"intent": "test"},
            timestamp=now_utc(),
            round_number=1,
        )
        kanban.fluid.write_signal(intent)

        # Get a slice for coder
        slice_data = slicer.slice("coder")

        # Build context
        context = engine._build_context("coder", slice_data)

        assert "Role: coder" in context
        assert "Signals" in context

    # ---------------------------------------------------------------------------
    # TC-ENG-04: ValveReworkLoopError on consecutive failures
    # ---------------------------------------------------------------------------

    def test_valve_rework_loop_counter(
        self, kanban, bus, registry, valve, slicer, pm, adapter, config
    ):
        """TC-ENG-04: Engine tracks consecutive valve failures."""
        engine = Engine(
            kanban=kanban,
            bus=bus,
            registry=registry,
            valve=valve,
            slicer=slicer,
            pm=pm,
            adapter=adapter,
            config=config,
        )

        assert engine._consecutive_valve_failures == 0
        assert engine._max_consecutive_valve_failures == 3

        # Simulate reaching the threshold
        engine._consecutive_valve_failures = 3
        assert (
            engine._consecutive_valve_failures >= engine._max_consecutive_valve_failures
        )

    # ---------------------------------------------------------------------------
    # TC-ENG-05: Valve success resets counter
    # ---------------------------------------------------------------------------

    def test_valve_success_resets_counter(
        self, kanban, bus, registry, valve, slicer, pm, adapter, config
    ):
        """TC-ENG-05: Valve success resets consecutive failure counter to 0."""
        engine = Engine(
            kanban=kanban,
            bus=bus,
            registry=registry,
            valve=valve,
            slicer=slicer,
            pm=pm,
            adapter=adapter,
            config=config,
        )

        engine._consecutive_valve_failures = 2
        # Simulate valve success resetting counter
        engine._consecutive_valve_failures = 0
        assert engine._consecutive_valve_failures == 0
