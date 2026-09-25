# Product Passport cycle — 13 September 2026

Branch: `feniq-phase1-platform`. Local development only; GitHub authentication is still needed to push. Main remains unchanged.

Implemented company-isolated sites under existing customers, persistent product identities, company passport catalogue/details, dated retained lifecycle notes and retained inspection links. Administrators register sites/products; company members can add lifecycle notes and link inspections they may access. Report listings retain the existing engineer/admin policy. A second link of the same inspection to the same product is idempotent; a link to another product is rejected.

Migration `0004_passports` adds four tables and immutability triggers for events/links. Existing customer/inspection data was not rewritten. The local database was backed up and migrated. API routes cover sites, passport create/list/detail, events and inspection links. The new Product Passports UI connects all these flows, with explicit team-supplied identity and retained-history explanations.

19 automated tests pass, including lifecycle links, date validation, cross-company isolation, admin-only registration, assigned-engineer report visibility, duplicate-link handling and retained-history SQL protection. JavaScript syntax passes. The visible browser flow created a fictional Willow House site/product, linked its existing inspection and recorded a service note.

The later `0018_passport_corrections` cycle adds administrator-controlled product identity and site correction with optimistic versions, immutable old/new snapshots, reasons, actors, timestamps and integrity hashes. Relocation is rejected if the new site's customer conflicts with a linked inspection or work order. See `PASSPORT_CORRECTION_CYCLE_2026-09-25.md`.

Limitations: no site metadata correction, passport archive, link correction, attached files, QR/export, external transfer or verified manufacturer identity. Lifecycle notes do not establish warranty entitlement or certify work. PostgreSQL remains untested against a live server. Full company policy/production governance remains staged work.

Next: Technical Cases linked to passports and jobs, preserving existing review/approval gates. See PRODUCT_PASSPORTS.md for the current access model and scope.
