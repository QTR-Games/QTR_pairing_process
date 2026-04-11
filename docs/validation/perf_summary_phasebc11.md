# Performance Summary

## Status

Generated from existing PerfTimer logs using:
- Selection mode: explicit globs (phasebc10_0[1-5]_perf_20260320_17*.log) vs (phasebc11_0[1-5]_perf_20260320_17[4-5]*.log)
- Baseline logs: 5 files
- New logs: 5 files
- Minimum samples required: startup=5, sort=5
- Observed failures against current thresholds: 1 span(s)

## Comparison Table

| Span | Baseline Median (ms) | New Median (ms) | Delta % | Threshold | Status | Baseline N | New N |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| startup.select_database | 7.76 | 3.26 | -57.99% | +5% | PASS | 5 | 5 |
| startup.initialize_ui_vars | 882.31 | 685.95 | -22.26% | +5% | PASS | 5 | 5 |
| startup.populate_dropdowns | 1.05 | 0.84 | -20.00% | +5% | PASS | 5 | 5 |
| startup.create_ui_grids | 57.52 | 79.87 | +38.86% | +5% | FAIL | 5 | 5 |
| sort.cumulative (apply_combined) | 3903.63 | 3208.06 | -17.82% | +10% | PASS | 5 | 5 |
| sort.confidence (apply_combined) | 8011.48 | 5707.03 | -28.76% | +10% | PASS | 5 | 5 |
| sort.counter/resistance (apply_combined) | 5801.94 | 3877.05 | -33.18% | +10% | PASS | 5 | 5 |
| sort.strategic (strategic.sort.end_to_end) | 20040.10 | 15595.67 | -22.18% | +10% | PASS | 5 | 5 |
## Interpretation

- Gate outcome: FAIL (1 span(s) exceeded thresholds).
- Stable spans: 7 span(s) currently pass regression gates.
- Confidence: Moderate until a controlled 5x5 baseline/new capture is completed.


## Gate Rules

1. Startup median regression must be <= 5%.
2. Generate/sort median regression must be <= 10%.
3. No critical span may regress > 15% without written rationale.

## Run Metadata

- Generated at: 2026-03-20 17:52:42
- Log directory: docs\validation\perf_capture
- Selection mode: explicit globs (phasebc10_0[1-5]_perf_20260320_17*.log) vs (phasebc11_0[1-5]_perf_20260320_17[4-5]*.log)
- Baseline files: phasebc10_01_perf_20260320_170259_271192.log, phasebc10_02_perf_20260320_170530_493884.log, phasebc10_03_perf_20260320_170832_725892.log, phasebc10_04_perf_20260320_171052_474936.log, phasebc10_05_perf_20260320_171316_991936.log
- New files: phasebc11_01_perf_20260320_174150_821981.log, phasebc11_02_perf_20260320_174348_163481.log, phasebc11_03_perf_20260320_174551_553308.log, phasebc11_04_perf_20260320_174751_009492.log, phasebc11_05_perf_20260320_175000_140995.log
