# FenIQ platform master plan

Status: approved Wave 1 foundation and modules 41–52 integrated; major feature scope frozen; implementation remains staged.

## Branch and feature freeze

- Repository: `lukemarkwilding1995-design/Feniq`
- Development branch: `feniq-phase1-platform`
- Do not modify, commit to, merge into, reset or rebase `main`.
- Positioning: **FenIQ — The Operating System for Windows & Doors.**
- Core line: **Quote it. Manufacture it. Check it. Install it. Track it. Fix it. All in FenIQ.**
- Major product feature scope is frozen after incorporating this extension. Additional major modules require explicit authorisation.
- The user supplied the Wave 1 foundation (modules 1–40) and approved extension (41–52). They are one programme. Synonymous capabilities map to existing domains; do not build duplicate modules.

## Current development cycle

The user selected a polished demo with complete core workflows. The existing root application contains company registration, engineer invitations, inspections, diagnostic rules, reports, guides, learning records and initial operational models. The historical `FenIQ_V11/` directory is not the active application.

Continue the current foundations cycle: connect existing operational APIs to usable screens, replace browser-only diagnosis with the server engine, enforce company access, complete error handling, test workflows and import the supplied private technical library. Do not interpret a demo implementation as production readiness or completion of later platform modules.

The supplied manufacturer PDFs and repair videos are authorised for the private local demo only. Store originals and extracted search text outside the repository. Access is scoped to explicit company IDs. Preserve source files and hash metadata; importing a source does not approve its tolerances or replace technical review.

## Shared architecture and dependencies

Every business record must carry a company identity. Establish linked customer, site, development/plot, installed product and Product Passport identities before extending end-to-end operations. New modules must reference these identities instead of duplicating disconnected data.

Foundations required before later waves:

1. Versioned database migrations, tenant-scoped repositories/services, referential integrity and transaction boundaries.
2. A documented granular permission policy, session lifecycle, audit events and controlled exports.
3. Versioned records and attachments with private storage, retention and access rules.
4. Explicit lifecycle/state transitions and immutable revision references for historical execution.
5. Reusable validation, error responses, accessible responsive forms and meaningful integration tests.
6. Reliable configuration, observability, backup/restore procedures and deployment checks.

Existing endpoints are not proof that these foundations are complete. The application now requires a versioned migration ledger; SQLite baseline adoption and snapshot migrations are tested. PostgreSQL integration and full legacy constraint reconciliation remain production gates. Introduce additive, reviewed migrations with backfill/rollback procedures before adding platform tables to persistent production databases.

## Approved extension: modules 41–52

| Module                               | Approved capability                                                                                                                                                                                                               | Principal dependencies                                                                                                     | Delivery boundary                                                                                                                                                                                                                                                                                                                  |
| ------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 41 Workflow Builder                  | Company-admin configurable surveys, quote approvals, manufacturing routes, QC, installation, service, warranty, remake gates, sign-offs, required photos, measurements, tolerances and approvals                                  | Shared record identities, permissions, versioned definitions and execution snapshots, private attachments                  | Definitions progress Draft → Published → Superseded or Archived. Each execution retains its starting revision. Conditions use a validated declarative operator allowlist, never arbitrary code or `eval`. Published revisions cannot rewrite historical jobs.                                                                      |
| 42 Data Import / Migration Engine    | Customers, sites, developments, plots, products, historical jobs, parts, suppliers, price books, warranties and appropriate users                                                                                                 | Target domain models, mapping schemas, company permissions, idempotency, audit, transaction strategy                       | CSV first; XLSX where supported. Upload → Map → Validate → Preview → Confirm → Import → Results. Preserve every rejected row and reason, counts for success/warnings/failure and a downloadable error report. No silent loss or cross-company import.                                                                              |
| 43 Enterprise Security               | MFA, password reset, email verification, sessions, login history/monitoring, expiry policy, lockout/rate limits, granular permissions, SSO architecture, security audit/export, retention, backup/restore, encryption and secrets | Identity model, approved mail delivery, secret configuration, audit and observability, operational runbooks                | Reset/verification tokens are short-lived, single-use and stored hashed. Session revocation and MFA recovery require explicit design. SSO uses provider adapters. Never claim ISO 27001, SOC 2 or other certification without achievement.                                                                                         |
| 44 Evidence Pack                     | Authorised chronological evidence for Product Passport, Technical Case, Warranty Claim, NCR, installation disputes and remake investigations                                                                                      | Linked lifecycle records, attachment versions, permission-aware export, record integrity                                   | PDF/ZIP package includes relevant approved survey, quote/specification/revisions, manufacture, QC/NCR/rework, component batches, dispatch, installation/commissioning, photos/measurements/reports, visits/diagnosis/repairs, approvals/sign-offs and audit timeline. Internal/commercial material must be filtered by permission. |
| 45 Tamper-evident Critical Records   | Version, user, timestamp and integrity/hash metadata for final QC, installation sign-off, customer acceptance, warranty submission, NCR closure, service sign-off and evidence packs                                              | Immutable revision storage, canonical serialization, actor identity, audit/export                                          | Historical versions remain auditable. Hashes detect changes relative to trusted references; they do not make database administrators incapable of alteration. No blockchain claim.                                                                                                                                                 |
| 46 Communications Hub                | Record-linked messages, sender/recipient, time, channel, attachments and linkage                                                                                                                                                  | Customer/quote/order/passport/case/warranty/supplier/NCR identities, permissions, attachment access, notification delivery | In-app initially, email adapter architecture and push later. Conversations remain attached to business records. External sending requires configured delivery and appropriate user authorisation.                                                                                                                                  |
| 47 Finance Bridge                    | Deposit required/received, invoice reference/status, payment status, credit-note reference, outstanding amount                                                                                                                    | Quotes/orders, monetary types/currency, strict finance permissions, audit and provider adapters                            | Operational status only, not a full ledger or accounting package. Keep provider-specific code behind interfaces; do not hard-wire one accounting provider.                                                                                                                                                                         |
| 48 CRM / Lead Pipeline               | Lead, opportunity, customer, site, survey appointment and quote; source, value, sales owner, notes, next action and lost reason                                                                                                   | Shared customer/site identity, scheduling, quotes, roles and lifecycle transitions                                         | New Lead → Contacted → Survey Booked → Survey Completed → Quote Drafted → Quote Sent → Accepted → Won, or Lost with reason. Accepted opportunities enter operations through linked records without duplication.                                                                                                                    |
| 49 Company Implementation Centre     | Company setup, branding, users, permissions, workflows, price book, manufacturers, suppliers, imports, training and launch-readiness tracking                                                                                     | Completion signals from approved modules, configuration permissions, tenant administration                                 | Show truthful completion and unresolved blockers. FenIQ staff/approved partners use scoped application workflows, not direct database edits.                                                                                                                                                                                       |
| 50 Partner / Developer Ecosystem     | Versioned API, webhooks, API credentials/scopes, tenant restrictions, rate limits and integration audit                                                                                                                           | Stable domain contracts, security/session architecture, job queue/outbox, secret storage                                   | Approved integrations only. Credentials stored hashed where possible, scoped/revocable and tenant-bound. Signed webhook delivery, retries and idempotency. No unrestricted database access.                                                                                                                                        |
| 51 White Label / Brand Configuration | Enterprise-authorised logo, company name/accent, PDF/quote/handover/customer-portal branding and email templates                                                                                                                  | Tenant entitlements, validated asset uploads, rendering/template boundaries                                                | FenIQ remains underlying platform. Templates use safe bounded substitutions, not arbitrary executable content. Permissions and accessible colour contrast apply.                                                                                                                                                                   |
| 52 Final Platform Lifecycle          | Linked lifetime lifecycle from lead through learning                                                                                                                                                                              | All preceding shared identities and staged modules                                                                         | Lead → Survey → Quote → Acceptance → Specification → Manufacturing Order → Manufacture → QC → Dispatch → Installation → Commissioning → Invoice/Payment Status → Product Passport → Warranty → Maintenance → Technical Case → Diagnosis → Parts → Repair/Remake → Sign-off → Lifetime Asset Management → Learning.                 |

## Safe condition example for module 41

For product type French Door and threshold Low Aluminium, require top clearance, bottom clearance, meeting sightline, threshold photos and a hinge-adjustment check. Model this as declarative `all` conditions and `require` field/attachment identifiers. Validate identifiers against the published schema. Tolerances must carry their source and review status; an admin-configured value is not automatically a manufacturer specification.

## Staged Wave 1 implementation order

These dependency groups implement the approved programme without renumbering the modules:

| Dependency group                        | Work                                                                                                                                     | Entry gate                                                                           |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Current foundations / demo              | Existing inspections and service operations, private library, tests, UI consistency, mobile/accessibility, data access and documentation | Continue now; no new major module scope                                              |
| Identity and lifecycle foundations      | Shared site/product/passport identity, migrations, permissions, revisions, audit, secure attachment storage and sessions                 | Pass baseline workflow tests and review the migration/identity design                |
| Configurable onboarding and acquisition | Workflow Builder, controlled imports, implementation centre, CRM and brand configuration                                                 | Stable identities/migrations and permission matrix                                   |
| Operational traceability                | Approved manufacturing, QC, dispatch/install/commissioning, warranty, communications, critical-record integrity and evidence pack        | Prior lifecycle domains delivered with UI, tests and historical integrity            |
| Enterprise integrations                 | Security extensions, finance adapters and partner API/webhooks                                                                           | Stable domain contracts, revocable credentials, monitoring and operational readiness |

Do not begin later groups merely because an API scaffold can be added quickly. No work in this plan creates an automatic deployment authorisation or permission to publish private manuals.

## Definition of done

A relevant feature includes: data model, migration, permissions, validation, audit, API, UI, tests, error handling and documentation. A complete endpoint without an operable user workflow is incomplete.

After the feature freeze, prioritise completion of Wave 1, automated testing, security, mobile and factory usability, performance, integrity/migrations, accessibility, UI consistency, observability, backups, deployment, onboarding, documentation and beta testing.

## Development-cycle reporting contract

At each cycle report branch, commit SHA (or explicitly uncommitted), completed functionality, migrations, APIs, UI, tests/results, known defects, technical debt, next implementation step and confirmation that `main` was unchanged. State whether changes are local or pushed. Never describe a planned module as shipped.

## Wave 1 principles

FenIQ serves installers, service engineers, surveyors, fabricators, manufacturers, suppliers, housing providers and other fenestration businesses. Structured engineering logic, manufacturer technical evidence, field knowledge and AI assistance work together. AI supports decisions; it must not invent specifications or independently authorise expensive remedial work.

Diagnostic path: Product → Component → Symptom → Test → Measurement → Result → Likely Cause → Corrective Action → Repair → Verification → Outcome.

Knowledge path: FenIQ controlled knowledge → verified supplier/manufacturer documents → official Internet technical sources → reputable third-party sources. Verified manufacturer documentation outranks general field guidance for manufacturer-specific specifications. Preserve manufacturer, system, title, revision, page/section, source and review status. An uploaded PDF, a search match or a high rule score is not automatically verified evidence.

Required classifications: Verified FenIQ Source; Official Manufacturer Web Source; Third-Party Technical Source; Field Guidance. Unreviewed imported material remains pending review and must not be promoted into numerical diagnostic rules.

Learning records must ultimately preserve an immutable snapshot of original fault, evidence, measurements and predicted diagnosis alongside actual repair and verified outcome. Newly saved inspections now retain an immutable original diagnosis, fault, evidence, typed checks/units and rule fingerprint. New feedback uses that prediction. Legacy captures are labelled explicitly. Unsaved run history and immutable repair/outcome events remain gaps.

## Wave 1 capability map

“Demo workflow” means the user flow is implemented at demo scope, not production-complete. “Partial” means usable components exist but the approved capability has material gaps. “Planned” means architecture only.

| ID  | Approved capability                               | Existing implementation / current status                                                      | Genuine remaining work                                                                                                    |
| --- | ------------------------------------------------- | --------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| 1   | Company accounts, auth, users, roles, permissions | Demo workflow: Company/User, register/join/login, admin/engineer checks, team UI              | Granular permission matrix, account lifecycle, security module 43                                                         |
| 2   | Isolated multi-user company data                  | Partial: tenant-filtered queries and ownership checks; private document allowlists            | Systematic authorization audit, database constraints and policy tests across every domain                                 |
| 3   | Customer/site management                          | Partial: Customer CRUD creation/list UI with address                                          | Separate persistent Site identity, editing/archival and linkage migration                                                 |
| 4   | Jobs and work orders                              | Demo workflow: list, assign, schedule, edit visit, status, linked inspection                  | Enforced transition rules, reassignment notifications and identity constraints                                            |
| 5   | New Inspection                                    | Demo workflow: details → checks → diagnosis → repair/report                                   | Durable draft/resume and concurrency handling                                                                             |
| 6   | Product/system identification                     | Partial: product selector, system text, manufacturer catalogue/router APIs                    | Linked product/system IDs, identification UI and passport relationship                                                    |
| 7   | Fault/symptom capture                             | Demo workflow: reported fault and module selection                                            | Structured component/symptom taxonomy                                                                                     |
| 8   | Photo/evidence capture                            | Demo workflow: before/after upload, validation, tenant-protected retrieval                    | Object storage, scan policy, deletion/retention, richer evidence types                                                    |
| 9   | Structured modules                                | Demo workflow: eight server-defined modules                                                   | Versioned rule sets and reviewed coverage expansion inside approved scope                                                 |
| 10  | Measurements/checks                               | Demo workflow: typed required findings, saved readable evidence                               | Completed for first saved diagnosis; next add diagnostic-run revision history                                                  |
| 11  | Rules-based engine                                | Demo workflow: server evaluation and save-time recomputation                                  | Rule version binding, stronger safety-condition evaluation and regression corpus                                          |
| 12  | AI/vision assistance                              | Partial: existing live AI adapter, UI only when configured                                    | Provider error handling, mocked contract tests, quotas/privacy policy and structured output guarantees; no fake AI result |
| 13  | Confidence/evidence                               | Demo workflow: rule score, evidence and limitations                                           | Calibrate scores only if justified; retain explicit non-probabilistic labelling                                           |
| 14  | Corrective actions                                | Demo workflow: engine recommendations                                                         | Versioned manufacturer evidence links                                                                                     |
| 15  | Guided repair                                     | Demo workflow: repair sequences and eight field guides                                        | Step-level completion/evidence capture and source revision binding                                                        |
| 16  | Parts/remake recommendations and approval gates   | Partial: engineer review flag, separate commercial approval UI and decisions                  | Enforce lifecycle-level approval before downstream expensive actions; no ordering/payment action exists yet               |
| 17  | Final tests/outcomes                              | Partial: repair outcome, resolution, repeat-visit feedback                                    | Structured final verification checklist and required measurements                                                         |
| 18  | Notes/engineer approval                           | Demo workflow: notes, review flag and report                                                  | Immutable sign-off revisions and revocation semantics                                                                     |
| 19  | Customer sign-off                                 | Partial: sign-off name recorded                                                               | Identity/consent-backed acceptance record, timestamp and record version                                                   |
| 20  | Professional PDF reports                          | Demo workflow: authenticated PDF export with wrapped/escaped content, photos and page numbers | Branding, immutable report revisions and export audit                                                                     |
| 21  | Technical Knowledge Library                       | Demo workflow: guides, private PDFs/videos, search and filters                                | Pagination/index scaling and controlled review workflow                                                                   |
| 22  | FenIQ field guides                                | Demo workflow: clearly labelled repair/adjustment guides                                      | Reviewed versioning and contributor workflow                                                                              |
| 23  | Manufacturer Intelligence                         | Partial: manufacturer/system catalogue and routing API                                        | Connect identification/routing UI and approved specification records                                                      |
| 24  | Controlled specifications                         | Partial: controlled-source registry concept, pending-review imported records                  | Approval roles, source revisions/supersession and typed specification extraction                                          |
| 25  | Supplier/manufacturer PDF library                 | Demo workflow: private company-scoped files, hashes, metadata and original viewing            | Admin import/review UI, operational storage and lifecycle management                                                      |
| 26  | PDF extraction/indexing/provenance                | Partial: page-indexed text, document hash, filename-derived revision/system and source path   | OCR for scanned pages, verified metadata, import validation report and reviewed extraction accuracy                       |
| 27  | Verified evidence during diagnosis                | Planned: no imported source is automatically verified                                         | Reviewed retrieval tied to diagnosis and preserved source/page references                                                 |
| 28  | Internet Technical Search                         | Planned                                                                                       | Official-source priority, constrained provider adapter, source validation and cited UI                                    |
| 29  | Source classification                             | Partial: field guidance distinct from pending-review manufacturer files                       | Full approved four-class taxonomy and verification controls                                                               |
| 30 | Product Passports | Demo workflow: persistent Site/Product IDs, company catalogue, retained lifecycle notes and inspection links | Metadata corrections/archival, verified manufacturer identity, richer lifecycle events, external sharing and production governance |
| 31 | Technical Cases | Demo workflow: owned investigations linked to passports/jobs, retained notes, versioned updates, resolution and reopening | External collaborators, attachments, escalation delivery, richer permissions and production hardening |
| 32  | Engineer Learning Engine                          | Partial: outcome metrics and patterns UI                                                      | Governed dataset versioning, evaluation and immutable outcome events                                                  |
| 33  | Diagnosis → repair → outcome records              | Partial: LearningRecord linked to Job                                                         | First-save original snapshot implemented; next immutable repair/outcome events                                                      |
| 34  | Governed/anonymised improvement                   | Partial: explicit opt-in flag, no automatic model updates                                     | Actual anonymisation pipeline, consent enforcement and reviewed promotion process                                         |
| 35  | Pattern/repeat-failure intelligence               | Partial: diagnosis aggregates and repeat-visit metrics scoped by role                         | Product/component-linked recurrence analysis and sample-size reporting                                                    |
| 36  | Dashboard/analytics                               | Demo workflow: inspections, visits, resolved records, approvals and feedback                  | Date filters, consistent definitions and production-scale queries                                                         |
| 37  | Commercial plans/subscriptions                    | Partial: plan metadata API only                                                               | Billing adapter, entitlements/webhooks, subscription lifecycle and UI; do not claim paid subscriptions are live           |
| 38  | Approvals/notifications                           | Demo workflow: request/decision, in-app notifications/read state                              | Delivery adapter, deduplication/outbox and broader permissions                                                            |
| 39  | Supplier/manufacturer portals                     | Planned                                                                                       | External identities, scoped contribution, approval workflow and contribution provenance                                   |
| 40  | Auditability/security/provenance/production       | Partial: audit model/events, token auth and company checks                                    | Migration framework, immutable history, rate limits, monitoring, backups, deployment and security gates                   |

## Next implementation sequence

1. Complete and verify the current demo/library cycle, preserve private assets outside Git and record the exact tested commit.
2. Migration baseline and immutable first-save diagnostic snapshots are implemented and tested on SQLite. Complete the tenant/permission audit, transition gates and final verification; validate PostgreSQL before production deployment.
3. Add shared Site/Product identity and Product Passports; link existing Jobs/WorkOrders through additive migrations. Then Technical Cases reuse those identities and existing approvals/notifications.
4. Implement controlled-source review/versioning and verified evidence retrieval in diagnosis. Add official Internet source search with provenance after trusted retrieval is stable.
5. Complete remaining Wave 1 gaps (governed learning, portal contributions, subscriptions and operational production requirements) in bounded cycles, meeting the definition of done.
6. Progress modules 41–52 only when their prerequisites and Wave 1 foundations are stable. Their inclusion in architecture does not mean they are implemented.

## Approval-gate update ? 13 September 2026

Migration 0003 binds requests to technical findings. Engineer review, stale-scope rejection, conditional single decisions, completion/reopening transitions, retained-history deletion protection and admin-only commercial aggregates are implemented. Seventeen automated tests pass. This advances capabilities 4, 16, 18, 38 and 40; it does not complete the entire permission matrix, physical verification model or production governance. Next domain: shared Site/Product identity and Product Passports.

## Product Passport update

Migration 0004 adds explicit sites under customers, persistent product identities, append-only lifecycle events and inspection links. Company-shared passports preserve assigned-engineer restrictions on linked reports. Existing text-only inspection identity is not automatically inferred or migrated. Next: Technical Cases linked to these identities, alongside staged passport corrections/archival and production hardening.

## Technical Case update

Migration 0005 adds owned investigations with retained event history and optimistic version checks. Cases link to existing passports/inspections without copying restricted reports to shared timelines. Resolution does not authorise commercial work. Twenty-one tests pass. Next bounded work: controlled manufacturer-source review and verified evidence provenance, while keeping external communications and unimplemented production features clearly scoped.

## Controlled source review update

Migration 0006 adds retained company review decisions tied to exact private PDF hashes, reviewed pages, revision and declared applicability. Imports remain pending until a human administrator records a review. Changed bytes invalidate reference approval. This is reference governance, not automatic verification of numerical specifications. Twenty-two tests pass. Next: provenance-preserving reviewed page citations attached to inspections, then controlled diagnostic retrieval.

## Reviewed inspection citation update

Migration 0007 retains exact reviewed-page excerpts with source/revision/hash provenance, historical status after withdrawal and fresh engineer review requirements. PDFs include a citation appendix. Twenty-three tests pass. This advances capabilities 8, 13, 20 and 25-27 without duplicating the library or claiming automated diagnostic retrieval. Next: controlled retrieval of relevant reviewed evidence.

## Reviewed evidence search update

Inspection-scoped literal PDF search now retrieves only currently reviewed pages, with source provenance and an explicit handoff to citation attachment. Results are bounded and incomplete coverage is disclosed. No migration. Twenty-three tests pass with expanded retrieval coverage. Human review of private documents remains outstanding; this is not automatic specification verification or semantic diagnosis.

## Search continuation

Reviewed-evidence retrieval now supports further batches with query/source snapshot validation and visible coverage counts. Twenty-four tests pass. Next domain remains governed repair outcomes; production retrieval performance remains outstanding.

## Retained outcome revisions

Migration 0008 adds append-only repair feedback history and original diagnostic snapshot linkage. Corrections need reasons and current revision; resolved feedback needs final-check notes. Existing metrics use the latest projection. Twenty-five tests pass. This advances Wave 1 outcome governance but does not complete anonymisation, reviewed dataset promotion or automatic final-job recording. Next: report/passport integration and structured verification.

## Outcome reporting and passport integration

Inspection screens and PDFs now show the latest retained repair result alongside the immutable original diagnosis, including final checks and integrity metadata. Linked Product Passports expose the latest authorised outcome and revision count without copying it into editable lifecycle notes. Twenty-five tests pass, including passport and PDF integration. Next: versioned structured verification checks and repeat-failure analysis.

## Structured repair verification

A server-owned core verification definition now records four structured final checks with its revision and hash inside every new outcome revision. Resolved outcomes require all checks to pass plus narrative observed results. Historical unstructured revisions remain visible and clearly labelled. Twenty-five tests pass. This is FenIQ field workflow guidance rather than manufacturer specification. Next: governed Product Passport repeat-failure analysis.

## Product Passport repeat-failure intelligence

Linked Passport inspections now expose transparent diagnosis recurrence counts using immutable originals where available and the latest retained outcome per inspection. The UI distinguishes single observations from repeated diagnoses, marks legacy mutable-source records, and recommends review only when repeat groups include unresolved or repeat-visit outcomes. No automatic rule changes, causation claims or cross-company pooling occur. Twenty-six tests pass. Next: performance hardening and governed, opt-in learning review.

Company-admin learning review now retains append-only decisions on exact, latest opted-in outcome revisions. The UI presents a review queue with consent and checksum context, while corrections and opt-outs remove obsolete candidates. This is preparation for de-identification only; no anonymisation, model training, or rule changes occur. Migration 0009 and two endpoints support the workflow; twenty-seven tests pass. Next: historical governance view and reviewed de-identification with explicit second approval.

The admin learning page now exposes paginated review history, showing whether each retained decision is current, superseded by a correction, or affected by consent withdrawal. History remains company-isolated, and current eligibility/status queries use latest outcome revisions. A fictional local demo record illustrates withdrawal after an excluded review. No migration or learning promotion was added; twenty-seven tests pass. Next: field-level de-identification and separate approval before dataset use.

Migration 0010 adds a second, append-only decision on a field-limited payload derived only from a currently opted-in, first-stage-prepared outcome. The UI presents the exact controlled-field preview and an approve/reject step; the internal company dataset returns only still-eligible approved payloads without source IDs and automatically excludes corrected or opted-out outcomes. Decision history remains retained. This is local research preparation, not anonymity, external publication or model training. Twenty-eight tests pass. Next: two-person governance, aggregation thresholds and revocation handling before any wider use.

The second dataset approval now requires a different company admin from the first review; earlier self-approved records are excluded while their decision history is retained. Admins can grant a company engineer admin access with an audited reason. A minimum cohort of five suppresses internal aggregate statistics below threshold. The fictional demo includes a second admin. This still does not authorise external sharing, cross-company pooling, or AI training. See `DUAL_ADMIN_LEARNING_CYCLE_2026-09-21.md`.

The inspection report now supports dedicated learning-consent withdrawal. It appends a checked revision, disables the current feedback projection's opt-in, and removes the outcome from active research eligibility without changing the repair record. Historical decisions remain available for audit and show consent withdrawal. See `LEARNING_CONSENT_WITHDRAWAL_CYCLE_2026-09-22.md`.
