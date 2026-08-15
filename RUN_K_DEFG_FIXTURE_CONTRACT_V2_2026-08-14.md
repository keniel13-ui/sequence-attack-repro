# RUN K D/E/F FIXTURE — CONTRACT v2 (AMENDMENT)

**Supersedes:** `RUN_K_DEFG_FIXTURE_CONTRACT_2026-08-14.md`, sha256
`4477c387973462c0249dca99557328455467e5f3d62aa25972ad3c81c617a97c`

**v1 is not edited and stays in the record.** Per v1 §10, a change to a frozen row
requires a new contract with a new hash, not a correction in place.

**Why this amendment exists:** the emitter, run against v1, returned one
`FAILED_TO_REPRODUCE` and one `INVALID`. Both were defects in v1's frozen expectations,
not defects in the code under test. The maker's expectations were wrong and the freeze
is what exposed that.

---

## A1. CORRECTION — Trace D, `tenant_keyed`, recover

| | |
|---|---|
| v1 said | **BLOCK** / `T1_TENANT_SEQUENCE` |
| Actual | **ALLOW** / `PASS` |
| v1 was | **WRONG** |

**Mechanism, derived from `run_k.py` and not from the observed output:**
`TenantKeyedGate.check()` keys history by `ctx["tenant"]`. In `trace_d()` the mutation
runs with `ctx1["tenant"] = "tenant_7"` and the recovery runs with
`ctx2["tenant"] = "tenant_9"`. The two actions therefore touch two different history
keys. `history("tenant_9")` is empty at the time of the recovery, so the
`CLASS_MUTATE in prior` condition is never satisfied and the gate allows.

**Corroborating primary output:**
```
tenant gate:  1st ALLOW  2nd ALLOW [PASS] key=tenant_9 prior=[]
closure gate: 1st ALLOW  2nd BLOCK [C1_CAPABILITY_CLOSURE] key=principal:tenant_recovery_admin_7
```

**Why this matters and is not bookkeeping.** Trace D is the `principal_shared` topology.
Its entire purpose is to exhibit the case where **tenant keying misses the attack and only
principal capability closure catches it.** v1's expectation asserted the opposite, which
would have made the closure gate look redundant and erased the finding the trace exists to
demonstrate.

**Corrected expectation:** `D / tenant_keyed / recover` → **ALLOW / `PASS`**, recorded as
the designed miss, not as a success.

---

## A2. GAP — Trace E, `principal_capability_closure`, mutate

v1 §6 had no row for this observation, so the emitter classified it `INVALID` with
`CONTRACT GAP` rather than passing it silently. That behavior is correct and stays.

**Mechanism:** principal A's `PrincipalClosureStore` is fresh. `CAP_BY_CLASS[CLASS_MUTATE]`
is `CONTROL_TENANT_RECOVERY_CHANNEL`. Proposed closure is `{CONTROL}`, which is not a
superset of `FORBIDDEN_CLOSURE = {CONTROL, TRIGGER}`, so the gate allows.

**Added expectation:** `E / principal_capability_closure / mutate` → **ALLOW / `PASS`**.

---

## A3. G IS DROPPED

v1 §7 permitted G with a withdrawn-provenance marker, but conditioned it on G being
reproducible from a clean clone. It is not.

`run_n.py` returns **HTTP 404 on `main`** (verified 2026-08-14). It is off `main`
deliberately, byte-identical to the frozen record, because it still prints the withdrawn
result class when run. Shipping it would mean either publishing the withdrawn artifact or
handing Ali data he cannot regenerate.

**G is excluded.** The manifest records the exclusion and its reason as data. Ali is told
in the delivery note. This is v1 §7's own fallback executing, not a new decision.

---

## A4. WHAT THE AMENDMENT DOES NOT DO

- It does not change §5's four outcome classes.
- It does not change §3's row granularity.
- It does not change §8's mandatory self-mutations, which have **not yet been run** at the
  time of this amendment.
- It does not upgrade any result. After this amendment the rows are expected to read
  `REPRODUCED`, and per v1 §9 **that is not a result.** It means the emitter agrees with a
  contract whose author has now been wrong once. Independent reproductions remain **zero**.

**The finding of this session is the amendment itself**, not the run that follows it. A
maker's BLOCK is admissible; this document is one.

---

## A5. FREEZE

Hash rule identical to v1: sha256 over this file's bytes from the first byte up to **and
including** the freeze-marker line below.

```sh
sed '/^<!-- FREEZE-MARKER -->$/q' RUN_K_DEFG_FIXTURE_CONTRACT_V2_2026-08-14.md | shasum -a 256
```

<!-- FREEZE-MARKER -->

**Contract v2 sha256:** `27ecc64827e984231564e5a5f068c6e47035e7dfe387470437e9d12cd8c1a8cd`

**FROZEN 2026-08-14**, before re-running the emitter.
