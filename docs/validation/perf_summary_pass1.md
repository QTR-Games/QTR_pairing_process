# Performance Summary

## Status

Generated from existing PerfTimer logs using:
- Selection mode: explicit globs (baseline_*.log) vs (pass1_*.log)
- Baseline logs: 5 files
- New logs: 5 files
- Minimum samples required: startup=5, sort=5
- Sample gate shortfall: 4 span(s) below minimum sample requirements
- Observed failures against current thresholds: 4 span(s)

## Comparison Table

| Span | Baseline Median (ms) | New Median (ms) | Delta % | Threshold | Status | Baseline N | New N |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| startup.select_database | 3.00 | 5.62 | +87.33% | +5% | FAIL | 5 | 5 |
| startup.initialize_ui_vars | 509.95 | 1768.40 | +246.78% | +5% | FAIL | 5 | 5 |
| startup.populate_dropdowns | 0.71 | 1.10 | +54.93% | +5% | FAIL | 5 | 5 |
| startup.create_ui_grids | 42.60 | 72.71 | +70.68% | +5% | FAIL | 5 | 5 |
| sort.cumulative (apply_combined) | 3537.57 | 7179.64 | +102.95% | +10% | INSUFFICIENT_SAMPLES | 5 | 3 |
| sort.confidence (apply_combined) | 6847.13 | 11617.62 | +69.67% | +10% | INSUFFICIENT_SAMPLES | 5 | 3 |
| sort.counter/resistance (apply_combined) | 4343.59 | 8376.13 | +92.84% | +10% | INSUFFICIENT_SAMPLES | 5 | 3 |
| sort.strategic (strategic.sort.end_to_end) | 18375.35 | 29656.07 | +61.39% | +10% | INSUFFICIENT_SAMPLES | 5 | 2 |
## Interpretation

- Gate outcome: FAIL (4 span(s) exceeded thresholds).
- Sample gate: 4 span(s) below minimum sample requirements (startup=5, sort=5).
- Confidence: Moderate until a controlled 5x5 baseline/new capture is completed.


## Gate Rules

1. Startup median regression must be <= 5%.
2. Generate/sort median regression must be <= 10%.
3. No critical span may regress > 15% without written rationale.

## Run Metadata

- Generated at: 2026-03-20 10:09:49
- Log directory: docs\validation\perf_capture_pass1_5x5
- Selection mode: explicit globs (baseline_*.log) vs (pass1_*.log)
- Baseline files: baseline_01_perf_20260319_171542_388395.log, baseline_02_perf_20260319_171631_963994.log, baseline_03_perf_20260319_171733_100797.log, baseline_04_perf_20260319_171818_392657.log, baseline_05_perf_20260319_171910_077595.log
- New files: pass1_01_perf_20260320_092134_131150.log, pass1_02_perf_20260320_092203_482684.log, pass1_03_perf_20260320_092342_136570.log, pass1_04_perf_20260320_092643_211045.log, pass1_05_perf_20260320_093401_755166.log
