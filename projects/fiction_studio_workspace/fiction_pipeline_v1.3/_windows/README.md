# Windows

This directory records AI window metadata.

Each AI conversation window belongs to exactly one room.

Required fields:

- window_id
- room
- role
- parent_window_id
- created_at
- source_command
- inherited_policy_versions
- effective_permissions
- status

Startup packets:

- JSON packets are machine-readable.
- Markdown packets are intended for the AI window to read directly.
- `.start.md` files are the first-message prompt for a new AI window.
