# Fiction Pipeline v1.2 Specification

This file defines the full `fiction_pipeline_v1.2` workflow.

## Core Model

A novel project has two layers:

1. Pipeline template layer: root files, `00_story_master/`, and `agent_protocol/`.
2. Project instance layer: files under `workspace/<project>/`.

The template layer defines how projects are created. The project instance layer contains the actual novel canon, state, drafts, reports, and frozen chapters.

## Requirement Intake

Requirement intake starts from:

```text
00_story_master/user_inputs/
```

This path is relative to the `fiction_pipeline_v1.2` repository root.

If the user prepared a requirement document in advance, the requirement-taking AI reads that file. If no prepared document exists, the requirement-taking AI discusses the novel with the user, then writes the first intake record to:

```text
00_story_master/user_inputs/<project>.md
```

## Project Creation

For a project named `<project>`, create:

```text
workspace/<project>/
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

## Standard Startup

Every project instance starts from:

```text
workspace/<project>/README.md
```

The README points to:

```text
_system/START_HERE.md
```

`START_HERE.md` defines the startup package. At minimum:

1. `_system/project_canon.md`
2. `_system/system_state.json`
3. `_system/stage_entrypoints.md`
4. `_system/stage_manifest.json`
5. frozen chapter context if any
6. voice anchor if available
7. rolling outline
8. continuity index
9. current stage input

## Project Canon

`_system/project_canon.md` is the standard location for initial novel settings produced during requirement discussion.

It contains:

- core premise
- world canon
- characters
- system rules if relevant
- terminology
- physical constraints
- volume goal
- hard continuity facts

It is generated from the intake record in `00_story_master/user_inputs/` plus approved discussion updates.

## Stage Entrypoints

`_system/stage_entrypoints.md` defines how each stage can be resumed independently.

Each stage entry must specify:

- purpose
- files to read
- files to write
- lock file to update

`_system/stage_manifest.json` contains the same file-flow contract in machine-readable form for dashboards and automation.

Each stage directory also contains a local `README.md`, allowing an AI window to start directly inside that directory and perform only that stage.

A stage window stops after completing its own outputs and lock. It must not automatically continue into the next stage unless the user explicitly instructs it to do so.

## Chapter Flow

Foundation stages:

```text
story_bible
  -> voice_anchor
  -> rolling_outline
```

Per-chapter stages:

```text
chapter_brief
  -> lead_writer
  -> style_editor + continuity_editor
  -> revision_lead
  -> chapter_freezer
  -> next chapter
```

## Canon Update Flow

If a running project receives new upstream requirements:

1. Store the new requirement or change request as an intake record.
2. Do not write chapters directly from the new request.
3. Produce a canon update plan.
4. After approval, update `_system/project_canon.md` and affected derivative files.
5. Mark the effective point, for example `effective_from: chapter_02`.
6. Frozen chapters remain unchanged unless explicitly reopened.

## Non-Negotiables

- The requirement-taking AI must write project canon into `_system/project_canon.md`.
- A follow-up AI must be able to start from `workspace/<project>/README.md`.
- Global canon belongs to startup, not to a midstream chapter brief.
- A stage window completes exactly one stage, then stops.
- Only one lead writer writes or revises prose for a chapter.
- Editors write reports; they do not rewrite the chapter.
- A chapter becomes source of truth only after it is frozen in `06_frozen_chapters/`.
