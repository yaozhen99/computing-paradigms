# Story Master v1.01 Startup Protocol

Role: receive novel requirements, create a project instance under `workspace/<project>/`, and write the discussion result into standard startup files.

## Requirement Intake

Requirement source files live in:

```text
00_story_master/user_inputs/
```

This path is relative to the `fiction_pipeline_v1.2` root.

If the user already prepared a requirement file, read it from that directory. If not, discuss the novel with the user and write the first intake record to:

```text
00_story_master/user_inputs/<story_name>.md
```

Collect:

- project name
- core premise
- world canon
- main characters
- terminology
- physical or system constraints
- volume goal
- voice preference
- hard boundaries and continuity facts

## Create Project Space

For `$STORY_SPACE`, create:

```text
README.md
_system/
  START_HERE.md
  project_canon.md
  stage_entrypoints.md
  stage_manifest.json
  system_state.json
  pipeline_blueprint.json
  pipeline_lock.md
_pipes/
_logs/
_shared/
01_story_bible/
  README.md
02_voice_anchor/
  README.md
03_rolling_outline/
  README.md
04_chapter_briefs/
  README.md
05_draft_chapters/
  README.md
06_frozen_chapters/
  README.md
07_continuity/
  README.md
08_style_reports/
  README.md
09_revision_notes/
  README.md
```

## Write Startup Files

`README.md` points to `_system/START_HERE.md`.

`_system/START_HERE.md` defines startup read order, current resume point, and current stage entrypoint.

`_system/project_canon.md` contains the initial global canon from requirement discussion.

`_system/stage_entrypoints.md` defines purpose, read files, write files, and lock file for each stage.

`_system/stage_manifest.json` defines the same stage file flow in machine-readable form for dashboards.

Each stage directory `README.md` lets an AI window open directly in that directory and perform only that stage.

## Initialize State

Create `_system/system_state.json` with:

```json
{
  "story_name": "<story_name>",
  "volume": 1,
  "status": "initialized",
  "current_stage": "story_bible",
  "current_chapter": 1,
  "total_chapters": null,
  "veto_count": 0,
  "max_veto": 3,
  "human_approval_required": ["story_bible", "voice_anchor", "rolling_outline"],
  "approved": {},
  "completed_stages": [],
  "frozen_chapters": [],
  "startup_inputs": [
    "_system/START_HERE.md",
    "_system/project_canon.md",
    "_system/stage_entrypoints.md",
    "_system/stage_manifest.json"
  ],
  "created_at": "<ISO 8601>",
  "updated_at": "<ISO 8601>"
}
```

## Initialize Locks

Create one `_pipes/lock_<stage>.json` per stage:

```json
{
  "stage": "<stage>",
  "status": "pending",
  "signed_by": null,
  "signed_at": null,
  "chapter": null,
  "output_files": []
}
```

## Hard Rules

- Do not rely on chat history as project memory.
- Do not scatter global settings into chapter briefs.
- Do not create old stage names such as `worldbuilding`, `outliner`, `writer`, `editor`, or `finalizer`.
- Do not allow parallel chapter prose writing.
