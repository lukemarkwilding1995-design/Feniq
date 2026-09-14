# Controlled private-source review

Migration `0006_source_reviews` adds company-scoped, append-only review history for private PDFs. Imports remain pending. Only a company administrator can record a decision; other company users can read the history for documents their company may access.

Each review captures the exact SHA-256, reviewer, title, manufacturer/publisher, stated revision, declared product/system applicability, reviewed PDF page range, rationale and time. Approval requires an explicit personal-review acknowledgement. The importer-provided hash is checked against the original file bytes before a decision is saved. A stale review form is rejected rather than silently replacing another review.

Decisions are Approved for reference, Rejected or Withdrawn. Later decisions do not erase earlier reviews. Changed source bytes or changed manifest hash invalidate reference approval. Approved entries are rechecked against local bytes when the catalogue is requested. This is currently a simple correctness-first implementation; caching and indexing are needed before large-scale production use.

Use **Knowledge library → Source review**. Read the original first, then reopen the form to record the reviewed revision, applicability and page range. Printed page labels can differ from PDF page numbers. Do not infer a revision or specification from a filename. If the source does not state a revision, explicitly record that finding in the revision field and review rationale.

Approved for reference is a company workflow decision, not proof that all technical values are verified or that every product variant is covered. No numeric diagnostic rules are changed, and no remedial work is authorised. Document metadata still comes from the import; the review retains separately checked metadata. Approval applies only to the reviewed range and declared applicability.

Current limitations: PDF sources only, generic administrator role rather than specialist reviewer permissions, no page-citation attachment to inspections, no reviewed specification extraction or automatic diagnosis retrieval, no external source verification, and no OCR. A future citation workflow must bind exact excerpts/pages to a current review and preserve historical provenance. PostgreSQL migration SQL remains untested on a running server.

No supplied manufacturer PDF was approved by the coding agent. Tests use a synthetic PDF explicitly labelled fictional. Private files, extracted text and review data stay in the local library/database, outside Git.
