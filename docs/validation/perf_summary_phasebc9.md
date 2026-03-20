# Performance Summary

## Status

Generated from existing PerfTimer logs using:
- Selection mode: explicit globs (baseline_*.log) vs (phasebc9_[0-9][0-9]_*.log)
- Baseline logs: 5 files
- New logs: 5 files
- Minimum samples required: startup=5, sort=5
- Observed failures against current thresholds: 4 span(s)

## Comparison Table

| Span | Baseline Median (ms) | New Median (ms) | Delta % | Threshold | Status | Baseline N | New N |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| startup.select_database | 3.00 | 4.01 | +33.67% | +5% | FAIL | 5 | 5 |
| startup.initialize_ui_vars | 509.95 | 1009.53 | +97.97% | +5% | FAIL | 5 | 5 |
| startup.populate_dropdowns | 0.71 | 0.95 | +33.80% | +5% | FAIL | 5 | 5 |
| startup.create_ui_grids | 42.60 | 51.90 | +21.83% | +5% | FAIL | 5 | 5 |
| sort.cumulative (apply_combined) | 3537.57 | 3866.17 | +9.29% | +10% | PASS | 5 | 5 |
| sort.confidence (apply_combined) | 6847.13 | 7413.91 | +8.28% | +10% | PASS | 5 | 5 |
| sort.counter/resistance (apply_combined) | 4343.59 | 4777.58 | +9.99% | +10% | PASS | 5 | 5 |
| sort.strategic (strategic.sort.end_to_end) | 18375.35 | 17348.25 | -5.59% | +10% | PASS | 5 | 5 |
## Interpretation

- Gate outcome: FAIL (4 span(s) exceeded thresholds).
- Stable spans: 4 span(s) currently pass regression gates.
- Confidence: Moderate until a controlled 5x5 baseline/new capture is completed.


## Gate Rules

1. Startup median regression must be <= 5%.
2. Generate/sort median regression must be <= 10%.
3. No critical span may regress > 15% without written rationale.

## Run Metadata

- Generated at: 2026-03-20 16:51:40
- Log directory: docs\validation\perf_capture
- Selection mode: explicit globs (baseline_*.log) vs (phasebc9_[0-9][0-9]_*.log)
- Baseline files: baseline_01_perf_20260319_171542_388395.log, baseline_02_perf_20260319_171631_963994.log, baseline_03_perf_20260319_171733_100797.log, baseline_04_perf_20260319_171818_392657.log, baseline_05_perf_20260319_171910_077595.log
- New files: phasebc9_01_perf_20260320_163934_803970.log, phasebc9_02_perf_20260320_164201_860887.log, phasebc9_03_perf_20260320_164415_046832.log, phasebc9_04_perf_20260320_164623_528017.log, phasebc9_05_perf_20260320_164839_643554.log
