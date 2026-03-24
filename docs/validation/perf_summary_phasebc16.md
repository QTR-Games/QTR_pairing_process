# Performance Summary

## Status

Generated from existing PerfTimer logs using:
- Selection mode: explicit globs (baseline_*.log) vs (new_*.log)
- Baseline logs: 5 files
- New logs: 5 files
- Minimum samples required: startup=5, sort=5
- Sample gate shortfall: 4 span(s) below minimum sample requirements
- Observed failures against current thresholds: 2 span(s)

## Comparison Table

| Span | Baseline Median (ms) | New Median (ms) | Delta % | Threshold | Status | Baseline N | New N |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| startup.select_database | 5.98 | 3.92 | -34.45% | +5% | PASS | 5 | 5 |
| startup.initialize_ui_vars | 580.96 | 663.60 | +14.22% | +5% | WARN | 5 | 5 |
| startup.populate_dropdowns | 1.11 | 1.97 | +77.48% | +5% | FAIL | 5 | 5 |
| startup.create_ui_grids | 115.82 | 179.69 | +55.15% | +5% | FAIL | 5 | 5 |
| sort.cumulative (apply_combined) | 2899.76 | 4677.61 | +61.31% | +10% | INSUFFICIENT_SAMPLES | 5 | 4 |
| sort.confidence (apply_combined) | 5133.04 | 9515.54 | +85.38% | +10% | INSUFFICIENT_SAMPLES | 5 | 4 |
| sort.counter/resistance (apply_combined) | 3295.32 | 5777.90 | +75.34% | +10% | INSUFFICIENT_SAMPLES | 5 | 4 |
| sort.strategic (strategic.sort.end_to_end) | 14031.97 | 22787.21 | +62.39% | +10% | INSUFFICIENT_SAMPLES | 5 | 4 |
## Interpretation

- Gate outcome: FAIL (2 span(s) exceeded thresholds).
- Sample gate: 4 span(s) below minimum sample requirements (startup=5, sort=5).
- Stable spans: 1 span(s) currently pass regression gates.
- Confidence: Moderate until a controlled 5x5 baseline/new capture is completed.


## Gate Rules

1. Startup median regression must be <= 5%.
2. Generate/sort median regression must be <= 10%.
3. No critical span may regress > 15% without written rationale.

## Run Metadata

- Generated at: 2026-03-23 11:16:18
- Log directory: docs\validation\perf_capture_phasebc16_eval
- Selection mode: explicit globs (baseline_*.log) vs (new_*.log)
- Baseline files: baseline_01.log, baseline_02.log, baseline_03.log, baseline_04.log, baseline_05.log
- New files: new_01.log, new_02.log, new_03.log, new_04.log, new_05.log
