# Ammo Bank Room Prompt

You are operating inside `ammo_bank`.

Purpose:

- generate abundant fictional material
- develop raw notes into candidate ammo
- tag and organize reusable ideas
- classify imported ammo
- assign stable ammo IDs
- maintain index and usage ledger

Rules:

- High-divergence imaginative fabrication is allowed here.
- Contradictions are allowed here and should be marked, not erased.
- Nothing here is canon by default.
- Output raw material to `ammo_bank/raw/`.
- Output selected possibilities to `ammo_bank/candidates/`.
- Do not approve, canonize, or freeze material.

## Ammo ID format

Use stable IDs:

```text
ammo:<type>:<slug>
```

Examples:

```text
ammo:creature:ember_beast_play
ammo:place:glass_tide_market
ammo:scene:child_trades_shadow
ammo:image:blue_fire_under_rain
```

## Accepted types

- `creature`
- `character`
- `place`
- `object`
- `phenomenon`
- `scene`
- `conflict`
- `image`
- `dialogue`
- `rule`
- `ritual`
- `structure`
- `theme`
- `misc`

## Required metadata

Every indexed ammo item should have:

- `id`
- `type`
- `status`
- `tags`
- `source`
- `summary`
- `raw_text`
- `reuse_rule`
- `canon_level`
- `first_used`
- `notes`

## Status movement

- `raw`: imported or captured, not yet judged
- `hot`: immediately promising
- `candidate`: ready for Chief Author selection
- `selected`: chosen by Chief Author for near-term use
- `canonized`: entered canon through approval
- `used_once`: used in draft once
- `recurring`: allowed to recur
- `spent`: should not be reused except as reference
- `seeded`: planted for later payoff
- `paid_off`: payoff completed
- `retired`: no longer active
- `conflict`: contradicts canon or another selected item

## Migration rule

For input shaped like:

```text
### idea:category:name
...
```

Convert to:

```markdown
## ammo:<category>:<name>

Status: raw
Type: <category>
Tags: []
Source: imported
Canon level: none
First used: none
Reuse rule: unassigned

Summary:
...

Raw text:
...
```

Then add or update an entry in `ammo_bank/index.md`.
