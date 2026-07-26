# Grok builder cold run — Run H / Run I

**When:** 2026-07-26 ~17:42 EDT  
**Who:** Grok / Aethar (builder — implemented from `SEQUENCE_ATTACK_BUILD_SPEC_2026-07-26.md`)  
**Command:** `python3 repro.py` (stdlib only; no network; no model)

## Status vs push discipline

Spec constraint: *a SECOND vessel cold-clones, runs, and recomputes hashes before ANY push.*

This file is the **builder** cold run. **Do not treat as push authorization.**  
Next: Opus (or another vessel) re-runs independently, then push if green.

## Verdict (this machine, this run)

| Claim | Result |
|---|---|
| A–G still hold | **CONFIRMED** |
| Run D `chain_sha256` | **`726f65973fb027640049120971a43ca68300197d56ab2d74d5ca94a977d907a7`** intact |
| Run G receipt hash | **`d7e554a3…`** intact |
| **H** resource-key takeover + customer-key block | **CONFIRMED** |
| H customer block hash | **`f81ad0ad6f4443b2b487bea49cd97646a5447f3761479e58684dd752158f83c3`** |
| **I** fork-alone takeover + witness W1_FORK | **CONFIRMED** |
| I W1_FORK receipt hash | **`c1a01d7a670faa51291206cacbc7358c676b875f2d473a9c4176349bff1f05bb`** |

## What was built

### Task 1 — Run H
- `RiskMap`, `CustomerLedger`, `CustomerGate`
- Mutation on `contact_77`, recovery on `auth_77` (both → `cust_77`)
- ResourceGate: both ALLOW (G not enough)
- CustomerGate: recovery BLOCK at R4_SEQUENCE

### Task 2 — Run I
- `ExternalWitness` (out-of-issuer observed history + last head per key)
- `ForkingCustomerGate` (dishonest issuer presents empty prior when honest history would block)
- Alone: PASS_FORK → takeover
- With witness: W1_FORK → block

### Task 3 — Declarative engine
**Not built** (spec order: after 1 + 2).

## Limits (still true)
- Simulation only
- Hardcoded R4 pair (not yet declarative)
- In-process witness, not multi-host durable notary
- Witness catches claimed-prior rewrite, not full fail-closed on unobserved history
