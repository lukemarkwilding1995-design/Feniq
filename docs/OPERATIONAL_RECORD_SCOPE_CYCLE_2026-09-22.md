# Operational records in privacy scope — 22 September 2026

Branch: `feniq-phase1-platform`. No migration or new endpoint. The company-admin privacy inventory now counts and checksums commercial approval requests and learning-record projections associated with explicitly linked inspections and unlinked name-match leads. New requests or learning records change the inventory checksum and require another scope review before an Access draft or closure. The UI shows their counts on each inspection.

The approval and learning projection rows are not copied into the Access draft. Existing outcome revisions in that draft can contain overlapping diagnosis and repair details. The inventory exposes metadata counts/checksums without approval descriptions or learning free text. Tests cover both additions, checksum changes, and the draft boundary.

This remains a partial data map. Governance decisions, notifications, audit events and other systems still need a reviewed scope policy. Human identity checks, third-party redaction, disclosure and erasure remain separate processes. Live PostgreSQL validation is outstanding.
