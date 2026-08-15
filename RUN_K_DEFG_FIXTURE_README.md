# Run K D/E/F offline JSONL fixture

Requested by [@alikhatersaibreakroom](https://dev.to/alikhatersaibreakroom) in
[DEV comment `3cl0d`](https://dev.to/alikhatersaibreakroom/comment/3cl0d).

Stdlib only. No network, no key, no install, no third-party package.

```sh
python3 fixture_defg.py --out expected.jsonl --manifest expected_manifest.json
python3 fixture_defg_mutation_check.py     # the fixture's own controls
```

---

## What this is

One JSONL row per **(trace × action × gate)** over the public Run K traces `D`, `E`, `F`.

The row granularity is the point. Trace D runs the *same* action through
`TenantKeyedGate` **and** `CapabilityClosureGate`, and they reach different verdicts for
different reasons. Emitting one row per gate is what makes that visible; collapsing to one
verdict per action would delete the only signal worth having.

## What this is not

- **Not** evidence for `CONFIRMED_BOUNDED_POLICY_UNDER_VERIFICATION_CUSTODY`. That class was
  withdrawn on 2026-08-05, commit
  [`9f0b352`](https://github.com/keniel13-ui/sequence-attack-repro/commit/9f0b352), and has
  not been repaired.
- **Not** evidence that lineage traversal establishes verification custody.
- **Not** an independent reproduction. **Independent reproductions: 0.**
- **Not** a repair of Run N.

## Governing contracts (ship with the data, read them first)

| File | sha256 | Role |
|---|---|---|
| `RUN_K_DEFG_FIXTURE_CONTRACT_2026-08-14.md` | `4477c387…17a97c` | v1, frozen **before** any emitter code |
| `RUN_K_DEFG_FIXTURE_CONTRACT_V2_2026-08-14.md` | `27ecc648…c1a8cd` | v2 amendment, frozen before re-running |

Reproduce either hash:

```sh
sed '/^<!-- FREEZE-MARKER -->$/q' <file> | shasum -a 256
```

**v1 is not edited.** It is kept wrong, in the record, next to the amendment that corrects
it. Quietly editing a frozen artifact to agree with a later finding is the thing this whole
repo argues against.

---

## The four outcome classes

| Class | Meaning |
|---|---|
| `REPRODUCED` | verdict matches **and** `reason_code` matches the frozen expectation |
| `FAILED_TO_REPRODUCE` | verdict does not match |
| `INCONCLUSIVE` | **verdict matches but the reason does not** |
| `INVALID` | row could not be produced, or no frozen expectation covers it |

`INCONCLUSIVE` is the reason this exists rather than a test suite. A verdict that lands for
an unexpected reason is not a pass. If you log only the decision, a control that blocks for
an unrelated cause is indistinguishable from one that works.

---

## What v1 got wrong, and how

v1 froze `D / tenant_keyed / recover` as **BLOCK / `T1_TENANT_SEQUENCE`**. The emitter
returned **ALLOW / `PASS`** and classified it `FAILED_TO_REPRODUCE`.

v1 was wrong. `TenantKeyedGate` keys history by tenant; in `trace_d()` the mutation runs on
`tenant_7` and the recovery on `tenant_9`, so `history("tenant_9")` is empty and the
sequence condition never fires:

```
tenant gate:  1st ALLOW  2nd ALLOW [PASS] key=tenant_9 prior=[]
closure gate: 1st ALLOW  2nd BLOCK [C1_CAPABILITY_CLOSURE] key=principal:tenant_recovery_admin_7
```

**That miss is the entire point of Trace D.** It is the `principal_shared` topology where
tenant keying cannot see the attack and only principal capability closure catches it. The
v1 expectation asserted the opposite, which would have made the closure gate look redundant.

Had the emitter been written first and the expectations back-filled from its output, all ten
rows would read `REPRODUCED` and this fixture would ship encoding a misunderstanding. The
freeze is what caught it. See `RUN_K_DEFG_FIXTURE_CONTRACT_V2_2026-08-14.md` §A1.

---

## Field notes (read before interpreting a row)

- **`observed_reads` / `observed_writes` are RECONSTRUCTED, not instrumented.** The gates
  were never wired with a read tracer. These fields report what each gate's own receipt
  shows it consulted, which is a **weaker claim than the field names imply**. Every row
  carries `observed_provenance: "reconstructed"` so the weakness travels with the data
  instead of living in this file.
- **`actor_id` and `principal_id` are the same value.** Run K has no separate actor concept.
  They do not corroborate each other.
- **Four fields are always `null`**, listed in the manifest under `empty_fields` with
  reasons: `object_version`, `declared_dependencies`, `lineage_edges`,
  `verification_record_id`. They are not filled with plausible-looking values.
- **`reason_code` is the load-bearing field.** It carries the rule that actually fired:
  `PASS`, `T1_TENANT_SEQUENCE`, `C1_CAPABILITY_CLOSURE`, `R1_SCOPE`, `R4_SEQUENCE`.
- **Trace F blocks, and that is a cost, not a win.** Pure capability closure over-blocks
  legitimate work. The Run K prereg forbids patching it by consulting `verified_destination`
  after the fact.

---

## Multi-hop G is not included

G was requested and is **not here.** It exists only in `run_n.py`, the withdrawn artifact,
which is deliberately not on `main`. Shipping it would mean either publishing withdrawn
machinery or handing over data that cannot be regenerated from a clean clone. Contract v1
§7 required G to be reproducible from `main` or dropped; it is not, so it is dropped. See
v2 §A3.

---

## How to falsify this

1. Clone, run the emitter, diff against the committed `expected.jsonl`. Any difference is a
   finding.
2. Break a gate's block condition. Rows expecting BLOCK **must** move to
   `FAILED_TO_REPRODUCE`. If they do not, the fixture is not reading the gate.
3. Corrupt an `expected_reason_code`. That row **must** move to `INCONCLUSIVE`. If it stays
   `REPRODUCED`, the reason check is vacuous.

Steps 2 and 3 are automated in `fixture_defg_mutation_check.py`, and each mutation is
**proven to land** before its result is read — a patch that matches nothing would otherwise
run against a healthy tree, pass, and report the guard alive.

---

## Maker limitation

This was produced by the maker. A maker's BLOCK is admissible; a maker's PASS is worthless.
A clean run here means the artifact is ready to hand to someone who is not the maker.

**Independent reproductions: 0.** That number does not move until someone else runs it.
