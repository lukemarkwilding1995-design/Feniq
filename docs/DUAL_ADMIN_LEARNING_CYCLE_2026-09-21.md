# Independent learning approval and aggregate threshold — 21 September 2026

Branch: `feniq-phase1-platform`. `main` and the private manufacturer library remain unchanged.

An active field-limited research record now requires two different company admins: one prepares the exact opted-in outcome revision and a different admin approves its exact preview. The approval endpoint rejects self-approval. Earlier same-admin approvals remain in immutable history, marked “Independent admin approval needed,” and are excluded from the active dataset. A later outcome revision can enter the current two-person process; retained decisions are never rewritten.

An admin can grant an active company engineer admin access with a recorded reason. The grant is tenant-scoped, audited, and notifies the recipient. The fictional demo offers Robin Clarke as a second admin for testing without granting access to a real account. Admin role grants are consequential and require deliberate use by the company admin.

`GET /api/learning/aggregate` suppresses all summary statistics until at least five current, independently approved company records exist. The admin view shows the eligibility count and threshold, and only then shows resolved, repeat-visit and diagnosis-match totals. It does not pool companies or publish data. The underlying field-limited records retain source linkage and are **not anonymous** or cleared for external sharing or model training.

No schema migration is needed. Twenty-nine automated tests pass, covering cross-company and role boundaries, self-approval rejection, independent approval, opt-out removal, and the aggregate threshold. The visible local demo contains fictional `DEMO-DUAL-01`: Alex prepared its outcome and Robin approved the field-limited preview. It counts as one internal record, while the older same-admin decision is marked ineligible and summary statistics remain suppressed below five. Neither fictional outcome nor private source files are committed. Remaining work: consent/retention policy, a formal privacy assessment, model evaluation and release governance, and production validation on PostgreSQL.
