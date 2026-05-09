# fiction_pipeline_v1.3

v1.3 is a writer-centered studio, not a chapter pipeline.

Core objects:

- `author_premise`: the author's first compass
- `author_outline`: the writer-owned working outline
- `room`: a directory with a defined purpose and permission boundary
- `window`: one AI session bound to one room
- `role`: the function a window performs
- `inheritance`: how room, role, and parent context shape the window
- `effective_permissions`: the final permissions a window actually has

Rule order:

`project root -> room -> role -> parent window -> manual override`

Primary rooms:

- `author_room`
- `notebook`
- `ammo_bank`
- `asset_room`
- `canon_room`
- `editorial_room`
- `revision_room`
- `publication_room`
- `_policy`
- `_logs`
- `_windows`

Room flow:

`author_room -> notebook -> ammo_bank -> asset_room -> author_room -> canon_room -> editorial_room -> revision_room -> publication_room`

This is not a rigid pipeline. It is the default material path. The Chief Author can move between rooms, reject material, or send work back to earlier rooms.

Startup principle:

- the bottom layer can keep using the existing OS, runtime, and platform
- the top layer must know window ownership, inheritance, and effective permissions
- each AI window belongs to exactly one room

Document index:

- `QUICKSTART.md`
- `_policy/roles.md`
- `_policy/room_permissions.md`
- `_policy/window_inheritance.md`
- `_policy/effective_permissions.md`
- `_policy/window_lifecycle.md`
- `_policy/conflict_resolution.md`
- `_policy/versioning.md`
- `_policy/audit_rules.md`
- `_policy/ui_mapping.md`
- `_policy/rooms.json`
- `_policy/roles.json`
- `_policy/permission_matrix.json`
- `_policy/policy_versions.json`
- `_windows/window_record.template.json`
- `_windows/window_registry.json`
- `tools/create_window.py`
- `tools/explain_permissions.py`
- `tools/build_window_packet.py`
- `tools/launch_window.py`
- `tools/validate_policy.py`
- `tools/record_action.py`
- `tools/write_room_file.py`
- `tools/control_panel.py`
- `tools/import_ammo.py`
- `tools/analyze_ammo.py`
- `tools/preflight_ammo.py`
- `tools/migrate_ammo.py`
- `tools/rebuild_ammo_index.py`
- `author_room/author_premise.md`
- `author_room/author_outline.md`

Each room has a `ROOM_PROMPT.md`.
Each role has a corresponding `_policy/agent_rules/*.md`.

Working model:

- `fiction_pipeline_v1.3` is the code tree.
- `fiction_pipeline_v1.3_test` is the execution tree for test runs and file residue.
- Keep code changes in `fiction_pipeline_v1.3`.
- Run validation in `fiction_pipeline_v1.3_test`.

First local command:

```bash
python tools/create_window.py --room ammo_bank --role "Idea Assistant"
```

One-command local launch packet:

```bash
python tools/launch_window.py --room author_room --role "Chief Author"
```

This creates a `.start.md` file under `_windows/packets/`.
Use that file as the first context for the new AI window.

Prefer launching with a task:

```bash
python tools/launch_window.py --room author_room --role "Chief Author" --task-file author_room/tasks/initial_premise.md
```

Preview without writing files:

```bash
python tools/launch_window.py --room author_room --role "Chief Author" --dry-run
```

Run tests:

```bash
python -m pytest
```

Run tests from `fiction_pipeline_v1.3_test`, not from the code tree.

The test tree is allowed to accumulate packets, registry updates, and other runtime artifacts.
