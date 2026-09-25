# Inspection navigation and fresh review — 25 September 2026

Development branch: `feniq-phase1-platform`.

Returning from the repair step to physical checks now explicitly captures the current form and clears engineer approval and the previous diagnostic result. Rerunning diagnosis retains repair notes but requires fresh engineer review. Returning from checks to details also captures the current form, including partial answers. Existing input-event retention remains available during typing.

Changing diagnostic modules clears the old check answers, result and approval. Details submission and explicit draft save share form capture, including a fallback for module changes that did not dispatch input events. The application script URL is versioned so a cached earlier script does not hide the change.

Validation: 41 Python workflow/migration tests; JavaScript syntax check; four focused Node regression scenarios in `tests/inspection_navigation.cjs`; live browser checks of measurement/repair-note retention, cleared engineer review after rerun, and blank checks after module change. Fictional browser inputs were not saved as an inspection or used to overwrite the existing private draft.

This remains an online, explicitly saved draft workflow. Automatic saving, offline recovery and broader navigation-away protection remain outstanding. No database migration is needed.
