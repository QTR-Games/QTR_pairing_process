# Performance Summary

## Status

Generated from existing PerfTimer logs using:
- Selection mode: explicit globs (perf_capture_phasebc15_eval/baseline_*.log) vs (perf_capture_phasebc16s17_eval/baseline_*.log)
- Baseline logs: 5 files
- New logs: 5 files
- Minimum samples required: startup=5, sort=5
- Observed failures against current thresholds: 1 span(s)

## Comparison Table

| Span | Baseline Median (ms) | New Median (ms) | Delta % | Threshold | Status | Baseline N | New N |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| startup.select_database | 3.26 | 3.93 | +20.55% | +5% | FAIL | 5 | 5 |
| startup.initialize_ui_vars | 685.95 | 550.13 | -19.80% | +5% | PASS | 5 | 5 |
| startup.populate_dropdowns | 0.84 | 0.10 | -88.10% | +5% | PASS | 5 | 5 |
| startup.create_ui_grids | 79.87 | 38.88 | -51.32% | +5% | PASS | 5 | 5 |
| sort.cumulative (apply_combined) | 3208.06 | 1478.95 | -53.90% | +10% | PASS | 5 | 5 |
| sort.confidence (apply_combined) | 5707.03 | 1097.26 | -80.77% | +10% | PASS | 5 | 5 |
| sort.counter/resistance (apply_combined) | 3877.05 | 3952.36 | +1.94% | +10% | PASS | 5 | 5 |
| sort.strategic (strategic.sort.end_to_end) | 15595.67 | 15071.96 | -3.36% | +10% | PASS | 5 | 5 |
## Interpretation

- Gate outcome: FAIL (1 span(s) exceeded thresholds).
- Stable spans: 7 span(s) currently pass regression gates.
- Confidence: Moderate until a controlled 5x5 baseline/new capture is completed.


## Gate Rules

1. Startup median regression must be <= 5%.
2. Generate/sort median regression must be <= 10%.
3. No critical span may regress > 15% without written rationale.

## Run Metadata

- Generated at: 2026-03-24 11:21:25
- Log directory: docs\validation
- Selection mode: explicit globs (perf_capture_phasebc15_eval/baseline_*.log) vs (perf_capture_phasebc16s17_eval/baseline_*.log)
- Baseline files: baseline_01.log, baseline_02.log, baseline_03.log, baseline_04.log, baseline_05.log
- New files: baseline_01_perf_20260324_111029_829534.log, baseline_02_perf_20260324_111222_483569.log, baseline_03_perf_20260324_111428_081990.log, baseline_04_perf_20260324_111633_073784.log, baseline_05_perf_20260324_111843_714744.log
