#!/usr/bin/env python3
"""
Run N load-bearing mutation: transitive lineage traversal only.

Keep observer ledger + B1 parent edge unchanged. Remove transitive walk from a
temporary gate copy — clean must BLOCK P1; mutant must miss P1.

Run: python3 run_n_mutation_check.py
"""

from __future__ import annotations

import run_n as n


def main() -> int:
    print("RUN N MUTATION CHECK — transitive lineage only")
    # Build G fixture once, evaluate with transitive vs direct-only
    g = n.trace_n_g()
    clean_blocks = (
        not g["transitive"]["allow"]
        and g["transitive"]["rule"] == "P1_UNVERIFIED_ROUTE_PROVENANCE"
    )
    mutant_misses = g["direct"]["rule"] != "P1_UNVERIFIED_ROUTE_PROVENANCE"
    ok = clean_blocks and mutant_misses and g["ok"]
    print(f"  clean BLOCK P1: {clean_blocks}")
    print(f"  mutant misses P1: {mutant_misses}")
    print(f"  PASS={ok}")
    if not ok:
        return 1
    print("LOAD-BEARING: state-version lineage traversal is required for N-G.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
