# RUN K D/E/F/G OFFLINE FIXTURE — FROZEN CONTRACT

**Date:** 2026-08-14
**Author (maker):** Ka'el / Claude, for Keniel
**Requested by:** Ali (`@alikhatersaibreakroom`), DEV comment `3cl0d`, 2026-08-09
**Commitment posted:** DEV `3d313`, 2026-08-14
**Status at freeze:** CONTRACT ONLY. Emitter code does not exist yet.

---

## 0. PROVENANCE DISCLOSURE (required, read first)

This project's method doctrine says *contract before code*, and that **if code already
exists when the contract is written, the contract must say so on its face and may not
claim contract-before-code provenance retroactively.**

Disclosing it:

| Component | Existed before this contract? |
|---|---|
| `trace_d()`, `trace_e()`, `trace_f()` in `run_k.py` | **YES.** Written 2026-07-30, public on `main`. |
| `CustomerKeyedGate`, `TenantKeyedGate`, `CapabilityClosureGate` | **YES.** Same file, same date. |
| `HistoryIndex`, `PrincipalClosureStore`, `RecoveryRoutingState` | **YES.** |
| Multi-hop G trace | **YES**, but in `run_n.py` — the withdrawn artifact. See §7. |
| **JSONL emitter, schema mapping, CLI, outcome classifier** | **NO. These are the contract-before-code portion.** |

So this contract governs **serialization and classification only**. It may not be cited as
evidence that the underlying traces or gates were built under contract-first discipline.
They were not; they predate this document by fifteen days.

---

## 1. WHAT THIS FIXTURE IS

A deterministic, offline, stdlib-only artifact that emits one JSONL row per
`(trace × action × gate)` observation from the public Run K traces, so that a third party
can re-run it and diff the output without trusting any claim made by its author.

## 2. WHAT THIS FIXTURE IS NOT

- It is **not** evidence for `CONFIRMED_BOUNDED_POLICY_UNDER_VERIFICATION_CUSTODY`. That
  result class was withdrawn 2026-08-05 (commit `9f0b352`) and has not been repaired.
- It is **not** evidence that lineage traversal establishes verification custody.
- It is **not** an independent reproduction. The reproduction counter remains **zero**.
- It is **not** a repair of Run N. Run N remains withdrawn and off `main`.

A reader who takes any sentence in the emitted data as support for the withdrawn class is
reading it against this contract.

---

## 3. ROW GRANULARITY (frozen)

**One row per `(trace_id, order_index, gate_kind)`.**

This is deliberate and it is the most useful property of the fixture. Trace D runs the
*same* action through `TenantKeyedGate` **and** `CapabilityClosureGate`. Both may block.
They block **for different reasons**. Emitting one row per gate is what makes that visible
in the data instead of collapsing into a single verdict.

Collapsing to one row per action would destroy the only signal here worth having.

---

## 4. FIELD CONTRACT

Ali's requested schema, mapped against what the code actually produces. Verified by reading
`run_k.py` lines 150–624 on 2026-08-14, not inferred.

| Field | Source | Status |
|---|---|---|
| `event_id` | `f"{trace_id}:{order_index}:{gate_kind}"` | **DERIVED** |
| `actor_id` | `receipt["principal"]` | POPULATED |
| `principal_id` | `receipt["principal"]` | **POPULATED — see caveat below** |
| `tenant_id` | `receipt["tenant"]` | POPULATED |
| `action` | `receipt["tool"]` | POPULATED |
| `object_id` | `receipt["resource"]` | POPULATED |
| `object_version` | — | **EMPTY** |
| `declared_dependencies` | — | **EMPTY** |
| `observed_reads` | `prior_action_classes` / `prior_capability_closure` | **DERIVED** |
| `observed_writes` | ledger `record()` / store `add()`, only when `allow` | **DERIVED** |
| `lineage_edges` | — | **EMPTY** for D/E/F |
| `destination` | `RecoveryRoutingState` destination at that step | POPULATED |
| `verification_record_id` | — | **EMPTY** |
| `causal_parent_ids` | `receipt["previous_head"]` | POPULATED |
| `expected_verdict` | this contract, §6 | POPULATED |
| `actual_verdict` | `receipt["decision"]["allow"]` | POPULATED |
| `reason_code` | `receipt["decision"]["rule"]` | **POPULATED — the load-bearing field** |
| `order_index` | `receipt["sequence_number"]` | POPULATED |

Additional fields emitted beyond the request, because they exist and withholding them would
be a choice: `gate_kind`, `action_class`, `routing_topology`, `semantic_key`,
`chain_sha256`, `why`.

### 4a. Caveats that must ship in the data, not in a README

1. **`actor_id` and `principal_id` are the same value.** Run K has no separate actor concept.
   They are not independent fields here and must not be read as corroborating each other.
2. **`observed_reads` / `observed_writes` are RECONSTRUCTED, not instrumented.** The gate was
   not wired with a read/write tracer. These are derived from what the gate's own receipt
   shows it consulted. **This is a weaker claim than the field name implies** and is exactly
   the seam that produced the Run N defect, where a ledger was the read source rather than a
   witness to it. Every row carries `observed_provenance: "reconstructed"` so the weakness
   travels with the data.
3. **Four fields ship empty.** They are emitted as `null` and listed in the manifest under
   `empty_fields`, with the reason. They are not filled with plausible values.

### 4b. Correction to a public statement

DEV comment `3d313` told Ali that `tenant_id` was among the fields the fixtures could not
populate honestly. **That was wrong.** `tenant_id` is present in every gate receipt via
`ctx["tenant"]`. The statement was made without reading the code. `tenant_id` is populated
here, and the delivery note to Ali must say the earlier claim was incorrect.

`verification_record_id` remains genuinely empty — Trace F calls
`routing.record_verification(...)` so a verification *event* exists, but no identifier is
ever issued for it. Empty, with that reason recorded.

---

## 5. OUTCOME CLASSES (frozen, four, mutually exclusive)

Assigned per row.

| Class | Condition |
|---|---|
| `REPRODUCED` | `actual_verdict == expected_verdict` **AND** `reason_code` is in this contract's expected set for that row |
| `FAILED_TO_REPRODUCE` | `actual_verdict != expected_verdict` |
| `INCONCLUSIVE` | verdict matches but `reason_code` is **not** the expected one |
| `INVALID` | the row could not be produced: trace raised, gate absent, assertion failed |

**`INCONCLUSIVE` is the entire point.** A verdict that matches for an unexpected reason is
not a pass. This is the wrong-reason rule expressed as a data class, and it is what makes
this fixture different from a test suite that only records the decision.

A run whose rows are all `REPRODUCED` proves the emitter agrees with this contract. It
proves nothing about whether the gate design is correct.

---

## 6. EXPECTED VERDICTS AND REASON CODES (frozen before running the emitter)

Taken from the Run K prereg and the trace docstrings, **not** from observed output.

| Trace | Gate | Action | Expected verdict | Expected `reason_code` |
|---|---|---|---|---|
| D | `tenant_keyed` | mutate | ALLOW | `PASS` |
| D | `tenant_keyed` | recover | **BLOCK** | `T1_TENANT_SEQUENCE` |
| D | `principal_capability_closure` | mutate | ALLOW | `PASS` |
| D | `principal_capability_closure` | recover | **BLOCK** | `C1_CAPABILITY_CLOSURE` |
| E | `tenant_keyed` | mutate | ALLOW | `PASS` |
| E | `tenant_keyed` | recover | **BLOCK** | `T1_TENANT_SEQUENCE` |
| E | `principal_capability_closure` (B) | recover | **ALLOW** | `PASS` |
| F | `principal_capability_closure` | mutate | ALLOW | `PASS` |
| F | `principal_capability_closure` | recover | **BLOCK** | `C1_CAPABILITY_CLOSURE` |

**Note on E and F, stated up front so nobody reports them as failures:**

- **E's closure gate ALLOWS the recovery.** Principal B has a fresh closure store, so the
  forbidden closure is never assembled. Only the tenant-keyed gate catches E. This is a
  known limit of principal closure, not a defect in the fixture.
- **F BLOCKS and that is the correct recorded outcome for the mechanism, while ALLOW is the
  correct outcome for the user.** Pure capability closure over-blocks legitimate work. The
  Run K prereg forbids consulting `verified_destination` to patch this after the fact.
  **F is a cost, not a win**, and the fixture must not present it as one.

Any row whose observed `reason_code` differs from this table is `INCONCLUSIVE` and must be
reported, not reconciled.

---

## 7. THE G ROWS (multi-hop) — HANDLING

G originates in `run_n.py`, the **withdrawn** artifact whose controls C5/C7/C8/C10 were
found absent or vacuous.

Therefore:

- G rows **are** included, per the commitment to Ali.
- **Every G row carries `source_run: "run_n"` and `source_status: "WITHDRAWN"`** as ordinary
  data fields, not a footnote.
- G rows are **excluded from all summary counts** by default. The CLI requires an explicit
  `--include-withdrawn` flag to count them.
- No G row may be classified `REPRODUCED`. The maximum class available to a G row is
  `INCONCLUSIVE`, because the controls that would have made a G pass meaningful are the
  four that failed.

If honoring this proves impossible without importing withdrawn machinery into the clean
D/E/F path, **G is dropped and Ali is told**, rather than contaminating the clean rows.

---

## 8. HOW A STRANGER FALSIFIES THIS

1. `git clone`, checkout `main`, run the emitter. No network, no key, no install.
2. Diff the emitted JSONL against the committed `expected.jsonl`. Any difference is a finding.
3. Delete a gate's block condition and re-run. Rows must move to `FAILED_TO_REPRODUCE`. If
   they do not, the fixture is not reading the gate and this contract is void.
4. Change an `expected_reason_code` in §6 to a wrong value. Rows must move to `INCONCLUSIVE`.
   If they stay `REPRODUCED`, the reason check is vacuous — the C8 defect, again.

**Steps 3 and 4 are mandatory before delivery.** They are this artifact's own controls, and
per §5 a suite that cannot fail is not a suite. If either mutation fails to move the rows,
delivery is blocked.

---

## 9. MAKER LIMITATION

I am the maker. Under this project's doctrine a maker's **BLOCK is admissible** and a
maker's **PASS is worthless**.

So: if steps 8.3 or 8.4 fail, that is a real finding and I may report it. If everything
passes, that is **not** a result. It means the artifact is ready to be handed to someone
else. Nothing in this contract, and nothing the emitter prints, may be reported as
verification.

The reproduction counter stays at **zero** until someone who is not Keniel and not an agent
in this workspace runs it.

---

## 10. FREEZE

Rows in §4, §5, §6, §7 do not move after the hash below is recorded. If they must change,
the change is a new contract with a new hash, and the old one stays in the record.

**Hash rule, so a stranger can reproduce it exactly:** the sha256 is taken over this file's
bytes from the first byte up to **and including** the freeze-marker line below. Everything
after that line is excluded. One command:

```sh
sed '/^<!-- FREEZE-MARKER -->$/q' RUN_K_DEFG_FIXTURE_CONTRACT_2026-08-14.md | shasum -a 256
```

<!-- FREEZE-MARKER -->

**Contract sha256:** `4477c387973462c0249dca99557328455467e5f3d62aa25972ad3c81c617a97c`

**FROZEN 2026-08-14.** Emitter code did not exist at this hash.
