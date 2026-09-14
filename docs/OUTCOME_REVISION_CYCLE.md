# Retained repair outcome revisions

Branch: feniq-phase1-platform. Local development; main untouched. Private sources remain outside Git.

Migration 0008_outcomes adds immutable outcome revisions with job/company identity, submitting user, timestamp, version, payload and integrity hash. Existing feedback is preserved as a labelled legacy capture before its next correction; no historical author or verification is invented. The existing learning record remains the latest-value projection used by current metrics, so corrections do not increase sample counts.

POST /api/jobs/{id}/learning now requires final check notes for resolved outcomes, an expected revision and correction reason after the first retained submission. It retains the original diagnostic snapshot reference/hash, predicted result, actual repair, verification notes and current parts text. Concurrent stale saves conflict. GET /api/jobs/{id}/outcome-history returns authorised retained history with hash verification. Saves produce audit events. Learning consent defaults false and is not claimed to complete anonymisation or enable automatic training.

The existing outcome form now includes final checks, correction reason and readable retained history. The demo database was backed up before migration. Twenty-five tests pass, covering correction retention, stale saves, verification requirements, original snapshot linkage, isolation and delete protection. JavaScript syntax passes. A fictional unresolved outcome was saved visibly, then its retained revision verified after browser refresh. A navigation click immediately after saving did not switch views during browser testing; refresh recovered the view. This requires follow-up if reproducible.

Limits: final checks are engineer-authored text, not structured physical test validation. This does not complete governed dataset approval, anonymisation, learning promotion, automatic completed-job outcome creation, evidence/photo snapshots, outcome inclusion in PDFs, or Product Passport repeat-failure analytics. Outcome feedback does not automatically change the inspection's operational outcome or authorise chargeable work. PostgreSQL DDL supplied but not server-tested. Hash plus database triggers does not protect against privileged database rewrites.

Next: integrate retained outcomes into reports and product lifecycle views, with structured verification and governed review before any learning use.
