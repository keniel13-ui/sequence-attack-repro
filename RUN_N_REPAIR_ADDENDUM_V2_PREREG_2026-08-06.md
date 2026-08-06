# Run N Repair — Addendum V2 Preregistration

**Frozen:** 2026-08-06 EDT
**Maker:** Ka'el
**Status:** contract only. No implementation exists. No result is claimed.
**Breaker required before any code is written:** a seat that is not Ka'el.
**Repairs:** the four failures published in `RUN_N_PUBLIC_CORRECTION_2026-08-05.md`
(commit `9f0b352`, attribution corrected at `0d8267d`).

This document must be committed **before** any implementation commit. The pre-commit
hook enforces that ordering, and a reader must be able to inspect this contract before
the code that satisfies it.

---

## 1. Why this addendum exists

Run N's published result class was withdrawn because the implementation did not satisfy
its own frozen contract:

- **N-C5** was never implemented — no function, no call site, no output.
- **N-C7** hand-wrote `"P2_VERSION_CHANGED_AFTER_READ"` into a dictionary and compared
  that string to itself. The gate was never asked.
- **N-C8** accepted any refusal and observably returned `P1_UNVERIFIED_ROUTE_PROVENANCE`,
  never the required `P3_LINEAGE_INVALID`.
- **N-C10** instantiated no baselines; it re-ran three passing traces and reported that
  our own gate passed them.

And a fifth item, which is the reason this is Option B rather than a narrower patch:

- The core path never performed a runtime read. `routing.preview(...)` was called only in
  the `head is None` branch; otherwise `destination = prepared.raw_value` took the value
  the observer ledger already held. **The ledger was the read source, not a witness to
  a read.** The claim "check what it actually read" was therefore not established.

Two review seats passed that implementation. Both read the printed output. The absent
control printed nothing, so nothing is what they found.

---

## 2. What this repair must produce, and what it must not claim

**Must produce:** a mechanism in which authorization is bound to a read that a separate
observer recorded, where every control named in this contract executes and is verifiable
by a stranger, and where removing the read binding demonstrably reopens an attack.

**Must not claim:** production IAM, a general solution to agent authorization, validation
on any outside substrate, or that any agent system is secure. The outside-substrate
reproduction counter is **zero** and nothing in this document moves it.

---

## 3. The runtime-read binding (Repair R1 — the headline)

### 3.1 A real two-stage API

`ProvenanceGate` gains two separate entry points. The single-call
`prepare_and_authorize` path is retired from the core traces.

```text
prepared = gate.prepare(session, tenant)
decision = gate.authorize(prepared, session, declaration)
issued   = issue_if_allowed(decision, prepared, session)
```

`prepare()` performs the **actual routing read** — `session.routing.preview(...)` — and
returns a frozen object. It emits no credential, token, or notification.

```python
@dataclass(frozen=True)
class PreparedRecovery:
    destination: str            # what routing actually returned
    state_object_id: str
    state_version_id: str       # observer's head at read time
    observed_value_digest: str  # digest the observer recorded for that version
    read_receipt: dict          # sealed, includes receipt_digest
```

### 3.2 The binding AUTHORIZE must verify

`authorize()` must independently confirm, and **refuse** if either fails:

```text
value_digest(prepared.destination) == prepared.observed_value_digest
observer.head(prepared.state_object_id) == prepared.state_version_id
```

The first is the new property. It asserts that the value the runtime read returned is the
same value the observer recorded for the version being authorized against. Without it,
the two can diverge silently and the gate is authorizing against a record rather than
against a read.

**New rule, frozen now:**

```text
runtime read value does not match the observed version's recorded digest
    -> BLOCK  P4_READ_BINDING_MISMATCH
```

### 3.3 R1 is load-bearing or the title is not earned

A new trace **N-H** is frozen as a core row:

1. routing returns destination X;
2. the observer's record for the head version carries the digest of a different value Y
   (a divergence the governed actor did not author and cannot see);
3. recovery is attempted.

```text
with binding verification     -> BLOCK  P4_READ_BINDING_MISMATCH   issuer 0
binding verification removed  -> ALLOW                             issuer 1
```

A mutation check must remove **only** the digest comparison — every fixture byte,
observer record, parent edge, and receipt unchanged — and show the verdict flip. If it
does not flip, R1 is decoration and **the title must be narrowed** (see §7).

---

## 4. Control repairs

### R2 — N-C5, implement it

Four cells, all printed, all asserted against frozen expectations:

| Fixture | Fail-open | Fail-closed |
|---|---|---|
| D attack | ALLOW — exposes the security cost of losing runtime evidence | BLOCK |
| F legitimate | ALLOW | BLOCK — exposes the availability cost |

No cell counts toward the core bar. All four must match. If fail-open does not allow D,
the missing-observation model is wrong and that is a finding, not a fix.

### R3 — N-C7, ask the gate

C7 must use the §3.1 split: `prepare()` reads V1, an intervening write commits V2,
`authorize(prepared, ...)` is called with the stale prepared object.

```python
assert decision["rule"] == "P2_VERSION_CHANGED_AFTER_READ"
assert decision["allow"] is False
assert issuer.calls == 0
```

The verdict must come from the gate. **Every hand-constructed decision dictionary is
removed from every control in this suite.**

### R4 — N-C8, require the right reason and build the integrity it tests

C8 must assert exactly:

```python
assert decision["rule"] == "P3_LINEAGE_INVALID"
assert decision["allow"] is False
assert issuer.calls == 0
```

This requires integrity verification that does not currently exist. A record retrieved
from the ledger is presently trusted. `verify_record()` must recompute and validate:

- `state_version_id` from the canonical version body;
- `record_digest` from the canonical observer-sealed body;
- observer sequence number and `previous_observer_head` continuity;
- object sequence number and `previous_object_version_id` continuity;
- uniqueness of version ids and absence of conflicting object heads;
- `value_digest` against the consumed value.

Each check gets its own mutation test: remove the check, show the corresponding corrupt
fixture stop being caught.

### R5 — N-C10, instantiate the baselines

Each baseline is a real adapter scored on the same traces, and the measured matrix is
printed:

| Baseline | D | E | F | C1 |
|---|---|---|---|---|
| always-allow | | | | |
| always-deny | | | | |
| tenant history | | | | |
| principal closure | | | | |
| version provenance | | | | |

Cells are filled by execution. No cell may be asserted from this document.

### R6 — receipts bind what the contract says they bind

Two artifacts replace the single seal.

**Authorization receipt**, sealed before any issuer call, binding: prepared read receipt
digest, observed object id and version id, destination digest, full lineage record
digests, authorization provenance and verification evidence, head-recheck result, caller
declaration and divergence flag, decision and rule.

**Issuance receipt**, sealed after the issuer call, binding: the authorization receipt
digest, the issuer operation, destination digest, call sequence number, and outcome.

This closes a defect the correction noted: the current seal runs before issuance, so
`issuer_calls_so_far` is zero even on an allow, and the receipt cannot attest to the
issuance it authorized.

---

## 5. The manifest rule — make an absent control fail loudly

This is the structural repair, and it is binding.

The contract's control list is frozen here as a machine-readable manifest. The runner
walks **the manifest**, not the set of implemented functions:

```python
CONTROL_MANIFEST = (
    "N-C1", "N-C2", "N-C3", "N-C4", "N-C5", "N-C6", "N-C7",
    "N-C8", "N-C9", "N-C10", "N-C11",
    "N-V1", "N-V2", "N-V3",
    "N-R1",   # runtime-read binding
)
```

The runner must:

1. resolve every manifest entry to an executed control and record its result;
2. **exit non-zero, printing `MISSING_CONTROL: <name>`, if any manifest entry has no
   executed evidence**;
3. refuse to emit any positive result class while any entry is missing or failing.

The reason is exact. Twice in this experiment a control was accepted because its absence
printed nothing. After this repair, **an absent control prints a failure.** The lesson
that was written in a verdict and then not applied becomes a property of the runner
instead of a habit reviewers must remember.

A control may not be removed from the manifest without a new frozen addendum.

---

## 6. The bar

Positive result requires **all** of:

```text
N-D  BLOCK   ·  N-E  BLOCK   ·  N-G  BLOCK (transitive)
N-F  ALLOW   ·  N-H  BLOCK (P4_READ_BINDING_MISMATCH)

+ every CONTROL_MANIFEST entry executes and passes
+ every core trace holds under HONEST / OMITTED / FORGED
+ both mutation checks flip: transitive traversal, and read binding
+ zero hand-constructed decisions anywhere in the suite
```

Conjunctive. Any single failure means no positive class.

---

## 7. How this can come out wrong — stated before code

Six defined ways to lose. Each is a real outcome that gets published as a receipt.

1. **R1 is not load-bearing.** Removing the digest comparison does not flip N-H. Then the
   binding is decoration, the title narrows to *authorization against an instrumented
   state-version ledger*, and we say so publicly.
2. **N-H is true by construction.** If the only way to produce a digest divergence is for
   the harness to plant one that no real runtime could produce, N-H proves nothing about
   runtime reads. This is the failure that killed five designs in `RESEARCH_SPINE.md` §3
   and it is the most likely way this one dies.
3. **C5's fail-open does not allow D.** The missing-observation model is then wrong and
   the fail-open/fail-closed framing is unsupported.
4. **Integrity verification makes C8 unreachable** — if every corrupt fixture is caught
   earlier by another rule, `P3_LINEAGE_INVALID` may be unreachable in practice, and a
   rule that cannot be reached is not a rule.
5. **The baselines do not lose where the contract predicts.** If tenant history does not
   fail D, or principal closure does not fail E and F, then Run K's frozen findings do
   not reproduce under this harness and Run N's premise is in question.
6. **The observer itself becomes the thing being trusted.** R1 moves the trust boundary
   from "the ledger's stored value" to "the observer correctly recorded the read." That is
   a real reduction, not an elimination, and it must be named in the result as a **third**
   custody source alongside runtime-observation and destination-verification custody, or
   the result overclaims.

---

## 8. Seat discipline for this repair

- Ka'el wrote this contract and **may not pass it**. A separate seat attacks this document
  before any code exists.
- Whoever implements does not review. Whoever reviews does not implement.
- Ka'el passed the withdrawn candidate twice and **may not be the sole breaker** on the
  repaired code.
- No seat spawns or briefs its own reviewer.
- The result file is written by the seat that ran the code, and the PASS is restored by a
  seat that did neither.

## 9. Review must be contract-side

Whoever reviews the implementation must produce, in writing, a walk of §5's manifest —
every entry named, with the executed evidence for it quoted. A review that reads the
suite's output and reports what it saw does not satisfy this requirement, however green
that output is.

---

## 10. Falsifiers for the eventual article

No article may publish from this work unless it can state, and survive, all of:

- D, E, G, or H allows under any declaration variant;
- F blocks, or allows for a different reason than the verified-provenance rule;
- removing only the read binding leaves N-H unchanged;
- removing only transitive traversal leaves N-G unchanged;
- any manifest control is absent, vacuous, or asserts a value the test constructed;
- the governed actor can write the observer, the verification record, or the read
  receipt without the suite naming that failure.

---

**No implementation exists at this commit. No result is claimed. The outside-substrate
reproduction counter remains zero.**
