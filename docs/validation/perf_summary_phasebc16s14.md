# Performance Summary

## Status

Generated from existing PerfTimer logs using:
- Selection mode: explicit globs (perf_capture_phasebc15_eval/baseline_*.log) vs (perf_capture_phasebc16s14_eval/baseline_*.log)
- Baseline logs: 5 files
- New logs: 5 files
- Minimum samples required: startup=5, sort=5
- Observed failures against current thresholds: 2 span(s)

## Comparison Table

| Span | Baseline Median (ms) | New Median (ms) | Delta % | Threshold | Status | Baseline N | New N |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| startup.select_database | 3.26 | 1.44 | -55.83% | +5% | PASS | 5 | 5 |
| startup.initialize_ui_vars | 685.95 | 549.03 | -19.96% | +5% | PASS | 5 | 5 |
| startup.populate_dropdowns | 0.84 | 0.17 | -79.76% | +5% | PASS | 5 | 5 |
| startup.create_ui_grids | 79.87 | 53.35 | -33.20% | +5% | PASS | 5 | 5 |
| sort.cumulative (apply_combined) | 3208.06 | 1623.59 | -49.39% | +10% | PASS | 5 | 5 |
| sort.confidence (apply_combined) | 5707.03 | 1477.17 | -74.12% | +10% | PASS | 5 | 5 |
| sort.counter/resistance (apply_combined) | 3877.05 | 5452.89 | +40.65% | +10% | FAIL | 5 | 5 |
| sort.strategic (strategic.sort.end_to_end) | 15595.67 | 23689.11 | +51.90% | +10% | FAIL | 5 | 5 |
## Interpretation

- Gate outcome: FAIL (2 span(s) exceeded thresholds).
- Stable spans: 6 span(s) currently pass regression gates.
- Confidence: Moderate until a controlled 5x5 baseline/new capture is completed.


## Gate Rules

1. Startup median regression must be <= 5%.
2. Generate/sort median regression must be <= 10%.
3. No critical span may regress > 15% without written rationale.

## Run Metadata

- Generated at: 2026-03-24 10:34:33
- Log directory: docs\validation
- Selection mode: explicit globs (perf_capture_phasebc15_eval/baseline_*.log) vs (perf_capture_phasebc16s14_eval/baseline_*.log)
- Baseline files: baseline_01.log, baseline_02.log, baseline_03.log, baseline_04.log, baseline_05.log
- New files: baseline_01_perf_20260324_102127_374381.log, baseline_02_perf_20260324_102420_853742.log, baseline_03_perf_20260324_102707_624946.log, baseline_04_perf_20260324_102925_880796.log, baseline_05_perf_20260324_103138_168702.log
