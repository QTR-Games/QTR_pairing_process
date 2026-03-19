# Performance Comparison Protocol

## Goal

Detect regressions introduced by UI modernization while allowing small expected variance.

## Thresholds

1. Startup median regression <= 5%
2. Generate/sort median regression <= 10%
3. No critical span regression > 15% unless justified

## Tracked Paths

From perf spans in ui_manager_v2.py:

1. startup.select_database
2. startup.initialize_ui_vars
3. startup.populate_dropdowns
4. startup.create_ui_grids
5. generate/sort workflow spans (cumulative/confidence/counter/strategic)

## Procedure

1. Run baseline build with perf logging enabled.
2. Execute consistent interaction script manually:
- launch app
- select teams/scenario
- generate combinations
- run each sort mode once
- extract matchups
3. Collect perf logs for N=5 runs.
4. Apply change set and repeat N=5 runs.
5. Compute median and max deltas by span.

## Generator Commands

Automatic window split (quick check):

```bash
python docs/validation/generate_perf_summary.py --log-dir perf_logs --out-md docs/validation/perf_summary.md --out-csv docs/validation/perf_summary.csv --baseline-count 5 --new-count 5
```

Explicit windows (recommended for controlled comparisons):

```bash
python docs/validation/generate_perf_summary.py --log-dir perf_logs --baseline-glob "perf_20260318_*.log" --new-glob "perf_20260319_*.log" --out-md docs/validation/perf_summary.md --out-csv docs/validation/perf_summary.csv
```

## Summary Template

| Span | Baseline Median (ms) | New Median (ms) | Delta % | Status |
| --- | ---: | ---: | ---: | --- |
| startup.initialize_ui_vars | 0 | 0 | 0.0 | PASS |

## Status Rules

- PASS: within thresholds
- WARN: within +15% for non-critical span
- FAIL: exceeds threshold or critical span > +15%
