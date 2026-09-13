# Foundation cycle — 13 September 2026

Development branch: `feniq-phase1-platform`. Changes are local; GitHub authentication is still required to push. The encompassing commit records this cycle. `main` was not modified.

## Implemented

Versioned baseline and snapshot migrations replace implicit `create_all` startup. Original saved diagnostic snapshots preserve fault, evidence, typed checks, units, engineer identity, server result and rule fingerprint. Database triggers reject snapshot updates/deletes. New learning feedback compares against the original snapshot, while existing feedback predictions remain unchanged. Legacy records are explicitly distinguished from original server diagnoses.

API: company/assigned-engineer/admin-protected `GET /api/jobs/{job_id}/diagnostic-snapshot`. No mutation endpoint. UI: expandable original-diagnosis panel within the existing inspection report, with readable findings and integrity/provenance information. Current service reports remain editable.

Migrations: `0001_baseline` and `0002_snapshots`. The local demo database was backed up outside Git and upgraded without losing its four pre-existing inspections. A fifth fictional inspection was created through the browser to verify capture and display. Private documents and media remain outside Git.

## Validation and limits

14 automated tests pass, covering migrations on fresh/legacy databases, repeat upgrades, rollback on schema mismatch, changed migration checksums, snapshot persistence through edits/feedback, SQL update/delete rejection, cross-company and same-company engineer access, and the prior demo workflows. JavaScript syntax passes. The browser inspection → checks → diagnosis → save → snapshot panel flow was verified visibly.

SQLite is validated. PostgreSQL DDL/trigger definitions are included but not integration-tested on a server. Baseline adoption validates column names, not every legacy type/constraint. Database owners can bypass ordinary triggers; hashes are not digital signatures. Unsaved diagnostic runs, later diagnostic revisions, immutable photo/outcome events and production governance remain work. No production-readiness claim is made.

Next: complete the existing tenant/permission and transition-gate audit, then introduce shared Site/Product identity and Product Passports through additive migrations. See the master plan and `MIGRATIONS_AND_SNAPSHOTS.md` for scope and recovery instructions.
