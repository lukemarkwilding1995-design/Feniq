# Technical Cases cycle — 14 September 2026

Branch: `feniq-phase1-platform`. Local only; GitHub authentication is still required to push. Main remains unchanged.

Implemented owned technical investigations linked to Product Passports and/or inspections, priority, internal assignment notifications, retained notes/history, investigation/waiting/resolution/closure transitions and administrator reopening. Resolution needs written text. Concurrent edits require the current version and stale submissions return a conflict. Company and inspection-owner checks apply to case creation and reassignment. A case does not authorise chargeable work or send external messages.

Migration `0005_cases` adds case and event tables, indexes and event immutability triggers. The demo database was backed up privately and upgraded successfully. Existing records and private manuals remain preserved. APIs support create/list/detail, status/assignment updates and notes. A new Technical Cases UI connects all of these operations to the existing passport/report navigation.

21 automated tests pass, including lifecycle resolution/reopening, stale updates, required resolutions, case history protection, company/owner access and mismatched links, plus prior migration/workflow coverage. JavaScript syntax passes. The visible demo created a fictional Willow House case linked to its existing passport/report, recorded investigation and saved a written resolution.

Remaining limitations: external participants and supplier escalation delivery, attachments, due dates, editable link context, richer collaboration roles and PostgreSQL server validation. Full production security and governance are not complete. Database history triggers do not protect against a privileged database owner.

Next bounded step: controlled manufacturer-source review and verified evidence provenance. Imported documents remain pending review; no technical specification is promoted automatically.
