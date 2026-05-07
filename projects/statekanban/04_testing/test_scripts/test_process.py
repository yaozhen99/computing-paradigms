"""Tests for ProcessManager: state machine, self-termination, handoff, heartbeat."""

from __future__ import annotations

import datetime

import pytest

from statekanban.core.errors import (
    HandoffError,
    InvalidStateTransitionError,
    SelfTerminationError,
)
from statekanban.core.kanban import ProcessState, ViewportSpec, SignalType, ArtifactType


def _make_viewport_spec(role: str) -> ViewportSpec:
    return ViewportSpec(
        role=role,
        visible_signal_types=[SignalType.INTENT],
        visible_artifact_types=[ArtifactType.CODE],
        visible_target_patterns=["*"],
    )


class TestProcessManagerCreate:
    """TC-PM-001 ~ TC-PM-002: Process creation."""

    def test_create_process(self, pm):
        # TC-PM-001
        info = pm.create_process(
            role="coder",
            tool_permits={"write_file", "read_file"},
            viewport_spec=_make_viewport_spec("coder"),
        )
        assert info.state == ProcessState.CREATED
        assert info.role == "coder"

    def test_duplicate_active_process_for_role(self, pm):
        # TC-PM-002
        info = pm.create_process(
            role="coder",
            tool_permits={"write_file"},
            viewport_spec=_make_viewport_spec("coder"),
        )
        pm.activate(info.process_id)
        # Creating another coder while first is active should fail
        with pytest.raises(InvalidStateTransitionError):
            pm.create_process(
                role="coder",
                tool_permits={"read_file"},
                viewport_spec=_make_viewport_spec("coder"),
            )


class TestProcessManagerActivate:
    """TC-PM-003 ~ TC-PM-006: State transitions for activation."""

    def test_created_to_active(self, pm):
        # TC-PM-003
        info = pm.create_process(
            role="coder",
            tool_permits={"write_file"},
            viewport_spec=_make_viewport_spec("coder"),
        )
        pm.activate(info.process_id)
        assert info.state == ProcessState.ACTIVE
        assert info.heartbeat_at is not None

    def test_suspended_to_active(self, pm):
        # TC-PM-004
        info = pm.create_process(
            role="coder",
            tool_permits={"write_file"},
            viewport_spec=_make_viewport_spec("coder"),
        )
        pm.activate(info.process_id)
        pm.suspend(info.process_id)
        pm.activate(info.process_id)
        assert info.state == ProcessState.ACTIVE

    def test_active_to_active_invalid(self, pm):
        # TC-PM-005
        info = pm.create_process(
            role="coder",
            tool_permits={"write_file"},
            viewport_spec=_make_viewport_spec("coder"),
        )
        pm.activate(info.process_id)
        with pytest.raises(InvalidStateTransitionError):
            pm.activate(info.process_id)

    def test_terminated_to_active_invalid(self, pm):
        # TC-PM-006
        info = pm.create_process(
            role="coder",
            tool_permits={"write_file"},
            viewport_spec=_make_viewport_spec("coder"),
        )
        pm.activate(info.process_id)
        pm.terminate(info.process_id, "scheduler")
        with pytest.raises(InvalidStateTransitionError):
            pm.activate(info.process_id)


class TestProcessManagerSuspend:
    """TC-PM-007 ~ TC-PM-008: Suspend transitions."""

    def test_active_to_suspended(self, pm):
        # TC-PM-007
        info = pm.create_process(
            role="coder",
            tool_permits={"write_file"},
            viewport_spec=_make_viewport_spec("coder"),
        )
        pm.activate(info.process_id)
        pm.suspend(info.process_id)
        assert info.state == ProcessState.SUSPENDED

    def test_created_to_suspended_invalid(self, pm):
        # TC-PM-008
        info = pm.create_process(
            role="coder",
            tool_permits={"write_file"},
            viewport_spec=_make_viewport_spec("coder"),
        )
        with pytest.raises(InvalidStateTransitionError):
            pm.suspend(info.process_id)


class TestProcessManagerTerminate:
    """TC-PM-009 ~ TC-PM-012, TC-PM-024: Terminate transitions."""

    def test_active_to_terminated(self, pm):
        # TC-PM-009
        info = pm.create_process(
            role="coder",
            tool_permits={"write_file"},
            viewport_spec=_make_viewport_spec("coder"),
        )
        pm.activate(info.process_id)
        pm.terminate(info.process_id, "scheduler")
        assert info.state == ProcessState.TERMINATED

    def test_suspended_to_terminated(self, pm):
        # TC-PM-010
        info = pm.create_process(
            role="coder",
            tool_permits={"write_file"},
            viewport_spec=_make_viewport_spec("coder"),
        )
        pm.activate(info.process_id)
        pm.suspend(info.process_id)
        pm.terminate(info.process_id, "scheduler")
        assert info.state == ProcessState.TERMINATED

    def test_self_termination_rejected(self, pm):
        # TC-PM-011
        info = pm.create_process(
            role="coder",
            tool_permits={"write_file"},
            viewport_spec=_make_viewport_spec("coder"),
        )
        pm.activate(info.process_id)
        with pytest.raises(SelfTerminationError):
            pm.terminate(info.process_id, info.process_id)

    def test_terminated_to_terminated_invalid(self, pm):
        # TC-PM-012
        info = pm.create_process(
            role="coder",
            tool_permits={"write_file"},
            viewport_spec=_make_viewport_spec("coder"),
        )
        pm.activate(info.process_id)
        pm.terminate(info.process_id, "scheduler")
        with pytest.raises(InvalidStateTransitionError):
            pm.terminate(info.process_id, "scheduler")

    def test_nonexistent_process_terminate(self, pm):
        # TC-PM-024
        with pytest.raises(InvalidStateTransitionError):
            pm.terminate("nonexistent_pid", "scheduler")


class TestProcessManagerHandoff:
    """TC-PM-013 ~ TC-PM-016: claim_primary and handoff."""

    def test_valid_handoff(self, pm, kanban):
        # TC-PM-013
        # Create first coder process, activate it
        old_info = pm.create_process(
            role="coder",
            tool_permits={"write_file"},
            viewport_spec=_make_viewport_spec("coder"),
        )
        pm.activate(old_info.process_id)
        old_pid = old_info.process_id

        # We cannot create a second coder process while first is active,
        # so we manually register a new process for the handoff test.
        # Simulate the new process by directly adding to the processes dict.
        import uuid

        new_pid = str(uuid.uuid4())
        new_spec = _make_viewport_spec("coder")
        from statekanban.core.kanban import ProcessInfo

        new_info = ProcessInfo(
            process_id=new_pid,
            role="coder",
            state=ProcessState.CREATED,
            tool_permits={"write_file", "read_file"},
            viewport_spec=new_spec,
        )
        # Bypass create_process to avoid the active-process check
        pm._processes[new_pid] = new_info

        # Now claim_primary should terminate the old and activate the new
        pm.claim_primary("coder", new_pid)

        assert pm._processes[old_pid].state == ProcessState.TERMINATED
        assert new_info.state == ProcessState.ACTIVE
        # Viewport should be inherited from predecessor (old process)
        assert new_info.viewport_spec.role == "coder"

    def test_no_predecessor_handoff(self, pm):
        # TC-PM-014: claim_primary with a role that has no process registered
        # We need a role that was never created
        with pytest.raises(HandoffError):
            pm.claim_primary("brand_new_role", "nonexistent_pid")

    def test_new_process_not_found(self, pm):
        # TC-PM-015
        old_info = pm.create_process(
            role="coder",
            tool_permits={"write_file"},
            viewport_spec=_make_viewport_spec("coder"),
        )
        pm.activate(old_info.process_id)
        pm.suspend(old_info.process_id)
        with pytest.raises(HandoffError):
            pm.claim_primary("coder", "nonexistent_pid")

    def test_role_mismatch_handoff(self, pm):
        # TC-PM-016
        old_info = pm.create_process(
            role="coder",
            tool_permits={"write_file"},
            viewport_spec=_make_viewport_spec("coder"),
        )
        pm.activate(old_info.process_id)
        pm.suspend(old_info.process_id)

        wrong_info = pm.create_process(
            role="reviewer",
            tool_permits={"read_file"},
            viewport_spec=_make_viewport_spec("reviewer"),
        )
        # Trying to claim_primary for "coder" with a "reviewer" process
        with pytest.raises(HandoffError):
            pm.claim_primary("coder", wrong_info.process_id)


class TestProcessManagerHeartbeat:
    """TC-PM-017 ~ TC-PM-019: Heartbeat."""

    def test_record_heartbeat(self, pm):
        # TC-PM-017
        info = pm.create_process(
            role="coder",
            tool_permits={"write_file"},
            viewport_spec=_make_viewport_spec("coder"),
        )
        pm.activate(info.process_id)
        pm.heartbeat(info.process_id)
        assert info.heartbeat_at is not None

    def test_heartbeat_non_active_rejected(self, pm):
        # TC-PM-018
        info = pm.create_process(
            role="coder",
            tool_permits={"write_file"},
            viewport_spec=_make_viewport_spec("coder"),
        )
        with pytest.raises(InvalidStateTransitionError):
            pm.heartbeat(info.process_id)

    def test_timeout_detection(self, pm):
        # TC-PM-019: Simulate heartbeat timeout
        info = pm.create_process(
            role="coder",
            tool_permits={"write_file"},
            viewport_spec=_make_viewport_spec("coder"),
        )
        pm.activate(info.process_id)
        # Set heartbeat_at to a time well past threshold
        info.heartbeat_at = datetime.datetime.now(
            tz=datetime.timezone.utc
        ) - datetime.timedelta(seconds=200)
        timed_out = pm.check_heartbeats()
        assert info.process_id in timed_out


class TestProcessManagerList:
    """TC-PM-020 ~ TC-PM-021: Process listing."""

    def test_list_all_processes(self, pm):
        # TC-PM-020
        pm.create_process(
            role="coder",
            tool_permits={"write_file"},
            viewport_spec=_make_viewport_spec("coder"),
        )
        pm.create_process(
            role="reviewer",
            tool_permits={"read_file"},
            viewport_spec=_make_viewport_spec("reviewer"),
        )
        processes = pm.list_processes()
        assert len(processes) == 2

    def test_filter_by_state(self, pm):
        # TC-PM-021
        c_info = pm.create_process(
            role="coder",
            tool_permits={"write_file"},
            viewport_spec=_make_viewport_spec("coder"),
        )
        pm.activate(c_info.process_id)
        r_info = pm.create_process(
            role="reviewer",
            tool_permits={"read_file"},
            viewport_spec=_make_viewport_spec("reviewer"),
        )
        # coder is ACTIVE, reviewer is CREATED
        active = pm.list_processes(state=ProcessState.ACTIVE)
        assert len(active) == 1
        assert active[0].role == "coder"


class TestProcessManagerAudit:
    """TC-PM-022: Audit logging on transitions."""

    def test_transition_logged(self, pm, kanban):
        # TC-PM-022
        info = pm.create_process(
            role="coder",
            tool_permits={"write_file"},
            viewport_spec=_make_viewport_spec("coder"),
        )
        pm.activate(info.process_id)
        entries = kanban.audit.read_entries(event_type="process_activated")
        assert len(entries) >= 1


class TestProcessManagerSnapshot:
    """TC-PM-023: Snapshot round-trip."""

    def test_snapshot_round_trip(self, pm):
        # TC-PM-023
        c_info = pm.create_process(
            role="coder",
            tool_permits={"write_file"},
            viewport_spec=_make_viewport_spec("coder"),
        )
        pm.activate(c_info.process_id)

        r_info = pm.create_process(
            role="reviewer",
            tool_permits={"read_file"},
            viewport_spec=_make_viewport_spec("reviewer"),
        )

        data = pm.get_state_for_snapshot()

        # Create new PM and load state
        new_kanban = type(pm._kanban)()
        new_bus = type(pm._bus)(new_kanban)
        new_pm = type(pm)(new_kanban, new_bus)
        new_pm.load_state_from_snapshot(data)

        restored = new_pm.list_processes()
        assert len(restored) == 2
        # Check coder is still ACTIVE
        coder_restored = new_pm.get_process(c_info.process_id)
        assert coder_restored.state == ProcessState.ACTIVE
