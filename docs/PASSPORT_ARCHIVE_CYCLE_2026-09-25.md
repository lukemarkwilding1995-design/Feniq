# Product Passport archive cycle — 25 September 2026

Branch: `feniq-phase1-platform`. `main` remains unchanged.

Migration `0019_passport_archive` adds an archived timestamp and an append-only Product Passport state ledger. Company administrators can archive or restore a passport only against the current passport version and with a reason. Every accepted transition advances the version and retains the previous state, new state, actor, timestamp, reason and SHA-256 digest. Database triggers reject changes or deletion of state history.

Archived passports remain readable with identity corrections, lifecycle events, linked inspections and repeat-failure information. They are omitted from the normal engineer catalogue and technical-case selector. FenIQ rejects new identity corrections, lifecycle notes, inspection links and technical cases until an administrator restores the passport. The company administrator catalogue includes archived records so restoration remains possible.

Passport state and immutable state-event metadata are included in the company privacy-request inventory. The reviewed Access draft contains the relevant archive/restore payloads alongside the passport record.

Archive is an operational state, not deletion, ownership transfer, warranty determination or evidence removal. Existing Technical Cases and linked inspections remain intact. Site correction, retained inspection-link correction, attachments, QR/export and external transfer remain staged work. SQLite is covered by automated migration and workflow tests; PostgreSQL DDL awaits live-server validation.
