# Performance Summary

## Status

Generated from existing PerfTimer logs using:
- Selection mode: explicit globs (baseline_*.log) vs (phasebc3_*.log)
- Baseline logs: 5 files
- New logs: 5 files
- Minimum samples required: startup=5, sort=5
- Observed failures against current thresholds: 4 span(s)

## Comparison Table

| Span | Baseline Median (ms) | New Median (ms) | Delta % | Threshold | Status | Baseline N | New N |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| startup.select_database | 3.00 | 5.91 | +97.00% | +5% | FAIL | 5 | 5 |
| startup.initialize_ui_vars | 509.95 | 941.46 | +84.62% | +5% | FAIL | 5 | 5 |
| startup.populate_dropdowns | 0.71 | 1.28 | +80.28% | +5% | FAIL | 5 | 5 |
| startup.create_ui_grids | 42.60 | 49.06 | +15.16% | +5% | FAIL | 5 | 5 |
| sort.cumulative (apply_combined) | 3537.57 | 4057.41 | +14.69% | +10% | WARN | 5 | 5 |
| sort.confidence (apply_combined) | 6847.13 | 7152.25 | +4.46% | +10% | PASS | 5 | 5 |
| sort.counter/resistance (apply_combined) | 4343.59 | 4801.75 | +10.55% | +10% | WARN | 5 | 5 |
| sort.strategic (strategic.sort.end_to_end) | 18375.35 | 17648.29 | -3.96% | +10% | PASS | 5 | 5 |
## Interpretation

- Gate outcome: FAIL (4 span(s) exceeded thresholds).
- Stable spans: 2 span(s) currently pass regression gates.
- Confidence: Moderate until a controlled 5x5 baseline/new capture is completed.


## Gate Rules

1. Startup median regression must be <= 5%.
2. Generate/sort median regression must be <= 10%.
3. No critical span may regress > 15% without written rationale.

## Run Metadata

- Generated at: 2026-03-20 12:40:15
- Log directory: docs\validation\perf_capture_phasebc3_5x5
- Selection mode: explicit globs (baseline_*.log) vs (phasebc3_*.log)
- Baseline files: baseline_01_perf_20260319_171542_388395.log, baseline_02_perf_20260319_171631_963994.log, baseline_03_perf_20260319_171733_100797.log, baseline_04_perf_20260319_171818_392657.log, baseline_05_perf_20260319_171910_077595.log
- New files: phasebc3_01_perf_20260320_111422_539244.log, phasebc3_02_perf_20260320_111710_283422.log, phasebc3_03_perf_20260320_111950_933210.log, phasebc3_04_perf_20260320_112206_372957.log, phasebc3_05_perf_20260320_112412_605763.log
