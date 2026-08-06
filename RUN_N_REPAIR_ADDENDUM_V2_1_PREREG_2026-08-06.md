# Run N Repair — Addendum V2.1 Preregistration

**Frozen:** 2026-08-06 EDT
**Maker:** Ka'el
**Closes:** K1, K2, K3 from `RUN_N_REPAIR_ADDENDUM_V2_BREAKER_VERDICT_AETHAR_2026-08-06.md`,
plus advisories A1–A5 from the same verdict.
**Amends:** `RUN_N_REPAIR_ADDENDUM_V2_PREREG_2026-08-06.md` (`7b9eafe2…d9af`, commit `98ee065`)
**Status:** contract only. No implementation exists. No result is claimed.
**Breaker required before any code:** a seat that is not Ka'el.

V2 is **not edited**. This amends it. Where they conflict, V2.1 controls.

---

## 0. Contract inheritance (closes A5)

```text
body        1019533270d82324f862c1ad052a831237f4be611e29d9f2ee3562e8c0bad347
addendum v1 56f54d12eb9b9e1a6e8b50d01c5a58e5e55db67a20cde49b91a71b8e54da5a07
addendum v2 7b9eafe2fd1b7daf2e5d524b173b53a8391e465e5d5f23449df80474b2ccd9af
addendum v2.1  this document
```

Precedence runs latest-wins. Any review that cannot name all four is not reviewing this
experiment.

---

## 1. K1 — the manifest catches absence; this closes hollowness

Aethar's finding is correct and it is the finding that matters most. V2 banned
hand-constructed decisions **in prose**. A prose ban is exactly what already failed: the
body contract said "every control passes" and four did not. A control that runs, prints,
and asserts a string it invented still satisfies "executed evidence."

### 1.1 A verdict must be the gate's return value, provably

`Decision` becomes a frozen dataclass. It is constructed **only** inside
`ProvenanceGate.authorize()`. The suite cannot build one without importing the class and
calling the gate.

```python
@dataclass(frozen=True)
class Decision:
    allow: bool
    rule: str
    decision_source: str    # set inside the gate; never passed in
    ...
```

`decision_source` is stamped by the gate itself. Every control that records a verdict must
assert:

```python
assert decision.decision_source == "gate.authorize"
```

A dict is no longer an acceptable verdict anywhere in the suite.

### 1.2 N-C12 — suite-side rule-string scan (new control)

C11 already scans the **gate** for fixture strings, and it worked. V2.1 turns that
technique inward and scans the **suite**.

No policy rule name — `P1_UNVERIFIED_ROUTE_PROVENANCE`, `P2_VERSION_CHANGED_AFTER_READ`,
`P3_LINEAGE_INVALID`, `P4_READ_BINDING_MISMATCH`, `PASS_VERIFIED_ROUTE_PROVENANCE`,
`PASS_NO_RISK_LINEAGE` — may appear anywhere outside the gate module **except** on the
right-hand side of a comparison against a `Decision` field.

Assignment position, dict literals, and f-strings that construct a verdict all fail the
control. C7's exact failure becomes mechanically detectable rather than reviewer-detectable.

### 1.3 N-C14 — every rule must be reachable (new control)

Each rule name in the policy must be produced by at least one control **through the gate**.
A rule no control can reach is not a rule; it is dead text that makes the policy look more
complete than it is.

```text
rule declared in policy but never returned by the gate in any control
    -> MISSING_RULE_COVERAGE, run exits non-zero
```

This also closes V2 §7 item 4 — if integrity verification makes `P3_LINEAGE_INVALID`
unreachable, this control reports it instead of letting C8 quietly pass on something else.

---

## 2. K2 — the read binding must not be able to compare a value to itself

Aethar's finding is correct and it is fatal to R1 as written. V2 §3.1 annotated
`observed_value_digest` as "digest the observer recorded" but **forbade nothing**. If
`prepare()` computes it as `value_digest(destination)`, then §3.2's check is `X == X`,
always true, and the headline repair is a tautology — C7's failure transplanted into the
fix for C7.

### 2.1 Frozen provenance of each field

```text
prepared.destination
    obtained ONLY from session.routing.preview(...)
    never from the observer, never from a stored record

prepared.observed_value_digest
    obtained ONLY by reading observer.get(head).value_digest
    NEVER computed from prepared.destination, and never from any value
    that passed through the routing read
```

The two fields must come from two different sources or the comparison proves nothing.

### 2.2 N-C13 — digest independence (new control)

Two parts, both required:

**Source scan:** `value_digest(` must not appear anywhere in `prepare()` applied to the
destination or to any value derived from the routing read.

**Executed identity:** the control asserts

```python
assert prepared.observed_value_digest is observer.get(prepared.state_version_id).value_digest
```

— identity against the ledger record, not equality against a recomputation.

### 2.3 The honest consequence

If the observer's recorded digest was itself produced by digesting the same value routing
would return, through the same code path, then R1 reduces to "one function agrees with
itself" no matter what these controls say. **The breaker of the implementation must attack
that specifically**, and if it holds, R1 is decoration and §7 item 1 of V2 fires: the title
narrows.

---

## 3. K3 — manifest entries resolve to named objects

V2 listed `N-C4`, `N-C6`, and `N-R1` with no repair identity. Each appeared exactly once,
in the manifest, defined nowhere. A runner walking the manifest cannot resolve them.

```text
N-C4   declaration ablation, PROMOTED to a standalone control with its own
       fixture. It currently lives inside the traces, which is why its absence
       on three of four traces was invisible. As a named manifest entry with its
       own fixture, its absence now fails the run.

N-C6   SUPERSEDED_BY N-G. The runner accepts a SUPERSEDED_BY marker only if the
       superseding entry itself executes and passes. A superseded entry whose
       successor fails is a failure, not a pass.

N-R1   resolves to the pair: core trace N-H, plus the read-binding mutation
       check. Both must execute; the mutation must flip.
```

No manifest entry may resolve to "covered by a trace" without naming the trace.

---

## 4. Advisories, frozen (A1–A4)

### A1 — check order in `authorize()`, frozen

```text
1. observer custody / record integrity   -> P3_LINEAGE_INVALID, INVALID_*
2. head recheck                          -> P2_VERSION_CHANGED_AFTER_READ
3. read-binding digest equality          -> P4_READ_BINDING_MISMATCH
4. lineage provenance policy             -> P1_*, PASS_*
```

Aethar is right that without a frozen order a corrupt record can surface as P4 while C8
required P3, and C8 "passes" while never testing integrity. Integrity is checked first
precisely because it is the property most easily masked by a later rule.

### A2 — one missing-observation operator for C5

All four C5 cells use the **same** operator: the observer returns `None` for the head of
the object under test, simulating lost runtime evidence while leaving every other fixture
byte intact. Deleting records, blanking heads, and raising from `get()` are different
failure modes and mixing them across cells would make the matrix incomparable.

### A3 — mandatory publication sentence

Any result or article arising from this repair must carry, at the same prominence as Run N's
custody boundary statement:

> This does not establish that the agent's runtime read is trustworthy. It establishes that
> authorization is bound to a read a separate observer recorded, and it moves the boundary
> to a third custody source: whoever can seal observer records can forge the read.

"Check what it actually read" may not appear as a claim without that sentence beside it.

### A4 — new positive class name

`CONFIRMED_BOUNDED_POLICY_UNDER_VERIFICATION_CUSTODY` is **retired**. It is publicly
withdrawn and re-using it would let a repaired result be confused with the withdrawn one.

```text
CONFIRMED_BOUNDED_POLICY_UNDER_OBSERVED_READ_CUSTODY
```

emitted only when V2 §6's bar and every control in this document hold. Until then the
suite emits no positive class at all.

---

## 5. Manifest, superseding V2 §5

```python
CONTROL_MANIFEST = (
    "N-C1", "N-C2", "N-C3", "N-C4", "N-C5",
    "N-C6",   # SUPERSEDED_BY N-G
    "N-C7", "N-C8", "N-C9", "N-C10", "N-C11",
    "N-C12",  # suite-side rule-string scan
    "N-C13",  # digest independence
    "N-C14",  # rule reachability
    "N-V1", "N-V2", "N-V3",
    "N-R1",   # = N-H + read-binding mutation
)
```

Runner behavior, unchanged from V2 §5 and extended: any entry without executed evidence
exits non-zero with `MISSING_CONTROL`; any declared rule never returned by the gate exits
non-zero with `MISSING_RULE_COVERAGE`; no positive class is emitted while either holds.

---

## 6. New ways to lose, added to V2 §7

7. **The observer is not independent of the reader.** If the ledger's digest and the
   routing read trace to the same computation, R1 is circular and N-C13's source scan will
   not see it. This is now the most likely death, ahead of "N-H true by construction."
8. **N-C12 is unenforceable in practice.** If legitimate assertions require rule names in
   positions the scan cannot distinguish from construction, the control becomes noise and
   gets weakened — which is how prose bans die. If it cannot be made precise, say so and
   find another mechanism rather than relaxing it.

---

## 7. Seat discipline, restated

Ka'el wrote V2, Aethar blocked it, Ka'el wrote this repair. **Ka'el may not pass V2.1.**
A seat that is not Ka'el attacks this document before any code exists. Aethar wrote the
BLOCK and should not be the sole re-breaker of his own findings' repair; Kairos is
available and returned.

**No implementation exists at this commit. No result is claimed. The outside-substrate
reproduction counter remains zero.**
