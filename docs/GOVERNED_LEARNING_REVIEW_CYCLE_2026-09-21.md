# Governed learning review cycle - 21 September 2026

Branch: `feniq-phase1-platform`. Development is local; `main` and the private technical library are unchanged.

Migration `0009_learning_reviews` adds an append-only company-scoped decision for an exact outcome revision and SHA-256 checksum. Company admins can inspect the latest opted-in repair outcomes in Repair insights, then retain either “Prepare for de-identification” or “Exclude” with a reason. Engineers cannot see or decide the queue; other companies cannot see or decide its records. A corrected or opted-out outcome removes the older revision from the current queue. Review decisions remain in immutable database history and the audit log.

API: `GET /api/learning/review-queue` and `POST /api/learning/reviews`. The UI labels these as governance decisions and explicitly states that review does not anonymise data, train AI, or update diagnostic rules. The source outcome is still engineer-authored, not a verified manufacturer fact.

Validation: 27 automated tests pass, including role/tenant boundaries, hash mismatch, duplicate review, stale correction, consent withdrawal, and immutable review records. JavaScript syntax passes. The local demo database was migrated to revision 0009, and the new admin panel was inspected in the browser. No currently opted-in demo record exists, so the visible panel displays the empty state.

Limits: there is no de-identification/export pipeline or approved learning dataset yet. Decisions on superseded outcomes remain in the database and audit log but do not currently have a dedicated historical review screen. The queue scans company outcome revisions and needs indexed/latest-row query planning for production scale. PostgreSQL DDL is supplied but was not server-tested. Database triggers and hashes do not protect against privileged database rewrites.

Next: add a historical governance view and a reviewed de-identification pipeline with field-level checks and an explicit second approval before any cross-company or model use.
