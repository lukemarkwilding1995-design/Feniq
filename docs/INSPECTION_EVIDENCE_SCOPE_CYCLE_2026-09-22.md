# Inspection evidence in privacy scope — 22 September 2026

Branch: `feniq-phase1-platform`. No migration or new endpoint. The company-admin privacy inventory now counts and checksums retained diagnostic snapshots and reviewed inspection citations for each currently linked inspection and unlinked name-match lead. A new citation or changed retained row changes the inventory checksum and requires another scope review before closure or inspection of an Access draft.

The inventory exposes counts and metadata checksums, not the snapshot payload or citation excerpt. These contents remain outside the internal Access draft pending manual review for third-party information and disclosure scope. The UI shows counts on inspection entries. Tests cover the checksum change after adding a real reviewed citation and verify that its excerpt is absent from both inventory and draft.

This is a partial data map. It does not cover every company record or private source file, perform disclosure or erasure, or replace an organisation's identity and redaction process. Live PostgreSQL validation remains outstanding.
