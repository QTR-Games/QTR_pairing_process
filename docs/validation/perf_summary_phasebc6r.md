# Performance Summary

## Status

Generated from existing PerfTimer logs using:
- Selection mode: explicit globs (baseline_*.log) vs (phasebc6r_[0-9][0-9]_*.log)
- Baseline logs: 5 files
- New logs: 5 files
- Minimum samples required: startup=5, sort=5
- Observed failures against current thresholds: 8 span(s)

## Comparison Table

| Span | Baseline Median (ms) | New Median (ms) | Delta % | Threshold | Status | Baseline N | New N |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| startup.select_database | 3.00 | 8.57 | +185.67% | +5% | FAIL | 5 | 5 |
| startup.initialize_ui_vars | 509.95 | 1368.50 | +168.36% | +5% | FAIL | 5 | 5 |
| startup.populate_dropdowns | 0.71 | 1.43 | +101.41% | +5% | FAIL | 5 | 5 |
| startup.create_ui_grids | 42.60 | 87.94 | +106.43% | +5% | FAIL | 5 | 5 |
| sort.cumulative (apply_combined) | 3537.57 | 4703.22 | +32.95% | +10% | FAIL | 5 | 5 |
| sort.confidence (apply_combined) | 6847.13 | 9508.37 | +38.87% | +10% | FAIL | 5 | 5 |
| sort.counter/resistance (apply_combined) | 4343.59 | 8458.05 | +94.72% | +10% | FAIL | 5 | 5 |
| sort.strategic (strategic.sort.end_to_end) | 18375.35 | 26833.16 | +46.03% | +10% | FAIL | 5 | 5 |
## Interpretation

- Gate outcome: FAIL (8 span(s) exceeded thresholds).
- Confidence: Moderate until a controlled 5x5 baseline/new capture is completed.


## Gate Rules

1. Startup median regression must be <= 5%.
2. Generate/sort median regression must be <= 10%.
3. No critical span may regress > 15% without written rationale.

## Run Metadata

- Generated at: 2026-03-20 15:54:07
- Log directory: docs\validation\perf_capture
- Selection mode: explicit globs (baseline_*.log) vs (phasebc6r_[0-9][0-9]_*.log)
- Baseline files: baseline_01_perf_20260319_171542_388395.log, baseline_02_perf_20260319_171631_963994.log, baseline_03_perf_20260319_171733_100797.log, baseline_04_perf_20260319_171818_392657.log, baseline_05_perf_20260319_171910_077595.log
- New files: phasebc6r_01_perf_20260320_153955_264416.log, phasebc6r_02_perf_20260320_154159_675638.log, phasebc6r_03_perf_20260320_154501_636745.log, phasebc6r_04_perf_20260320_154745_597489.log, phasebc6r_05_perf_20260320_155058_648718.log
