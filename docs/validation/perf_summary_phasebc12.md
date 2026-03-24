# Performance Summary

## Status

Generated from existing PerfTimer logs using:
- Selection mode: explicit globs (phasebc11_0[1-5]_perf_20260320_17[4-5]*.log) vs (phasebc12_0[1-5]_perf_20260320_1[78]*.log)
- Baseline logs: 5 files
- New logs: 5 files
- Minimum samples required: startup=5, sort=5
- Observed failures against current thresholds: 2 span(s)

## Comparison Table

| Span | Baseline Median (ms) | New Median (ms) | Delta % | Threshold | Status | Baseline N | New N |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| startup.select_database | 3.26 | 5.04 | +54.60% | +5% | FAIL | 5 | 5 |
| startup.initialize_ui_vars | 685.95 | 678.87 | -1.03% | +5% | PASS | 5 | 5 |
| startup.populate_dropdowns | 0.84 | 1.12 | +33.33% | +5% | FAIL | 5 | 5 |
| startup.create_ui_grids | 79.87 | 83.98 | +5.15% | +5% | WARN | 5 | 5 |
| sort.cumulative (apply_combined) | 3208.06 | 3165.89 | -1.31% | +10% | PASS | 5 | 5 |
| sort.confidence (apply_combined) | 5707.03 | 5663.17 | -0.77% | +10% | PASS | 5 | 5 |
| sort.counter/resistance (apply_combined) | 3877.05 | 3974.02 | +2.50% | +10% | PASS | 5 | 5 |
| sort.strategic (strategic.sort.end_to_end) | 15595.67 | 15410.09 | -1.19% | +10% | PASS | 5 | 5 |
## Interpretation

- Gate outcome: FAIL (2 span(s) exceeded thresholds).
- Stable spans: 5 span(s) currently pass regression gates.
- Confidence: Moderate until a controlled 5x5 baseline/new capture is completed.


## Gate Rules

1. Startup median regression must be <= 5%.
2. Generate/sort median regression must be <= 10%.
3. No critical span may regress > 15% without written rationale.

## Run Metadata

- Generated at: 2026-03-20 18:05:28
- Log directory: docs\validation\perf_capture
- Selection mode: explicit globs (phasebc11_0[1-5]_perf_20260320_17[4-5]*.log) vs (phasebc12_0[1-5]_perf_20260320_1[78]*.log)
- Baseline files: phasebc11_01_perf_20260320_174150_821981.log, phasebc11_02_perf_20260320_174348_163481.log, phasebc11_03_perf_20260320_174551_553308.log, phasebc11_04_perf_20260320_174751_009492.log, phasebc11_05_perf_20260320_175000_140995.log
- New files: phasebc12_01_perf_20260320_175450_556873.log, phasebc12_02_perf_20260320_175703_942788.log, phasebc12_03_perf_20260320_175901_856456.log, phasebc12_04_perf_20260320_180058_406955.log, phasebc12_05_perf_20260320_180255_232681.log
