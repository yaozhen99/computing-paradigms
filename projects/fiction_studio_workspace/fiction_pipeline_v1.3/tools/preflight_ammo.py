import argparse
import json
from collections import Counter

from import_ammo import find_suspicious_headings, parse_items, scan_existing_ids
from studio_core import ROOT, resolve_project_path, write_json, write_text


def preflight(source):
    source_path = resolve_project_path(source)
    if not source_path.exists():
        raise SystemExit(f"Unknown source file: {source}")
    text = source_path.read_text(encoding="utf-8")
    items = parse_items(text)
    ids = [item["id"] for item in items]
    id_counts = Counter(ids)
    duplicate_ids = {
        ammo_id: count for ammo_id, count in sorted(id_counts.items()) if count > 1
    }
    type_counts = Counter(item["type"] for item in items)
    planned_targets = []
    planned_target_paths = []
    existing_targets = []
    for item in items:
        target = ROOT / "ammo_bank" / "raw" / f"{item['id'].replace(':', '__')}.md"
        planned_target_paths.append(target)
        rel = str(target.relative_to(ROOT))
        planned_targets.append(rel)
        if target.exists():
            existing_targets.append(rel)

    existing_ids_by_id = scan_existing_ids(exclude_paths=planned_target_paths)
    existing_ids = {
        item["id"]: existing_ids_by_id[item["id"]]
        for item in items
        if item["id"] in existing_ids_by_id
    }
    suspicious = find_suspicious_headings(text)
    report = {
        "source": source,
        "valid_items": len(items),
        "type_counts": dict(sorted(type_counts.items())),
        "duplicate_ids": duplicate_ids,
        "suspicious_headings": suspicious,
        "planned_targets": planned_targets,
        "existing_targets": existing_targets,
        "existing_ids": existing_ids,
        "ok_to_import": bool(items)
        and not duplicate_ids
        and not suspicious
        and not existing_targets
        and not existing_ids,
    }
    return report


def render_markdown(report):
    lines = [
        "# Ammo Migration Preflight",
        "",
        f"Source: `{report['source']}`",
        "",
        f"Valid items: {report['valid_items']}",
        f"OK to import: {report['ok_to_import']}",
        "",
        "## Type Counts",
        "",
    ]
    if report["type_counts"]:
        for key, value in report["type_counts"].items():
            lines.append(f"- `{key}`: {value}")
    else:
        lines.append("- none")

    lines.extend(["", "## Duplicate IDs", ""])
    if report["duplicate_ids"]:
        for ammo_id, count in report["duplicate_ids"].items():
            lines.append(f"- `{ammo_id}`: {count}")
    else:
        lines.append("- none")

    lines.extend(["", "## Suspicious Headings", ""])
    if report["suspicious_headings"]:
        for item in report["suspicious_headings"]:
            lines.append(f"- line {item['line']}: `{item['heading']}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Existing Targets", ""])
    if report["existing_targets"]:
        for target in report["existing_targets"]:
            lines.append(f"- `{target}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Existing IDs", ""])
    if report["existing_ids"]:
        for ammo_id, paths in report["existing_ids"].items():
            lines.append(f"- `{ammo_id}`: {', '.join(f'`{path}`' for path in paths)}")
    else:
        lines.append("- none")

    lines.extend(["", "## Planned Targets", ""])
    if report["planned_targets"]:
        for target in report["planned_targets"]:
            lines.append(f"- `{target}`")
    else:
        lines.append("- none")

    return "\n".join(lines).rstrip() + "\n"


def main():
    parser = argparse.ArgumentParser(description="Preflight a raw ammo migration source.")
    parser.add_argument("--source", required=True)
    parser.add_argument("--json-output")
    parser.add_argument("--markdown-output")
    args = parser.parse_args()

    report = preflight(args.source)
    if args.json_output:
        write_json(ROOT / args.json_output, report)
    if args.markdown_output:
        write_text(ROOT / args.markdown_output, render_markdown(report))
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok_to_import"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
