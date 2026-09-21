# Product Passport repeat-failure cycle - 21 September 2026

Branch: `feniq-phase1-platform`. Changes remain local. `main` and the private technical library are unchanged.

The Product Passport now presents a read-only repeat-failure summary derived from linked inspections the current user may access. It groups case- and whitespace-normalised original diagnoses, shows the number of inspections, resolved and unresolved latest repair outcomes, missing outcomes, repeat visits, and the number based on an immutable original snapshot. Records lacking any diagnosis are counted as omitted. Historical inspections without a snapshot are explicitly labelled as using their current legacy diagnosis.

A repeated diagnosis is an observation across at least two linked inspections of the same product. The page recommends engineer review only when that group also includes an unresolved outcome or an indicated repeat visit. It does not claim causation, certify a repair, alter the diagnostic engine, or silently promote learning data. Earlier outcome revisions remain retained but the counts use each inspection's latest revision so corrections do not inflate the sample.

No migration or new endpoint was needed; existing company and assigned-engineer access rules govern `GET /api/passports/{id}`. Its response now includes `failure_analysis`, and the Passport UI shows the summary and its method. The test suite has 26 passing tests, including immutable-diagnosis grouping after later edits, latest-outcome correction, honest omission counts, and prior tenancy and workflow tests. JavaScript syntax checks pass. The live demo visibly shows the new panel and correctly labels the old Willow House inspection as one provisional legacy observation without a retained outcome.

Limitations: the analysis is descriptive and is not a verified fault taxonomy or statistical failure-rate estimate. It uses one company's linked Passport inspections, not all product installs. Legacy current diagnoses can change, so they remain labelled rather than treated as immutable evidence. It presently runs per Passport request and needs batched queries/caching before large production use. Outcomes are engineer-authored; governed anonymisation, external evidence verification and learning promotion remain future work.

Next: extend testing and performance on larger Passport histories, then implement a reviewed, opt-in learning dataset promotion workflow without changing diagnostic rules automatically.
