# Individual Player Import Export Implementation Plan

## Goal

Enable asynchronous, file-based collaboration where five teammates contribute ratings to a shared master database without overwriting unrelated player data.

The feature must support:

- Exporting one friendly player's ratings and comments.
- Importing one friendly player's ratings and comments into a captain-managed master database.
- Bulk import of multiple player files.
- Safe overwrite behavior limited to the targeted player scope.

## Confirmed Product Decisions

- Identity authority: IDs first when file lineage is verified to the captain seed database.
- Team name + player name are guarded fallback and mismatch-detection keys.
- Scope authority: currently selected friendly team in the left dropdown.
- Export scope: all scenarios and all opponent teams.
- Single import behavior: strict identity validation for target player mapping.
- Bulk import behavior: strict fail for any identity mismatch in each file.
- Overwrite behavior: full replacement for target player import scope.
- Empty comment behavior: empty comment clears existing comment.
- Missing rows behavior: warn and continue (not hard fail).
- Messaging policy: align user-facing wording across single import, bulk import, diagnostics, and related documentation for equivalent conditions.
- Concurrency model: asynchronous file handoff only (no shared live DB writes).
- Phase 1 UX: file picker first; drag-and-drop deferred.

Canonical wording categories used across UI + diagnostics:

- `Schema validation failed:` malformed CSV contract (missing columns, unsupported schema version).
- `Identity mismatch:` file identity conflicts with selected targets or database identity bindings.
- `Identity resolution failed:` referenced team/player identity cannot be resolved in the target database.
- `Lineage mismatch detected:` source DB/roster fingerprint differs; guarded fallback checks are applied.
- `Partial export detected (by design):` file is intentionally incomplete; import proceeds with provided rows only.
- `Operation failed:` generic non-validation operational failures in related Data Management actions.
- `Operation notice:` non-error informational notices for related Data Management actions.

## Why This Design

This approach preserves teammate isolation by writing only one player's rows at a time, while still allowing the captain to assemble a complete team dataset. It uses ID-first mapping for the expected same-seed workflow and adds lineage checks plus name fallback for safety when files are from a diverged database.

## Phase Plan

## Phase 1 Contract and File Format

1. Define CSV format `player_ratings_export_v1.csv`.
2. Include metadata per row:
- `schema_version`
- `app_export_version`
- `source_db_fingerprint`
- `source_roster_hash`
- `source_team_name`
- `source_player_name`
- `source_player_id`
- `opponent_team_name`
- `opponent_player_name`
- `scenario_id`
- `rating`
- `comment`
3. Enforce schema/version compatibility checks at import time.
4. Verify source lineage with `source_db_fingerprint` and `source_roster_hash` before trusting IDs.
5. Define expected row cardinality for warnings:
- expected rows = scenario_count x opponent_player_count across included opponent teams.

## Phase 2 Data Layer APIs and Transaction Safety

1. Add export query APIs for one friendly player's ratings/comments in `DbManager`.
2. Add transactional import APIs in `DbManager` with this sequence:
- Validate file, verify lineage, and resolve identities.
- Begin transaction.
- Delete existing rows for target friendly player in import scope.
- Upsert imported ratings.
- Upsert comments, clearing when comment field is empty.
- Commit.
- Roll back on any error.
3. Add dry-run validation method returning warnings and errors before write.

## Phase 3 UI Integration

Add new actions in Data Management menu:

1. Export Individual Player Ratings.
2. Import Individual Player Ratings.
3. Bulk Import Individual Player Files.

For each action:

1. Use currently selected friendly team as scope.
2. Use player selector dropdown where required.
3. Use file picker for single export/import.
4. Use folder picker for bulk import.
5. Show overwrite confirmation before destructive import.
6. Show post-run report summary with counts and warnings.

## Phase 4 Parser and Validation Rules

1. Strict schema/version check.
2. Validate all required columns present.
3. Validate `scenario_id` is an integer and in expected range.
4. Validate rating against configured bounds.
5. Validate comment length max 2000.
6. Resolve all identities by team/player name; fail unresolved rows.
6. Resolve identities by ID first when lineage is verified; fallback to team/player name only when ID resolution cannot be trusted.
7. Fail on any ID-name conflict in the imported file.
8. For missing expected rows, continue with warning and include details in report.

## Phase 5 Cache and UI Consistency

After successful import:

1. Invalidate team/player caches.
2. Invalidate comments cache.
3. Invalidate matchup data cache.
4. Refresh current grid and comments overlays.
5. Refresh dependent analysis state as needed for the active matchup.

## Phase 6 Testing

1. Unit tests:
- parser schema/version validation
- identity resolution behavior
- comment clearing behavior
- dry-run result generation
2. Integration tests:
- export one player then import round-trip equivalence
- single-player overwrite does not mutate other players
- bulk import mixed success/failure report behavior
3. Negative-path tests:
- schema mismatch
- identity mismatch
- unresolved team/player names
- overwrite confirmation declined
4. Regression checks:
- run existing critical suites after implementation.

## Phase 7 Documentation and Operator Guidance

1. Document captain workflow and teammate workflow.
2. Document file format versioning and compatibility rules.
3. Document common import warnings and remediation steps.
4. Document safe handoff checklist for distributed teams.

## Integration Targets

Primary integration file areas:

- UI menu and dialogs: [qtr_pairing_process/ui_manager_v2.py](qtr_pairing_process/ui_manager_v2.py)
- DB import/export primitives: [qtr_pairing_process/db_management/db_manager.py](qtr_pairing_process/db_management/db_manager.py)
- Ratings uniqueness behavior: [qtr_pairing_process/db_management/sql/ratings.sql](qtr_pairing_process/db_management/sql/ratings.sql)
- Comments uniqueness and FK behavior: [qtr_pairing_process/db_management/sql/matchup_comments.sql](qtr_pairing_process/db_management/sql/matchup_comments.sql)
- Validation helpers: [qtr_pairing_process/data_validator.py](qtr_pairing_process/data_validator.py)
- Cache refresh touchpoints: [qtr_pairing_process/matchup_data_cache.py](qtr_pairing_process/matchup_data_cache.py)

## Risks and Mitigations

1. Cross-machine ID mismatch risk.
- Mitigation: verify source lineage and use IDs first only when lineage matches; fail on ID-name conflicts and use name fallback only under guarded rules.

2. Accidental overwrite risk.
- Mitigation: mandatory overwrite confirmation and dry-run summary.

3. Stale data risk from partial files.
- Mitigation: replacement mode + explicit missing-row warnings.

4. Cache incoherence risk after DB writes.
- Mitigation: explicit cache invalidation and UI refresh sequence.

5. Future schema evolution risk.
- Mitigation: schema_version gates and explicit compatibility errors.

## Scope Boundaries

Included in this plan:

- Single-player export/import
- Bulk file import
- Comments support
- Transaction-safe overwrite
- Schema/version checks
- Reporting and warnings
- Documentation and tests

Deferred:

- Drag-and-drop upload UX
- Cryptographic signing/HMAC validation
- Live shared-network DB concurrency controls
- Interactive remapping UI for mismatched identities

## Deliverables Checklist

1. CSV spec and parser implementation.
2. `DbManager` scoped read and transactional import APIs.
3. Data Management UI actions and dialogs.
4. Overwrite confirmation and result reports.
5. Cache invalidation and refresh integration.
6. Test coverage for round-trip, overwrite scope, and failures.
7. End-user and captain workflow documentation.

## Implementation Status (Current Session)

Completed in code:

1. Data-layer API additions in [qtr_pairing_process/db_management/db_manager.py](qtr_pairing_process/db_management/db_manager.py):
- `query_sql_params` for parameterized reads.
- `get_db_fingerprint` for source-database lineage checks.
- `get_team_roster_hash` for friendly-team roster lineage checks.
- `export_individual_player_ratings` to export one friendly player's ratings/comments across all opponents and scenarios.
- `replace_individual_player_ratings` transactional replace import for one friendly player (ratings + comments) with rollback safety.

2. UI workflow additions in [qtr_pairing_process/ui_manager_v2.py](qtr_pairing_process/ui_manager_v2.py):
- Data Management menu buttons:
	- Export Individual Ratings
	- Import Individual Ratings
	- Bulk Import Player Files
- CSV contract helpers and required columns including lineage metadata.
- Friendly-team player selector dialog.
- Single-file import pipeline with:
	- schema/version checks
	- lineage-aware ID-first mapping
	- guarded name fallback
	- strict mismatch failures
	- overwrite confirmation
	- immediate persistence and cache/UI refresh.
- Bulk folder import pipeline with per-file success/failure summary.

3. Robust failure-path diagnostics and log exportability:
- Added structured diagnostics report generation for import/export operations.
- Reports are persisted as JSON files under `import_logs/` in the repository root.
- Added a Data Management UI action to open the `import_logs/` folder directly in Explorer for fast log retrieval.
- Partial export wording is now standardized and reused across single-import warnings and bulk-import per-file summaries.
- Implemented operation-level report generation for:
	- single player export
	- single player import
	- bulk import (including per-file success/failure trace details)
- Each failure path now records:
	- operation metadata (team/scenario/db context)
	- exception type and message
	- full traceback
	- relevant file/folder paths
- UI completion/failure dialogs now surface the diagnostics log path so users can send logs back for troubleshooting.
- Application logger now records success/failure events and exception traces for these operations.

4. Reliability improvement discovered and fixed during implementation:
- Fresh DB initialization now handles BOM-prefixed SQL schema files by reading schema files with `utf-8-sig` encoding in `create_tables`.

5. Automated test coverage added:
- New test module [test_individual_player_import_export.py](test_individual_player_import_export.py) covering:
	- individual export row completeness
	- overwrite isolation to target player only
	- empty-comment clear semantics.

Validation results from this implementation slice:

- `test_individual_player_import_export.py`
- `test_database_preferences.py`
- `test_phase11_regression.py`

Result: 35 passed.

Remaining planned work:

1. Add stricter CSV parser diagnostics/reporting details in UI summary dialogs.
2. Add broader negative-path tests (schema mismatch, identity mismatch, unresolved names in mixed bulk batches).
3. Expand user-facing captain/member workflow docs and troubleshooting guidance.
