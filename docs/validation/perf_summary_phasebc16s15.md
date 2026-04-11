# Performance Summary

## Status

Generated from existing PerfTimer logs using:
- Selection mode: explicit globs (perf_capture_phasebc15_eval/baseline_*.log) vs (perf_capture_phasebc16s15_eval/baseline_*.log)
- Baseline logs: 5 files
- New logs: 5 files
- Minimum samples required: startup=5, sort=5
- Observed failures against current thresholds: 2 span(s)

## Comparison Table

| Span | Baseline Median (ms) | New Median (ms) | Delta % | Threshold | Status | Baseline N | New N |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| startup.select_database | 3.26 | 3.01 | -7.67% | +5% | PASS | 5 | 5 |
| startup.initialize_ui_vars | 685.95 | 601.27 | -12.34% | +5% | PASS | 5 | 5 |
| startup.populate_dropdowns | 0.84 | 0.07 | -91.67% | +5% | PASS | 5 | 5 |
| startup.create_ui_grids | 79.87 | 47.00 | -41.15% | +5% | PASS | 5 | 5 |
| sort.cumulative (apply_combined) | 3208.06 | 1706.98 | -46.79% | +10% | PASS | 5 | 5 |
| sort.confidence (apply_combined) | 5707.03 | 1768.51 | -69.01% | +10% | PASS | 5 | 5 |
| sort.counter/resistance (apply_combined) | 3877.05 | 5862.46 | +51.21% | +10% | FAIL | 5 | 5 |
| sort.strategic (strategic.sort.end_to_end) | 15595.67 | 22214.64 | +42.44% | +10% | FAIL | 5 | 5 |
## Interpretation

- Gate outcome: FAIL (2 span(s) exceeded thresholds).
- Stable spans: 6 span(s) currently pass regression gates.
- Confidence: Moderate until a controlled 5x5 baseline/new capture is completed.


## Gate Rules

1. Startup median regression must be <= 5%.
2. Generate/sort median regression must be <= 10%.
3. No critical span may regress > 15% without written rationale.

## Run Metadata

- Generated at: 2026-03-24 10:49:18
- Log directory: docs\validation
- Selection mode: explicit globs (perf_capture_phasebc15_eval/baseline_*.log) vs (perf_capture_phasebc16s15_eval/baseline_*.log)
- Baseline files: baseline_01.log, baseline_02.log, baseline_03.log, baseline_04.log, baseline_05.log
- New files: baseline_01_perf_20260324_103616_257511.log, baseline_02_perf_20260324_103856_526294.log, baseline_03_perf_20260324_104135_694262.log, baseline_04_perf_20260324_104352_729035.log, baseline_05_perf_20260324_104613_674927.log
