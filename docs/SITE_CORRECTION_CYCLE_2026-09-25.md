# Site correction cycle — 25 September 2026

Branch: `feniq-phase1-platform`. `main` remains unchanged.

Migration `0020_site_corrections` adds a version to every Site and an append-only correction ledger. Company administrators can correct the site name and address only against the version they reviewed and with a reason. Stale and no-change submissions are rejected. Customer reassignment is explicitly outside the request model and rejected as an extra field.

Every accepted correction retains the complete previous and revised site details, administrator, timestamp, reason and SHA-256 digest. Database triggers reject update or deletion of correction history. The Product Passport catalogue shows the site version and provides an administrator correction form with its retained history.

Site records keep the same persistent identifier and customer association. Existing Product Passports therefore display the corrected site details without rewriting passport, inspection or Technical Case history. Site correction metadata is included in privacy-request inventory hashes and reviewed Access drafts.

This workflow corrects team-maintained site metadata. It does not move the site to another customer, transfer ownership, alter historical inspection evidence or validate an address against an external source. Controlled site/customer reassignment, retained inspection-link correction and wider lifecycle governance remain staged work. SQLite is covered by automated migration and workflow tests; PostgreSQL DDL awaits live-server validation.
