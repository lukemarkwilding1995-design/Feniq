# Demo and private library cycle — 13 September 2026

Branch: `feniq-phase1-platform`. This cycle preserves the root application and leaves `main` unchanged. The encompassing Git commit identifies the tested source; private library material is not included in Git.

## Completed

- Responsive admin/engineer workspace with customers, scheduling, linked inspections, typed server diagnostic checks, report editing, authenticated photos, approvals, notifications, repair outcomes and operational metrics.
- Private company-scoped PDF/video library, content search with page excerpts, original downloads and rendered PDF page navigation. Source metadata remains pending technical review; no imported numerical values become approved diagnostic rules.
- Local library validation: 99 unique PDFs, 25 videos and 7,199 PDF pages. 89 PDFs contain extractable text; 10 need extraction review or OCR. Video archive contents were limited to MP4 files. Executable files were excluded.
- Atomic catalogue replacement prevents readers observing a partially written import. Importer and local demo launch instructions included.
- Wave 1 capabilities 1–40 mapped to existing implementations and genuine gaps in the master plan, integrated with approved extension modules 41–52.

## APIs, UI and data

Added/extended: diagnostic catalogue/run validation; job and work-order updates/linkage; approval decisions; learning feedback read; authenticated photo content; opt-in demo/config; private document catalogue/file/page-image endpoints. The UI connects these into operable workflows.

No SQL schema changes or migrations in this cycle. Existing database startup uses `create_all`; a migration baseline is the next foundation task. Library metadata/files remain in a separate, private local directory with explicit company allowlists. Run the private demo on localhost only.

## Verification

- Eight unittest workflows pass: authentication/roles, service lifecycle, tenant isolation, diagnostic validation, opt-in demo idempotence, photo validation/access, report text and private document search/render/access.
- JavaScript syntax validation and Git whitespace checks pass.
- Visible browser checks: inspection creation/save, source search, PDF page navigation, AluK video playback, desktop/390px mobile layout. Responsive asset cache version updated so existing sessions receive layout fixes.
- Exported sample report rendered and visually inspected: readable metadata, section text, sign-off and page footer without clipping.

## Remaining work

This is a local demo, not the completed production platform. Gaps include OCR, reviewed manufacturer evidence/metadata, immutable execution-time diagnostic snapshots, formal migrations, stronger transition/permission policies, persistent Site/Product identity, Product Passports, Technical Cases, governed learning, billing and production operations. The master plan records the detailed staged order. Video codec support is browser-dependent. The test runtime emits an upstream Starlette/httpx deprecation notice; it does not fail the tests.

Next implementation step: migrations, tenant-policy coverage and immutable diagnostic snapshots, followed by shared Site/Product identity. No new extension module is claimed as shipped by this cycle.
