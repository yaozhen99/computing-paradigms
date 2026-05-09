# UI Mapping

The visual layer must expose the structure below.

## Views

- room tree
- window tree
- inheritance chain
- effective permission matrix
- audit trail
- version history
- room flow map
- active window list
- policy diff view

## UI rule

When the user opens a window from a room, the UI must show:

- which room owns it
- which role it uses
- which parent it inherits from
- what permissions it actually has

## Command mapping

When a command is issued inside a room, the created AI window inherits that room as its owner.

Example:

`ammo_bank -> new window`

- room: `ammo_bank`
- default role: `Idea Assistant`
- default writes: `ammo_bank/raw`, `ammo_bank/candidates`
- default denies: `canon_room`, `publication_room`

