# FenIQ V11 — Production Launch Candidate

FenIQ is a fenestration diagnostic, repair and reporting platform.

## V5 adds
- Company registration and onboarding
- Company invite codes for engineers
- JWT access tokens with expiry
- PBKDF2 password hashing
- Engineer/admin role separation
- PostgreSQL support
- SQLite fallback for simple local development
- Persistent jobs and photo evidence
- Company-scoped data isolation
- Engineer approval flag before expensive/remake decisions
- Real AI vision integration path using the OpenAI Responses API
- Server-generated PDF service reports
- Dockerfile + Docker Compose deployment
- Analytics and company user listing

## Start with Docker

1. Install Docker Desktop.
2. Copy `.env.example` to `.env`.
3. Change `SECRET_KEY` and the database password values before using real data.
4. From this folder run:

    docker compose up --build

5. Open:

    http://localhost:8000

There are no default accounts in V5. Use **Create Company** on the login screen. The first user becomes the company admin. Engineers join using the company's invite code.

## Real AI photo analysis

FenIQ can run without AI. To enable live photo analysis, set both in `.env`:

    OPENAI_API_KEY=your_key
    OPENAI_VISION_MODEL=your_vision_capable_model

The backend sends the selected inspection image to the OpenAI Responses API and asks for:
- factual visual observations
- possible faults
- recommended physical/measurement checks
- limitations

The prompt explicitly prevents the AI from authorising remakes, replacement sashes, chargeable parts or warranty decisions. Those remain engineer decisions.

## Development without Docker

Use SQLite in `.env`:

    DATABASE_URL=sqlite:///./feniq.db
    SECRET_KEY=change-me

Then:

    python -m venv .venv
    # Windows:
    .venv\Scripts\activate
    # macOS/Linux:
    source .venv/bin/activate

    pip install -r requirements.txt
    uvicorn app.main:app --reload

## Important before real customer data / public launch

V5 is a production-style beta codebase, not a security-certified production service. Before commercial launch you should add:
- HTTPS/TLS through a production host or reverse proxy
- password reset + email verification
- refresh-token/revocation strategy
- rate limiting and brute-force protection
- database migrations (Alembic)
- encrypted backups
- S3-compatible/cloud object storage rather than local upload volume
- malware/content scanning for uploads
- audit logs
- retention/deletion policies
- UK GDPR privacy notice, DPA/subprocessor review and data retention controls
- monitoring/error reporting
- automated tests and CI/CD
- billing/subscription system
- formal manufacturer-approved diagnostic content and versioning

## Suggested first private beta

Use one company, 3–10 engineers and 50–100 real service jobs. Compare:
1. FenIQ diagnosis vs engineer conclusion
2. predicted corrective action vs actual repair
3. first-visit fix rate
4. report-writing time
5. repeat-call rate
6. remake/parts accuracy

That produces the first proprietary FenIQ evidence dataset without allowing AI to make uncontrolled commercial decisions.


## V6 Technical Intelligence Engine

V6 adds a server-side diagnostic engine rather than relying on browser-only rules.

New API endpoints:

- `GET /api/diagnostics/catalogue`
- `POST /api/diagnostics/run`

Initial structured modules:
1. French Door Sash Clearance & Alignment
2. Locking Camb & Keep Diagnosis
3. Toe & Heel / Glazing Support
4. Multipoint Lock / Gearbox
5. Gasket, Draught & Compression
6. Friction Stay / Window Hinge
7. Bifold Panel Alignment
8. Sliding Door Alignment

Each module contains:
- required physical checks
- typed measurements/answers
- rule IDs
- weighted evidence
- diagnosis thresholds
- corrective actions
- repair sequence
- commercial/remake approval gate
- fallback path when evidence is insufficient

### Important technical-data rule

FenIQ V6 deliberately distinguishes **FenIQ working diagnostic rules** from verified manufacturer specifications. For example, the 6 mm meeting sightline used in the French-door module is labelled as a FenIQ working rule rather than a universal manufacturer tolerance.

Before manufacturer-specific values are promoted to specifications, add the relevant approved technical document, revision/version, product/system, and source reference.

### Example diagnostic API request

POST `/api/diagnostics/run`

```json
{
  "module_id": "french_door_clearance",
  "answers": {
    "top_clearance": 1,
    "bottom_clearance": 0,
    "meeting_sightline": 2,
    "hinge_limit": true,
    "frame_geometry": "Yes",
    "threshold_type": "Low aluminium",
    "sash_dimensions_verified": true
  }
}
```

This returns the matched evidence/rules, confidence, recommended action, repair steps and whether engineer approval is required.


## V7 Manufacturer Intelligence Layer

V7 adds product/system routing above the V6 diagnostic engine.

Initial manufacturer/system catalogue:
- Residence Collection — Residence French Door, Residence Window
- AluK — S67 Sliding Door, 58BW Window, 58BD Door
- Cotswold — friction-stay / egress-easy-clean hardware routing
- Avantis — window locking / keep routing

These entries currently have `pending_verification` status. That is intentional: FenIQ can route an engineer to the correct diagnostic workflow without presenting unverified product-specific tolerances as official specifications.

New API endpoints:
- `GET /api/manufacturers`
- `GET /api/manufacturer-systems?manufacturer_id=...`
- `POST /api/manufacturer-route`

The router uses the selected manufacturer/system plus symptom wording to suggest the most relevant V6 diagnostic module.

### Controlled source registry

`CONTROLLED_TECHNICAL_SOURCES.json` is the starting registry for approved technical documentation. Manufacturer-specific numerical limits should only be promoted to `verified` after a document title, revision, date and source reference are recorded.

### Next data milestone

Add approved manuals, adjustment sheets and technical bulletins to build:
manufacturer -> system -> component -> symptom -> verified test/specification -> corrective procedure -> source/version.

That will let FenIQ show an engineer both:
1. FenIQ field diagnosis; and
2. the exact verified manufacturer procedure/specification supporting the repair.


## V8 Connected Knowledge Library

V8 connects repair guidance directly to the diagnostic engine.

Initial field guides:
- Locking Camb Adjustment
- Toe & Heel Glazing Adjustment
- Friction Stay / Window Hinge Inspection & Adjustment
- French Door Sash Clearance Investigation
- Gasket & Compression Inspection
- Multipoint Lock / Gearbox Investigation
- Aluminium Sliding Door Alignment & Operation
- Bifold Alignment & Locking Sequence

New API endpoints:
- `GET /api/guides`
- `GET /api/guides/search?q=...`
- `GET /api/guides/{guide_id}`
- `GET /api/diagnostics/{module_id}/guides?system=...`

The library ranks system-specific guides first when a system is known.

All initial guides are marked as **FenIQ field guides**. Manufacturer-specific limits and instructions remain pending controlled-source verification until approved technical documentation is loaded into the controlled source registry.

The intended V8 workflow is now:

**Product/System → Symptom → Diagnostic Checks → Diagnosis → Relevant Technical Guide → Repair → Engineer Approval → Report**

This is the foundation for adding the polished illustrated guides already used by the engineering team. Their PDFs/images can later be attached to the corresponding guide records rather than mixing visual assets into the diagnostic rules themselves.


## V9 Engineer Learning Engine

V9 closes the diagnostic feedback loop.

For every completed job, the engineer can now record:
- FenIQ's original predicted diagnosis and confidence (preserved automatically)
- engineer-confirmed diagnosis
- actual repair carried out
- whether the repair resolved the fault
- whether a repeat visit is required
- whether an ordered part/remake was correct
- 1–5 usefulness rating
- engineer feedback
- whether the record may be used in anonymised learning

New API endpoints:
- `POST /api/jobs/{job_id}/learning`
- `GET /api/learning/metrics`
- `GET /api/learning/patterns`

New metrics:
- diagnosis confirmation rate
- repair resolution rate
- repeat-visit rate
- average engineer rating
- diagnosis-level confirmation/resolution patterns
- dataset maturity status

### Critical design rule

FenIQ does **not** automatically retrain itself from every job. Engineer outcomes are collected as governed evidence first. Future rule/model changes should be evaluated against confirmed historical jobs before being promoted.

Company-admin learning governance now has a first review of an opted-in outcome and a separate decision on a field-limited local research preview. The prepared payload uses controlled categories and verification answers only; it excludes free text and customer/site identifiers. Approved records are removed from the active company dataset when the outcome is corrected or consent is withdrawn. They remain linked to their source inside the company database, so they are not anonymous or authorised for external sharing or model training. See `docs/FIELD_LIMITED_LEARNING_DATASET_CYCLE_2026-09-21.md` for the schema and limits.

This prevents one incorrect field conclusion from silently teaching the whole platform the wrong repair.

### Proprietary-data pathway

The long-term learning record can be anonymised to:
product/system + symptoms + measurements + predicted diagnosis + confirmed diagnosis + repair + outcome.

That is the core dataset that can eventually quantify which diagnostic paths actually produce successful first-time repairs.


## V10 Commercial Operations

V10 adds the first company-operations layer around the technical engine.

### New capabilities
- Customer CRM records
- Work orders
- Engineer assignment
- Schedule/date field for work orders
- Work-order lifecycle: New → Scheduled → In Progress → Awaiting Approval → Complete
- Remake/part/chargeable-work approval requests
- Admin approve/reject decisions
- In-app engineer/admin notifications
- Commercial dashboard metrics
- Subscription plan catalogue

### Approval workflow

An engineer can request approval for:
- replacement part
- sash remake
- full frame remake
- chargeable repair
- warranty escalation
- further investigation

Company admins receive an in-app notification, can approve/reject the request, add a decision note, and the requesting engineer receives the decision.

### Pricing catalogue

V10 exposes the planned tiers:
- Engineer — £29/month
- Pro — £99/month
- Business — £299/month
- Manufacturer — from £999/month

**No payment processor is connected in V10.** The pricing API is product scaffolding only. A production billing release should use a proper payment provider, webhooks, subscription state, invoices, tax/VAT handling and entitlement checks rather than storing card data in FenIQ.

### Next commercial milestone

A later production release should add:
- real calendar/date-time scheduling UI
- email/push notifications
- customer portal
- quote/parts ordering
- subscription billing
- VAT/invoicing integration
- manufacturer dashboards
- audit trail for approvals
- permissions matrix
- production database migrations and tests


## V11 Production Launch Candidate

V11 is deliberately a hardening release rather than another large feature expansion.

### Added
- `/api/health` deployment health check
- explicit role/permission endpoint
- audit-event database model and admin audit endpoint
- deployment indexes reference
- Railway deployment configuration
- Procfile and Docker ignore rules
- launch/security checklist
- production-readiness separation between code-ready and operationally-ready items

### Deployment

The repository remains Docker deployable. `railway.json` is included for Railway-style deployment and uses `/api/health` as the health check.

A managed PostgreSQL database should be used for the private beta. Photo uploads should move from local disk to persistent/cloud object storage before relying on the service for real customer evidence.

### Billing

V11 still does **not** process payments. Connect a PCI-compliant provider such as Stripe rather than storing payment-card data inside FenIQ. Billing needs verified webhooks, subscription entitlement state, VAT/tax configuration, invoice lifecycle and cancellation handling.

### Private-beta gate

Do not treat “deployable” as “security certified.” Before real customer data is used:
1. configure managed Postgres and backups;
2. configure HTTPS and a production secret;
3. add email verification/password reset;
4. add rate limiting and brute-force controls;
5. use cloud/persistent photo storage;
6. run automated/API tests and a security review;
7. publish UK GDPR privacy/retention/DPA documentation;
8. add proper migration execution and rollback.

Recommended first private beta remains deliberately small: one company, a handful of engineers and controlled real jobs while diagnosis accuracy, report time, repeat visits and repair outcomes are measured.
