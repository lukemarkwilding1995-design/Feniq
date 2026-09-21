# Learning review history cycle - 21 September 2026

Branch: `feniq-phase1-platform`. Changes are local; `main` and private technical documents are unchanged.

Company admins can now see paginated, retained review decisions in Repair insights, including decisions whose exact outcome revision has since been corrected or whose latest outcome has withdrawn learning consent. The history shows the original revision and checksum, decision, reason, reviewer identity, timestamp, source integrity, and a current/superseded/consent-withdrawn status. It does not expose the original free-text repair in the historical list. `GET /api/learning/review-history` supports limits of 1–100 and non-negative offsets; engineers and other companies cannot access a company's history. The UI can load older decisions in batches.

The active review queue and history status checks now retrieve only the latest outcome revision per relevant job. This avoids scanning every historical revision merely to decide current eligibility. No migration was needed because the immutable `learning_reviews` table was added in revision 0009.

Validation: all 27 automated tests pass, including historical status after correction and consent withdrawal, tenant/role boundaries, pagination, and retained source integrity. JavaScript syntax passes. The local demo was visually checked with a clearly fictional, local-only inspection (`DEMO-GOVERNANCE-01`): its excluded review remains visible as “Consent withdrawn” after a correction. That fixture and the private document library are not in Git.

Limits: this is a governance history, not a de-identified dataset or training approval. A privileged database rewrite could defeat trigger/hash protections. PostgreSQL remains untested against a live server. Next: build field-level de-identification with a second explicit approval, then measure performance with larger company histories.
