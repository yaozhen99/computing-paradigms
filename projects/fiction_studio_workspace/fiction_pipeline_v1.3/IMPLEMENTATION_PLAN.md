# Implementation Plan

## Phase 1: Studio documents

Status: started

Goals:

- define the room model
- define AI window ownership
- define inheritance
- define effective permissions
- create initial room directories

Outputs:

- `README.md`
- `_policy/*`
- `_windows/window_record.template.json`
- initial room READMEs

## Phase 2: Policy data files

Status: started

Goals:

- add machine-readable room policy
- add machine-readable role policy
- add permission matrix
- add policy version records

Suggested outputs:

- `_policy/rooms.json`
- `_policy/roles.json`
- `_policy/permission_matrix.json`
- `_policy/policy_versions.json`

## Phase 3: Window registry

Status: running

Goals:

- record every AI window
- bind windows to rooms
- store parent-child relationships
- compute effective permissions

Suggested outputs:

- `_windows/window_registry.json`
- `_windows/window_log.md`
- `tools/create_window.py`

First command:

```bash
python tools/create_window.py --room ammo_bank --role "Idea Assistant"
```

## Phase 4: Control panel prototype

Goals:

- show room tree
- show active windows
- show inheritance chain
- show effective permission matrix
- allow safe policy edits

The control panel may be a local script or web UI. It should not replace the OS or runtime.

## Phase 5: Launch mapping

Status: running

Goals:

- issue commands from a selected room
- create window metadata before launching AI
- inject room, role, and permission context into the AI prompt
- write output into the correct room

Initial tools:

- `tools/explain_permissions.py`
- `tools/build_window_packet.py`
- `tools/launch_window.py`
- `tools/validate_policy.py`
- `tools/record_action.py`
- `tools/write_room_file.py`
- `tools/import_ammo.py`
- `tools/analyze_ammo.py`
- `tools/preflight_ammo.py`
- `tools/migrate_ammo.py`
- `tools/rebuild_ammo_index.py`

Task support:

- inline `--task`
- file-based `--task-file`
- first task example: `author_room/tasks/initial_premise.md`

Runnable entry:

- `QUICKSTART.md`

## Phase 7: Tests

Status: started

Goals:

- validate policy JSON files
- validate permission explanation
- validate launch packet generation

Initial tests:

- `tests/test_tools.py`

Current coverage:

- policy JSON parsing
- permission explanation
- launch packet generation
- parent window permission constraints

## Phase 9: Audit tools

Status: started

Goals:

- record window actions
- route editorial/canon/asset/publication actions to the correct logs
- reject audited actions that the window is not permitted to perform

## Phase 10: Controlled writes

Status: started

Goals:

- write files through room/window permissions
- reject writes outside allowed room roots
- automatically audit successful writes

## Phase 11: Ammo migration

Status: started

Goals:

- import `### idea:category:name` raw ammo
- assign stable ammo IDs
- write raw ammo files
- update `ammo_bank/index.md`
- prepare material for `Ammo Librarian` review

Current outputs:

- `ammo_bank/librarian_report.md`
- `ammo_bank/librarian_report.json`

Recommended migration order:

1. `tools/preflight_ammo.py`
2. `tools/import_ammo.py --dry-run`
3. `tools/import_ammo.py`
4. `tools/analyze_ammo.py`

One-command migration:

- `tools/migrate_ammo.py`

Maintenance:

- `tools/rebuild_ammo_index.py`

## Phase 6: Writing workflow

Goals:

- author premise
- author outline
- notebook capture
- ammo generation
- asset development
- canonization
- editorial review
- revision
- publication freeze

Rule:

This workflow is room-based, not stage-based.

## Phase 8: Room and role prompts

Status: started

Goals:

- provide AI-readable room instructions
- provide AI-readable role instructions
- include both in generated window packets
