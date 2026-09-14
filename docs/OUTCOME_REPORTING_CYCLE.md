# Outcome reporting and passport integration

Branch: `feniq-phase1-platform`. Development remains local; `main` is unchanged and private source files remain outside Git.

The inspection screen now shows the latest retained repair outcome beside the immutable original diagnosis. The PDF report adds a separate latest-outcome appendix containing the predicted and engineer-confirmed diagnoses, actual repair, final checks, reported resolution, repeat-visit status, correction reason, diagnostic snapshot hash and outcome hash. It identifies the retained revision and states that earlier revisions remain in audit history.

Product Passport detail now derives the latest authorised repair outcome for each linked inspection and shows its revision count, final checks and integrity status. It does not copy outcome data into editable lifecycle notes. Existing report and passport access rules still apply.

No migration or new endpoint was required. The existing passport detail response now includes `repair_outcome` and `outcome_revision_count` for each visible linked inspection. The existing report endpoint includes the latest retained revision when present.

All 25 automated tests pass. The outcome integration test verifies passport projection and PDF content while retaining the earlier correction/history, tenant-isolation and database-protection checks. JavaScript syntax checks pass. The two-page fictional outcome report was rendered and visually inspected with readable margins, hierarchy, hashes and page numbering. The local browser visibly shows the latest outcome and final-check text on the inspection.

Known gaps: the PDF intentionally shows the latest outcome only; authorised app users use the retained history for earlier revisions. Product Passport outcome data is derived at request time and needs query optimisation before production scale. Final checks remain free text rather than a versioned structured verification definition. Outcome revisions do not yet snapshot photos/citations, automatically create a critical Passport event, or drive repeat-failure analytics. PostgreSQL remains unvalidated against a live server.

Next: versioned structured verification checks for repair outcomes, followed by controlled inclusion of outcome evidence in Product Passport repeat-failure analysis.
