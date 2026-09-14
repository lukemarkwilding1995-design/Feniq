# Technical Cases

Cases provide owned investigations linked to an existing Product Passport, inspection, or both. If both are selected, the inspection must already belong to that passport. Cases never copy restricted report contents into a company-shared passport timeline.

Company administrators see all company cases and can assign active owners. Engineers see and modify their own cases. An engineer owner must already have access to the linked inspection. Case creation validates all company and inspection relationships. Assignment creates an internal notification; there is no external supplier/manufacturer communication in this release.

Workflow: Open → Investigating → Awaiting Response or Resolved → Closed. Awaiting Response can return to investigation. Resolving requires a written resolution. Only administrators can reopen Closed cases; closed cases reject notes. Status changes, assignments, notes and resolutions are retained as events. Reopening clears the current resolution but preserves its historical text. Resolution is an investigation outcome, not commercial approval or certification of a repair.

Updates and notes include the version read by the client. A competing change returns a conflict and requires a refresh. This prevents silent overwrites. Case-event database triggers reject ordinary updates/deletes; privileged database administration is outside that guarantee. No delete API is provided. Linked inspections with case history are protected from deletion.

Migration `0005_cases` adds `technical_cases`, `case_events`, indexes and retained-event triggers. Existing records are unchanged. SQLite migrations and workflow tests pass; PostgreSQL definitions are supplied but have not been tested on a running PostgreSQL instance.

Current scope includes case creation, list/detail, internal ownership, priority, notes, resolution and reopening. External participants, attachments, due dates, manufacturer escalation delivery, editable source context and granular collaboration permissions remain future work. Source review and commercial approval remain separate existing workflows.
