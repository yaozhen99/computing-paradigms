# Node Protocol v1.01

## Role Boundary

- Each agent only edits files owned by its stage.
- Prose is written only by `lead_writer` and revised only by `revision_lead`.
- Editors write reports; they do not rewrite chapters.
- Freezer freezes and advances state; it does not rewrite prose.
- A stage window performs exactly one stage and stops after updating its lock.

## Startup Canon

Before any stage work, read the project startup package from `_system/START_HERE.md`.

Global settings come from `_system/project_canon.md`. They are not invented inside a chapter stage.

## Atomic Output

Do not submit placeholders, half chapters, empty reports, or incomplete canon files.

After completing a stage, update:

```json
{
  "stage": "<stage_name>",
  "status": "completed",
  "signed_by": "<role>",
  "signed_at": "<ISO 8601>",
  "chapter": <number or null>,
  "output_files": ["<relative/path>"]
}
```

After updating the lock, stop. Do not begin the next stage unless the user explicitly asks this same window to continue.

## Frozen Chapters

Files in `06_frozen_chapters/` are source of truth. Do not silently edit them.

## Canon Updates

If new upstream requirements arrive after a project has started, do not apply them directly to prose. Create a canon update plan, wait for approval, then update canon and derived planning files with an effective point.

## Logging

Append important actions to `_logs/pipeline_execution_log.md`:

```text
[<ISO 8601>] <role> - <action> - <result>
```
