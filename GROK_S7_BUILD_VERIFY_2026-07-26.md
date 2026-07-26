> **STALE HASHES.** Written before receipts became a previous-head chain (commit 311cd58). Every hash below predates that change. The verdicts stand; the digests do not.

# Grok builder cold run — S7 + scorecard

**When:** 2026-07-26 ~18:25 EDT (build); docs reframe ~same session  
**Who:** Grok / Aethar (build); Ka'el PHASE 351 (second vessel — green)

## Status

| Step | Status |
|---|---|
| S7 built + Grok self cold-run | Green — expected card matched |
| Second vessel (Ka'el): numbers + fairness read | Green — witness ledger also wiped; pass earned by external head |
| Docs: proposed-suite reframe + S7 opt-in weakness | Done in README / RESULT / adapter header |
| Push adapter + docs | **Hold for Keniel word** |

## Expected card (matched)

| Implementation | Score | S7 |
|---|---|---|
| always-allow | 2/7 | FAIL |
| always-deny | 0/7 | FAIL |
| rbac + scoped token | 2/7 | FAIL |
| purpose gate, session-keyed | 4/7 | FAIL |
| purpose gate, **customer-keyed** | **6/7** | **FAIL** (author not top) |
| purpose gate, **witness-anchored** | **7/7** | **PASS** |

## Fork model (fairness — Ka'el confirmed)

- Reset is capability-based (`hasattr(issuer_history_reset)`), not class-name rigging.
- Witness-anchored **also** wipes its ledger; survives only via `ExternalWitness` outside the reset.
- **Limitation (documented public-ready):** S7 is opt-in. A third-party gate that withholds `issuer_history_reset` is never forked and could post a high score without an external anchor — and cannot prove history is not self-authored. S7 does not mean “any 7/7 is witness-anchored.”

## Command

```bash
cd claim30_repro
python3 adapter.py
# customer 6/7 FAIL S7, witness 7/7 PASS S7
python3 repro.py   # A–I green; 726f6597 intact
```
