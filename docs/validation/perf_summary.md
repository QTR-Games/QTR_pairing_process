# Performance Summary

## Status

Generated from existing PerfTimer logs using:
- Selection mode: explicit globs (baseline_*.log) vs (new_*.log)
- Baseline logs: 5 files
- New logs: 5 files
- Minimum samples required: startup=5, sort=5
- Observed failures against current thresholds: 8 span(s)

## Comparison Table

| Span | Baseline Median (ms) | New Median (ms) | Delta % | Threshold | Status | Baseline N | New N |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| startup.select_database | 3.00 | 6.82 | +127.33% | +5% | FAIL | 5 | 5 |
| startup.initialize_ui_vars | 509.95 | 1174.00 | +130.22% | +5% | FAIL | 5 | 5 |
| startup.populate_dropdowns | 0.71 | 1.21 | +70.42% | +5% | FAIL | 5 | 5 |
| startup.create_ui_grids | 42.60 | 80.02 | +87.84% | +5% | FAIL | 5 | 5 |
| sort.cumulative (apply_combined) | 3537.57 | 4773.22 | +34.93% | +10% | FAIL | 5 | 5 |
| sort.confidence (apply_combined) | 6847.13 | 12190.58 | +78.04% | +10% | FAIL | 5 | 5 |
| sort.counter/resistance (apply_combined) | 4343.59 | 9648.22 | +122.13% | +10% | FAIL | 5 | 5 |
| sort.strategic (strategic.sort.end_to_end) | 18375.35 | 32956.88 | +79.35% | +10% | FAIL | 5 | 5 |
## Interpretation

- Gate outcome: FAIL (8 span(s) exceeded thresholds).
- Confidence: Moderate until a controlled 5x5 baseline/new capture is completed.


## Gate Rules

1. Startup median regression must be <= 5%.
2. Generate/sort median regression must be <= 10%.
3. No critical span may regress > 15% without written rationale.

## Run Metadata

- Generated at: 2026-03-20 08:34:23
- Log directory: docs\validation\perf_capture_5x5
- Selection mode: explicit globs (baseline_*.log) vs (new_*.log)
- Baseline files: baseline_01_perf_20260319_171542_388395.log, baseline_02_perf_20260319_171631_963994.log, baseline_03_perf_20260319_171733_100797.log, baseline_04_perf_20260319_171818_392657.log, baseline_05_perf_20260319_171910_077595.log
- New files: new_01_perf_20260320_082349_520708.log, new_02_perf_20260320_082623_646030.log, new_03_perf_20260320_082755_495512.log, new_04_perf_20260320_082915_894119.log, new_05_perf_20260320_083041_854017.log
