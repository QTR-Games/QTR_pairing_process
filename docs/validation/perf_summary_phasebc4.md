# Performance Summary

## Status

Generated from existing PerfTimer logs using:
- Selection mode: explicit globs (baseline_*.log) vs (phasebc4_[0-9][0-9]_*.log)
- Baseline logs: 5 files
- New logs: 5 files
- Minimum samples required: startup=5, sort=5
- Observed failures against current thresholds: 8 span(s)

## Comparison Table

| Span | Baseline Median (ms) | New Median (ms) | Delta % | Threshold | Status | Baseline N | New N |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| startup.select_database | 3.00 | 6.39 | +113.00% | +5% | FAIL | 5 | 5 |
| startup.initialize_ui_vars | 509.95 | 1180.79 | +131.55% | +5% | FAIL | 5 | 5 |
| startup.populate_dropdowns | 0.71 | 1.37 | +92.96% | +5% | FAIL | 5 | 5 |
| startup.create_ui_grids | 42.60 | 57.74 | +35.54% | +5% | FAIL | 5 | 5 |
| sort.cumulative (apply_combined) | 3537.57 | 4545.77 | +28.50% | +10% | FAIL | 5 | 5 |
| sort.confidence (apply_combined) | 6847.13 | 13395.81 | +95.64% | +10% | FAIL | 5 | 5 |
| sort.counter/resistance (apply_combined) | 4343.59 | 6187.85 | +42.46% | +10% | FAIL | 5 | 5 |
| sort.strategic (strategic.sort.end_to_end) | 18375.35 | 27608.04 | +50.24% | +10% | FAIL | 5 | 5 |
## Interpretation

- Gate outcome: FAIL (8 span(s) exceeded thresholds).
- Confidence: Moderate until a controlled 5x5 baseline/new capture is completed.


## Gate Rules

1. Startup median regression must be <= 5%.
2. Generate/sort median regression must be <= 10%.
3. No critical span may regress > 15% without written rationale.

## Run Metadata

- Generated at: 2026-03-20 14:48:10
- Log directory: docs\validation\perf_capture
- Selection mode: explicit globs (baseline_*.log) vs (phasebc4_[0-9][0-9]_*.log)
- Baseline files: baseline_01_perf_20260319_171542_388395.log, baseline_02_perf_20260319_171631_963994.log, baseline_03_perf_20260319_171733_100797.log, baseline_04_perf_20260319_171818_392657.log, baseline_05_perf_20260319_171910_077595.log
- New files: phasebc4_01_perf_20260320_143046_030946.log, phasebc4_02_perf_20260320_143405_050220.log, phasebc4_03_perf_20260320_143719_227352.log, phasebc4_04_perf_20260320_144007_083312.log, phasebc4_05_perf_20260320_144301_281663.log
