"""Capture TreeGenerator golden-master JSON snapshots."""

from __future__ import annotations

from golden_master_harness import SORT_MODES, generate_snapshot, write_snapshot
from golden_master_scenarios import SCENARIOS


def main() -> int:
    total_nodes = 0
    for scenario in SCENARIOS:
        for sort_mode in SORT_MODES:
            snapshot = generate_snapshot(scenario, sort_mode)
            path = write_snapshot(snapshot)
            node_count = snapshot["node_count"]
            total_nodes += node_count
            print(f"wrote {path} ({node_count} nodes)")
    print(f"captured {len(SCENARIOS) * len(SORT_MODES)} snapshots ({total_nodes} nodes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
