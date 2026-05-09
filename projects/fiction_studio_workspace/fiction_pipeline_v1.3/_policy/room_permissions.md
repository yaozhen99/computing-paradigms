# Room Permissions

Each room defines what it holds and what actions are allowed there.

## Actions

- `enter`
- `collect`
- `propose`
- `write`
- `approve`

## Room rule

Rooms are directories with policy.

The room decides:

- what material can live here
- who can read it
- who can write it
- what may leave the room

## Example

`canon_room`:

- holds durable facts, ledgers, timelines, and inherited states
- allows `Canon Keeper` and approved `Chief Author` access
- forbids raw divergence from becoming canon automatically

## Default room map

| Room | Primary purpose | Default primary role | Canon-safe |
| --- | --- | --- | --- |
| `author_room` | premise, outline, author choices, drafts | `Chief Author` | partial |
| `notebook` | raw capture | `Chief Author` | no |
| `ammo_bank` | creative ammunition | `Idea Assistant` | no |
| `asset_room` | reusable story assets | `Research Assistant` | partial |
| `canon_room` | durable facts and continuity | `Canon Keeper` | yes |
| `editorial_room` | reports and blockers | editors | yes |
| `revision_room` | author-led revision | `Chief Author` | partial |
| `publication_room` | frozen chapters | `Publisher` | yes |

## Boundary rule

Material can move from a looser room to a stricter room only through selection, approval, or an explicit change request.
