# Effective Permissions

Effective permissions are the final permissions after inheritance and overrides.

## Sources

- project policy
- room policy
- role policy
- parent window constraints
- manual override

## Default computation

`effective = project ∩ room ∩ role ∩ parent`

Manual override is allowed only when explicitly approved.

## Output

The UI must show:

- granted permissions
- denied permissions
- source of each permission
- any conflict that was resolved

## Deny rule

If any inherited policy denies an action, the action is denied unless a manual override is approved and logged.

## No silent widening

A child window cannot silently gain broader write or approve permissions than its parent.

Current implementation applies parent constraints to all actions:

- `enter`
- `collect`
- `propose`
- `write`
- `approve`

## Machine-readable sources

The first policy data files are:

- `_policy/rooms.json`
- `_policy/roles.json`
- `_policy/permission_matrix.json`
- `_policy/policy_versions.json`

## Window registry

Window records live in:

- `_windows/window_registry.json`
- `_windows/window_log.md`
- `_windows/window_record.template.json`

The launcher or UI should create a window record before starting an AI session.
