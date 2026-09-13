# FenIQ Phase 1 demo

Development branch: `feniq-phase1-platform`. Do not commit or push directly to `main`.

The active application is at the repository root. `FenIQ_V11/` is the historical launch-candidate snapshot.

## Start locally

Requires Python 3.11 or newer (tested with Python 3.12).

```sh
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python scripts/run_demo.py
```

On macOS/Linux, activate with `source .venv/bin/activate` and run the same launcher. It binds only to localhost and stores its database, photos and persistent session key in `demo-data/`. Use `--data-dir` to select a separate directory.

Open http://127.0.0.1:8000 and choose **Explore as admin** or **Explore as engineer**. The opt-in demo creates fictional customer records, inspections, visits, an approval request and repair feedback. The two roles share this demo company so you can demonstrate the handoff. Saved changes persist in the demo database. Use a separate database for each demonstration when a fresh set of records is wanted.

`FENIQ_DEMO` must be disabled for any environment holding real customer data. Demo entry intentionally permits access to the fictional demo company without a password. Do not add real data to that company.

Without demo mode, **Create company**, **Join team** and **Sign in** support normal account flows. If `SECRET_KEY` is omitted, the local server generates a temporary signing key, so sessions end when it restarts. Set a stable, random `SECRET_KEY` for a persistent or multi-worker environment.

## Demonstrate the core workflow

1. Enter as admin. Open **Customers**, add a fictional site, then open **Schedule** to assign a visit to Jamie Taylor.
2. **Switch role** to engineer. Open the assigned visit and **Start inspection**.
3. Capture details, choose a diagnostic module and explicitly enter physical checks. Run the server diagnosis.
4. Record work, outcome and engineer review. Save the inspection. Add before/after photo evidence and download its PDF.
5. Request commercial approval from the report. Switch to admin, review the request and record the decision. Switch back to see the notification.
6. Open the inspection to edit the repair record or **Record repair outcome**. Explore **Repair insights**, **Knowledge library** and **Company & team**.

## Private technical library

Keep source documents and the extracted search index outside the repository. Import only into an explicitly selected company; the local demo company must never be exposed to the Internet when it has private reference material attached.

```sh
python scripts/import_manuals.py "PATH/TO/MANUALS" "../private-library" --company-id 1 --manufacturer "Manufacturer name"
python scripts/run_demo.py --library "../private-library"
```

Check the intended company ID before importing. PDF, MP4, MOV and WebM files are supported. Duplicate files are identified by SHA-256; executable files and archives are not imported. PDF text search retains PDF page numbers, while printed page labels may differ. Scanned pages without embedded text need a future OCR step. Original files and rendered pages require company-authorised access.

Imported metadata is pending technical review. A source's presence in the library does not approve its specifications as diagnostic rules. Review document revision, product applicability and exact page evidence before adopting any manufacturer values. Video playback depends on the browser's codec support; the original file remains downloadable.

## Validation

```sh
python -m unittest discover -s tests -v
node --check app/static/app.js
```

Tests use an isolated database. `FENIQ_TEST_DIR` can specify a dedicated writable test directory where a restricted Windows runtime cannot use its default temporary directory. Never point it at a real application data directory.

## Scope

This is a demo release, not a public commercial launch. It includes onboarding, role-aware navigation, inspections, server diagnostics, authenticated photo evidence, PDF reports, repair feedback, customer creation, scheduling, approvals, notifications, a team directory and audit events for inspection/work-order changes and approval decisions.

Billing, password recovery, email verification, outbound notifications, offline sync and production object storage are not part of this demo. Live photo AI appears only when the existing `OPENAI_API_KEY` and `OPENAI_VISION_MODEL` configuration is present; it is not simulated. Manufacturer-specific values remain unverified unless the source registry says otherwise.
