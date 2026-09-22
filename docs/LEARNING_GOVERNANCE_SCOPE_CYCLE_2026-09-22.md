# Learning governance decisions in privacy scope — 22 September 2026

Branch: `feniq-phase1-platform`. No migration or new endpoint. The company-admin privacy inventory now counts and checksums retained first-stage learning reviews and second-stage dataset decisions for explicitly linked inspections and unlinked name-match leads. These append-only decisions remain visible in their own governance histories, including after outcome corrections or consent withdrawal. A new decision changes the inventory checksum and requires another customer-request scope review.

The privacy inventory exposes counts and metadata checksums, not decision reasons or prepared payloads. The internal Access draft excludes those decision rows; existing outcome revisions can still contain overlapping repair details and need manual review. Tests cover both decision stages, checksum changes and draft exclusion of decision reasons.

This is a partial customer data map. It does not decide whether a research governance record is disclosable, automatically export or erase it, or authorise external research or model training. Live PostgreSQL validation remains outstanding.
