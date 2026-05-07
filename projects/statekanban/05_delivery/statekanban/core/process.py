"""ProcessManager: process lifecycle management.

State machine: CREATED -> ACTIVE -> SUSPENDED -> TERMINATED
No self-termination -- only the scheduler can terminate a process.
"""

from __future__ import annotations

import datetime
import uuid

from statekanban.core.errors import (
    HandoffError,
    HeartbeatTimeoutError,
    InvalidStateTransitionError,
    SelfTerminationError,
)
from statekanban.core.kanban import (
    ProcessInfo,
    ProcessState,
    StateKanban,
    ViewportSpec,
)
from statekanban.core.message_bus import MessageBus

# Default heartbeat interval in seconds
DEFAULT_HEARTBEAT_INTERVAL = 30


class ProcessManager:
    """Process lifecycle management."""

    # Valid state transitions: {from_state: {to_state}}
    VALID_TRANSITIONS: dict[ProcessState, set[ProcessState]] = {
        ProcessState.CREATED: {ProcessState.ACTIVE},
        ProcessState.ACTIVE: {ProcessState.SUSPENDED, ProcessState.TERMINATED},
        ProcessState.SUSPENDED: {ProcessState.ACTIVE, ProcessState.TERMINATED},
        ProcessState.TERMINATED: set(),  # Terminal state
    }

    def __init__(self, kanban: StateKanban, bus: MessageBus) -> None:
        """
        Args:
            kanban: StateKanban instance for state storage.
            bus: MessageBus instance for inter-process communication.
        """
        self._kanban = kanban
        self._bus = bus
        self._processes: dict[str, ProcessInfo] = {}
        self._role_processes: dict[str, str] = {}  # role -> process_id (latest)
        self._heartbeat_interval = DEFAULT_HEARTBEAT_INTERVAL
        self._heartbeat_threshold = DEFAULT_HEARTBEAT_INTERVAL * 3

    def create_process(
        self,
        role: str,
        tool_permits: set[str],
        viewport_spec: ViewportSpec,
    ) -> ProcessInfo:
        """Create a new process in CREATED state.

        Args:
            role: Process role name.
            tool_permits: Set of allowed tool names.
            viewport_spec: Viewport configuration for this role.

        Returns:
            ProcessInfo for the newly created process.

        Raises:
            InvalidStateTransitionError: Role already has an active process.
        """
        # Check if role already has an active process
        existing_pid = self._role_processes.get(role)
        if existing_pid and existing_pid in self._processes:
            existing = self._processes[existing_pid]
            if existing.state == ProcessState.ACTIVE:
                raise InvalidStateTransitionError(
                    f"Role '{role}' already has an active process: {existing_pid}"
                )

        process_id = str(uuid.uuid4())
        process_info = ProcessInfo(
            process_id=process_id,
            role=role,
            state=ProcessState.CREATED,
            tool_permits=tool_permits,
            viewport_spec=viewport_spec,
        )

        self._processes[process_id] = process_info
        self._role_processes[role] = process_id

        self._kanban.audit.log(
            event_type="process_created",
            actor="ProcessManager",
            action="create_process",
            details={
                "process_id": process_id,
                "role": role,
            },
        )

        return process_info

    def activate(self, process_id: str) -> None:
        """Transition process from CREATED or SUSPENDED to ACTIVE.

        Starts heartbeat timer.

        Raises:
            InvalidStateTransitionError: Current state does not allow activation.
        """
        process = self._get_process_or_error(process_id)
        self._validate_transition(process.state, ProcessState.ACTIVE)

        process.state = ProcessState.ACTIVE
        process.heartbeat_at = datetime.datetime.now(tz=datetime.timezone.utc)

        self._kanban.audit.log(
            event_type="process_activated",
            actor="ProcessManager",
            action="activate",
            details={"process_id": process_id, "role": process.role},
        )

    def suspend(self, process_id: str) -> None:
        """Transition process from ACTIVE to SUSPENDED.

        Raises:
            InvalidStateTransitionError: Not currently ACTIVE.
        """
        process = self._get_process_or_error(process_id)
        self._validate_transition(process.state, ProcessState.SUSPENDED)

        process.state = ProcessState.SUSPENDED

        self._kanban.audit.log(
            event_type="process_suspended",
            actor="ProcessManager",
            action="suspend",
            details={"process_id": process_id, "role": process.role},
        )

    def terminate(self, process_id: str, terminator: str) -> None:
        """Transition process to TERMINATED.

        Args:
            process_id: The process to terminate.
            terminator: Identity of the terminating entity (must not be the process itself).

        Raises:
            SelfTerminationError: Process attempted to terminate itself.
            InvalidStateTransitionError: Already TERMINATED.
        """
        process = self._get_process_or_error(process_id)

        # Self-termination check
        if terminator == process_id:
            raise SelfTerminationError(f"Process {process_id} cannot terminate itself")

        self._validate_transition(process.state, ProcessState.TERMINATED)

        process.state = ProcessState.TERMINATED

        self._kanban.audit.log(
            event_type="process_terminated",
            actor="ProcessManager",
            action="terminate",
            details={
                "process_id": process_id,
                "role": process.role,
                "terminated_by": terminator,
            },
        )

    def claim_primary(self, role: str, new_process_id: str) -> None:
        """New process claims primary role, cleaning up predecessor.

        Terminates the old process for this role and activates the new one.

        Raises:
            HandoffError: No predecessor exists or handoff failed.
        """
        old_pid = self._role_processes.get(role)
        if not old_pid or old_pid not in self._processes:
            raise HandoffError(f"No predecessor process exists for role: {role}")

        if new_process_id not in self._processes:
            raise HandoffError(f"New process not found: {new_process_id}")

        new_process = self._processes[new_process_id]
        if new_process.role != role:
            raise HandoffError(
                f"New process role '{new_process.role}' does not match expected role '{role}'"
            )

        # Terminate old process
        old_process = self._processes[old_pid]
        if old_process.state != ProcessState.TERMINATED:
            old_process.state = ProcessState.TERMINATED

        # Activate new process
        if new_process.state == ProcessState.CREATED:
            new_process.state = ProcessState.ACTIVE
        new_process.heartbeat_at = datetime.datetime.now(tz=datetime.timezone.utc)

        # Update role mapping
        self._role_processes[role] = new_process_id

        # Inherit viewport spec from predecessor
        new_process.viewport_spec = old_process.viewport_spec

        self._kanban.audit.log(
            event_type="handoff",
            actor="ProcessManager",
            action="claim_primary",
            details={
                "role": role,
                "old_process_id": old_pid,
                "new_process_id": new_process_id,
            },
        )

    def check_heartbeats(self) -> list[str]:
        """Check all active processes for heartbeat timeout.

        Returns:
            List of process IDs that have timed out.
        """
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        timed_out: list[str] = []

        for pid, process in self._processes.items():
            if process.state != ProcessState.ACTIVE:
                continue
            if process.heartbeat_at is None:
                continue

            elapsed = (now - process.heartbeat_at).total_seconds()
            if elapsed > self._heartbeat_threshold:
                timed_out.append(pid)
                self._kanban.audit.log(
                    event_type="heartbeat_timeout",
                    actor="ProcessManager",
                    action="check_heartbeats",
                    details={
                        "process_id": pid,
                        "role": process.role,
                        "elapsed_seconds": elapsed,
                    },
                )

        return timed_out

    def heartbeat(self, process_id: str) -> None:
        """Record a heartbeat for a process.

        Updates the heartbeat_at timestamp on the ProcessInfo.
        """
        process = self._get_process_or_error(process_id)
        if process.state != ProcessState.ACTIVE:
            raise InvalidStateTransitionError(
                f"Cannot heartbeat process in state: {process.state.value}"
            )
        process.heartbeat_at = datetime.datetime.now(tz=datetime.timezone.utc)

    def get_process(self, process_id: str) -> ProcessInfo | None:
        """Get process info by ID."""
        return self._processes.get(process_id)

    def list_processes(self, state: ProcessState | None = None) -> list[ProcessInfo]:
        """List processes, optionally filtered by state."""
        processes = list(self._processes.values())
        if state is not None:
            processes = [p for p in processes if p.state == state]
        return processes

    def get_state_for_snapshot(self) -> dict[str, Any]:
        """Export process state for snapshot serialization."""
        return {
            "processes": {pid: p.to_dict() for pid, p in self._processes.items()},
            "role_processes": dict(self._role_processes),
            "heartbeat_interval": self._heartbeat_interval,
            "heartbeat_threshold": self._heartbeat_threshold,
        }

    def load_state_from_snapshot(self, data: dict[str, Any]) -> None:
        """Import process state from snapshot data."""
        self._processes.clear()
        self._role_processes.clear()

        for pid, pdata in data.get("processes", {}).items():
            self._processes[pid] = ProcessInfo.from_dict(pdata)
        self._role_processes.update(data.get("role_processes", {}))
        self._heartbeat_interval = data.get(
            "heartbeat_interval", DEFAULT_HEARTBEAT_INTERVAL
        )
        self._heartbeat_threshold = data.get(
            "heartbeat_threshold", DEFAULT_HEARTBEAT_INTERVAL * 3
        )

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _get_process_or_error(self, process_id: str) -> ProcessInfo:
        """Get a process or raise if not found."""
        process = self._processes.get(process_id)
        if process is None:
            raise InvalidStateTransitionError(f"Process not found: {process_id}")
        return process

    def _validate_transition(
        self, from_state: ProcessState, to_state: ProcessState
    ) -> None:
        """Validate that a state transition is allowed."""
        allowed = self.VALID_TRANSITIONS.get(from_state, set())
        if to_state not in allowed:
            raise InvalidStateTransitionError(
                f"Invalid transition: {from_state.value} -> {to_state.value}"
            )
