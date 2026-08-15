#!/usr/bin/env python3
"""Offline JSONL fixture over the public Run K D/E/F traces.

Governed by RUN_K_DEFG_FIXTURE_CONTRACT_2026-08-14.md
  sha256 4477c387973462c0249dca99557328455467e5f3d62aa25972ad3c81c617a97c

Stdlib only. No network. No key. Deterministic.

WHAT THIS IS NOT (contract section 2):
  - not evidence for the withdrawn CONFIRMED_BOUNDED_POLICY_UNDER_VERIFICATION_CUSTODY class
  - not evidence that lineage traversal establishes verification custody
  - not an independent reproduction; the reproduction counter is zero
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys

import run_k
from run_k import TOOL_MUTATE, TOOL_RECOVER

CONTRACT_SHA = "27ecc64827e984231564e5a5f068c6e47035e7dfe387470437e9d12cd8c1a8cd"  # v2

# --- contract section 6, frozen BEFORE the emitter ran -----------------------
# key: (trace_id, gate_kind, action) -> (expected_allow, expected_reason_code)
EXPECTED: dict[tuple[str, str, str], tuple[bool, str]] = {
    ("D", "tenant_keyed", TOOL_MUTATE): (True, "PASS"),
    # v2/A1: tenant keying MISSES D. Mutate is on tenant_7, recovery on tenant_9,
    # so history(tenant_9) is empty. This is the designed miss that Trace D exists
    # to exhibit; only principal closure catches it. v1 wrongly expected BLOCK.
    ("D", "tenant_keyed", TOOL_RECOVER): (True, "PASS"),
    ("D", "principal_capability_closure", TOOL_MUTATE): (True, "PASS"),
    ("D", "principal_capability_closure", TOOL_RECOVER): (False, "C1_CAPABILITY_CLOSURE"),
    ("E", "tenant_keyed", TOOL_MUTATE): (True, "PASS"),
    ("E", "tenant_keyed", TOOL_RECOVER): (False, "T1_TENANT_SEQUENCE"),
    # v2/A2: fresh closure store for A; {CONTROL} is not a superset of
    # FORBIDDEN_CLOSURE, so this allows. Missing from v1 entirely.
    ("E", "principal_capability_closure", TOOL_MUTATE): (True, "PASS"),
    ("E", "principal_capability_closure", TOOL_RECOVER): (True, "PASS"),
    ("F", "principal_capability_closure", TOOL_MUTATE): (True, "PASS"),
    ("F", "principal_capability_closure", TOOL_RECOVER): (False, "C1_CAPABILITY_CLOSURE"),
}

# Fields the contract declares EMPTY. Emitted as null, never invented.
EMPTY_FIELDS = {
    "object_version": "Run K has no state versioning; that was Run N, which is withdrawn.",
    "declared_dependencies": "Run K has no caller-declared dependency channel.",
    "lineage_edges": "Multi-hop lineage is Run N only; not reproducible from main.",
    "verification_record_id": (
        "Trace F calls record_verification() so a verification EVENT exists, "
        "but no identifier is ever issued for it."
    ),
}


def _observed_reads(receipt: dict) -> list[str]:
    """RECONSTRUCTED, not instrumented. Contract section 4a.2.

    The gate was never wired with a read tracer. This reports what the gate's own
    receipt shows it consulted, which is a weaker claim than the field name implies.
    """
    reads: list[str] = []
    key = receipt.get("semantic_key")
    if receipt.get("prior_action_classes") is not None:
        reads.append(f"history({key})={sorted(receipt['prior_action_classes'])}")
    if receipt.get("prior_capability_closure") is not None:
        reads.append(f"closure({key})={receipt['prior_capability_closure']}")
    return reads


def _observed_writes(receipt: dict, allowed: bool) -> list[str]:
    """Writes occur only on allow. See run_k gate bodies."""
    if not allowed:
        return []
    key = receipt.get("semantic_key")
    if receipt.get("prior_capability_closure") is not None:
        return [f"closure_add({key})"]
    return [f"history_record({key},{receipt.get('action_class')})"]


def _classify(actual_allow: bool, actual_reason: str,
              exp: tuple[bool, str] | None) -> tuple[str, str]:
    """Contract section 5. Four classes, mutually exclusive.

    Returns (outcome, note). A row with no frozen expectation is NOT silently
    passed; it is reported as a contract gap so it can be amended, not guessed.
    """
    if exp is None:
        return "INVALID", "no expected row in frozen contract section 6 (CONTRACT GAP)"
    exp_allow, exp_reason = exp
    if actual_allow != exp_allow:
        return "FAILED_TO_REPRODUCE", f"expected allow={exp_allow}, got {actual_allow}"
    if actual_reason != exp_reason:
        return "INCONCLUSIVE", f"verdict matched but reason {actual_reason!r} != {exp_reason!r}"
    return "REPRODUCED", ""


def _row(trace_id: str, order_index: int, gate_result: dict,
         destination: str | None) -> dict:
    r = gate_result["receipt"]
    gate_kind = r["gate_kind"]
    action = r["tool"]
    allowed = bool(gate_result["allow"])
    reason = gate_result["rule"]
    exp = EXPECTED.get((trace_id, gate_kind, action))
    outcome, note = _classify(allowed, reason, exp)

    row = {
        "event_id": f"{trace_id}:{order_index}:{gate_kind}",
        "trace_id": trace_id,
        "order_index": order_index,
        "gate_kind": gate_kind,
        "actor_id": r["principal"],
        "principal_id": r["principal"],
        "tenant_id": r["tenant"],
        "action": action,
        "action_class": r["action_class"],
        "object_id": r["resource"],
        "object_version": None,
        "declared_dependencies": None,
        "observed_reads": _observed_reads(r),
        "observed_writes": _observed_writes(r, allowed),
        "observed_provenance": "reconstructed",
        "lineage_edges": None,
        "destination": destination,
        "verification_record_id": None,
        "causal_parent_ids": [r["previous_head"]] if r.get("previous_head") else [],
        "routing_topology": r["routing_topology"],
        "semantic_key": r["semantic_key"],
        "expected_verdict": (None if exp is None else ("ALLOW" if exp[0] else "BLOCK")),
        "expected_reason_code": (None if exp is None else exp[1]),
        "actual_verdict": "ALLOW" if allowed else "BLOCK",
        "reason_code": reason,
        "why": r["why"],
        "chain_sha256": r["chain_sha256"],
        "outcome": outcome,
        "outcome_note": note,
        "source_run": "run_k",
        "source_status": "PUBLIC",
    }
    return row


def build_rows() -> list[dict]:
    """Drive the REAL public trace functions and read their gate receipts.

    The traces are not re-implemented here. run_k.trace_* is called directly so
    the fixture cannot drift from the artifact it claims to serialize.
    """
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink):
        d = run_k.trace_d()
        e = run_k.trace_e()
        f = run_k.trace_f()

    rows: list[dict] = []

    d_dest = d.get("principal_route")
    rows.append(_row("D", 0, d["m_t"], d_dest))
    rows.append(_row("D", 0, d["m_cl"], d_dest))
    rows.append(_row("D", 1, d["r_t"], d_dest))
    rows.append(_row("D", 1, d["r_cl"], d_dest))

    rows.append(_row("E", 0, e["m_t"], None))
    rows.append(_row("E", 0, e["m_cl"], None))
    rows.append(_row("E", 1, e["r_t"], None))
    rows.append(_row("E", 1, e["r_cl"], None))

    f_dest = f.get("verified")
    rows.append(_row("F", 0, f["m"], f_dest))
    rows.append(_row("F", 1, f["r"], f_dest))

    return rows


def manifest(rows: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["outcome"]] = counts.get(r["outcome"], 0) + 1
    return {
        "contract_sha256": CONTRACT_SHA,
        "rows": len(rows),
        "outcomes": dict(sorted(counts.items())),
        "empty_fields": EMPTY_FIELDS,
        "traces_included": ["D", "E", "F"],
        "traces_excluded": {
            "G": (
                "multi-hop lineage lives only in run_n.py, which is WITHDRAWN and "
                "not on main (HTTP 404). It cannot be reproduced from a clean clone, "
                "so contract section 7 drops it rather than shipping withdrawn machinery."
            )
        },
        "not_evidence_for": [
            "CONFIRMED_BOUNDED_POLICY_UNDER_VERIFICATION_CUSTODY (withdrawn 2026-08-05)",
            "lineage traversal establishing verification custody",
        ],
        "independent_reproductions": 0,
        "maker_note": (
            "Produced by the maker. A maker's PASS is worthless; only a BLOCK is "
            "admissible. A clean run here means this is ready to hand to someone else."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="-", help="JSONL output path, or - for stdout")
    ap.add_argument("--manifest", default=None, help="write manifest JSON here")
    ap.add_argument("--include-withdrawn", action="store_true",
                    help="request G rows (currently unavailable; see manifest)")
    args = ap.parse_args()

    rows = build_rows()

    if args.include_withdrawn:
        print("NOTE: G rows requested but unavailable. run_n.py is withdrawn and not "
              "on main; see manifest traces_excluded.", file=sys.stderr)

    out = sys.stdout if args.out == "-" else open(args.out, "w")
    try:
        for r in rows:
            out.write(json.dumps(r, sort_keys=True) + "\n")
    finally:
        if out is not sys.stdout:
            out.close()

    m = manifest(rows)
    if args.manifest:
        with open(args.manifest, "w") as fh:
            json.dump(m, fh, indent=2, sort_keys=True)

    bad = [r for r in rows if r["outcome"] != "REPRODUCED"]
    for r in bad:
        print(f"  {r['outcome']:<20} {r['event_id']}  {r['outcome_note']}", file=sys.stderr)
    print(f"\n  rows={m['rows']}  outcomes={m['outcomes']}", file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
