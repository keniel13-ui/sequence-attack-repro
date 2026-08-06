# Run N Repair Addendum V2 — Breaker Verdict (Aethar)

**Breaker:** Aethar (Grok)  
**Maker:** Ka'el  
**Candidate:** `RUN_N_REPAIR_ADDENDUM_V2_PREREG_2026-08-06.md`  
**Local + public SHA-256:** `7b9eafe2fd1b7daf2e5d524b173b53a8391e465e5d5f23449df80474b2ccd9af`  
**Public commit:** `98ee065` (HTTP 200; raw bytes hash-match)  
**Date:** 2026-08-06 EDT  
**No implementation exists.** This attack is contract-only.

Candidate not edited during this attack.

---

## Verdict: **BLOCK — three findings.** Do not implement until closed.

The addendum is a serious repair. It names the real failures (absent + hollow controls,
ledger-as-read-source), freezes a real prepare/authorize split, freezes N-H + mutation for
R1, bans hand-built decisions in prose, and promotes the control list into a runner
manifest that fails closed on absence. Ka'el's §7 ways-to-lose are honest, including the
true-by-construction risk that killed five designs.

It still leaves open the **exact failure mode that withdrew the first result**: a control
that *runs*, *prints*, and *asserts* while never exercising the property. The manifest
repairs absence. It does not yet repair hollowness. That gap was named by the maker as a
weak point. It is load-bearing. It is a block.

---

## What is strong (protect these)

| Piece | Why it holds |
|---|---|
| R1 split API + retired monopath on core traces | C7's own comment said the race needed this; now it is the design, not a note |
| Digest equality + head recheck as authorize obligations | Separates "ledger value" from "routing return" if prepare is non-reconciling (see K2) |
| N-H + one-line mutation | Load-bearing test shape is correct in principle |
| R2–R5 control repairs | Address the four published failures by substance, not by renaming |
| §5 MISSING_CONTROL on absence | Exact lesson from C5 and from declaration ablation |
| §7 six ways to lose | Especially #2 (true by construction) and #6 (third custody) |
| Seat discipline §8–§9 | Ka'el correctly barred from sole breaker; contract-side walk required |
| No overclaim | Outside counter zero; not production |

---

## K1 (BLOCK) — hollowness is still unfalsifiable by the runner

§5 freezes:

```text
resolve every manifest entry to an executed control and record its result
exit non-zero if any entry has no executed evidence
```

That catches **C5** (no function, no print).

It does **not** catch **C7** or **C8**. Those had executed functions, printed lines, and
asserted values. They failed because the asserted value was not produced by the gate
(or not the right rule). The addendum forbids hand-constructed decisions **in prose**
(§4 R3, §6) and requires a human walk with "executed evidence quoted" (§9). That is the
same class of review that already failed twice: humans reading green output.

**Required freeze before code (not a suggestion):**

1. **Decision provenance rule.** In every core and control path, `decision` must be the
   return value of `gate.authorize(...)` (or a thin wrapper that does not assign
   `rule` / `allow`). The suite must fail if a control function contains an assignment to
   `decision["rule"]` or constructs a dict that is later treated as a gate verdict —
   static scan of the suite source is acceptable and preferred (grep/AST), because it does
   not depend on a tired reviewer.

2. **Hollow-control definition, machine-checkable where possible:**
   - For any control that asserts a rule code, that code must appear in the returned
     decision object from `authorize` under a failing fixture that is constructed so that
     **only** that rule (or a documented predecessor) can fire.
   - A control that asserts `not allow` without a frozen rule code is INVALID.
   - A control that asserts a rule code that never appears in any authorize return across
     the suite is INVALID (unreachable rule — §7.4 made load-bearing for the suite, not
     only C8).

3. **Manifest record shape.** Each executed entry must store at least:
   `{name, allow, rule, issuer_calls, source: "gate.authorize"}`  
   and the runner must refuse positive class if `source != "gate.authorize"` for any entry
   that claims a policy verdict.

Until (1)–(3) are frozen, an implementer can reintroduce C7 with a green manifest.

---

## K2 (BLOCK) — prepare may make R1 tautological unless non-reconciliation is frozen

§3.1 says prepare performs `routing.preview(...)` and returns:

```text
destination              # what routing returned
observed_value_digest    # digest the observer recorded for that version
```

It does **not** say that `observed_value_digest` is taken from the ledger **without**
being overwritten by `value_digest(destination)`.

If prepare does:

```text
destination = routing.preview(...)
observed_value_digest = value_digest(destination)   # "helpfully" recompute
```

then authorize's first equality is always true at prepare time, and N-H can only fail if
the observer head moves or the prepared object is mutated after prepare. That collapses R1
into "head recheck" (old C7 race), not "read binding." The title claim is then unearned
while the suite can still print P4 on a harness-only plant that rewrites digests after
prepare.

**Required freeze:**

```text
prepare() MUST:
  1. destination := session.routing.preview(...)   # sole source of destination
  2. head := observer.head(object_id)
  3. record := observer.get(head)   # may be None only in the no-version path
  4. observed_value_digest := record.value_digest   # from ledger; NEVER recomputed
       from destination inside prepare
  5. seal PreparedRecovery with both fields as obtained
```

Authorize then independently checks equality. Divergence is possible without post-prepare
mutation of a frozen dataclass. N-H plants Y on the **ledger record** before prepare
(or swaps the ledger under a custody fault model), not by editing `PreparedRecovery`.

If the maker intends post-prepare harness mutation of prepared fields, that is true by
construction and §7.2 should say the candidate is INVALID, not merely a way to lose.

---

## K3 (BLOCK) — CONTROL_MANIFEST lists N-C4 and N-C6 without repair identity

Manifest:

```python
"N-C1", "N-C2", "N-C3", "N-C4", "N-C5", "N-C6", "N-C7",
...
"N-R1",
```

This addendum freezes repairs for C5, C7, C8, C10, R1, and receipts. It does **not**
define N-C4 or N-C6.

From the original body:

- **N-C4** was declaration ablation (HONEST/OMITTED/FORGED).
- **N-C6** was multi-hop lineage, **promoted to core N-G** in addendum v1.

And §6 already requires ablation on every core trace. So either:

- **C4** is satisfied by the core-trace ablation bar and must be marked
  `SATISFIED_BY: core ablation` with no separate hollow function allowed, or  
- **C4** remains a distinct control with its own fixture and print — text required.

- **C6** must be marked `SUPERSEDED_BY: N-G` and removed from the executable manifest, or  
  kept only as an alias that fails if N-G's mutation check fails.

**N-R1** is also undefined as a control object: is it the N-H mutation check, a separate
function, or authorize's digest equality unit test? Freeze one identity.

An implementer facing orphan names will invent functions — the exact path to hollow
controls.

---

## Advisories (do not block alone; freeze or they will become false PASSes)

### A1 — Check order: P4 vs P3 vs P2

Authorize must freeze an order of checks (recommended):

1. observer custody / record integrity (may yield P3 or INVALID_*)  
2. head recheck (P2)  
3. read binding digest equality (P4)  
4. lineage provenance policy (P1 / PASS_*)

Without order, a corrupt digest can be reported as P4 when C8 required P3, and C8
"passes" while never testing integrity — hollow again.

### A2 — C5 "missing observation" operator

R2 freezes a matrix but not the operation that removes evidence (delete observer?
blank head? fail get()?). Freeze one operator used for all four cells.

### A3 — N-H custody labeling

§7.6 correctly requires a third custody source if R1 holds. Result language must not
claim "runtime read" without saying the observer must have correctly sealed that read.
Already almost there; make it mandatory publication sentence, same class as Run N's
custody boundary statement.

### A4 — Positive class name

Withdrawal used `CONFIRMED_BOUNDED_POLICY_UNDER_VERIFICATION_CUSTODY`. V2 does not rename
or re-pin that string. Either re-use it only when §6 holds, or freeze a new class name so
old result files cannot be confused with the repaired bar.

### A5 — Body inheritance

State explicitly: body `10195332…` + addendum v1 `56f54d12…` + this v2, with v2
superseding where conflict. Prevents "which contract?" during code review.

---

## What would make this a PASS

A short **addendum v2.1** (or patch section in a new freeze commit — still contract-before-
code) that freezes only:

1. K1 hollow-control / decision-provenance rules;  
2. K2 non-reconciling prepare algorithm;  
3. K3 C4/C6/R1 manifest identities (satisfied-by / superseded-by / exact function).

No implementation. Same hook discipline. Then a non-Ka'el seat re-breaks. Then code.

---

## What I am not doing

- Not writing `run_n.py` repairs  
- Not "PASS with notes" that an implementer can ignore  
- Not attacking Ka'el's integrity — the contract is strong; the gap is the one that already
  burned this line twice  

## Outside counter

Still **zero**. Nothing in this verdict moves it.

---

**Bottom line:** Freeze hollowness the way you froze absence, freeze prepare so R1 cannot
be a tautology, and clear the orphan manifest names. Then implement.
