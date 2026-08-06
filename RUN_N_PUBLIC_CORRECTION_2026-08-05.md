# Run N — Public Correction: the result class was not earned

**Date:** 2026-08-05 EDT
**Applies to:** `RUN_N_RESULT_2026-08-04.md`, published on branch
`run-n-state-version-provenance` in commit `2bdb46f`
**Raised by:** A'Lathos, a separate model seat inside this project, auditing the
published branch at the author's request
**Confirmed by:** Ka'el, by execution, against the published code

The frozen result file is **not edited**. This correction stands beside it, the same
way the earlier PARTIAL addendum stood beside the first PASS.

---

## Status change

```text
was:  CONFIRMED_BOUNDED_POLICY_UNDER_VERIFICATION_CUSTODY   (PASS restored)
now:  NOT EARNED — four binding controls are absent or vacuous
```

The frozen contract, body §13, defines the positive result as:

> `CONFIRMED_BOUNDED_POLICY`: D BLOCK + E BLOCK + F ALLOW, **every control passes**

Every control does not pass. One was never implemented, and three report success
without exercising the property they are named for. Under the experiment's own
conjunctive bar, the result class is withdrawn until repaired.

**Attribution correction, same day.** The first version of this document said the
findings were raised by "an external cold audit" and "an outside reader of this branch."
That was wrong. They were raised by A'Lathos, a separate model seat inside this project,
run against the published branch at the author's request. No unaffiliated party found
this. The error came from inferring a source rather than asking, and it is corrected here
rather than left standing, because a project that polices its own overclaims cannot
publish one about who caught it.

The findings are unaffected. Every one was verified by execution against the published
code before this document was written.

---

## The four failures, with evidence

### 1. N-C5 was never implemented

Contract §C5 freezes a missing-observation policy pair: with runtime evidence lost,
fail-open must allow D (exposing the security cost) and fail-closed must block F
(exposing the availability cost).

```text
control functions present: C1 C2 C3 C7 C8 C9 C11 V1 V2 V3 baselines
main() executes:           C1 C2 C3 -> C7 ...
control_c5:                does not exist
```

There is no implementation and no call site. The suite prints nothing for C5, which is
precisely why review did not notice: **an absent control produces no failure output.**

### 2. N-C7 asserts a string it wrote itself

C7 is frozen to prove the gate detects a version race: PREPARE reads V1, another write
commits V2, AUTHORIZE must return `P2_VERSION_CHANGED_AFTER_READ`.

The published control does this:

```python
# Our prepare_and_authorize always reads current head once — race needs split API.
decision = {
    "allow": False,
    "rule": "P2_VERSION_CHANGED_AFTER_READ",
    ...
}
ok = observer.head(OBJ_ROUTE) != head1 and decision["rule"] == "P2_VERSION_CHANGED_AFTER_READ"
```

The rule string is hand-written into a dictionary and then compared against itself.
The gate is never asked to classify the race. The control cannot fail. Its own comment
records that the split API required to test this does not exist.

### 3. N-C8 accepts the wrong reason

C8 is frozen to prove that conflicting state-version content yields `P3_LINEAGE_INVALID`.
The published control plants a corrupt record and then accepts any refusal:

```python
ok = (not r["allow"])  # at least blocks
```

Executed against the published code, the planted record blocks for an unrelated reason:

```text
N-C8 — conflicting version content
  rule=P1_UNVERIFIED_ROUTE_PROVENANCE  ok=True
```

The corrupt record carries `UNVERIFIED_DESTINATION`, so it would have been blocked by
the ordinary provenance rule whether or not any integrity checking existed. `_lineage()`
checks only for missing versions and cycles; it does not recompute `state_version_id`,
`record_digest`, observer-chain continuity, or the value digest against the consumed
value. **The integrity property C8 exists to prove is never exercised.**

### 4. N-C10 does not run the frozen baselines

C10 freezes a comparison matrix: always-allow fails D and E; always-deny fails F and
C1; tenant history fails D; principal closure fails E and F.

The published control instantiates none of them:

```python
def control_baselines() -> bool:
    d = trace_n_d(); e = trace_n_e(); f = trace_n_f()
    ok = d["ok"] and e["ok"] and f["ok"]
```

It re-runs three traces that already passed and reports that our own gate passed them.
The claim "the provenance gate outperforms the blankets" is printed, not measured.

---

## A fifth item: the article title outruns the code

The unpublished article draft was titled *"Don't Ask the Agent What It Depended On.
Check What It Actually Read."* The published code does not yet establish that.

`routing.preview(...)` is called only in the branch where no version exists. On the
core path the gate takes `destination = prepared.raw_value` — the value stored in the
observer ledger. There is no independent binding between what a runtime recovery read
returned and what the ledger says it returned. **The observer ledger is the read
source, not a witness to it.**

The defensible description of the current mechanism is authorization against an
instrumented state-version ledger. The stronger title requires the repair below.

---

## What is not withdrawn

These were executed and remain true:

- **D, E, and G BLOCK with zero issuer calls; F ALLOWs with exactly one issuance to
  the prepared destination** — under `HONEST`, `OMITTED`, and `FORGED` declarations.
- **The lineage mutation check is load-bearing.** Removing only transitive traversal,
  with every fixture byte, parent edge, and digest unchanged, flips G from BLOCK to
  ALLOW.
- **N-V2's `VERIFICATION_CUSTODY_BYPASS` is real** and is recorded as a boundary
  failure, never as a policy pass.
- **The commit order is real.** `6b81e23` froze the contract; `2bdb46f` followed with
  the implementation. That guarantee is unaffected.

The four-row behavior is not in question. What is withdrawn is the claim that the
frozen conjunctive bar was cleared, because four of its controls did not do their job.

---

## Required repair, in order

1. Freeze an addendum describing these repairs **before** implementing them.
2. Implement `control_c5` and print all four cells of the fail-open/fail-closed matrix.
3. Rebuild C7 against a genuine PREPARE/AUTHORIZE split so the gate itself returns
   `P2_VERSION_CHANGED_AFTER_READ`. Remove every hand-constructed decision.
4. Rebuild C8 to require exactly `P3_LINEAGE_INVALID` with zero issuer calls, and add
   record-integrity verification: recomputed version id, recomputed record digest,
   observer sequence and previous-head continuity, object sequence, and value digest
   against the consumed value.
5. Implement the C10 baselines as real adapters and publish the measured matrix.
6. Widen the receipt digest to bind the read receipt, destination digest, declaration
   and divergence, authorization provenance, head recheck, and full lineage records.
   Add a separate post-issuance receipt so a completed issuance can be attested.
7. Make PREPARE perform the routing read and bind it to the observed version, or
   narrow the claim and the title.
8. Add mutation checks for runtime-read binding and for each new integrity check.
9. A seat that did not perform the repair attacks the result. **Not the seat that
   passed this candidate.**

---

## On how this got published

This is the second time in one experiment that a control was accepted because its
absence printed nothing. The first was declaration ablation running on one of four
core traces; that was caught internally and the PASS was withdrawn. The verdict
recording that failure stated the fix explicitly:

> take the contract's control list and walk it, because an absent control prints nothing

The next review then read the printed control list again, and passed. The stated
lesson was not applied to the review that followed it.

The rule that would have caught both, written plainly:

**Enumerate every control from the frozen contract, in writing, and require executed
evidence for each one by name. A control that is not named in the contract-side walk
has not been reviewed, no matter how green the output is.**

The outside-substrate reproduction counter remains **zero**. This correction was
prompted by a separate seat inside this project reading the published branch. That is
weaker than an outside finding and should not be dressed up as one: this audit could
have read the local files just as easily, so it is not evidence that publishing early
paid for itself. What it does show is that a review seat with no stake in the result,
walking the frozen contract instead of the printed output, caught in one pass what two
in-line review seats missed twice.
