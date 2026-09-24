# Customer acceptance cycle — 24 September 2026

Migration `0015_customer_acceptance` adds append-only customer acceptance revisions to saved inspections. An assigned engineer or company administrator can record Accepted, Declined or Customer unavailable only after engineer review. Named decisions require an explicit attestation that the customer reviewed the report and made the decision.

Every revision is bound to a server-derived SHA-256 of the report fields, photo evidence metadata, legacy sign-off data, engineer-review state, citation version and latest retained repair outcome. The acceptance decision and report fingerprint are hashed together. Later report changes leave the acceptance intact but mark it historical. Corrections append a new version and require a reason. Database triggers reject updates and deletes.

The inspection screen and PDF show the latest retained revision, timestamp, integrity status and current/historical report relationship. This is an engineer-witnessed acceptance record, not a cryptographic customer signature, identity service, payment authorisation or permission for parts, remakes or chargeable work. Existing `signature` text remains visible as a legacy field but new workflows no longer collect it.
