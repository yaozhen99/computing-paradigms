import argparse
import json
import re
from collections import Counter, defaultdict

from studio_core import ROOT, now_iso, write_json, write_text


FIELD_RE = re.compile(r"^([A-Za-z][A-Za-z ]+):\s*(.*)$")
ID_RE = re.compile(r"^#\s+(ammo:[A-Za-z0-9_-]+:[A-Za-z0-9_-]+)\s*$", re.MULTILINE)


REQUIRED_FIELDS = [
    "Status",
    "Type",
    "Tags",
    "Source",
    "Canon level",
    "First used",
    "Reuse rule",
]


def parse_ammo_file(path):
    text = path.read_text(encoding="utf-8")
    id_match = ID_RE.search(text)
    ammo_id = id_match.group(1) if id_match else None
    fields = {}
    for line in text.splitlines():
        match = FIELD_RE.match(line)
        if match:
            fields[match.group(1)] = match.group(2).strip()
    return {
        "path": str(path.relative_to(ROOT)),
        "id": ammo_id,
        "fields": fields,
        "text": text,
    }


def classify_quality(item):
    missing = [field for field in REQUIRED_FIELDS if field not in item["fields"]]
    status = item["fields"].get("Status", "")
    tags = item["fields"].get("Tags", "")
    summary_present = "Summary:" in item["text"] and bool(item["text"].split("Summary:", 1)[1].strip())
    candidate_signals = []
    if status == "raw" and summary_present and tags not in ["", "[]"]:
        candidate_signals.append("raw item has summary and tags")
    return {
        "missing_fields": missing,
        "candidate_signals": candidate_signals,
    }


def analyze_ammo():
    raw_dir = ROOT / "ammo_bank" / "raw"
    items = [parse_ammo_file(path) for path in sorted(raw_dir.glob("ammo__*.md"))]
    ids = [item["id"] for item in items if item["id"]]
    id_counts = Counter(ids)
    type_counts = Counter(item["fields"].get("Type", "unknown") for item in items)
    status_counts = Counter(item["fields"].get("Status", "unknown") for item in items)

    missing_by_item = {}
    candidate_suggestions = []
    for item in items:
        quality = classify_quality(item)
        if quality["missing_fields"]:
            missing_by_item[item["path"]] = quality["missing_fields"]
        if quality["candidate_signals"]:
            candidate_suggestions.append(
                {
                    "id": item["id"],
                    "path": item["path"],
                    "signals": quality["candidate_signals"],
                }
            )

    duplicates = {
        ammo_id: count for ammo_id, count in sorted(id_counts.items()) if count > 1
    }
    by_type = defaultdict(list)
    for item in items:
        by_type[item["fields"].get("Type", "unknown")].append(item["id"] or item["path"])

    return {
        "generated_at": now_iso(),
        "total_items": len(items),
        "type_counts": dict(sorted(type_counts.items())),
        "status_counts": dict(sorted(status_counts.items())),
        "duplicates": duplicates,
        "missing_metadata": missing_by_item,
        "candidate_suggestions": candidate_suggestions,
        "by_type": {key: sorted(value) for key, value in sorted(by_type.items())},
    }


def render_markdown(report):
    lines = [
        "# Ammo Librarian Report",
        "",
        f"Generated at: {report['generated_at']}",
        "",
        f"Total items: {report['total_items']}",
        "",
        "## Status Counts",
        "",
    ]
    if report["status_counts"]:
        for key, value in report["status_counts"].items():
            lines.append(f"- `{key}`: {value}")
    else:
        lines.append("- none")

    lines.extend(["", "## Type Counts", ""])
    if report["type_counts"]:
        for key, value in report["type_counts"].items():
            lines.append(f"- `{key}`: {value}")
    else:
        lines.append("- none")

    lines.extend(["", "## Duplicates", ""])
    if report["duplicates"]:
        for ammo_id, count in report["duplicates"].items():
            lines.append(f"- `{ammo_id}`: {count}")
    else:
        lines.append("- none")

    lines.extend(["", "## Missing Metadata", ""])
    if report["missing_metadata"]:
        for path, fields in report["missing_metadata"].items():
            lines.append(f"- `{path}`: {', '.join(fields)}")
    else:
        lines.append("- none")

    lines.extend(["", "## Candidate Suggestions", ""])
    if report["candidate_suggestions"]:
        for item in report["candidate_suggestions"]:
            lines.append(f"- `{item['id']}` from `{item['path']}`: {', '.join(item['signals'])}")
    else:
        lines.append("- none")

    lines.extend(["", "## By Type", ""])
    if report["by_type"]:
        for item_type, ids in report["by_type"].items():
            lines.append(f"### {item_type}")
            for ammo_id in ids:
                lines.append(f"- `{ammo_id}`")
            lines.append("")
    else:
        lines.append("- none")

    return "\n".join(lines).rstrip() + "\n"


def main():
    parser = argparse.ArgumentParser(description="Analyze indexed raw ammo.")
    parser.add_argument("--json-output", default="ammo_bank/librarian_report.json")
    parser.add_argument("--markdown-output", default="ammo_bank/librarian_report.md")
    args = parser.parse_args()

    report = analyze_ammo()
    write_json(ROOT / args.json_output, report)
    write_text(ROOT / args.markdown_output, render_markdown(report))
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

