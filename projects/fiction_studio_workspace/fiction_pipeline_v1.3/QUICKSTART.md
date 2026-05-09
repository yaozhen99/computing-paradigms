# Quickstart

## 1. Launch a room-owned AI window packet

```bash
python tools/launch_window.py --room author_room --role "Chief Author"
```

For a useful first author task:

```bash
python tools/launch_window.py --room author_room --role "Chief Author" --task-file author_room/tasks/initial_premise.md
```

Preview the packet without writing files:

```bash
python tools/launch_window.py --room author_room --role "Chief Author" --dry-run
```

This creates:

- `_windows/packets/<window_id>.json`
- `_windows/packets/<window_id>.md`
- `_windows/packets/<window_id>.start.md`

## 2. Start the AI window

Use the generated `.start.md` file as the first context for the new AI window.

The AI must read the startup packet and then read every file listed under `Must Read`.

## 3. Keep work room-scoped

The AI window belongs to one room.

It must follow:

- its role rule
- its room prompt
- its effective permissions
- its denied permissions

## Test

```bash
python -m pytest
```

Run that from `fiction_pipeline_v1.3_test`.
