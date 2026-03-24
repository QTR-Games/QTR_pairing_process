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
| startup.select_database | 3.26 | 5.67 | +73.93% | +5% | FAIL | 5 | 5 |
| startup.initialize_ui_vars | 685.95 | 207.16 | -69.80% | +5% | PASS | 5 | 5 |
| startup.populate_dropdowns | 0.84 | 1.71 | +103.57% | +5% | FAIL | 5 | 5 |
| startup.create_ui_grids | 79.87 | 58.75 | -26.44% | +5% | PASS | 5 | 5 |
| sort.cumulative (apply_combined) | 3208.06 | 10601.76 | +230.47% | +10% | FAIL | 5 | 5 |
| sort.confidence (apply_combined) | 5707.03 | 20822.50 | +264.86% | +10% | FAIL | 5 | 5 |
| sort.counter/resistance (apply_combined) | 3877.05 | 12561.46 | +224.00% | +10% | FAIL | 5 | 5 |
| sort.strategic (strategic.sort.end_to_end) | 15595.67 | 47844.20 | +206.78% | +10% | FAIL | 5 | 5 |
## Interpretation

- Gate outcome: FAIL (6 span(s) exceeded thresholds).
- Stable spans: 2 span(s) currently pass regression gates.
- Confidence: Moderate until a controlled 5x5 baseline/new capture is completed.


## Gate Rules

1. Startup median regression must be <= 5%.
2. Generate/sort median regression must be <= 10%.
3. No critical span may regress > 15% without written rationale.

## Run Metadata

- Generated at: 2026-03-23 12:45:46
- Log directory: docs\validation\perf_capture_phasebc16s5_eval
- Selection mode: explicit globs (baseline_*.log) vs (new_*.log)
- Baseline files: baseline_01.log, baseline_02.log, baseline_03.log, baseline_04.log, baseline_05.log
- New files: new_01.log, new_02.log, new_03.log, new_04.log, new_05.log
