import argparse
import json
from uuid import uuid4

from analyze_ammo import analyze_ammo, render_markdown as render_analysis_markdown
from import_ammo import import_ammo
from preflight_ammo import preflight, render_markdown as render_preflight_markdown
from studio_core import ROOT, now_iso, write_json, write_text


def namespace(**kwargs):
    return argparse.Namespace(**kwargs)


def batch_report_paths(batch_id):
    log_dir = ROOT / "ammo_bank" / "migration_logs"
    return (
        log_dir / f"migration_{batch_id}.json",
        log_dir / f"migration_{batch_id}.md",
    )


def render_batch_markdown(report):
    lines = [
        "# Ammo Migration Batch Report",
        "",
        f"Batch ID: `{report['batch_id']}`",
        f"Generated at: {report['generated_at']}",
        f"Source: `{report['source']}`",
        f"OK: {report['ok']}",
        f"Stopped at: {report['stopped_at'] or 'completed'}",
        "",
        "## Preflight",
        "",
        f"- OK to import: {report['preflight']['ok_to_import']}",
        f"- Valid items: {report['preflight']['valid_items']}",
        f"- Duplicate IDs: {len(report['preflight']['duplicate_ids'])}",
        f"- Existing targets: {len(report['preflight']['existing_targets'])}",
        f"- Existing IDs: {len(report['preflight']['existing_ids'])}",
        f"- Suspicious headings: {len(report['preflight']['suspicious_headings'])}",
        "",
        "## Dry Run",
        "",
    ]
    if report.get("dry_run"):
        dry_run = report["dry_run"]
        lines.extend(
            [
                f"- Planned writes: {len(dry_run['written'])}",
                f"- Planned skips: {len(dry_run['skipped'])}",
                f"- Existing targets: {len(dry_run['existing_targets'])}",
                f"- Existing IDs: {len(dry_run['existing_ids'])}",
            ]
        )
    else:
        lines.append("- not run")

    lines.extend(["", "## Import", ""])
    if report.get("import"):
        imported = report["import"]
        lines.extend(
            [
                f"- Written: {len(imported['written'])}",
                f"- Skipped: {len(imported['skipped'])}",
                f"- Index updated: {imported['index_updated']}",
            ]
        )
    else:
        lines.append("- not run")

    lines.extend(["", "## Analysis", ""])
    if report.get("analysis"):
        analysis = report["analysis"]
        lines.extend(
            [
                f"- Total items: {analysis['total_items']}",
                f"- Duplicate IDs: {len(analysis['duplicates'])}",
            ]
        )
    else:
        lines.append("- not run")

    if report.get("reason"):
        lines.extend(["", "## Reason", "", report["reason"]])

    return "\n".join(lines).rstrip() + "\n"


def write_batch_report(report):
    json_path, md_path = batch_report_paths(report["batch_id"])
    write_json(json_path, report)
    write_text(md_path, render_batch_markdown(report))
    return {
        "batch_json": str(json_path.relative_to(ROOT)),
        "batch_markdown": str(md_path.relative_to(ROOT)),
    }


def migrate(args):
    generated_at = now_iso()
    batch_id = generated_at.replace(":", "").replace("-", "") + "_" + uuid4().hex[:8]
    preflight_report = preflight(args.source)
    preflight_json = ROOT / "ammo_bank" / "preflight_report.json"
    preflight_md = ROOT / "ammo_bank" / "preflight_report.md"
    write_json(preflight_json, preflight_report)
    write_text(preflight_md, render_preflight_markdown(preflight_report))

    if args.preflight_only:
        result = {
            "batch_id": batch_id,
            "generated_at": generated_at,
            "ok": preflight_report["ok_to_import"],
            "stopped_at": "preflight_only",
            "source": args.source,
            "preflight_json": str(preflight_json.relative_to(ROOT)),
            "preflight_markdown": str(preflight_md.relative_to(ROOT)),
            "preflight": preflight_report,
        }
        result.update(write_batch_report(result))
        return result

    if not preflight_report["ok_to_import"] and not args.force:
        result = {
            "batch_id": batch_id,
            "generated_at": generated_at,
            "ok": False,
            "stopped_at": "preflight",
            "source": args.source,
            "reason": "Preflight failed. Use --force only after reviewing the report.",
            "preflight_json": str(preflight_json.relative_to(ROOT)),
            "preflight_markdown": str(preflight_md.relative_to(ROOT)),
            "preflight": preflight_report,
        }
        result.update(write_batch_report(result))
        return result

    dry_run_result = import_ammo(
        namespace(
            source=args.source,
            overwrite=args.overwrite,
            skip_existing=args.skip_existing,
            dry_run=True,
            no_index=args.no_index,
            allow_duplicate_ids=args.allow_duplicate_ids or args.force,
            allow_existing_ids=args.allow_existing_ids or args.force,
        )
    )

    if args.dry_run_only:
        result = {
            "batch_id": batch_id,
            "generated_at": generated_at,
            "ok": True,
            "stopped_at": "dry_run",
            "source": args.source,
            "preflight_json": str(preflight_json.relative_to(ROOT)),
            "preflight_markdown": str(preflight_md.relative_to(ROOT)),
            "preflight": preflight_report,
            "dry_run": dry_run_result,
        }
        result.update(write_batch_report(result))
        return result

    import_result = import_ammo(
        namespace(
            source=args.source,
            overwrite=args.overwrite,
            skip_existing=args.skip_existing,
            dry_run=False,
            no_index=args.no_index,
            allow_duplicate_ids=args.allow_duplicate_ids or args.force,
            allow_existing_ids=args.allow_existing_ids or args.force,
        )
    )

    analysis_report = analyze_ammo()
    analysis_json = ROOT / "ammo_bank" / "librarian_report.json"
    analysis_md = ROOT / "ammo_bank" / "librarian_report.md"
    write_json(analysis_json, analysis_report)
    write_text(analysis_md, render_analysis_markdown(analysis_report))

    result = {
        "batch_id": batch_id,
        "generated_at": generated_at,
        "ok": True,
        "stopped_at": None,
        "source": args.source,
        "preflight_json": str(preflight_json.relative_to(ROOT)),
        "preflight_markdown": str(preflight_md.relative_to(ROOT)),
        "analysis_json": str(analysis_json.relative_to(ROOT)),
        "analysis_markdown": str(analysis_md.relative_to(ROOT)),
        "preflight": preflight_report,
        "dry_run": dry_run_result,
        "import": import_result,
        "analysis": {
            "total_items": analysis_report["total_items"],
            "type_counts": analysis_report["type_counts"],
            "status_counts": analysis_report["status_counts"],
            "duplicates": analysis_report["duplicates"],
        },
    }
    result.update(write_batch_report(result))
    return result


def main():
    parser = argparse.ArgumentParser(description="Run the full ammo migration workflow.")
    parser.add_argument("--source", required=True)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--allow-duplicate-ids", action="store_true")
    parser.add_argument("--allow-existing-ids", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--no-index", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--dry-run-only", action="store_true")
    args = parser.parse_args()
    result = migrate(args)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
