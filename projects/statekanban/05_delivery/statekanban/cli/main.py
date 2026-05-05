"""CLI entry point for StateKanban.

Commands:
  statekanban run --intent INTENT [--config CONFIG]
  statekanban status
  statekanban snapshot [--output PATH]
  statekanban restore --file PATH
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

import click

from statekanban.config import Config
from statekanban.core.kanban import (
    ArtifactType,
    ProcessState,
    SignalType,
    StateKanban,
    ViewportSpec,
    make_signal_id,
    now_utc,
)
from statekanban.core.message_bus import MessageBus
from statekanban.core.process import ProcessManager
from statekanban.core.registry import ToolRegistry
from statekanban.core.valve import OutputValve
from statekanban.core.viewport import ViewportSlicer
from statekanban.snapshot import load_snapshot, save_snapshot


# ---------------------------------------------------------------------------
# Built-in viewport specs per role
# ---------------------------------------------------------------------------

def _default_viewport_specs() -> dict[str, ViewportSpec]:
    """Create default viewport specs for all built-in roles."""
    return {
        "coder": ViewportSpec(
            role="coder",
            visible_signal_types=[SignalType.INTENT, SignalType.ERROR],
            visible_artifact_types=[ArtifactType.CODE, ArtifactType.CONFIG],
            visible_target_patterns=["*"],
            max_tokens=2000,
        ),
        "reviewer": ViewportSpec(
            role="reviewer",
            visible_signal_types=[SignalType.INTENT, SignalType.VETO, SignalType.ERROR],
            visible_artifact_types=[ArtifactType.CODE, ArtifactType.CONFIG, ArtifactType.DOC],
            visible_target_patterns=["*"],
            max_tokens=2000,
        ),
        "tester": ViewportSpec(
            role="tester",
            visible_signal_types=[SignalType.INTENT, SignalType.ERROR],
            visible_artifact_types=[ArtifactType.CODE, ArtifactType.TEST],
            visible_target_patterns=["*"],
            max_tokens=2000,
        ),
        "integrator": ViewportSpec(
            role="integrator",
            visible_signal_types=[SignalType.INTENT, SignalType.VETO, SignalType.ERROR],
            visible_artifact_types=[ArtifactType.CODE, ArtifactType.CONFIG, ArtifactType.TEST],
            visible_target_patterns=["*"],
            max_tokens=2000,
        ),
        "architect": ViewportSpec(
            role="architect",
            visible_signal_types=[SignalType.INTENT, SignalType.VETO, SignalType.ERROR],
            visible_artifact_types=[ArtifactType.CODE, ArtifactType.CONFIG, ArtifactType.DOC],
            visible_target_patterns=["*"],
            max_tokens=2000,
        ),
    }


# ---------------------------------------------------------------------------
# Role tool permits
# ---------------------------------------------------------------------------

ROLE_TOOL_PERMITS: dict[str, set[str]] = {
    "coder": {"write_file", "read_file", "call_llm", "search_code"},
    "reviewer": {"read_file", "call_llm", "search_code"},
    "tester": {"read_file", "run_shell", "call_llm", "search_code"},
    "integrator": {"write_file", "read_file", "run_shell", "call_llm", "search_code"},
    "architect": {"read_file", "call_llm", "search_code"},
}


# ---------------------------------------------------------------------------
# System bootstrap
# ---------------------------------------------------------------------------

def _bootstrap_system(config: Config) -> dict[str, Any]:
    """Initialize all system components in the correct dependency order.

    Returns a dict with all initialized components.
    """
    # 1. StateKanban (no dependencies)
    kanban = StateKanban()

    # 2. MessageBus (depends on StateKanban)
    bus = MessageBus(kanban)

    # 3. ToolRegistry (depends on StateKanban)
    registry = ToolRegistry(kanban)

    # 4. OutputValve (validators)
    valve = OutputValve(kanban=kanban)

    # 5. ViewportSlicer (depends on StateKanban)
    specs = _default_viewport_specs()
    for spec in specs.values():
        kanban.register_viewport(spec)
    slicer = ViewportSlicer(kanban, specs)

    # 6. ProcessManager (depends on StateKanban + MessageBus)
    pm = ProcessManager(kanban, bus)

    # 7. LLM Adapter
    adapter = _create_llm_adapter(config)

    # 8. Register built-in tools
    _register_tools(registry, valve, adapter)

    return {
        "kanban": kanban,
        "bus": bus,
        "registry": registry,
        "valve": valve,
        "slicer": slicer,
        "pm": pm,
        "adapter": adapter,
        "config": config,
    }


def _create_llm_adapter(config: Config) -> Any:
    """Create the configured LLM adapter."""
    if config.llm_adapter == "anthropic":
        from statekanban.adapters.anthropic_adapter import AnthropicMessagesAdapter
        return AnthropicMessagesAdapter(model=config.llm_model)
    elif config.llm_adapter == "cli":
        from statekanban.adapters.cli_adapter import ClaudeCLIAdapter
        return ClaudeCLIAdapter()
    else:
        from statekanban.adapters.mock_adapter import MockLLMAdapter
        return MockLLMAdapter()


def _register_tools(registry: ToolRegistry, valve: OutputValve, adapter: Any) -> None:
    """Register all built-in tools in the registry."""
    from statekanban.core.kanban import ToolDef

    # write_file
    from statekanban.tools.write_file import create_write_file_tool
    registry.register(
        ToolDef(
            name="write_file",
            description="Write artifact to filesystem (via OutputValve)",
            param_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "artifact_type": {"type": "string", "default": "code"},
                },
                "required": ["path", "content"],
            },
            required_permissions={"coder", "integrator"},
            timeout_seconds=60.0,
        ),
        create_write_file_tool(valve),
    )

    # read_file
    from statekanban.tools.read_file import read_file
    registry.register(
        ToolDef(
            name="read_file",
            description="Read file contents",
            param_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                },
                "required": ["path"],
            },
            required_permissions={"all_roles"},
            timeout_seconds=30.0,
        ),
        read_file,
    )

    # run_shell
    from statekanban.tools.run_shell import run_shell
    registry.register(
        ToolDef(
            name="run_shell",
            description="Execute shell command",
            param_schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "timeout": {"type": "number", "default": 60},
                    "cwd": {"type": "string"},
                },
                "required": ["command"],
            },
            required_permissions={"integrator", "tester"},
            timeout_seconds=120.0,
        ),
        run_shell,
    )

    # call_llm
    from statekanban.tools.call_llm import create_call_llm_tool
    registry.register(
        ToolDef(
            name="call_llm",
            description="Invoke LLM via adapter",
            param_schema={
                "type": "object",
                "properties": {
                    "messages": {"type": "array"},
                    "tools": {"type": "array"},
                    "max_tokens": {"type": "integer", "default": 4096},
                    "temperature": {"type": "number", "default": 0.0},
                },
                "required": ["messages"],
            },
            required_permissions={"all_roles"},
            timeout_seconds=120.0,
        ),
        create_call_llm_tool(adapter),
    )

    # search_code
    from statekanban.tools.search_code import search_code
    registry.register(
        ToolDef(
            name="search_code",
            description="Search codebase for patterns",
            param_schema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string", "default": "."},
                    "file_glob": {"type": "string", "default": "*.py"},
                    "max_results": {"type": "integer", "default": 50},
                },
                "required": ["pattern"],
            },
            required_permissions={"all_roles"},
            timeout_seconds=30.0,
        ),
        search_code,
    )


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------

@click.group()
def cli() -> None:
    """StateKanban -- Instruction-level development engine."""
    pass


@cli.command()
@click.option("--intent", required=True, help="Task intent description")
@click.option("--config", "config_path", default=None, help="Path to config file")
def run(intent: str, config_path: str | None) -> None:
    """Start a development task."""
    # Validate intent
    if len(intent) > 4096:
        click.echo("Error: Intent exceeds maximum length (4096 characters)", err=True)
        sys.exit(1)

    try:
        intent.encode("utf-8")
    except UnicodeEncodeError:
        click.echo("Error: Intent must be valid UTF-8", err=True)
        sys.exit(1)

    # Load config
    config = _load_config(config_path)

    # Bootstrap system
    components = _bootstrap_system(config)
    kanban = components["kanban"]
    pm = components["pm"]

    # Create and activate processes
    click.echo(f"Starting task: {intent}")
    click.echo(f"LLM adapter: {config.llm_adapter}")

    # Create Coder process
    coder_spec = kanban.get_viewport_spec("coder")
    if coder_spec is None:
        click.echo("Error: Coder viewport spec not found", err=True)
        sys.exit(1)

    coder_info = pm.create_process(
        role="coder",
        tool_permits=ROLE_TOOL_PERMITS["coder"],
        viewport_spec=coder_spec,
    )
    pm.activate(coder_info.process_id)
    click.echo(f"Coder process created: {coder_info.process_id[:8]}...")

    # Create Reviewer process
    reviewer_spec = kanban.get_viewport_spec("reviewer")
    if reviewer_spec:
        reviewer_info = pm.create_process(
            role="reviewer",
            tool_permits=ROLE_TOOL_PERMITS["reviewer"],
            viewport_spec=reviewer_spec,
        )
        pm.activate(reviewer_info.process_id)
        click.echo(f"Reviewer process created: {reviewer_info.process_id[:8]}...")

    # Create Tester process
    tester_spec = kanban.get_viewport_spec("tester")
    if tester_spec:
        tester_info = pm.create_process(
            role="tester",
            tool_permits=ROLE_TOOL_PERMITS["tester"],
            viewport_spec=tester_spec,
        )
        pm.activate(tester_info.process_id)
        click.echo(f"Tester process created: {tester_info.process_id[:8]}...")

    # Write initial intent signal to FluidZone
    from statekanban.core.kanban import IntentSignal
    intent_signal = IntentSignal(
        signal_id=make_signal_id(),
        author_role="user",
        target_id="task_root",
        payload={"intent": intent},
        timestamp=now_utc(),
        round_number=0,
    )
    kanban.fluid.write_signal(intent_signal)

    click.echo(f"\nIntent signal written to FluidZone")
    click.echo(f"Active processes: {len(pm.list_processes(ProcessState.ACTIVE))}")
    click.echo(f"FluidZone signals: {len(kanban.fluid.read_signals())}")
    click.echo(f"CrystalZone artifacts: {kanban.crystal.latest_seq_no()}")
    click.echo(f"\nTask initialized. Use 'statekanban status' to check progress.")


@cli.command()
def status() -> None:
    """Display current kanban status (FluidZone / CrystalZone summary)."""
    # Try to load from default snapshot
    import os
    default_snapshot = os.path.join(".statekanban", "snapshots", "latest.json")

    if os.path.exists(default_snapshot):
        try:
            kanban = load_snapshot(default_snapshot)
        except Exception as exc:
            click.echo(f"Error loading snapshot: {exc}", err=True)
            sys.exit(1)
    else:
        # Create a fresh kanban for status display
        kanban = StateKanban()

    # FluidZone summary
    all_signals = kanban.fluid.read_signals()
    intent_count = len(kanban.fluid.read_signals(signal_type=SignalType.INTENT))
    veto_count = len(kanban.fluid.read_signals(signal_type=SignalType.VETO))
    error_count = len(kanban.fluid.read_signals(signal_type=SignalType.ERROR))

    click.echo("=== StateKanban Status ===")
    click.echo("")
    click.echo("--- FluidZone ---")
    click.echo(f"  Total signals: {len(all_signals)}")
    click.echo(f"  Intent signals: {intent_count}")
    click.echo(f"  Veto signals: {veto_count}")
    click.echo(f"  Error signals: {error_count}")

    # CrystalZone summary
    click.echo("")
    click.echo("--- CrystalZone ---")
    click.echo(f"  Latest seq_no: {kanban.crystal.latest_seq_no()}")
    for at in ArtifactType:
        artifacts = kanban.crystal.read_artifacts(artifact_type=at)
        click.echo(f"  {at.value} artifacts: {len(artifacts)}")

    # AuditZone summary
    click.echo("")
    click.echo("--- AuditZone ---")
    entries = kanban.audit.read_entries()
    click.echo(f"  Total entries: {len(entries)}")
    if entries:
        click.echo(f"  Last entry: {entries[-1].action} by {entries[-1].actor}")

    # ProcessManager summary
    click.echo("")
    click.echo("--- Processes ---")
    pm = ProcessManager(kanban, MessageBus(kanban))
    for state in ProcessState:
        processes = pm.list_processes(state)
        click.echo(f"  {state.value}: {len(processes)}")


@cli.command()
@click.option("--output", default="snapshot.json", help="Output file path")
def snapshot(output: str) -> None:
    """Create a kanban snapshot."""
    # Try to load from default snapshot first
    import os
    default_snapshot = os.path.join(".statekanban", "snapshots", "latest.json")

    if os.path.exists(default_snapshot):
        try:
            kanban = load_snapshot(default_snapshot)
        except Exception:
            kanban = StateKanban()
    else:
        kanban = StateKanban()

    try:
        save_snapshot(kanban, output)
        click.echo(f"Snapshot saved to: {output}")
        click.echo(f"Checksum: {kanban.to_json().get('checksum', 'N/A')[:16]}...")
    except Exception as exc:
        click.echo(f"Error saving snapshot: {exc}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--file", "snapshot_file", required=True, help="Snapshot file to restore from")
def restore(snapshot_file: str) -> None:
    """Restore kanban from a snapshot."""
    try:
        kanban = load_snapshot(snapshot_file)
        click.echo(f"Snapshot restored from: {snapshot_file}")

        # Show restored state summary
        all_signals = kanban.fluid.read_signals()
        click.echo(f"FluidZone signals: {len(all_signals)}")
        click.echo(f"CrystalZone latest: {kanban.crystal.latest_seq_no()}")

        # Save as latest snapshot
        import os
        latest_path = os.path.join(".statekanban", "snapshots", "latest.json")
        save_snapshot(kanban, latest_path)
        click.echo(f"Saved as latest snapshot: {latest_path}")

    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except Exception as exc:
        click.echo(f"Error restoring snapshot: {exc}", err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_config(config_path: str | None) -> Config:
    """Load configuration from file or return defaults."""
    if config_path is None:
        return Config()

    import os
    if not os.path.exists(config_path):
        click.echo(f"Config file not found: {config_path}, using defaults", err=True)
        return Config()

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Config.from_dict(data)
    except Exception as exc:
        click.echo(f"Error loading config: {exc}, using defaults", err=True)
        return Config()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
