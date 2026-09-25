# Report access audit cycle — 25 September 2026

FenIQ now records every authenticated download of a generated current report or an exact retained PDF revision. Each company-scoped audit event identifies the user and time, distinguishes current from retained output, records the retained revision when applicable and binds the event to the downloaded PDF SHA-256. Report responses are private and no-store; their ETag matches that checksum.

Assigned engineers and company administrators can review the latest 250 report-download events from the inspection screen. Access to both the PDF and its history reuses the inspection's tenant and assignment policy. The history refreshes immediately after a download and does not expose another company's activity.

This cycle uses the existing audit-event store and requires no schema migration. All 37 automated tests pass, including exact-byte verification, actor attribution, current-report checksum matching and cross-company denial. Application audit records provide operational accountability; they are not digitally signed, and a privileged database owner could alter them. Controlled external delivery, retention policy and production object storage remain future work.
