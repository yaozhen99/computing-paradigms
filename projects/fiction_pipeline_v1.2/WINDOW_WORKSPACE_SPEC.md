# Window Workspace Spec

This file defines how `fiction_pipeline_v1.2` supports multiple AI windows, each working in a specific stage directory.

## Goal

Each stage directory in a generated project is a workspace entrypoint.

An AI window can open directly in:

```text
workspace/<project>/<stage_directory>/
```

Then it reads the local `README.md` and performs only that stage's work.

## Project Stage Directories

Generated projects must include local entry README files:

```text
workspace/<project>/
  01_story_bible/README.md
  02_voice_anchor/README.md
  03_rolling_outline/README.md
  04_chapter_briefs/README.md
  05_draft_chapters/README.md
  06_frozen_chapters/README.md
  07_continuity/README.md
  08_style_reports/README.md
  09_revision_notes/README.md
```

## Local README Contract

Each stage README must state:

- stage id
- role
- when to run
- required startup files
- stage-specific input files
- allowed output files
- lock file to update
- whether the stage may run in parallel
- recommended model profile

## Window Rule

An AI window opened inside a stage directory must not scan the whole project by default.

It reads:

1. local `README.md`
2. `../_system/START_HERE.md`
3. `../_system/project_canon.md`
4. `../_system/stage_manifest.json`
5. only the files listed for its stage

## Stop Rule

A stage window owns exactly one stage.

After completing its allowed outputs and updating its lock file, it must stop. It must not automatically start the next stage, even if the next stage is obvious from `system_state.json` or `stage_manifest.json`.

The final response from a stage window should state:

```text
<stage_id> completed. Next stage: <next_stage_id>. Open that stage window to continue.
```

The only exception is an explicit user instruction to continue into another stage in the same window.

## Dashboard Rule

A dashboard reads:

```text
workspace/<project>/_system/stage_manifest.json
workspace/<project>/_system/system_state.json
workspace/<project>/_pipes/lock_*.json
```

It can then show:

- stage status
- assigned model profile
- input files
- output files
- blocked/runnable/completed state

## Parallelism

Default:

- `style_editor` and `continuity_editor` may run in parallel after `lead_writer` completes.
- prose writing stages do not run in parallel with other prose writing stages.
- `revision_lead` waits for both editor reports.
- `chapter_freezer` waits for revision.

## Model Profiles

Stage directories refer to symbolic model profiles such as:

- `requirement_architect`
- `canon_planner`
- `prose_lead`
- `style_critic`
- `continuity_auditor`
- `mechanical_operator`

Concrete model names are configured outside the project canon so they can change without changing the novel.
