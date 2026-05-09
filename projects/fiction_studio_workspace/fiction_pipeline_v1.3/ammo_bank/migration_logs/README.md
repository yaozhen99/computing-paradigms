# Ammo Migration Logs

This directory is the audit trail for ammo migration.

Log types:

- `import_*.json`: one log per `import_ammo.py` attempt, including dry runs and rejected attempts
- `migration_*.json`: structured batch report from `migrate_ammo.py`
- `migration_*.md`: human-readable batch report from `migrate_ammo.py`

Use `--dry-run` or `--preflight-only` before importing large batches.

Historical logs may remain here. Do not delete them as part of normal tool tests.
