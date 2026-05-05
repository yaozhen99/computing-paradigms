"""Tests for ToolRegistry: permission, audit, timeout, dispatch."""

from __future__ import annotations

import asyncio

import pytest

from statekanban.core.errors import (
    PermissionDeniedError,
    ToolNotFoundError,
    ToolTimeoutError,
)
from statekanban.core.kanban import (
    SignalType,
    StateKanban,
    ToolDef,
    make_signal_id,
    now_utc,
)
from statekanban.core.registry import ToolRegistry, ToolResult


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


async def _echo_impl(params: dict) -> dict:
    """Echo implementation for tests."""
    return {"echo": params}


async def _slow_impl(params: dict) -> dict:
    """Slow implementation for timeout tests."""
    await asyncio.sleep(100)
    return {"late": True}


async def _failing_impl(params: dict) -> dict:
    """Implementation that raises an exception."""
    raise ValueError("tool internal error")


class TestToolRegistryRegister:
    """TC-TR-001 ~ TC-TR-002: Tool registration."""

    @pytest.mark.asyncio
    async def test_register_new_tool(self, registry, sample_tool_def):
        # TC-TR-001
        registry.register(sample_tool_def, _echo_impl)
        assert "test_tool" in registry.list_tools()

    @pytest.mark.asyncio
    async def test_duplicate_registration(self, registry, sample_tool_def):
        # TC-TR-002
        registry.register(sample_tool_def, _echo_impl)
        with pytest.raises(ToolNotFoundError):
            registry.register(sample_tool_def, _echo_impl)


class TestToolRegistryDispatch:
    """TC-TR-003 ~ TC-TR-006: Dispatch and permission."""

    @pytest.mark.asyncio
    async def test_allowed_role_dispatch(self, registry, sample_tool_def):
        # TC-TR-003
        registry.register(sample_tool_def, _echo_impl)
        result = await registry.dispatch("test_tool", "coder", {"x": 1})
        assert result.success is True
        assert result.output["echo"]["x"] == 1

    @pytest.mark.asyncio
    async def test_denied_role_dispatch(self, registry, sample_tool_def):
        # TC-TR-004
        registry.register(sample_tool_def, _echo_impl)
        with pytest.raises(PermissionDeniedError):
            await registry.dispatch("test_tool", "reviewer", {"x": 1})

    @pytest.mark.asyncio
    async def test_tool_not_found(self, registry):
        # TC-TR-005
        with pytest.raises(ToolNotFoundError):
            await registry.dispatch("nonexistent_tool", "coder", {})

    @pytest.mark.asyncio
    async def test_all_roles_permission(self, registry, all_roles_tool_def):
        # TC-TR-006
        registry.register(all_roles_tool_def, _echo_impl)
        result = await registry.dispatch("universal_tool", "any_role", {})
        assert result.success is True


class TestToolRegistryTimeout:
    """TC-TR-007 ~ TC-TR-008: Timeout handling."""

    @pytest.mark.asyncio
    async def test_tool_timeout(self, registry):
        # TC-TR-007
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
        # TC-TR-008
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


class TestToolRegistryAudit:
    """TC-TR-009 ~ TC-TR-012: Audit logging."""

    @pytest.mark.asyncio
    async def test_successful_dispatch_logged(self, registry, kanban, sample_tool_def):
        # TC-TR-009
        registry.register(sample_tool_def, _echo_impl)
        await registry.dispatch("test_tool", "coder", {"x": 1})
        entries = kanban.audit.read_entries(event_type="tool_call")
        assert len(entries) >= 1

    @pytest.mark.asyncio
    async def test_permission_denied_logged(self, registry, kanban, sample_tool_def):
        # TC-TR-010
        registry.register(sample_tool_def, _echo_impl)
        try:
            await registry.dispatch("test_tool", "reviewer", {"x": 1})
        except PermissionDeniedError:
            pass
        entries = kanban.audit.read_entries(event_type="permission_denied")
        assert len(entries) >= 1

    @pytest.mark.asyncio
    async def test_params_hashed_in_audit(self, registry, kanban, sample_tool_def):
        # TC-TR-011
        registry.register(sample_tool_def, _echo_impl)
        await registry.dispatch("test_tool", "coder", {"x": 1})
        entries = kanban.audit.read_entries(event_type="tool_call")
        assert len(entries) >= 1
        assert "params_hash" in entries[0].details

    @pytest.mark.asyncio
    async def test_tool_error_logged(self, registry, kanban):
        # TC-TR-012
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