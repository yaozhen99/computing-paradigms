# Window Inheritance

Every AI window must know its lineage.

## Inheritance chain

`project root -> room -> role -> parent window -> current window`

## Required metadata

- `window_id`
- `room`
- `role`
- `parent_window_id`
- `source_command`
- `created_at`
- `effective_permissions`

## Rule

The UI must be able to explain why a window has its permissions.

## Room ownership

Each window belongs to exactly one room.

The room determines:

- default role candidates
- default readable material
- default writable paths
- output location
- audit log target

## Parent constraint rule

When a child window is created with `parent_window_id`, its effective permissions are constrained by the parent.

Default rule:

`child effective permissions = child role-room permissions ∩ parent effective permissions`

This prevents child windows from silently gaining broader access than the parent.
