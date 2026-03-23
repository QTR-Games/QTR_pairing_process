# Performance Summary

## Status

Generated from existing PerfTimer logs using:
- Selection mode: explicit globs (baseline_*.log) vs (new_*.log)
- Baseline logs: 5 files
- New logs: 5 files
- Minimum samples required: startup=5, sort=5
- Observed failures against current thresholds: 6 span(s)

## Comparison Table

| Span | Baseline Median (ms) | New Median (ms) | Delta % | Threshold | Status | Baseline N | New N |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| startup.select_database | 3.26 | 13.64 | +318.40% | +5% | FAIL | 5 | 5 |
| startup.initialize_ui_vars | 685.95 | 390.75 | -43.04% | +5% | PASS | 5 | 5 |
| startup.populate_dropdowns | 0.84 | 1.45 | +72.62% | +5% | FAIL | 5 | 5 |
| startup.create_ui_grids | 79.87 | 26.03 | -67.41% | +5% | PASS | 5 | 5 |
| sort.cumulative (apply_combined) | 3208.06 | 4436.37 | +38.29% | +10% | FAIL | 5 | 5 |
| sort.confidence (apply_combined) | 5707.03 | 9992.45 | +75.09% | +10% | FAIL | 5 | 5 |
| sort.counter/resistance (apply_combined) | 3877.05 | 5845.69 | +50.78% | +10% | FAIL | 5 | 5 |
| sort.strategic (strategic.sort.end_to_end) | 15595.67 | 20707.31 | +32.78% | +10% | FAIL | 5 | 5 |
## Interpretation

- Gate outcome: FAIL (6 span(s) exceeded thresholds).
- Stable spans: 2 span(s) currently pass regression gates.
- Confidence: Moderate until a controlled 5x5 baseline/new capture is completed.


## Gate Rules

1. Startup median regression must be <= 5%.
2. Generate/sort median regression must be <= 10%.
3. No critical span may regress > 15% without written rationale.

## Run Metadata

- Generated at: 2026-03-23 14:18:24
- Log directory: docs\validation\perf_capture_phasebc16rb1_eval
- Selection mode: explicit globs (baseline_*.log) vs (new_*.log)
- Baseline files: baseline_01.log, baseline_02.log, baseline_03.log, baseline_04.log, baseline_05.log
- New files: new_01.log, new_02.log, new_03.log, new_04.log, new_05.log
