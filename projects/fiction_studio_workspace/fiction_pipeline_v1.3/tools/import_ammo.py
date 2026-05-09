import argparse
import json
import re
from collections import Counter
from pathlib import Path
from uuid import uuid4

from studio_core import ROOT, now_iso, resolve_project_path, write_json, write_text


HEADING_RE = re.compile(r"^###\s+idea:([A-Za-z0-9_-]+):([A-Za-z0-9_-]+)\s*$", re.MULTILINE)
LOOSE_HEADING_RE = re.compile(r"^###\s+(.+)$", re.MULTILINE)
AMMO_ID_RE = re.compile(r"^#\s+(ammo:[A-Za-z0-9_-]+:[A-Za-z0-9_-]+)\s*$", re.MULTILINE)


def normalize_slug(value):
    return re.sub(r"[^a-zA-Z0-9_:-]+", "_", value.strip()).strip("_").lower()


def parse_items(text):
    matches = list(HEADING_RE.finditer(text))
    items = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        category = normalize_slug(match.group(1))
        name = normalize_slug(match.group(2))
        raw_text = text[start:end].strip()
        ammo_id = f"ammo:{category}:{name}"
        items.append(
            {
                "id": ammo_id,
                "type": category,
                "slug": name,
                "raw_text": raw_text,
            }
        )
    return items


def find_suspicious_headings(text):
    valid_spans = {match.span() for match in HEADING_RE.finditer(text)}
    suspicious = []
    for match in LOOSE_HEADING_RE.finditer(text):
        if match.span() not in valid_spans:
            suspicious.append(
                {
                    "line": text.count("\n", 0, match.start()) + 1,
                    "heading": match.group(0),
                }
            )
    return suspicious


def scan_existing_ids(exclude_paths=None):
    excluded = {Path(path).resolve() for path in exclude_paths or []}
    ids = {}
    raw_dir = ROOT / "ammo_bank" / "raw"
    for path in sorted(raw_dir.glob("ammo__*.md")):
        if path.resolve() in excluded:
            continue
        text = path.read_text(encoding="utf-8")
        match = AMMO_ID_RE.search(text)
        if match:
            ids.setdefault(match.group(1), []).append(str(path.relative_to(ROOT)))
    return ids


def render_item(item, source):
    summary = item["raw_text"].splitlines()[0] if item["raw_text"] else ""
    return f"""# {item["id"]}

Status: raw
Type: {item["type"]}
Tags: []
Source: {source}
Canon level: none
First used: none
Reuse rule: unassigned

Summary:
{summary}

Raw text:
{item["raw_text"]}
"""


def index_entry(item):
    path = f"ammo_bank/raw/{item['id'].replace(':', '__')}.md"
    summary = item["raw_text"].splitlines()[0] if item["raw_text"] else ""
    return f"""
## {item["id"]}

Status: raw
Type: {item["type"]}
Tags: []
Source: imported
Canon level: none
First used: none
Reuse rule: unassigned

Summary:
{summary}

Location:
{path}
"""


def import_ammo(args):
    source_path = resolve_project_path(args.source)
    if not source_path.exists():
        raise SystemExit(f"Unknown source file: {args.source}")
    text = source_path.read_text(encoding="utf-8")
    items = parse_items(text)
    if not items:
        raise SystemExit("No ammo headings found. Expected headings like: ### idea:category:name")

    id_counts = Counter(item["id"] for item in items)
    duplicate_ids = {ammo_id: count for ammo_id, count in id_counts.items() if count > 1}
    existing_targets = []
    planned_target_paths = []
    planned = []
    skipped = []
    errors = []

    for item in items:
        filename = f"{item['id'].replace(':', '__')}.md"
        target = ROOT / "ammo_bank" / "raw" / filename
        planned_target_paths.append(target)
        rel_target = str(target.relative_to(ROOT))
        planned.append(rel_target)
        if target.exists():
            existing_targets.append(rel_target)

    existing_ids_by_id = scan_existing_ids(exclude_paths=planned_target_paths)
    existing_ids = {
        item["id"]: existing_ids_by_id[item["id"]]
        for item in items
        if item["id"] in existing_ids_by_id
    }

    if duplicate_ids and not args.allow_duplicate_ids:
        errors.append("Duplicate IDs in source. Use --allow-duplicate-ids to import anyway.")

    if existing_targets and not (args.overwrite or args.skip_existing):
        errors.append("Some targets already exist. Use --overwrite or --skip-existing.")

    if existing_ids and not args.allow_existing_ids:
        errors.append("Some ammo IDs already exist in different raw files. Review before importing.")

    batch = {
        "time": now_iso(),
        "source": args.source,
        "dry_run": args.dry_run,
        "count": len(items),
        "planned": planned,
        "existing_targets": existing_targets,
        "existing_ids": existing_ids,
        "duplicate_ids": duplicate_ids,
        "skipped": skipped,
        "errors": errors,
    }

    if errors:
        write_batch_log(batch)
        raise SystemExit(json.dumps(batch, indent=2, ensure_ascii=False))

    written = []
    for item in items:
        filename = f"{item['id'].replace(':', '__')}.md"
        target = ROOT / "ammo_bank" / "raw" / filename
        rel_target = str(target.relative_to(ROOT))
        if target.exists() and args.skip_existing:
            skipped.append(rel_target)
            continue
        if not args.dry_run:
            write_text(target, render_item(item, "imported"))
        written.append(rel_target)

    if not args.no_index and not args.dry_run:
        index_path = ROOT / "ammo_bank" / "index.md"
        with index_path.open("a", encoding="utf-8") as f:
            f.write("\n")
            f.write(f"<!-- import source: {args.source} -->\n")
            for item in items:
                filename = f"{item['id'].replace(':', '__')}.md"
                if str((ROOT / "ammo_bank" / "raw" / filename).relative_to(ROOT)) in skipped:
                    continue
                f.write(index_entry(item))

    batch.update(
        {
            "written": written,
            "skipped": skipped,
            "index_updated": not args.no_index and not args.dry_run,
        }
    )
    write_batch_log(batch)
    return {
        "source": args.source,
        "count": len(items),
        "written": written,
        "skipped": skipped,
        "dry_run": args.dry_run,
        "duplicate_ids": duplicate_ids,
        "existing_targets": existing_targets,
        "existing_ids": existing_ids,
        "index_updated": not args.no_index and not args.dry_run,
    }


def write_batch_log(batch):
    log_dir = ROOT / "ammo_bank" / "migration_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    safe_time = batch["time"].replace(":", "").replace("-", "")
    log_path = log_dir / f"import_{safe_time}_{uuid4().hex[:8]}.json"
    write_json(log_path, batch)


def main():
    parser = argparse.ArgumentParser(description="Import ### idea:category:name ammo into ammo_bank.")
    parser.add_argument("--source", required=True)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-index", action="store_true")
    parser.add_argument("--allow-duplicate-ids", action="store_true")
    parser.add_argument("--allow-existing-ids", action="store_true")
    args = parser.parse_args()
    print(json.dumps(import_ammo(args), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
