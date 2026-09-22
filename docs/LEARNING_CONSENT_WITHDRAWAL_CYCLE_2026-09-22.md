# Learning consent withdrawal — 22 September 2026

Branch: `feniq-phase1-platform`. No change to `main`, no private technical files in Git, and no schema migration.

An assigned engineer or company admin can now withdraw the latest opted-in repair outcome from local learning consideration directly from its inspection report. The action requires a reason plus the displayed revision version and SHA-256 hash. A stale, damaged, already-withdrawn, unowned or cross-company outcome is rejected. The app appends a new outcome revision with consent off, updates the current feedback projection, and audits the action; it never rewrites the original repair evidence.

Current research candidates and internal dataset membership derive from the latest outcome revision. Withdrawal therefore removes a prepared or approved record immediately, while prior review and approval decisions remain visible with a “Consent withdrawn” status. The UI shows the current consent state and withdrawal reason on the report. Withdrawal does not erase the retained service record or claim to recall data that may have been shared elsewhere; this demo has no external research export.

API: `POST /api/jobs/{job_id}/learning/withdraw-consent` with `expected_version`, `expected_sha256`, and `reason`. The existing outcome, review-history, dataset-history, and aggregate endpoints reflect the new latest revision. All 29 automated tests pass, including ownership, stale-hash rejection, retained history and immediate dataset removal; JavaScript syntax and formatting pass. In the visible local demo, fictional `DEMO-DUAL-01` moved from one eligible record to zero after withdrawal, while its original outcome and both retained decisions remained visible with “Consent withdrawn” status. Demo database changes remain outside Git.

Remaining governance work includes a published retention schedule, request handling for deletion or access where legally appropriate, privacy assessment, and production database validation. Retained history is intentionally preserved for service audit; any future erasure workflow needs its own legal and technical design.
