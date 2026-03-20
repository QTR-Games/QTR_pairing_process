#!/usr/bin/env python3
"""Generate performance comparison artifacts from PerfTimer logs."""

from __future__ import annotations

import argparse
import csv
import re
import statistics
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

LINE_RE = re.compile(r"^\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([0-9]+(?:\.[0-9]+)?)ms(?:\s*\|\s*(.*))?$")
KV_RE = re.compile(r"([A-Za-z0-9_.-]+)=([^\s|]+)")


@dataclass
class Record:
    timestamp: datetime
    label: str
    ms: float
    meta: dict[str, str]


@dataclass
class Metric:
    key: str
    display: str
    threshold_pct: float
    is_critical: bool
    matcher: Callable[[Record], bool]


def parse_line(line: str) -> Optional[Record]:
    match = LINE_RE.match(line.strip())
    if not match:
        return None

    ts_raw, label, ms_raw, meta_raw = match.groups()
    try:
        timestamp = datetime.fromisoformat(ts_raw.strip())
        ms = float(ms_raw)
    except ValueError:
        return None

    meta: dict[str, str] = {}
    if meta_raw:
        for m in KV_RE.finditer(meta_raw):
            meta[m.group(1)] = m.group(2)

    return Record(timestamp=timestamp, label=label.strip(), ms=ms, meta=meta)


def load_records(log_paths: list[Path]) -> list[Record]:
    records: list[Record] = []
    for path in log_paths:
        try:
            for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                rec = parse_line(line)
                if rec:
                    records.append(rec)
        except OSError:
            continue
    return records


def pct_delta(baseline: float, new: float) -> Optional[float]:
    if baseline <= 0:
        return None
    return ((new - baseline) / baseline) * 100.0


def median_or_none(values: list[float]) -> Optional[float]:
    if not values:
        return None
    return float(statistics.median(values))


def status_for_metric(delta: Optional[float], metric: Metric) -> str:
    if delta is None:
        return "PENDING"
    if delta <= metric.threshold_pct:
        return "PASS"
    if metric.is_critical and delta > 15.0:
        return "FAIL"
    if delta <= 15.0:
        return "WARN"
    return "FAIL"


def status_with_sample_gate(
    delta: Optional[float],
    metric: Metric,
    baseline_samples: int,
    new_samples: int,
    min_samples_startup: int,
    min_samples_sort: int,
) -> str:
    min_required = min_samples_startup if metric.key.startswith("startup.") else min_samples_sort
    if baseline_samples < min_required or new_samples < min_required:
        return "INSUFFICIENT_SAMPLES"
    return status_for_metric(delta, metric)


def fmt_ms(value: Optional[float]) -> str:
    return "-" if value is None else f"{value:.2f}"


def fmt_pct(value: Optional[float]) -> str:
    return "-" if value is None else f"{value:+.2f}%"


def build_interpretation(
    rows: list[dict[str, str]],
    min_samples_startup: int,
    min_samples_sort: int,
) -> list[str]:
    fail_rows = [row for row in rows if row["status"] == "FAIL"]
    warn_rows = [row for row in rows if row["status"] == "WARN"]
    insufficient_rows = [row for row in rows if row["status"] == "INSUFFICIENT_SAMPLES"]
    pending_rows = [row for row in rows if row["status"] == "PENDING"]
    pass_rows = [row for row in rows if row["status"] == "PASS"]

    lines = [
        "## Interpretation",
        "",
    ]

    if fail_rows:
        lines.append(f"- Gate outcome: FAIL ({len(fail_rows)} span(s) exceeded thresholds).")
    elif warn_rows:
        lines.append(f"- Gate outcome: WARN ({len(warn_rows)} span(s) in warning band).")
    elif insufficient_rows:
        lines.append("- Gate outcome: INCONCLUSIVE (sample minimum not met).")
    elif pending_rows:
        lines.append("- Gate outcome: INCONCLUSIVE (pending spans without comparable medians).")
    else:
        lines.append("- Gate outcome: PASS (all comparable spans met thresholds).")

    if insufficient_rows:
        lines.append(
            f"- Sample gate: {len(insufficient_rows)} span(s) below minimum sample requirements (startup={min_samples_startup}, sort={min_samples_sort})."
        )

    if pending_rows:
        lines.append(f"- Data completeness: {len(pending_rows)} span(s) are pending due to missing baseline/new medians.")

    if pass_rows:
        lines.append(f"- Stable spans: {len(pass_rows)} span(s) currently pass regression gates.")

    if not fail_rows and not warn_rows and not insufficient_rows and not pending_rows:
        lines.append("- Confidence: High (all tracked spans have sufficient comparable data).")
    else:
        lines.append("- Confidence: Moderate until a controlled 5x5 baseline/new capture is completed.")

    lines.append("")
    return lines


def build_metrics() -> list[Metric]:
    return [
        Metric(
            key="startup.select_database",
            display="startup.select_database",
            threshold_pct=5.0,
            is_critical=True,
            matcher=lambda r: r.label == "startup.select_database",
        ),
        Metric(
            key="startup.initialize_ui_vars",
            display="startup.initialize_ui_vars",
            threshold_pct=5.0,
            is_critical=True,
            matcher=lambda r: r.label == "startup.initialize_ui_vars",
        ),
        Metric(
            key="startup.populate_dropdowns",
            display="startup.populate_dropdowns",
            threshold_pct=5.0,
            is_critical=True,
            matcher=lambda r: r.label == "startup.populate_dropdowns",
        ),
        Metric(
            key="startup.create_ui_grids",
            display="startup.create_ui_grids",
            threshold_pct=5.0,
            is_critical=True,
            matcher=lambda r: r.label == "startup.create_ui_grids",
        ),
        Metric(
            key="sort.cumulative",
            display="sort.cumulative (apply_combined)",
            threshold_pct=10.0,
            is_critical=False,
            matcher=lambda r: r.label == "sort.apply_combined.total" and r.meta.get("primary") == "cumulative",
        ),
        Metric(
            key="sort.confidence",
            display="sort.confidence (apply_combined)",
            threshold_pct=10.0,
            is_critical=False,
            matcher=lambda r: r.label == "sort.apply_combined.total" and r.meta.get("primary") == "confidence",
        ),
        Metric(
            key="sort.counter",
            display="sort.counter/resistance (apply_combined)",
            threshold_pct=10.0,
            is_critical=False,
            matcher=lambda r: r.label == "sort.apply_combined.total" and r.meta.get("primary") in {"resistance", "counter"},
        ),
        Metric(
            key="sort.strategic",
            display="sort.strategic (strategic.sort.end_to_end)",
            threshold_pct=10.0,
            is_critical=False,
            matcher=lambda r: r.label == "strategic.sort.end_to_end",
        ),
    ]


def select_log_groups(log_dir: Path, baseline_count: int, new_count: int) -> tuple[list[Path], list[Path]]:
    logs = sorted(log_dir.glob("perf_*.log"))
    if not logs:
        return [], []

    new_logs = logs[-new_count:] if len(logs) >= new_count else logs[:]
    remaining = logs[: max(0, len(logs) - len(new_logs))]
    baseline_logs = remaining[-baseline_count:] if remaining else []
    return baseline_logs, new_logs


def select_log_groups_by_glob(log_dir: Path, baseline_glob: str, new_glob: str) -> tuple[list[Path], list[Path]]:
    """Select log groups explicitly by glob patterns within log_dir."""
    baseline_logs = sorted(log_dir.glob(baseline_glob))
    new_logs = sorted(log_dir.glob(new_glob))
    return baseline_logs, new_logs


def generate(
    log_dir: Path,
    out_md: Path,
    out_csv: Path,
    baseline_count: int,
    new_count: int,
    min_samples_startup: int,
    min_samples_sort: int,
    baseline_glob: Optional[str] = None,
    new_glob: Optional[str] = None,
) -> None:
    if baseline_glob and new_glob:
        baseline_logs, new_logs = select_log_groups_by_glob(log_dir, baseline_glob, new_glob)
        selection_mode = f"explicit globs ({baseline_glob}) vs ({new_glob})"
    else:
        baseline_logs, new_logs = select_log_groups(log_dir, baseline_count, new_count)
        selection_mode = "automatic latest-window split"

    baseline_records = load_records(baseline_logs)
    new_records = load_records(new_logs)

    rows: list[dict[str, str]] = []
    metrics = build_metrics()

    for metric in metrics:
        b_vals = [r.ms for r in baseline_records if metric.matcher(r)]
        n_vals = [r.ms for r in new_records if metric.matcher(r)]

        b_med = median_or_none(b_vals)
        n_med = median_or_none(n_vals)
        delta = pct_delta(b_med, n_med) if b_med is not None and n_med is not None else None
        status = status_with_sample_gate(
            delta=delta,
            metric=metric,
            baseline_samples=len(b_vals),
            new_samples=len(n_vals),
            min_samples_startup=min_samples_startup,
            min_samples_sort=min_samples_sort,
        )

        rows.append(
            {
                "span": metric.display,
                "baseline_median_ms": fmt_ms(b_med),
                "new_median_ms": fmt_ms(n_med),
                "delta_pct": fmt_pct(delta),
                "threshold_pct": f"+{metric.threshold_pct:.0f}%",
                "status": status,
                "baseline_samples": str(len(b_vals)),
                "new_samples": str(len(n_vals)),
            }
        )

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "span",
                "baseline_median_ms",
                "new_median_ms",
                "delta_pct",
                "threshold_pct",
                "status",
                "baseline_samples",
                "new_samples",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pending_rows = [row for row in rows if row["status"] == "PENDING"]
    fail_rows = [row for row in rows if row["status"] == "FAIL"]
    insufficient_rows = [row for row in rows if row["status"] == "INSUFFICIENT_SAMPLES"]

    status_lines = [
        "Generated from existing PerfTimer logs using:",
        f"- Selection mode: {selection_mode}",
        f"- Baseline logs: {len(baseline_logs)} files",
        f"- New logs: {len(new_logs)} files",
        f"- Minimum samples required: startup={min_samples_startup}, sort={min_samples_sort}",
    ]

    if not (baseline_glob and new_glob):
        status_lines.append(f"- Baseline window: last {baseline_count} logs before new window")
        status_lines.append(f"- New window: latest {new_count} logs")

    if pending_rows:
        status_lines.append(f"- Provisional: {len(pending_rows)} span(s) have no sample in one or both windows")
    if insufficient_rows:
        status_lines.append(f"- Sample gate shortfall: {len(insufficient_rows)} span(s) below minimum sample requirements")
    if fail_rows:
        status_lines.append(f"- Observed failures against current thresholds: {len(fail_rows)} span(s)")

    md_lines = [
        "# Performance Summary",
        "",
        "## Status",
        "",
        *status_lines,
        "",
        "## Comparison Table",
        "",
        "| Span | Baseline Median (ms) | New Median (ms) | Delta % | Threshold | Status | Baseline N | New N |",
        "| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |",
    ]

    for row in rows:
        md_lines.append(
            f"| {row['span']} | {row['baseline_median_ms']} | {row['new_median_ms']} | {row['delta_pct']} | {row['threshold_pct']} | {row['status']} | {row['baseline_samples']} | {row['new_samples']} |"
        )

    md_lines.extend(build_interpretation(rows, min_samples_startup=min_samples_startup, min_samples_sort=min_samples_sort))

    md_lines.extend(
        [
            "",
            "## Gate Rules",
            "",
            "1. Startup median regression must be <= 5%.",
            "2. Generate/sort median regression must be <= 10%.",
            "3. No critical span may regress > 15% without written rationale.",
            "",
            "## Run Metadata",
            "",
            f"- Generated at: {generated_at}",
            f"- Log directory: {log_dir}",
            f"- Selection mode: {selection_mode}",
            f"- Baseline files: {', '.join([p.name for p in baseline_logs]) if baseline_logs else 'none'}",
            f"- New files: {', '.join([p.name for p in new_logs]) if new_logs else 'none'}",
        ]
    )

    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate perf summary markdown and CSV from perf logs")
    parser.add_argument("--log-dir", default="perf_logs", help="Directory containing perf_*.log files")
    parser.add_argument("--out-md", default="docs/validation/perf_summary.md", help="Output markdown path")
    parser.add_argument("--out-csv", default="docs/validation/perf_summary.csv", help="Output CSV path")
    parser.add_argument("--baseline-count", type=int, default=5, help="Number of baseline log files")
    parser.add_argument("--new-count", type=int, default=5, help="Number of new log files")
    parser.add_argument("--min-samples-startup", type=int, default=5, help="Minimum baseline/new samples required for startup spans")
    parser.add_argument("--min-samples-sort", type=int, default=5, help="Minimum baseline/new samples required for sort spans")
    parser.add_argument("--baseline-glob", default=None, help="Optional glob for explicit baseline selection (relative to log-dir)")
    parser.add_argument("--new-glob", default=None, help="Optional glob for explicit new selection (relative to log-dir)")
    args = parser.parse_args()

    generate(
        log_dir=Path(args.log_dir),
        out_md=Path(args.out_md),
        out_csv=Path(args.out_csv),
        baseline_count=max(1, args.baseline_count),
        new_count=max(1, args.new_count),
        min_samples_startup=max(1, args.min_samples_startup),
        min_samples_sort=max(1, args.min_samples_sort),
        baseline_glob=args.baseline_glob,
        new_glob=args.new_glob,
    )


if __name__ == "__main__":
    main()
