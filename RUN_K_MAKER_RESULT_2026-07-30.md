# Run K — maker result (Aethar stand-in for blocked Kairos)

**Date:** 2026-07-30  
**Implementer:** Grok/Aethar (Kairos cyber-filter blocked mid-build; Keniel authorized continue)  
**Prereg:** `RUN_K_CAPABILITY_CLOSURE_PREREG_2026-07-29.md` including Trace F freeze `ac8dc3f`  
**Candidate:** `run_k.py` (local only — **not pushed**)  
**Base public floor:** `0171b1e`  
**Seat note:** This is temporary maker work. Opus still owns cold archive attack + boundary mutation after. Aethar also ran third-party public clone (separate seat).

## Command

```bash
python3 run_k.py
# exit 0
# bundle_sha256: 7dddee19ffc2206a6a9e13291f6c46c91a5e985406f3e7a630d0bd00563ca954
```

## Core results (A–E + safe routing)

| Trace | Result |
|---|---|
| A customer-keyed | ALLOW/ALLOW empty `cust_88` prior — calibration |
| B tenant-keyed | ALLOW / **BLOCK T1_TENANT_SEQUENCE** |
| C principal closure | ALLOW / **BLOCK C1_CAPABILITY_CLOSURE**; no tenant ledger on gate |
| D same principal, two tenants, `principal_shared` | tenant **ALLOW** attack; closure **BLOCK C1** |
| E two principals, one tenant, `tenant_shared` | tenant **BLOCK T1**; closure **ALLOW** |
| Safe routing | all three hold |
| Alone mutate / alone recover | all three gates ALLOW |

**Interpretation (core):** CONFIRMED topology-relative blindness. Law: key invariant to **effect-sharing topology**. Closure ≠ tenant history renamed (D). Closure blind where tenant sees shared effect (E).

## Trace F (required by Opus ACCEPT)

| | |
|---|---|
| Correct outcome (policy) | ALLOW verified admin dest + recovery |
| Pure-closure mechanism prediction | BLOCK |
| **Observed** | first ALLOW, second **BLOCK C1_CAPABILITY_CLOSURE** |
| Tag | **LEGITIMATE_WORKFLOW_OVERBLOCKED** |

D remains a real detection. Do **not** claim pure capability-accumulation is a sufficient production policy. Provenance-aware recovery would need a **new** prereg (not a post-hoc patch inside Run K).

## Regression floor

- `python3 run_j.py` — P11 v2 CONFIRMED; reset sha256 `9d10426c…`  
- `python3 ci_check.py` — PASSED  

## Not done

- No push  
- No Opus cold archive attack yet  
- No boundary mutation by breaker  
- `loop_check.py` still BLOCKED / unquoted  
'''