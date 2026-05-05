"""CLI entry point for StateKanban.

Commands:
  statekanban run --intent INTENT [--config CONFIG] [--adapter ADAPTER] [--max-rounds N] [--verbose]
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
    "coder": {"write_file", "read_file", "call_llm", "call_codex", "search_code"},
    "reviewer": {"read_file", "call_llm", "search_code"},
    "tester": {"read_file", "run_shell", "call_llm", "search_code"},
    "integrator": {"write_file", "read_file", "run_shell", "call_llm", "call_codex", "search_code"},
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

    # 7. LLM Adapter (selected via --adapter)
    adapter = _create_llm_adapter(config)

    # 8. CodexAdapter (if selected)
    codex_adapter = None
    if config.llm_adapter == "codex":
        from statekanban.adapters.codex_adapter import CodexAdapter
        codex_adapter = CodexAdapter(
            cli_path=config.codex_cli_path,
            timeout=config.codex_timeout,
        )

    # 9. Engine sub-components (NEW)
    from statekanban.engine.engine import Engine
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

    # 10. Register built-in tools
    _register_tools(registry, valve, adapter, codex_adapter)

    return {
        "kanban": kanban,
        "bus": bus,
        "registry": registry,
        "valve": valve,
        "slicer": slicer,
        "pm": pm,
        "adapter": adapter,
        "codex_adapter": codex_adapter,
        "engine": engine,
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
    elif config.llm_adapter == "codex":
        from statekanban.adapters.codex_adapter import CodexAdapter
        return CodexAdapter(
            cli_path=config.codex_cli_path,
            timeout=config.codex_timeout,
        )
    else:
        from statekanban.adapters.mock_adapter import MockLLMAdapter
        return MockLLMAdapter()


def _register_tools(
    registry: ToolRegistry,
    valve: OutputValve,
    adapter: Any,
    codex_adapter: Any | None = None,
) -> None:
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

    # call_codex (NEW) -- only register if CodexAdapter is available
    if codex_adapter is not None:
        from statekanban.tools.call_codex import create_call_codex_tool
        registry.register(
            ToolDef(
                name="call_codex",
                description="Generate code via OpenAI Codex CLI. Input: prompt + context_files. Output: code snippet.",
                param_schema={
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "Code generation prompt"},
                        "context_files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of file paths for Codex context",
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Target file path for generated code",
                        },
                        "max_tokens": {"type": "integer", "default": 4096},
                    },
                    "required": ["prompt"],
                },
                required_permissions={"coder", "integrator"},
                timeout_seconds=300.0,
            ),
            create_call_codex_tool(codex_adapter),
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
@click.option("--adapter", type=click.Choice(["mock", "anthropic", "cli", "codex"]),
              default="mock", help="LLM adapter to use")
@click.option("--max-rounds", default=10, type=int, help="Maximum drive loop rounds")
@click.option("--verbose", is_flag=True, help="Output per-round details")
def run(intent: str, config_path: str | None, adapter: str,
        max_rounds: int, verbose: bool) -> None:
    """Start a development task with the drive loop."""
    # Validate intent
    if len(intent) > 4096:
        click.echo("Error: Intent exceeds maximum length (4096 characters)", err=True)
        sys.exit(1)

    try:
        intent.encode("utf-8")
    except UnicodeEncodeError:
        click.echo("Error: Intent must be valid UTF-8", err=True)
        sys.exit(1)

    # Load config with overrides
    config = _load_config(config_path)
    config.llm_adapter = adapter
    config.convergence_max_rounds = max_rounds

    # Bootstrap system
    components = _bootstrap_system(config)
    kanban = components["kanban"]
    pm = components["pm"]
    engine = components["engine"]

    # Set verbose mode on Engine
    engine.set_verbose(verbose)

    # Create and activate processes
    click.echo(f"Starting task: {intent}")
    click.echo(f"LLM adapter: {config.llm_adapter}")
    click.echo(f"Max rounds: {config.convergence_max_rounds}")

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

    # Create Integrator process
    integrator_spec = kanban.get_viewport_spec("integrator")
    if integrator_spec:
        integrator_info = pm.create_process(
            role="integrator",
            tool_permits=ROLE_TOOL_PERMITS["integrator"],
            viewport_spec=integrator_spec,
        )
        pm.activate(integrator_info.process_id)
        click.echo(f"Integrator process created: {integrator_info.process_id[:8]}...")

    # Run the drive loop via Engine
    click.echo("\nRunning drive loop...")
    try:
        result = asyncio.run(engine.drive(intent))
    except KeyboardInterrupt:
        click.echo("\nDrive loop interrupted by user", err=True)
        sys.exit(1)
    except Exception as exc:
        click.echo(f"\nDrive loop error: {exc}", err=True)
        sys.exit(1)

    # Output result summary
    click.echo("\n=== Drive Loop Result ===")
    click.echo(f"Converged: {result.converged}")
    click.echo(f"Forced terminate: {result.forced_terminate}")
    click.echo(f"Total rounds: {result.total_rounds}")
    click.echo(f"Error count: {result.error_count}")
    click.echo(f"Duration: {result.duration_seconds:.1f}s")
    if result.artifact_files:
        click.echo(f"Artifacts written: {', '.join(result.artifact_files)}")
    click.echo(f"Signal summary: {result.signal_summary}")

    if result.forced_terminate:
        click.echo(
            "\nCircuit break: max rounds exceeded. Manual intervention required.",
            err=True,
        )
        sys.exit(2)


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
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Config.from_dict(data)
    except FileNotFoundError:
        click.echo(f"Config file not found: {config_path}, using defaults", err=True)
        return Config()
    except Exception as exc:
        click.echo(f"Error loading config: {exc}, using defaults", err=True)
        return Config()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()