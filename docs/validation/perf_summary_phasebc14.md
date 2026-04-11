# Performance Summary

## Status

Generated from existing PerfTimer logs using:
- Selection mode: explicit globs (baseline_*.log) vs (new_*.log)
- Baseline logs: 5 files
- New logs: 5 files
- Minimum samples required: startup=5, sort=5
- Observed failures against current thresholds: 3 span(s)

## Comparison Table

| Span | Baseline Median (ms) | New Median (ms) | Delta % | Threshold | Status | Baseline N | New N |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| startup.select_database | 3.26 | 5.78 | +77.30% | +5% | FAIL | 5 | 5 |
| startup.initialize_ui_vars | 685.95 | 566.69 | -17.39% | +5% | PASS | 5 | 5 |
| startup.populate_dropdowns | 0.84 | 1.46 | +73.81% | +5% | FAIL | 5 | 5 |
| startup.create_ui_grids | 79.87 | 37.61 | -52.91% | +5% | PASS | 5 | 5 |
| sort.cumulative (apply_combined) | 3208.06 | 3177.72 | -0.95% | +10% | PASS | 5 | 5 |
| sort.confidence (apply_combined) | 5707.03 | 5502.89 | -3.58% | +10% | PASS | 5 | 5 |
| sort.counter/resistance (apply_combined) | 3877.05 | 4736.42 | +22.17% | +10% | FAIL | 5 | 5 |
| sort.strategic (strategic.sort.end_to_end) | 15595.67 | 16698.93 | +7.07% | +10% | PASS | 5 | 5 |
## Interpretation

- Gate outcome: FAIL (3 span(s) exceeded thresholds).
- Stable spans: 5 span(s) currently pass regression gates.
- Confidence: Moderate until a controlled 5x5 baseline/new capture is completed.


## Gate Rules

1. Startup median regression must be <= 5%.
2. Generate/sort median regression must be <= 10%.
3. No critical span may regress > 15% without written rationale.

## Run Metadata

- Generated at: 2026-03-23 10:16:15
- Log directory: docs\validation\perf_capture_phasebc14_eval
- Selection mode: explicit globs (baseline_*.log) vs (new_*.log)
- Baseline files: baseline_01.log, baseline_02.log, baseline_03.log, baseline_04.log, baseline_05.log
- New files: new_01.log, new_02.log, new_03.log, new_04.log, new_05.log
