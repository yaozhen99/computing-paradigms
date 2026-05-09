# Tools

## create_window.py

Creates a room-owned AI window record.

Example:

```bash
python tools/create_window.py --room ammo_bank --role "Idea Assistant"
```

The tool writes:

- `_windows/window_registry.json`
- `_windows/window_log.md`

## explain_permissions.py

Explains why a role has its permissions in a room.

Example:

```bash
python tools/explain_permissions.py --room ammo_bank --role "Idea Assistant"
```

## build_window_packet.py

Builds a startup packet for an existing window.

Example:

```bash
python tools/build_window_packet.py --window-id win_example
```

Markdown output:

```bash
python tools/build_window_packet.py --window-id win_example --markdown-output _windows/packets/win_example.md
```

## launch_window.py

Creates a window record and builds both JSON and Markdown startup packets.

Example:

```bash
python tools/launch_window.py --room author_room --role "Chief Author"
```

With an inline task:

```bash
python tools/launch_window.py --room author_room --role "Chief Author" --task "Draft the initial author premise."
```

With a task file:

```bash
python tools/launch_window.py --room author_room --role "Chief Author" --task-file author_room/tasks/initial_premise.md
```

Preview without writing files:

```bash
python tools/launch_window.py --room author_room --role "Chief Author" --dry-run
```

The command creates:

- `_windows/packets/<window_id>.json`
- `_windows/packets/<window_id>.md`
- `_windows/packets/<window_id>.start.md`

Use the `.start.md` file as the first message/context for the AI window.

## validate_policy.py

Checks policy consistency.

Example:

```bash
python tools/validate_policy.py
```

## record_action.py

Records an audited action for a window.

Example:

```bash
python tools/record_action.py --window-id win_example --action write --target author_room/author_premise.md --result "Updated premise draft."
```

## write_room_file.py

Writes a file only if the window has permission for the target room.

Example:

```bash
python tools/write_room_file.py --window-id win_example --target author_room/author_premise.md --content "Draft text" --overwrite
```

## control_panel.py

Renders a read-only summary of rooms, windows, and parent chains.

Example:

```bash
python tools/control_panel.py --room author_room
```

## import_ammo.py

Imports raw ammo with headings shaped like `### idea:category:name`.

Example:

```bash
python tools/import_ammo.py --source path/to/temp_ammo.md
```

Dry run:

```bash
python tools/import_ammo.py --source path/to/temp_ammo.md --dry-run
```

Skip existing targets:

```bash
python tools/import_ammo.py --source path/to/temp_ammo.md --skip-existing
```

By default, imports reject duplicate IDs inside the source and IDs that already exist in another raw ammo file.
Use `--allow-duplicate-ids` or `--allow-existing-ids` only after reviewing the conflict.

## preflight_ammo.py

Checks a migration source without writing imported ammo.

Example:

```bash
python tools/preflight_ammo.py --source path/to/temp_ammo.md --markdown-output ammo_bank/preflight_report.md
```

## migrate_ammo.py

Runs the full migration workflow:

1. preflight
2. dry run
3. import
4. librarian analysis
5. batch report

Example:

```bash
python tools/migrate_ammo.py --source path/to/temp_ammo.md
```

The command writes a batch report under `ammo_bank/migration_logs/migration_*.json` and `.md`.

Stop after preflight:

```bash
python tools/migrate_ammo.py --source path/to/temp_ammo.md --preflight-only
```

## analyze_ammo.py

Generates an Ammo Librarian report from `ammo_bank/raw/ammo__*.md`.

Example:

```bash
python tools/analyze_ammo.py
```

## rebuild_ammo_index.py

Rebuilds `ammo_bank/index.md` from `ammo_bank/raw/ammo__*.md`.

Example:

```bash
python tools/rebuild_ammo_index.py
```
