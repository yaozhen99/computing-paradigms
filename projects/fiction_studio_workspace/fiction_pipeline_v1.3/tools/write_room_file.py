import argparse
import json
from pathlib import Path

from record_action import record_action
from studio_core import ROOT, find_window, load_window_registry, resolve_project_path, write_text


def ensure_window(window_id):
    registry = load_window_registry()
    window = find_window(registry, window_id)
    if not window:
        raise SystemExit(f"Unknown window_id: {window_id}")
    return window


def relative_to_root(path):
    try:
        return path.resolve().relative_to(ROOT.resolve())
    except ValueError:
        raise SystemExit(f"Target is outside project root: {path}")


def validate_write_target(window, target):
    target_path = resolve_project_path(target)
    rel = relative_to_root(target_path)
    allowed_roots = window["effective_permissions"].get("write", [])
    if not allowed_roots:
        raise SystemExit(f"Window `{window['window_id']}` has no write permission.")

    rel_text = rel.as_posix()
    for room in allowed_roots:
        if rel_text == room or rel_text.startswith(f"{room}/"):
            return target_path, rel_text

    allowed = ", ".join(allowed_roots)
    raise SystemExit(
        f"Target `{rel_text}` is not under writable room(s) for window `{window['window_id']}`: {allowed}"
    )


def read_content(args):
    if args.content is not None:
        return args.content
    if args.content_file:
        path = resolve_project_path(args.content_file)
        if not path.exists():
            raise SystemExit(f"Unknown content file: {args.content_file}")
        return path.read_text(encoding="utf-8")
    raise SystemExit("Provide --content or --content-file.")


def write_room_file(args):
    window = ensure_window(args.window_id)
    target_path, rel_text = validate_write_target(window, args.target)
    content = read_content(args)

    if target_path.exists() and not args.overwrite:
        raise SystemExit(f"Target already exists. Use --overwrite to replace: {rel_text}")

    write_text(target_path, content)

    action_args = argparse.Namespace(
        window_id=args.window_id,
        action="write",
        target=rel_text,
        result=args.result or "Wrote file.",
        reason=args.reason,
        log=None,
    )
    record_action(action_args)

    return {
        "window_id": args.window_id,
        "target": rel_text,
        "bytes": len(content.encode("utf-8")),
        "overwrote": args.overwrite,
    }


def main():
    parser = argparse.ArgumentParser(description="Write a file through room/window permissions.")
    parser.add_argument("--window-id", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--content")
    parser.add_argument("--content-file")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--result")
    parser.add_argument("--reason")
    args = parser.parse_args()
    print(json.dumps(write_room_file(args), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

