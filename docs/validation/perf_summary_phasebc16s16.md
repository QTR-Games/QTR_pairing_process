# Performance Summary

## Status

Generated from existing PerfTimer logs using:
- Selection mode: explicit globs (perf_capture_phasebc15_eval/baseline_*.log) vs (perf_capture_phasebc16s16_eval/baseline_*.log)
- Baseline logs: 5 files
- New logs: 5 files
- Minimum samples required: startup=5, sort=5
- Observed failures against current thresholds: 1 span(s)

## Comparison Table

| Span | Baseline Median (ms) | New Median (ms) | Delta % | Threshold | Status | Baseline N | New N |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| startup.select_database | 3.26 | 3.18 | -2.45% | +5% | PASS | 5 | 5 |
| startup.initialize_ui_vars | 685.95 | 441.16 | -35.69% | +5% | PASS | 5 | 5 |
| startup.populate_dropdowns | 0.84 | 0.08 | -90.48% | +5% | PASS | 5 | 5 |
| startup.create_ui_grids | 79.87 | 79.33 | -0.68% | +5% | PASS | 5 | 5 |
| sort.cumulative (apply_combined) | 3208.06 | 1123.37 | -64.98% | +10% | PASS | 5 | 5 |
| sort.confidence (apply_combined) | 5707.03 | 1098.27 | -80.76% | +10% | PASS | 5 | 5 |
| sort.counter/resistance (apply_combined) | 3877.05 | 3437.43 | -11.34% | +10% | PASS | 5 | 5 |
| sort.strategic (strategic.sort.end_to_end) | 15595.67 | 20772.90 | +33.20% | +10% | FAIL | 5 | 5 |
## Interpretation

- Gate outcome: FAIL (1 span(s) exceeded thresholds).
- Stable spans: 7 span(s) currently pass regression gates.
- Confidence: Moderate until a controlled 5x5 baseline/new capture is completed.


## Gate Rules

1. Startup median regression must be <= 5%.
2. Generate/sort median regression must be <= 10%.
3. No critical span may regress > 15% without written rationale.

## Run Metadata

- Generated at: 2026-03-24 11:09:32
- Log directory: docs\validation
- Selection mode: explicit globs (perf_capture_phasebc15_eval/baseline_*.log) vs (perf_capture_phasebc16s16_eval/baseline_*.log)
- Baseline files: baseline_01.log, baseline_02.log, baseline_03.log, baseline_04.log, baseline_05.log
- New files: baseline_01_perf_20260324_105936_572608.log, baseline_02_perf_20260324_110113_520397.log, baseline_03_perf_20260324_110301_721769.log, baseline_04_perf_20260324_110457_462452.log, baseline_05_perf_20260324_110708_460085.log
