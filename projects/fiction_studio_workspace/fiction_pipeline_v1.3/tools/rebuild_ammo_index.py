import argparse
import json
import re

from studio_core import ROOT, write_text


FIELD_RE = re.compile(r"^([A-Za-z][A-Za-z ]+):\s*(.*)$")
ID_RE = re.compile(r"^#\s+(ammo:[A-Za-z0-9_-]+:[A-Za-z0-9_-]+)\s*$", re.MULTILINE)


def parse_ammo_file(path):
    text = path.read_text(encoding="utf-8")
    id_match = ID_RE.search(text)
    ammo_id = id_match.group(1) if id_match else None
    fields = {}
    for line in text.splitlines():
        match = FIELD_RE.match(line)
        if match:
            fields[match.group(1)] = match.group(2).strip()
    summary = ""
    if "Summary:" in text:
        after = text.split("Summary:", 1)[1].strip()
        summary = after.splitlines()[0].strip() if after else ""
    return {
        "id": ammo_id,
        "path": str(path.relative_to(ROOT)),
        "status": fields.get("Status", "unknown"),
        "type": fields.get("Type", "unknown"),
        "tags": fields.get("Tags", ""),
        "source": fields.get("Source", ""),
        "canon_level": fields.get("Canon level", ""),
        "first_used": fields.get("First used", ""),
        "reuse_rule": fields.get("Reuse rule", ""),
        "summary": summary,
    }


def render_index(items):
    lines = [
        "# Ammo Index",
        "",
        "This file is maintained by the `Ammo Librarian`.",
        "",
        "Each indexed item should use:",
        "",
        "```markdown",
        "## ammo:<type>:<slug>",
        "",
        "Status:",
        "Type:",
        "Tags:",
        "Source:",
        "Canon level:",
        "First used:",
        "Reuse rule:",
        "",
        "Summary:",
        "",
        "Location:",
        "```",
        "",
        "Statuses:",
        "",
        "- `raw`",
        "- `hot`",
        "- `candidate`",
        "- `selected`",
        "- `canonized`",
        "- `used_once`",
        "- `recurring`",
        "- `spent`",
        "- `seeded`",
        "- `paid_off`",
        "- `retired`",
        "- `conflict`",
        "",
        "## Entries",
        "",
    ]
    if not items:
        lines.append("No ammo indexed yet.")
        return "\n".join(lines) + "\n"

    for item in sorted(items, key=lambda value: value["id"] or value["path"]):
        lines.extend(
            [
                f"## {item['id'] or 'UNKNOWN_ID'}",
                "",
                f"Status: {item['status']}",
                f"Type: {item['type']}",
                f"Tags: {item['tags']}",
                f"Source: {item['source']}",
                f"Canon level: {item['canon_level']}",
                f"First used: {item['first_used']}",
                f"Reuse rule: {item['reuse_rule']}",
                "",
                "Summary:",
                item["summary"],
                "",
                "Location:",
                item["path"],
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def rebuild_index(args):
    raw_dir = ROOT / "ammo_bank" / "raw"
    items = [parse_ammo_file(path) for path in sorted(raw_dir.glob("ammo__*.md"))]
    index_text = render_index(items)
    index_path = ROOT / "ammo_bank" / "index.md"
    if not args.dry_run:
        write_text(index_path, index_text)
    return {
        "count": len(items),
        "index": str(index_path.relative_to(ROOT)),
        "dry_run": args.dry_run,
        "items": [item["id"] for item in items],
    }


def main():
    parser = argparse.ArgumentParser(description="Rebuild ammo_bank/index.md from raw ammo files.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(json.dumps(rebuild_index(args), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

