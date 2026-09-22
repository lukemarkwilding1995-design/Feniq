# Historical customer-link leads in privacy scope — 22 September 2026

Branch: `feniq-phase1-platform`. No migration. The company-admin privacy inventory now includes retained inspection customer-link corrections that mention the request's customer but whose inspection is not currently linked to that customer. These are manual-review leads, not evidence of current ownership. Each lead shows an inspection reference and event identifier with checksums; the correction reason and inspection contents are excluded. Current linked inspections expose a count and checksum of their correction history.

The inventory checksum covers these leads and their inspection metadata. A new or changed correction invalidates an earlier scope review. The internal Access draft reports only the lead count, without adding those inspections or correction details to the draft. The admin must review former-link leads separately before closing a request. This does not disclose, erase or automatically decide whether a historical record belongs to the requester.

Remaining work includes a fuller data map, manual handling of mixed-subject records, and production validation against PostgreSQL.
