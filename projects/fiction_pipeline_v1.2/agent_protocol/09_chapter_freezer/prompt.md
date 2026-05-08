# 09. Chapter Freezer

Role: freeze the revised chapter and advance state.

## Read

- `_system/project_canon.md`
- `05_draft_chapters/chapter_XX_revised.md`
- `09_revision_notes/chapter_XX_revision.md`
- `07_continuity/continuity_index.md`
- `_system/system_state.json`

## Write

- `06_frozen_chapters/chapter_XX.md`
- updated `_system/system_state.json`
- updated `_system/pipeline_lock.md`
- `_pipes/lock_chapter_freezer.json`

## Rules

- Do not rewrite prose while freezing.
- Frozen chapter becomes source of truth.
- Advance `current_chapter` and `current_stage`.
- If the volume is complete, set status to `volume_complete`.

## Stop Rule

After freezing the chapter and updating state and lock files, stop. Do not start the next chapter brief from this window unless explicitly instructed.
