# Reviewed inspection citations

An authorised inspection user can attach an exact excerpt from a PDF page covered by the company's current human reference review. The server reads the actual PDF and normalises whitespace before matching; invented or paraphrased quotations and pages outside the reviewed range are rejected. Sources without extractable text need extraction/OCR work first.

Each retained citation captures title, manufacturer, revision, applicability, page, document hash, review identity, excerpt, relevance, author and time. Later source changes, withdrawal or unavailability mark it historical without erasing it. Reference approval does not establish every numerical specification as verified and does not authorise remedial work.

Adding evidence increments the inspection's approval scope and clears engineer review. Existing commercial requests cannot silently approve the changed scope. Completed visits must be reopened before evidence is added. The initial predicted diagnosis remains unchanged. Duplicate identical attachments are idempotent; citation updates/deletes are prohibited by database triggers.

Migration: 0007_citations (SQLite tested; PostgreSQL DDL supplied but not server-tested).

APIs:
- GET /api/documents/{identifier}/reviewed-pages/{page}
- GET /api/jobs/{job_id}/citations
- POST /api/jobs/{job_id}/citations

The report UI displays current/historical excerpts and a source/page selection form. PDFs include a separate citation appendix with provenance and status at report generation time. Previously downloaded PDFs are not retroactively updated. Source review withdrawal changes citation status; it does not automatically revoke a previously recorded engineer decision or commercial decision.

Limitations: no automated diagnostic retrieval or numeric-rule promotion; no OCR; no citation correction/supersession workflow; no serializable cross-request review/approval guarantees. Exact quote matching establishes provenance, not technical applicability or completeness. Per-citation byte hashing needs performance work before production scale.
