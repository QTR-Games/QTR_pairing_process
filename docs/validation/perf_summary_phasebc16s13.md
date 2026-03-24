# Performance Summary

## Status

Generated from existing PerfTimer logs using:
- Selection mode: explicit globs (perf_capture_phasebc15_eval/baseline_*.log) vs (perf_capture_phasebc16s13_eval/baseline_*.log)
- Baseline logs: 5 files
- New logs: 5 files
- Minimum samples required: startup=5, sort=5
- Observed failures against current thresholds: 2 span(s)

## Comparison Table

| Span | Baseline Median (ms) | New Median (ms) | Delta % | Threshold | Status | Baseline N | New N |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| startup.select_database | 3.26 | 1.71 | -47.55% | +5% | PASS | 5 | 5 |
| startup.initialize_ui_vars | 685.95 | 491.89 | -28.29% | +5% | PASS | 5 | 5 |
| startup.populate_dropdowns | 0.84 | 0.07 | -91.67% | +5% | PASS | 5 | 5 |
| startup.create_ui_grids | 79.87 | 24.02 | -69.93% | +5% | PASS | 5 | 5 |
| sort.cumulative (apply_combined) | 3208.06 | 1657.17 | -48.34% | +10% | PASS | 5 | 5 |
| sort.confidence (apply_combined) | 5707.03 | 1805.00 | -68.37% | +10% | PASS | 5 | 5 |
| sort.counter/resistance (apply_combined) | 3877.05 | 4965.13 | +28.06% | +10% | FAIL | 5 | 5 |
| sort.strategic (strategic.sort.end_to_end) | 15595.67 | 18143.06 | +16.33% | +10% | FAIL | 5 | 5 |
## Interpretation

- Gate outcome: FAIL (2 span(s) exceeded thresholds).
- Stable spans: 6 span(s) currently pass regression gates.
- Confidence: Moderate until a controlled 5x5 baseline/new capture is completed.


## Gate Rules

1. Startup median regression must be <= 5%.
2. Generate/sort median regression must be <= 10%.
3. No critical span may regress > 15% without written rationale.

## Run Metadata

- Generated at: 2026-03-24 10:18:52
- Log directory: docs\validation
- Selection mode: explicit globs (perf_capture_phasebc15_eval/baseline_*.log) vs (perf_capture_phasebc16s13_eval/baseline_*.log)
- Baseline files: baseline_01.log, baseline_02.log, baseline_03.log, baseline_04.log, baseline_05.log
- New files: baseline_01_perf_20260324_100707_029810.log, baseline_02_perf_20260324_100854_532745.log, baseline_03_perf_20260324_101057_608103.log, baseline_04_perf_20260324_101334_469306.log, baseline_05_perf_20260324_101547_942398.log
