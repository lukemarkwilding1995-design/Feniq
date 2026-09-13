# Approval and permission gate cycle — 13 September 2026

Branch: `feniq-phase1-platform`. This cycle is local and not pushed; GitHub authentication remains outstanding. `main` is unchanged.

## Completed

- Approval requires engineer review and a match to the inspection findings captured when the request was submitted. Changed findings require a new request. Legacy requests are labelled as lacking a current scope. Historical decisions remain preserved.
- Conditional decision updates prevent a second decision from replacing the first and check that the reviewed inspection has not changed during authorisation.
- Changes to technical findings or the service record clear the review flag. Reviews produce audit events.
- Work-order transitions are enforced on the server. Completion requires a linked, reviewed inspection with a resolved/no-fault outcome and no pending requests. Only administrators can reopen terminal visits. Completed inspections cannot be edited before reopening.
- Linked inspections cannot be detached/replaced through visit edits; linked visit and inspection engineers must match. Closed visits cannot be used to start new inspections.
- Inspections with snapshots, feedback, work orders or approval history cannot be deleted. A future archival workflow is needed. Company commercial aggregates require admin access.

## Migration, API and UI

`0003_approval_scope` adds `approval_requests.scope_sha256` with an empty default for legacy records. The demo database was backed up outside Git and upgraded successfully. No private documents were added to Git.

Existing approval decision, report edit/review, visit status/edit and deletion APIs now apply the gates. The approval list reports whether findings still match. Approval cards and the decision form explain review requirements and stale/legacy requests. Invalid actions return actionable errors.

## Verification and remaining work

17 automated tests pass, including review/scope invalidation, completion/reopening, pending approval blocking, retained-history deletion protection, engineer/link consistency and prior workflow/migration coverage. JavaScript syntax and Git whitespace checks pass. SQLite is the validated database; PostgreSQL server integration remains outstanding.

These controls govern recorded workflow authorisations; no purchasing, billing or remake-order execution is implemented. Final physical tests still use the existing outcome/review workflow, not a new structured verification model. Approval cancellation/replacement UX, archival, full concurrency stress testing and a complete permission-matrix audit remain work. No claim is made that all production security requirements are complete.

Next: shared Site/Product identity and Product Passports using additive migrations, while retaining these gates and addressing remaining governance gaps in staged cycles.
