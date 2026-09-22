# Customer request register — 22 September 2026

Branch: `feniq-phase1-platform`. `main` and the private technical library remain unchanged.

Migration `0011_privacy_requests` adds a company-scoped request register linked to an existing customer and an immutable event history. Company admins can record an access, correction or deletion request, advance it through Open → Investigating → Awaiting Decision or Closed, and retain a decision note when closing. Closed requests can be reopened for further investigation; the earlier decision remains in event history. Optimistic version checks reject stale updates. Engineers and other companies cannot view or change the register.

The Company workspace now has an admin-only Privacy requests page. The page supports intake, status review and event history, and explicitly states that recording or closing a request does not automatically disclose, correct or delete data. It is an operational register, not a legal decision engine or an erasure mechanism. No deadline or legal outcome is inferred by FenIQ.

API: `GET/POST /api/privacy-requests`, `GET/PATCH /api/privacy-requests/{id}`. Status changes are audited. This work uses a separate register because Technical Cases require an inspection or Product Passport, while a customer request can arrive before either exists. No customer or inspection record is deleted by this migration or workflow.

The local demo database was backed up before migration. A fictional Willow House access request was entered and moved to Investigating through the visible browser. All 30 automated tests pass, including migration, company isolation, admin role, stale version, workflow transitions, retained decision and event immutability. JavaScript syntax and formatting pass. PostgreSQL DDL is provided but remains untested against a running server. Further work includes an organisation-specific retention schedule, verified identity/intake procedure, controlled fulfilment, and production review.
