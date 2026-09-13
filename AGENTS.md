# Feniq development

All development must use `feniq-phase1-platform`. Never commit or push changes directly to `main`.

The active application is the root `app/` directory. `FenIQ_V11/` is a historical snapshot, not the active application.

Phase 1 targets a polished demo with complete engineer and company-admin workflows. Keep sample data fictional, demo access explicitly opt-in, and manufacturer rules labelled according to their verification status.

Run `python -m unittest discover -s tests` and `node --check app/static/app.js` before delivery.
