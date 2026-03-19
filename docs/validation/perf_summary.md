# Performance Summary

## Status

Generated from existing PerfTimer logs using:
- Selection mode: explicit globs (perf_20260318_*.log) vs (perf_20260319_*.log)
- Baseline logs: 5 files
- New logs: 5 files
- Provisional: 4 span(s) have no sample in one or both windows
- Observed failures against current thresholds: 4 span(s)

## Comparison Table

| Span | Baseline Median (ms) | New Median (ms) | Delta % | Threshold | Status | Baseline N | New N |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| startup.select_database | 2.67 | 3.59 | +34.46% | +5% | FAIL | 4 | 4 |
| startup.initialize_ui_vars | 87.78 | 606.87 | +591.31% | +5% | FAIL | 4 | 4 |
| startup.populate_dropdowns | 452.35 | 2095.26 | +363.20% | +5% | FAIL | 4 | 4 |
| startup.create_ui_grids | 8.81 | 18.98 | +115.38% | +5% | FAIL | 4 | 4 |
| sort.cumulative (apply_combined) | - | - | - | +10% | PENDING | 0 | 0 |
| sort.confidence (apply_combined) | - | - | - | +10% | PENDING | 0 | 0 |
| sort.counter/resistance (apply_combined) | - | - | - | +10% | PENDING | 0 | 0 |
| sort.strategic (strategic.sort.end_to_end) | 21067.68 | - | - | +10% | PENDING | 3 | 0 |

## Gate Rules

1. Startup median regression must be <= 5%.
2. Generate/sort median regression must be <= 10%.
3. No critical span may regress > 15% without written rationale.

## Run Metadata

- Generated at: 2026-03-19 16:42:25
- Log directory: perf_logs
- Selection mode: explicit globs (perf_20260318_*.log) vs (perf_20260319_*.log)
- Baseline files: perf_20260318_120433_882811.log, perf_20260318_121407_662732.log, perf_20260318_122358_605699.log, perf_20260318_142422_441911.log, perf_20260318_143022_945965.log
- New files: perf_20260319_151213_796903.log, perf_20260319_152340_318346.log, perf_20260319_154414_602948.log, perf_20260319_155622_186351.log, perf_20260319_163706_134533.log
