# Round Selection (Legacy)

This folder stores the legacy round-selection dropdown feature that was removed from the live UI.
It is not wired into the application and will not be loaded or referenced at runtime.

Why this exists:
- The round-selection UI and its sync logic were removed to reduce UI bloat and improve performance.
- Future reimplementation should start fresh and intentionally re-integrate only the needed pieces.

Restoring the feature:
- Treat this as a reference snapshot only.
- Expect to re-implement the UI integration, event wiring, and state management from scratch.
- Review earlier commits (before removal) for the exact wiring in UiManager.

Contents:
- round_selection_legacy.py: standalone snapshot of the legacy methods and logic.
- ui_sync_legacy.py: snapshot of the legacy UI sync controller used by round selection.
- tests/: archived tests that exercised the round-selection and tree-sync behavior.
