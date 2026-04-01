# Code Review Decisions Log

This file records explicit review decisions so the same settled topics are not reopened in future reviews without new evidence.

## 2026-04-01

- DbManager identifier interpolation in insert_row/upsert_row:
  - Decision: accepted as internal-only.
  - Rationale: table/column identifiers are code-defined constants, not user input; value payloads remain parameterized.
  - Guardrail: keep user input out of identifier parameters.

- DataValidator comma support in team/player names:
  - Decision: accepted and intentional.
  - Rationale: real-world names include commas; behavior is covered by punctuation regression tests.
  - Coverage: test_import_export_punctuation.py.

- Multi-scale ratings in import-ready templates:
  - Decision: accepted as expected.
  - Rationale: application supports 1-3, 1-5, and 1-10 scales; values above 5 are valid under higher-range systems.

- Placeholder ratings in default_team_1_vs_Other_Room_import_ready.csv:
  - Decision: changed.
  - Rationale: replaced 0 placeholders with neutral midpoint value 5 per project policy for blank/default rating behavior.

- Secure interface thread cache lifecycle:
  - Decision: changed with periodic bulk cleanup.
  - Rationale: thread-local cache correctness is required; cleanup is intentionally batched to avoid hot-path overhead.
  - Coverage: test_db_manager_bootstrap.py (thread-local behavior + cleanup regression).
