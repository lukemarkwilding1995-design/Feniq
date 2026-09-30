# Unsaved inspection exit protection — 30 September 2026

The inspection wizard now tracks unsaved input and step progression. Leaving for another workspace page, signing out, or switching demo accounts offers Keep editing or Leave without saving edits. The latter leaves the stored draft and completed inspection unchanged. Forward and backward wizard navigation remains uninterrupted. Successful draft and inspection saves clear the warning; failed saves retain it.

A browser beforeunload handler requests the browser's standard warning when refreshing, closing or navigating away with unsaved edits. Browser support and interaction requirements apply; this is loss prevention rather than guaranteed recovery. Automatic saving and offline recovery remain outstanding. Authentication expiry may still clear session state to enforce access boundaries.

Validation: all 41 Python tests; app.js syntax; existing inspection navigation regression scenarios; new `node tests/inspection_exit.cjs` guard checks; live tests of staying, leaving, wizard navigation, original stored draft preservation, and successful explicit draft save. No database migration is needed. Browser test records are fictional.
