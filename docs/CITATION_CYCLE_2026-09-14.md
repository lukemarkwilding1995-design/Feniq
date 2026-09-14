# Reviewed citation cycle - 14 September 2026

Branch: feniq-phase1-platform. Local development only; GitHub authentication remains outstanding. Main is unchanged.

Implemented exact-page reviewed excerpts on inspections with retained source/revision/hash/page provenance, current/historical status, duplicate handling and engineer review reset. Citation changes invalidate the prior commercial request scope. The PDF adds a source appendix. No supplied manufacturer document was approved or published.

Migration 0007_citations adds retained citations and inspection citation versions. The private demo database was backed up before upgrade. Three citation endpoints and report UI are described in REVIEWED_CITATIONS.md.

Validation: 23 automated tests pass. The synthetic-PDF integration checks unreviewed and out-of-range rejection, invented quote rejection, duplicate attachment, fresh engineer review, stale commercial request rejection, withdrawn source history, PDF content and database delete protection. JavaScript syntax checks pass. Both rendered report pages were visually inspected. The live demo visibly displayed the citation panel and correctly blocked attachment when no source has human reference approval. The successful attachment path was tested through the API using a fictional PDF, not through the live browser.

Next: controlled diagnostic evidence retrieval using reviewed applicability and source provenance. Remaining gaps include human review of private sources, OCR, source correction/supersession workflows, concurrency hardening and PostgreSQL validation. The wider Wave 1 and Module 41+ programme remains staged, not complete.
