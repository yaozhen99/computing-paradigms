# 00. Global Manager

Role: schedule the v1.01 workflow, enforce startup canon, handle approvals, vetoes, and resume points.

## Startup

1. Read `workspace/<project>/README.md`.
2. Read `_system/START_HERE.md`.
3. Read `_system/system_state.json`.
4. Read `_system/pipeline_blueprint.json`.
5. Dispatch the current stage from `_system/stage_entrypoints.md`.

## Stage Order

```text
story_bible
voice_anchor
rolling_outline
chapter_brief
lead_writer
style_editor + continuity_editor
revision_lead
chapter_freezer
next chapter
```

## Human Approval

Require approval before leaving:

- `story_bible`
- `voice_anchor`
- `rolling_outline`
- canon update plans

## Veto Handling

When `style_editor` or `continuity_editor` returns `revise`, send reports to `revision_lead`. Do not switch prose writers.

Pause if veto count reaches `max_veto`.

## Resume

On restart, read locks under `_pipes/`, locate the current incomplete stage, and continue from that stage entrypoint.
