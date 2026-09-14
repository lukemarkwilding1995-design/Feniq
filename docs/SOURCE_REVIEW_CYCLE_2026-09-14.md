# Controlled source review cycle — 14 September 2026

Branch: `feniq-phase1-platform`. Changes remain local; GitHub authentication is outstanding. Main is unchanged.

Implemented company-scoped, append-only source review history tied to exact PDF bytes, reviewer, checked title/publisher/revision, applicability, page range and rationale. Human administrator approval requires explicit acknowledgement. Stale submissions conflict; later reviews retain earlier history. Changed bytes invalidate reference approval. Catalogue cards show current status and open the review/history form.

Migration: `0006_source_reviews`. The private demo database was backed up and upgraded. APIs: document review GET/POST and enriched existing document catalogue. UI: source status cards, administrator decision form, readable review history and original-PDF access. No manufacturer document was approved during development.

22 tests pass, including synthetic-source approval, administrator access, acknowledgement requirement, stale-review conflict, changed-byte invalidation, withdrawal, company isolation and SQL history protection. Prior workflow/migration tests remain passing; JavaScript syntax passes. The supplied-manual form was checked visibly and left pending without a submitted decision.

Remaining work: attaching reviewed page citations to inspections, controlled diagnostic retrieval, specialist reviewer permissions, review metadata search, OCR and PostgreSQL server validation. Current reference approval does not verify all specifications or change numerical rules. Per-document review lookup and byte checks need optimisation before a large production catalogue.

Next: reviewed page citations with preserved source/revision/hash/page provenance and clear handling of withdrawn reviews.
