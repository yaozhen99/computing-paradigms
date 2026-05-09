# Ammo Migration Spec

Purpose:

Convert existing raw ammo into v1.3 indexed ammo.

## Source format

Expected source heading:

```text
### idea:category:name
```

Example:

```text
### idea:creature:ember_beast_play
The ember beast plays with burned bones like toys.
```

## Target ID

```text
ammo:<category>:<name>
```

Example:

```text
ammo:creature:ember_beast_play
```

## Initial status

Imported items start as `raw`.

The `Ammo Librarian` may later propose:

- `hot`
- `candidate`
- `conflict`
- `retired`

Only Chief Author selection or approved canon process can move material to:

- `selected`
- `canonized`
- `used_once`
- `recurring`
- `spent`
- `seeded`
- `paid_off`

## Required output locations

- raw imported item file: `ammo_bank/raw/<ammo_id>.md`
- index update: `ammo_bank/index.md`
- usage tracking later: `ammo_bank/usage_ledger.md`
- batch logs: `ammo_bank/migration_logs/`
  - `import_*.json` for each `import_ammo.py` attempt, including dry runs and rejected attempts
  - `migration_*.json` and `migration_*.md` for each orchestrated `migrate_ammo.py` run

## Safety options

Run a dry run first:

```bash
python tools/import_ammo.py --source path/to/temp_ammo.md --dry-run
```

For stricter source checking before dry run:

```bash
python tools/preflight_ammo.py --source path/to/temp_ammo.md --markdown-output ammo_bank/preflight_report.md
```

Or run the orchestrated migration:

```bash
python tools/migrate_ammo.py --source path/to/temp_ammo.md
```

If `ammo_bank/index.md` drifts, rebuild it from raw ammo files:

```bash
python tools/rebuild_ammo_index.py
```

If files already exist, choose one:

- `--overwrite`
- `--skip-existing`

Duplicate IDs in the same source are rejected unless `--allow-duplicate-ids` is passed.

IDs that already exist in another raw ammo file are rejected unless `--allow-existing-ids` is passed.
Use that override only after reviewing the existing file paths in the preflight report.
