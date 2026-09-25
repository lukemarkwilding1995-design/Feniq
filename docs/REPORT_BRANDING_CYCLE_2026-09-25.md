# Report branding cycle — 25 September 2026

Migration `0017_report_branding` adds a company-scoped PDF report name, business contact line and accent colour. Company administrators manage these values from **Company & team**. Engineers can see the effective identity but cannot change it. Accent input is restricted to a six-digit hexadecimal colour, and text fields are length bounded and escaped by the PDF renderer.

New current reports and retained revisions use the configured identity. **Powered by FenIQ** remains visible, as do the source classification, rule-score limitations, engineer-review state and other safety wording. This cycle does not permit executable templates, arbitrary markup or removal of FenIQ provenance.

The effective report identity is included in both the customer-acceptance report scope and the canonical retained-report source checksum. Changing it marks an earlier customer acceptance and retained PDF as historical and requires new records for the updated appearance; the original acceptance and PDF bytes/checksum remain unchanged. The branding change itself is audited.

All 38 automated tests pass, covering migrations, admin permissions, invalid colour rejection, PDF text, audit creation and report-revision checksum changes. PostgreSQL DDL is supplied but has not been validated against a running server. Logo uploads, customer-portal/quote/email theming, entitlement controls, contrast analysis and production asset storage remain staged Module 51 work.
