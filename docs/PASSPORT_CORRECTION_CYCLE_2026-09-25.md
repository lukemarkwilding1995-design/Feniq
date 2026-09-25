# Product Passport correction cycle — 25 September 2026

Branch: `feniq-phase1-platform`. `main` remains unchanged.

Migration `0018_passport_corrections` adds a version to every Product Passport and an append-only correction ledger. Company administrators can correct the product label, type, manufacturer, system, serial number or site. Every submission is bound to the identity version the administrator reviewed and must give a reason. Stale submissions and submissions that change nothing are rejected.

An accepted correction records the complete previous and revised identity, actor, timestamp, reason and SHA-256 digest before advancing the current passport. Database triggers reject updates and deletes to correction history. The detail screen shows changed fields and the integrity result. A generic lifecycle correction note also makes the change visible in the chronological record.

Site changes preserve customer boundaries. FenIQ examines all linked inspections and linked work orders before accepting the new site. A conflicting customer blocks the correction and leaves the passport unchanged. Tenant ownership and administrator role checks apply before any mutation.

This is controlled internal product identification. It does not verify manufacturer identity or specifications, transfer product ownership, decide warranty coverage, or alter historical inspection evidence. Site metadata correction, archive/link correction, attachments, QR/export and external transfer remain staged work. SQLite is covered by the automated workflow and migration tests; PostgreSQL DDL is supplied for later live-server validation.
