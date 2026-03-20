# Performance Summary

## Status

Generated from existing PerfTimer logs using:
- Selection mode: explicit globs (baseline_*.log) vs (phasebc2_*.log)
- Baseline logs: 5 files
- New logs: 5 files
- Minimum samples required: startup=5, sort=5
- Observed failures against current thresholds: 8 span(s)

## Comparison Table

| Span | Baseline Median (ms) | New Median (ms) | Delta % | Threshold | Status | Baseline N | New N |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| startup.select_database | 3.00 | 10.56 | +252.00% | +5% | FAIL | 5 | 5 |
| startup.initialize_ui_vars | 509.95 | 1611.77 | +216.06% | +5% | FAIL | 5 | 5 |
| startup.populate_dropdowns | 0.71 | 1.43 | +101.41% | +5% | FAIL | 5 | 5 |
| startup.create_ui_grids | 42.60 | 93.17 | +118.71% | +5% | FAIL | 5 | 5 |
| sort.cumulative (apply_combined) | 3537.57 | 4302.53 | +21.62% | +10% | FAIL | 5 | 5 |
| sort.confidence (apply_combined) | 6847.13 | 9862.73 | +44.04% | +10% | FAIL | 5 | 5 |
| sort.counter/resistance (apply_combined) | 4343.59 | 5666.31 | +30.45% | +10% | FAIL | 5 | 5 |
| sort.strategic (strategic.sort.end_to_end) | 18375.35 | 25675.94 | +39.73% | +10% | FAIL | 5 | 5 |
## Interpretation

- Gate outcome: FAIL (8 span(s) exceeded thresholds).
- Confidence: Moderate until a controlled 5x5 baseline/new capture is completed.


## Gate Rules

1. Startup median regression must be <= 5%.
2. Generate/sort median regression must be <= 10%.
3. No critical span may regress > 15% without written rationale.

## Run Metadata

- Generated at: 2026-03-20 11:09:41
- Log directory: docs\validation\perf_capture_phasebc2_5x5
- Selection mode: explicit globs (baseline_*.log) vs (phasebc2_*.log)
- Baseline files: baseline_01_perf_20260319_171542_388395.log, baseline_02_perf_20260319_171631_963994.log, baseline_03_perf_20260319_171733_100797.log, baseline_04_perf_20260319_171818_392657.log, baseline_05_perf_20260319_171910_077595.log
- New files: phasebc2_01_perf_20260320_105437_599570.log, phasebc2_02_perf_20260320_105655_696048.log, phasebc2_03_perf_20260320_105914_633403.log, phasebc2_04_perf_20260320_110209_800082.log, phasebc2_05_perf_20260320_110514_446200.log
