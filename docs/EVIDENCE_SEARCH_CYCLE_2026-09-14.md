# Reviewed evidence search - 14 September 2026

Branch: feniq-phase1-platform. Local only; GitHub Git authentication remains unresolved. Main untouched. Private manuals stay outside Git.

Added GET /api/jobs/{job_id}/reviewed-evidence with inspection access checks, required search words and optional reviewed-applicability text filter. Searches actual text on currently reviewed pages, retaining title, manufacturer, revision, page and document hash. Results lead into the existing explicit citation workflow. Search does not mutate diagnoses, reviews or approvals. No migration required.

The inspection UI now offers Find reviewed evidence, shows the original fault as context and pre-fills the optional applicability filter with the recorded system. All query words must occur on a page; this is literal retrieval, not semantic or engineering applicability validation. Searches stop after 100 pages or 20 results and disclose incomplete results. Pages without text are counted. No OCR, Internet search or automatic numeric-rule promotion was introduced.

Validation: all 23 tests pass, with the existing synthetic citation integration extended for successful retrieval, page/hash provenance, out-of-review page exclusion, non-matches, applicability filtering, query validation, company isolation and withdrawal. Both JavaScript syntax checks pass. The live browser form and no-reviewed-source response were tested. Positive result retrieval was API-tested with a fictional PDF; private manufacturer documents remain unapproved.

Limitations: repeated PDF extraction and byte hashing require caching/indexing before production-scale retrieval. Search has no continuation cursor beyond its page budget; applicability filtering can reduce the search scope. There is no comprehensive concurrent review-change guarantee. Reopening a result and attaching it rechecks the current review. Specialist source review, OCR, governed outcomes and production validation remain outstanding.

Next: improve bounded retrieval performance and coverage, then continue governed outcome records while preserving the immutable original diagnosis.
