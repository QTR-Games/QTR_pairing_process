# Performance Summary

## Status

Generated from existing PerfTimer logs using:
- Selection mode: explicit globs (baseline_*.log) vs (phasebc10_[0-9][0-9]_*.log)
- Baseline logs: 5 files
- New logs: 5 files
- Minimum samples required: startup=5, sort=5
- Observed failures against current thresholds: 6 span(s)

## Comparison Table

| Span | Baseline Median (ms) | New Median (ms) | Delta % | Threshold | Status | Baseline N | New N |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| startup.select_database | 3.00 | 7.76 | +158.67% | +5% | FAIL | 5 | 5 |
| startup.initialize_ui_vars | 509.95 | 882.31 | +73.02% | +5% | FAIL | 5 | 5 |
| startup.populate_dropdowns | 0.71 | 1.05 | +47.89% | +5% | FAIL | 5 | 5 |
| startup.create_ui_grids | 42.60 | 57.52 | +35.02% | +5% | FAIL | 5 | 5 |
| sort.cumulative (apply_combined) | 3537.57 | 3903.63 | +10.35% | +10% | WARN | 5 | 5 |
| sort.confidence (apply_combined) | 6847.13 | 8011.48 | +17.00% | +10% | FAIL | 5 | 5 |
| sort.counter/resistance (apply_combined) | 4343.59 | 5801.94 | +33.57% | +10% | FAIL | 5 | 5 |
| sort.strategic (strategic.sort.end_to_end) | 18375.35 | 20040.10 | +9.06% | +10% | PASS | 5 | 5 |
## Interpretation

- Gate outcome: FAIL (6 span(s) exceeded thresholds).
- Stable spans: 1 span(s) currently pass regression gates.
- Confidence: Moderate until a controlled 5x5 baseline/new capture is completed.


## Gate Rules

1. Startup median regression must be <= 5%.
2. Generate/sort median regression must be <= 10%.
3. No critical span may regress > 15% without written rationale.

## Run Metadata

- Generated at: 2026-03-20 17:15:46
- Log directory: docs\validation\perf_capture
- Selection mode: explicit globs (baseline_*.log) vs (phasebc10_[0-9][0-9]_*.log)
- Baseline files: baseline_01_perf_20260319_171542_388395.log, baseline_02_perf_20260319_171631_963994.log, baseline_03_perf_20260319_171733_100797.log, baseline_04_perf_20260319_171818_392657.log, baseline_05_perf_20260319_171910_077595.log
- New files: phasebc10_01_perf_20260320_170259_271192.log, phasebc10_02_perf_20260320_170530_493884.log, phasebc10_03_perf_20260320_170832_725892.log, phasebc10_04_perf_20260320_171052_474936.log, phasebc10_05_perf_20260320_171316_991936.log
