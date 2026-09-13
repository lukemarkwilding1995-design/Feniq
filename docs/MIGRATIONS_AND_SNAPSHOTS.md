# Migrations and original diagnostic snapshots

## Running migrations

Stop application writers, back up the database, and use the same `DATABASE_URL` as the application:

```sh
python scripts/migrate.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The localhost demo launcher runs pending migrations before starting. Back up existing demo data before upgrading. Normal application startup checks the revision and refuses an unmigrated or mismatched database; it no longer silently runs `create_all`.

- `0001_baseline`: frozen original schema. Creates fresh tables or adopts legacy tables after checking their column names. Does not reconstruct or overwrite existing records. Full legacy constraint/type reconciliation remains a production prerequisite.
- `0002_snapshots`: adds `diagnostic_snapshots`, company/job indexes and database triggers rejecting UPDATE and DELETE. No existing inspection fields are altered.

The migration ledger records canonical DDL checksums, independent of JSON whitespace/line endings. SQLite uses an immediate transaction; PostgreSQL uses an advisory transaction lock. Run one migration process per deployment with application writers stopped. Newer databases, changed applied migration content and unexpected legacy columns cause a failure. Migrations are forward-only: recovery is by restoring the pre-upgrade backup, not deleting snapshot history. Never edit an applied migration to implement a later feature.

SQLite has automated fresh/legacy/repeat/failure tests and was used for the local demo upgrade. PostgreSQL DDL is supplied but has not been integration-tested against a PostgreSQL server; production deployment is not approved by this cycle.

## Snapshot contract

The first saved inspection captures its server-recomputed result, original fault, product/system labels, evidence, typed answers, check definitions/units, engineer identity and rule-file SHA-256. Capture is in the same transaction as the job. Unsaved diagnostic previews are not persisted. Later edits leave the original snapshot unchanged.

`GET /api/jobs/{job_id}/diagnostic-snapshot` follows the same company and assigned-engineer/admin access policy as the inspection. There is no snapshot edit/delete API. Its JSON integrity fingerprint detects content mismatch; database triggers reject normal SQL updates/deletes. This is not a digital signature or protection against a privileged database owner who can remove triggers or rewrite storage.

Reports show the original finding, human-readable checks and provenance separately from the current editable service record. New repair feedback uses this original prediction for comparison. Existing feedback predictions are retained, not rewritten. Legacy inspections without a snapshot return no snapshot until their first subsequent edit/feedback; that capture is explicitly labelled `legacy_capture` and never presented as the historical original execution. Engineer-entered records are labelled separately from server diagnoses. No absent measurements are invented.

Still needed: diagnostic-run revision history, unsaved/durable drafts, immutable photo/review/outcome event references, richer source provenance, production retention controls and a full tenant-policy audit. Snapshot immutability does not authorise any remedial or chargeable action.
