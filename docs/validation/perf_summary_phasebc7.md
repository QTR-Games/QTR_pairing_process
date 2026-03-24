# Performance Summary

## Status

Generated from existing PerfTimer logs using:
- Selection mode: explicit globs (baseline_*.log) vs (phasebc7_[0-9][0-9]_*.log)
- Baseline logs: 5 files
- New logs: 5 files
- Minimum samples required: startup=5, sort=5
- Observed failures against current thresholds: 8 span(s)

## Comparison Table

| Span | Baseline Median (ms) | New Median (ms) | Delta % | Threshold | Status | Baseline N | New N |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| startup.select_database | 3.00 | 6.34 | +111.33% | +5% | FAIL | 5 | 5 |
| startup.initialize_ui_vars | 509.95 | 1256.74 | +146.44% | +5% | FAIL | 5 | 5 |
| startup.populate_dropdowns | 0.71 | 1.31 | +84.51% | +5% | FAIL | 5 | 5 |
| startup.create_ui_grids | 42.60 | 52.22 | +22.58% | +5% | FAIL | 5 | 5 |
| sort.cumulative (apply_combined) | 3537.57 | 5078.92 | +43.57% | +10% | FAIL | 5 | 5 |
| sort.confidence (apply_combined) | 6847.13 | 11905.86 | +73.88% | +10% | FAIL | 5 | 5 |
| sort.counter/resistance (apply_combined) | 4343.59 | 8414.25 | +93.72% | +10% | FAIL | 5 | 5 |
| sort.strategic (strategic.sort.end_to_end) | 18375.35 | 26096.00 | +42.02% | +10% | FAIL | 5 | 5 |
## Interpretation

- Gate outcome: FAIL (8 span(s) exceeded thresholds).
- Confidence: Moderate until a controlled 5x5 baseline/new capture is completed.


## Gate Rules

1. Startup median regression must be <= 5%.
2. Generate/sort median regression must be <= 10%.
3. No critical span may regress > 15% without written rationale.

## Run Metadata

- Generated at: 2026-03-20 16:11:02
- Log directory: docs\validation\perf_capture
- Selection mode: explicit globs (baseline_*.log) vs (phasebc7_[0-9][0-9]_*.log)
- Baseline files: baseline_01_perf_20260319_171542_388395.log, baseline_02_perf_20260319_171631_963994.log, baseline_03_perf_20260319_171733_100797.log, baseline_04_perf_20260319_171818_392657.log, baseline_05_perf_20260319_171910_077595.log
- New files: phasebc7_01_perf_20260320_155524_168963.log, phasebc7_02_perf_20260320_155826_785442.log, phasebc7_03_perf_20260320_160145_161767.log, phasebc7_04_perf_20260320_160436_169538.log, phasebc7_05_perf_20260320_160736_568905.log
