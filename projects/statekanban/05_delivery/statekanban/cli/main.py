#!/usr/bin/env python3
"""StateKanban CLI entry point.

Supports:
  - drive   : run the engine loop for a given intent
  - snapshot: save / load / list / delete snapshots
  - --structured / --behavior : select MockLLMAdapter mode
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from typing import Any

from statekanban import __version__
from statekanban.config import Config
from statekanban.core.kanban import StateKanban
from statekanban.core.message_bus import MessageBus
from statekanban.core.process import ProcessManager
from statekanban.core.registry import ToolRegistry
from statekanban.core.valve import OutputValve
from statekanban.core.viewport import ViewportSlicer
from statekanban.engine.engine import Engine
from statekanban.snapshot import (
    SnapshotManager,
    save_snapshot,
    load_snapshot,
    list_snapshots,
    delete_snapshot,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="statekanban",
        description="StateKanban -- instruction-level development engine",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    sub = parser.add_subparsers(dest="command", help="sub-commands")

    # --- drive sub-command ---
    drive_p = sub.add_parser("drive", help="Run the engine loop")
    drive_p.add_argument("intent", help="Task intent string")
    drive_p.add_argument(
        "--adapter",
        choices=["mock", "codex"],
        default="mock",
        help="LLM adapter to use (default: mock)",
    )
    drive_p.add_argument(
        "--structured",
        action="store_true",
        help="Use MockLLMAdapter structured_mode (REQ-001)",
    )
    drive_p.add_argument(
        "--behavior",
        action="store_true",
        help="Use MockLLMAdapter behavior_mode (REQ-001)",
    )
    drive_p.add_argument(
        "--rounds",
        type=int,
        default=None,
        help="Max convergence rounds (overrides config)",
    )
    drive_p.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-round progress to stderr",
    )
    drive_p.add_argument(
        "--snapshot-save",
        default=None,
        help="Save snapshot after drive completes",
    )
    drive_p.add_argument(
        "--no-registry",
        action="store_true",
        help="Bypass ToolRegistry for LLM calls (direct adapter, for testing)",
    )
    drive_p.add_argument(
        "--project-root",
        default=None,
        help="Project root directory (default: current working directory)",
    )

    # --- snapshot sub-command ---
    snap_p = sub.add_parser("snapshot", help="Snapshot management")
    snap_sub = snap_p.add_subparsers(dest="snapshot_action", help="snapshot actions")

    # snapshot save
    save_p = snap_sub.add_parser("save", help="Save current kanban snapshot")
    save_p.add_argument("path", help="Snapshot file path")
    save_p.add_argument(
        "--kanban-state",
        default=None,
        help="Path to existing kanban JSON (if omitted, creates empty)",
    )

    # snapshot load
    load_p = snap_sub.add_parser("load", help="Load kanban from snapshot")
    load_p.add_argument("path", help="Snapshot file path")

    # snapshot list
    snap_sub.add_parser("list", help="List all snapshots")

    # snapshot delete
    del_p = snap_sub.add_parser("delete", help="Delete a snapshot")
    del_p.add_argument("path", help="Snapshot file path")

    return parser


def cmd_drive(args: argparse.Namespace) -> int:
    """Execute the 'drive' sub-command."""
    config = Config()
    if args.rounds is not None:
        config.convergence_max_rounds = args.rounds

    # REQ-502: --project-root validation and propagation
    if args.project_root is not None:
        if "\x00" in args.project_root:
            print("Error: --project-root contains null bytes", file=sys.stderr)
            return 1
        resolved = os.path.abspath(args.project_root)
        if not os.path.isdir(resolved):
            print(f"Project root does not exist: {resolved}")
            return 1
        config.project_root = resolved

    # Determine MockLLMAdapter mode
    adapter = _create_adapter(args)

    # Build system components
    kanban = StateKanban()
    bus = MessageBus(kanban)
    registry = ToolRegistry(kanban)
    valve = OutputValve(kanban=kanban, project_root=config.project_root)

    # Set up viewport specs
    specs = _default_viewport_specs()
    for spec in specs.values():
        kanban.register_viewport(spec)
    slicer = ViewportSlicer(kanban, specs)

    pm = ProcessManager(kanban, bus)

    # Create engine
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
    engine.set_verbose(args.verbose)

    # REQ-004: Configure registry routing
    if args.no_registry:
        engine.set_use_registry_for_llm(False)

    # Register call_llm tool
    from statekanban.core.kanban import ToolDef
    from statekanban.tools.call_llm import create_call_llm_tool

    registry.register(
        ToolDef(
            name="call_llm",
            description="Invoke LLM via adapter",
            param_schema={
                "type": "object",
                "properties": {
                    "messages": {"type": "array"},
                    "max_tokens": {"type": "integer"},
                    "temperature": {"type": "number"},
                },
                "required": ["messages"],
            },
            required_permissions={"all_roles"},
            timeout_seconds=120.0,
        ),
        create_call_llm_tool(adapter),
    )

    # Create and activate a coder process
    coder_spec = kanban.get_viewport_spec("coder")
    if coder_spec:
        coder_info = pm.create_process(
            role="coder",
            tool_permits={"write_file", "read_file", "call_llm"},
            viewport_spec=coder_spec,
        )
        pm.activate(coder_info.process_id)

    # Run
    try:
        result = asyncio.run(engine.drive(args.intent))
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # Print result
    print(f"Rounds: {result.total_rounds}")
    print(f"Converged: {result.converged}")
    if result.artifact_files:
        print("Artifacts:")
        for f in result.artifact_files:
            print(f"  - {f}")

    # Save snapshot if requested
    if args.snapshot_save:
        try:
            save_snapshot(kanban, args.snapshot_save)
            print(f"Snapshot saved: {args.snapshot_save}", file=sys.stderr)
        except Exception as exc:
            print(f"Snapshot save failed: {exc}", file=sys.stderr)

    return 0 if result.converged else 1


def cmd_snapshot(args: argparse.Namespace) -> int:
    """Execute the 'snapshot' sub-command."""
    if args.snapshot_action == "save":
        if args.kanban_state:
            kanban = load_snapshot(args.kanban_state)
        else:
            kanban = StateKanban()
        save_snapshot(kanban, args.path)
        print(f"Snapshot saved: {args.path}")
        return 0

    elif args.snapshot_action == "load":
        kanban = load_snapshot(args.path)
        print(f"Snapshot loaded: {args.path}")
        print(f"  Fluid signals: {len(kanban.fluid.read_signals())}")
        print(f"  Crystal artifacts: {len(kanban.crystal.read_artifacts())}")
        return 0

    elif args.snapshot_action == "list":
        entries = list_snapshots()
        if not entries:
            print("No snapshots found.")
        else:
            print("Snapshots:")
            for name in entries:
                print(f"  - {name}")
        return 0

    elif args.snapshot_action == "delete":
        delete_snapshot(args.path)
        print(f"Snapshot deleted: {args.path}")
        return 0

    else:
        print("Unknown snapshot action. Use: save, load, list, delete", file=sys.stderr)
        return 1


def _create_adapter(args: argparse.Namespace) -> Any:
    """Create the LLM adapter based on CLI arguments.

    Handles --structured, --behavior, and --adapter flags.
    """
    if args.adapter == "codex":
        from statekanban.adapters.codex_adapter import CodexAdapter

        return CodexAdapter()

    # Default: MockLLMAdapter
    from statekanban.adapters.mock_adapter import MockLLMAdapter

    if args.structured:
        return MockLLMAdapter(mode="structured")
    elif args.behavior:
        return MockLLMAdapter(mode="behavior")
    else:
        return MockLLMAdapter(mode="mock")


def _default_viewport_specs() -> dict[str, Any]:
    """Create default viewport specs for built-in roles."""
    from statekanban.core.kanban import (
        ArtifactType,
        SignalType,
        ViewportSpec,
    )

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
            visible_artifact_types=[
                ArtifactType.CODE,
                ArtifactType.CONFIG,
                ArtifactType.DOC,
            ],
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
            visible_artifact_types=[
                ArtifactType.CODE,
                ArtifactType.CONFIG,
                ArtifactType.TEST,
            ],
            visible_target_patterns=["*"],
            max_tokens=2000,
        ),
    }


def main() -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "drive":
        return cmd_drive(args)
    elif args.command == "snapshot":
        return cmd_snapshot(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
