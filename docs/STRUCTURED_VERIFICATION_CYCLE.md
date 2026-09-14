# Structured repair verification

Branch: `feniq-phase1-platform`. Development remains local; `main` is unchanged. Private technical sources remain outside Git.

FenIQ now serves a versioned core repair-verification definition containing four required checks: recorded work matches the repair, full operation cycle completed, original fault rechecked, and relevant safety/security functions rechecked. The definition is declarative, server-owned, hash-identified and labelled as FenIQ field workflow rather than manufacturer specification.

The outcome form records Pass, Fail or Not checked for every check. A resolved outcome is rejected unless all required checks pass and narrative final-check evidence is present. The server rejects incomplete check sets, unexpected keys and stale definition identifiers/hashes. Each append-only outcome revision embeds the exact definition, revision, hash and answers used, so later definition releases cannot rewrite historical outcomes.

API: `GET /api/jobs/{job_id}/verification-definition` applies existing inspection access rules. `POST /api/jobs/{job_id}/learning` accepts the definition identity and structured answers in addition to the existing retained outcome fields. No database migration is needed because the versioned definition snapshot is stored inside the immutable outcome payload.

The inspection UI shows the definition source, revision and structured choices. Current report summaries and retained history display recorded answers; older revisions are explicitly labelled as having no structured definition. PDFs include the checklist, field-workflow source classification and definition hash.

All 25 automated tests pass. Coverage includes stale-definition rejection, failed required-check rejection, retained revision/hash content, company isolation, Product Passport projection and PDF text. JavaScript syntax checks pass. The fictional two-page report was rendered and visually inspected with clean spacing, page numbering and readable hashes. The live browser form visibly shows all four checks and identifies the prior local demo outcome as a legacy unstructured revision.

Known gaps: revision 1 is a general field checklist, not a product-specific or manufacturer specification. It does not prove physical testing occurred; engineer identity, notes and audit history provide accountability. There is no admin workflow for proposing/publishing later definitions, required evidence/photo binding, electronic test-device capture, signature over the whole evidence bundle, or live PostgreSQL validation. Failed checks do not yet create a follow-up visit automatically.

Next: Product Passport repeat-failure analysis using the immutable original diagnosis and latest governed outcome, with transparent sample counts and no automatic diagnostic-rule changes.
