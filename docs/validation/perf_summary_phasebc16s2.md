# Performance Summary

## Status

Generated from existing PerfTimer logs using:
- Selection mode: explicit globs (baseline_*.log) vs (new_*.log)
- Baseline logs: 5 files
- New logs: 5 files
- Minimum samples required: startup=5, sort=5
- Observed failures against current thresholds: 5 span(s)

## Comparison Table

| Span | Baseline Median (ms) | New Median (ms) | Delta % | Threshold | Status | Baseline N | New N |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| startup.select_database | 5.98 | 3.56 | -40.47% | +5% | PASS | 5 | 5 |
| startup.initialize_ui_vars | 580.96 | 638.49 | +9.90% | +5% | WARN | 5 | 5 |
| startup.populate_dropdowns | 1.11 | 2.04 | +83.78% | +5% | FAIL | 5 | 5 |
| startup.create_ui_grids | 115.82 | 83.83 | -27.62% | +5% | PASS | 5 | 5 |
| sort.cumulative (apply_combined) | 2899.76 | 3868.70 | +33.41% | +10% | FAIL | 5 | 5 |
| sort.confidence (apply_combined) | 5133.04 | 6874.88 | +33.93% | +10% | FAIL | 5 | 5 |
| sort.counter/resistance (apply_combined) | 3295.32 | 4854.13 | +47.30% | +10% | FAIL | 5 | 5 |
| sort.strategic (strategic.sort.end_to_end) | 14031.97 | 18404.25 | +31.16% | +10% | FAIL | 5 | 5 |
## Interpretation

- Gate outcome: FAIL (5 span(s) exceeded thresholds).
- Stable spans: 2 span(s) currently pass regression gates.
- Confidence: Moderate until a controlled 5x5 baseline/new capture is completed.


## Gate Rules

1. Startup median regression must be <= 5%.
2. Generate/sort median regression must be <= 10%.
3. No critical span may regress > 15% without written rationale.

## Run Metadata

- Generated at: 2026-03-23 11:36:45
- Log directory: docs\validation\perf_capture_phasebc16s2_eval
- Selection mode: explicit globs (baseline_*.log) vs (new_*.log)
- Baseline files: baseline_01.log, baseline_02.log, baseline_03.log, baseline_04.log, baseline_05.log
- New files: new_01.log, new_02.log, new_03.log, new_04.log, new_05.log
