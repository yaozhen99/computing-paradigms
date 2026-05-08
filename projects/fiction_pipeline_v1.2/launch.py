"""Fiction Pipeline v1.2 — One-click Launch

Reads launch_config.json and opens a mintty window for each stage,
running the configured AI tool (claude/codex/opencode) with per-stage
model, effort, and prompt settings.

Usage:  python launch.py [options]
        python launch.py --list              # show stages without launching
        python launch.py --stages 01 04 05   # launch specific stages only
        python launch.py --project test_novel
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parent
LAUNCH_CONFIG = PIPELINE_ROOT / "launch_config.json"
WORKSPACE = PIPELINE_ROOT / "workspace"
MINTTY = Path(os.environ.get("MINGW_PREFIX", r"C:\Program Files\Git")) / "usr" / "bin" / "mintty.exe"

WINDOW_POSITIONS = [
    "left",
    "right",
    "top",
    "bottom",
    "center",
]

TOOL_FLAGS = {
    # tool_name: { flag_key: cli_flag }
    "claude": {
        "model": "--model",
        "effort": "--effort",
        "name": "--name",
        "prompt_file": "--append-system-prompt-file",
    },
    "codex": {
        "model": "-m",
        "prompt_file": None,  # codex takes prompt as positional arg
    },
    "opencode": {
        "model": "-m",
        "prompt_file": "--prompt",
    },
}


def load_config(config_path: Path) -> dict:
    try:
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR: Cannot read {config_path}: {e}", file=sys.stderr)
        sys.exit(1)


def find_mintty() -> Path:
    if MINTTY.is_file():
        return MINTTY
    found = shutil.which("mintty")
    if found:
        return Path(found)
    print("ERROR: mintty not found. Install Git for Windows.", file=sys.stderr)
    sys.exit(1)


def check_tool(tool: str) -> str | None:
    found = shutil.which(tool)
    if not found:
        return None
    return found


def resolve_stage_dir(project: str, directory: str) -> Path:
    stage_dir = WORKSPACE / project / directory
    if not stage_dir.is_dir():
        print(f"WARNING: Stage directory not found: {stage_dir}", file=sys.stderr)
    return stage_dir


def resolve_prompt(prompt_file: str) -> Path:
    p = PIPELINE_ROOT / prompt_file
    if not p.is_file():
        print(f"WARNING: Prompt file not found: {p}", file=sys.stderr)
    return p


def build_tool_command(stage: dict, project: str) -> list[str]:
    tool = stage.get("tool", "claude")
    flags = TOOL_FLAGS.get(tool, {})
    cmd = [tool]

    # model
    model = stage.get("model")
    if model and "model" in flags:
        cmd.extend([flags["model"], model])

    # effort (claude only)
    effort = stage.get("effort")
    if effort and "effort" in flags:
        cmd.extend([flags["effort"], effort])

    # session name (claude only)
    if "name" in flags:
        cmd.extend([flags["name"], f"{project}/{stage['stage']}"])

    # prompt
    prompt_file = stage.get("prompt_file", "")
    prompt_path = resolve_prompt(prompt_file) if prompt_file else None
    if prompt_path and prompt_path.is_file():
        flag = flags.get("prompt_file")
        if flag:
            cmd.extend([flag, str(prompt_path)])
        elif tool == "codex":
            # codex: pass prompt content as positional arg
            cmd.append(str(prompt_path))

    return cmd


def launch_stage(mintty: Path, stage: dict, project: str, position: str) -> subprocess.Popen | None:
    stage_id = stage["stage"]
    tool = stage.get("tool", "claude")
    directory = stage["directory"]

    stage_dir = resolve_stage_dir(project, directory)

    # Check tool is available
    if not check_tool(tool):
        print(f"  SKIPPED:  {stage_id} — tool '{tool}' not found in PATH", file=sys.stderr)
        return None

    title = f"[{project}] {stage_id} ({tool}/{stage.get('model', 'default')})"

    tool_cmd = build_tool_command(stage, project)

    cmd = [
        str(mintty),
        "--title", title,
        "-s", "120x40",
        "-p", position,
        "-h", "always",
        "--exec",
    ] + tool_cmd

    try:
        proc = subprocess.Popen(cmd, cwd=str(stage_dir))
        model_str = stage.get("model", "default")
        effort_str = stage.get("effort", "")
        info = f"tool={tool}  model={model_str}"
        if effort_str:
            info += f"  effort={effort_str}"
        print(f"  Launched: {stage_id:<22s}  (PID {proc.pid})  {info}")
        return proc
    except OSError as e:
        print(f"  FAILED:   {stage_id} — {e}", file=sys.stderr)
        return None


def list_stages(config: dict):
    project = config.get("project", "?")
    stages = config.get("launches", [])
    print(f"Project: {project}")
    print(f"Stages:  {len(stages)}\n")
    for i, s in enumerate(stages):
        idx = f"{i+1:02d}"
        stage_dir = resolve_stage_dir(project, s["directory"])
        prompt_path = resolve_prompt(s.get("prompt_file", "")) if s.get("prompt_file") else None
        dir_ok = "OK" if stage_dir.is_dir() else "MISSING"
        prompt_ok = "OK" if prompt_path and prompt_path.is_file() else ("MISSING" if prompt_path else "NONE")
        tool = s.get("tool", "claude")
        model = s.get("model", "default")
        effort = s.get("effort", "-")
        tool_ok = "OK" if check_tool(tool) else "MISSING"
        print(f"  [{idx}] {s['stage']:<22s}  dir={dir_ok}  prompt={prompt_ok}  tool={tool_ok}")
        print(f"       tool:      {tool}")
        print(f"       model:     {model}")
        print(f"       effort:    {effort}")
        print(f"       directory: {s['directory']}")
        if s.get("prompt_file"):
            print(f"       prompt:    {s['prompt_file']}")


def main():
    parser = argparse.ArgumentParser(description="Launch fiction pipeline stage windows")
    parser.add_argument("--list", action="store_true", help="List stages without launching")
    parser.add_argument("--project", help="Override project name from config")
    parser.add_argument("--stages", nargs="+", help="Launch only specific stage numbers (e.g. 01 04 05)")
    parser.add_argument("--config", help="Override config file path")
    args = parser.parse_args()

    config_path = Path(args.config) if args.config else LAUNCH_CONFIG
    config = load_config(config_path)
    project = args.project or config.get("project", "")

    if not project:
        print("ERROR: No project specified. Use --project or set 'project' in launch_config.json", file=sys.stderr)
        sys.exit(1)

    stages = config.get("launches", [])

    if args.list:
        list_stages(config)
        return

    # Filter stages if --stages specified
    if args.stages:
        selected = set()
        for s in args.stages:
            try:
                idx = int(s) - 1
                if 0 <= idx < len(stages):
                    selected.add(idx)
                else:
                    print(f"WARNING: Stage number {s} out of range (1-{len(stages)})", file=sys.stderr)
            except ValueError:
                matches = [i for i, st in enumerate(stages) if st["stage"].startswith(s)]
                if matches:
                    selected.update(matches)
                else:
                    print(f"WARNING: No stage matching '{s}'", file=sys.stderr)
        stages = [stages[i] for i in sorted(selected)]

    if not stages:
        print("No stages to launch.", file=sys.stderr)
        sys.exit(1)

    mintty = find_mintty()

    print(f"Launching {len(stages)} stage(s) for project '{project}'...\n")

    procs = []
    for i, stage in enumerate(stages):
        pos = WINDOW_POSITIONS[i % len(WINDOW_POSITIONS)]
        proc = launch_stage(mintty, stage, project, pos)
        if proc:
            procs.append(proc)

    print(f"\nDone. {len(procs)}/{len(stages)} windows launched.")
    print("Close each window when its stage completes.")


if __name__ == "__main__":
    main()
