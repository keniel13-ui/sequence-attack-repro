#!/usr/bin/env python3
"""Contract section 8 controls for fixture_defg.py. MANDATORY BEFORE DELIVERY.

Two mutations. Each must be PROVEN TO LAND before its result is read, because a
patch that matches nothing runs against a healthy tree, passes, and reports the
guard alive. That defect is the whole reason this file exists.

  M1  remove the capability-closure BLOCK condition in run_k.py
      -> rows that expect BLOCK must become FAILED_TO_REPRODUCE
      if they stay REPRODUCED, the fixture is not reading the gate  -> CONTRACT VOID

  M2  corrupt one expected_reason_code in the fixture
      -> that row must become INCONCLUSIVE
      if it stays REPRODUCED, the reason check is vacuous (the C8 defect) -> VOID

Exit 0 only if BOTH mutations landed AND both produced the required movement.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

SRC = pathlib.Path(__file__).parent


def _apply(path: pathlib.Path, old: str, new: str, label: str) -> None:
    """Patch and PROVE it landed. Raises if the target string was not present."""
    text = path.read_text()
    n = text.count(old)
    if n != 1:
        raise SystemExit(
            f"MUTATION {label} DID NOT APPLY: target string found {n} times, need exactly 1.\n"
            f"  target: {old!r}\n"
            f"  A non-applying mutation must throw, never silently skip."
        )
    path.write_text(text.replace(old, new))
    after = path.read_text()
    if new not in after or old in after:
        raise SystemExit(f"MUTATION {label} FAILED VERIFICATION after write.")
    print(f"  [{label}] mutation applied and verified present in tree")


def _run(workdir: pathlib.Path) -> list[dict]:
    out = workdir / "rows.jsonl"
    proc = subprocess.run(
        [sys.executable, "fixture_defg.py", "--out", str(out)],
        cwd=workdir, capture_output=True, text=True,
    )
    if not out.exists():
        raise SystemExit(f"emitter produced no output.\n{proc.stderr}")
    return [json.loads(l) for l in out.read_text().splitlines() if l.strip()]


def _fresh() -> pathlib.Path:
    d = pathlib.Path(tempfile.mkdtemp(prefix="defg_mut_"))
    for f in ("run_k.py", "fixture_defg.py"):
        shutil.copy2(SRC / f, d / f)
    return d


def main() -> int:
    failures: list[str] = []

    # ---------------- baseline ----------------
    base = _fresh()
    rows = _run(base)
    base_bad = [r for r in rows if r["outcome"] != "REPRODUCED"]
    print(f"\nBASELINE: {len(rows)} rows, non-REPRODUCED = {len(base_bad)}")
    if base_bad:
        failures.append("baseline is not clean; run the emitter before mutating")

    # ---------------- M1: break the gate ----------------
    print("\nM1 — remove the capability-closure BLOCK condition")
    w1 = _fresh()
    _apply(
        w1 / "run_k.py",
        "elif FORBIDDEN_CLOSURE.issubset(proposed):",
        "elif False:  # MUTATED: closure block removed",
        "M1",
    )
    r1 = _run(w1)
    expect_block = [r for r in r1 if r["expected_verdict"] == "BLOCK"]
    moved = [r for r in expect_block if r["outcome"] == "FAILED_TO_REPRODUCE"]
    closure_block_rows = [r for r in expect_block
                          if r["gate_kind"] == "principal_capability_closure"]
    still_green = [r for r in closure_block_rows if r["outcome"] == "REPRODUCED"]
    print(f"  rows expecting BLOCK: {len(expect_block)}")
    print(f"  closure rows expecting BLOCK: {len(closure_block_rows)}")
    print(f"  moved to FAILED_TO_REPRODUCE: {len(moved)}")
    for r in moved:
        print(f"    {r['event_id']}  {r['actual_verdict']} [{r['reason_code']}]")
    if still_green:
        failures.append(
            f"M1: {len(still_green)} closure BLOCK row(s) stayed REPRODUCED after the "
            f"gate condition was removed. The fixture is not reading the gate."
        )
    elif not moved:
        failures.append("M1: no rows moved at all; mutation had no observable effect")

    # ---------------- M2: corrupt an expected reason ----------------
    print("\nM2 — corrupt one expected_reason_code (verdict left correct)")
    w2 = _fresh()
    _apply(
        w2 / "fixture_defg.py",
        '("D", "principal_capability_closure", TOOL_RECOVER): (False, "C1_CAPABILITY_CLOSURE"),',
        '("D", "principal_capability_closure", TOOL_RECOVER): (False, "WRONG_REASON_SENTINEL"),',
        "M2",
    )
    r2 = _run(w2)
    target = [r for r in r2 if r["event_id"] == "D:1:principal_capability_closure"]
    if not target:
        failures.append("M2: target row not found in output")
    else:
        t = target[0]
        print(f"  {t['event_id']}: verdict={t['actual_verdict']} "
              f"expected={t['expected_verdict']} outcome={t['outcome']}")
        print(f"    note: {t['outcome_note']}")
        if t["outcome"] != "INCONCLUSIVE":
            failures.append(
                f"M2: expected INCONCLUSIVE, got {t['outcome']}. The reason_code check "
                f"is vacuous; a wrong-reason pass would be invisible."
            )

    # ---------------- verdict ----------------
    print("\n" + "=" * 70)
    if failures:
        print("CONTROLS FAILED — DELIVERY BLOCKED (contract section 8)")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("BOTH CONTROLS PASSED: mutations landed AND rows moved as required.")
    print("Per contract section 9 this is NOT a result. It means the artifact is")
    print("ready to hand to someone who is not the maker. Reproductions remain 0.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
