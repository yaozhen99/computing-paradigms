import argparse
import json
from pathlib import Path

from build_window_packet import build_packet, render_markdown, write_json, write_text
from create_window import create_window
from studio_core import PACKET_DIR, ROOT, resolve_project_path


def render_start_prompt(record, markdown_packet_path):
    return f"""# Start AI Window

You are starting a room-owned AI window.

Window: `{record["window_id"]}`

Room: `{record["room"]}`

Role: `{record["role"]}`

Parent window: `{record["parent_window_id"] or "none"}`

Task: {record.get("task") or "No inline task was provided."}

Task file: `{record.get("task_file") or "none"}`

## Required First Action

Read `{markdown_packet_path}` before doing any work.

Then read every file listed under `Must Read` in that packet.

If `Task file` is not `none`, read it before starting the task.

## Operating Boundary

- Work only as the role assigned above.
- Treat the room above as your owning room.
- Follow the effective permissions in the packet.
- Do not write outside allowed paths.
- Do not canonize, approve, or freeze unless the packet explicitly grants that permission.
- Stop after completing the room-scoped task.
"""


def launch(args):
    if args.task_file:
        task_path = resolve_project_path(args.task_file)
        if not task_path.exists():
            raise SystemExit(f"Unknown task file: {args.task_file}")

    record = create_window(args, persist=not args.dry_run)
    packet = build_packet(record)

    json_path = PACKET_DIR / f"{record['window_id']}.json"
    md_path = PACKET_DIR / f"{record['window_id']}.md"
    start_path = PACKET_DIR / f"{record['window_id']}.start.md"
    if args.dry_run:
        return {
            "window_id": record["window_id"],
            "room": record["room"],
            "role": record["role"],
            "dry_run": True,
            "packet_json": str(json_path.relative_to(ROOT)),
            "packet_markdown": str(md_path.relative_to(ROOT)),
            "start_prompt": str(start_path.relative_to(ROOT)),
            "next_step": f"Review the planned packet at {md_path.relative_to(ROOT)}",
        }
    write_json(json_path, packet)
    write_text(md_path, render_markdown(packet))
    md_rel = str(md_path.relative_to(ROOT))
    write_text(start_path, render_start_prompt(record, md_rel))

    result = {
        "window_id": record["window_id"],
        "room": record["room"],
        "role": record["role"],
        "packet_json": str(json_path.relative_to(ROOT)),
        "packet_markdown": str(md_path.relative_to(ROOT)),
        "start_prompt": str(start_path.relative_to(ROOT)),
        "next_step": f"Start the AI window with prompt: {start_path.relative_to(ROOT)}",
    }
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Create a room-owned AI window and build its startup packet."
    )
    parser.add_argument("--room", required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--parent-window-id")
    parser.add_argument("--source-command")
    parser.add_argument("--window-id")
    parser.add_argument("--task")
    parser.add_argument("--task-file")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(json.dumps(launch(args), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
