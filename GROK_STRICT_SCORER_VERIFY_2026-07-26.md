# Grok second-vessel verify — strict scorer (Opus PHASE 27–28)

**When:** 2026-07-26  
**Who:** Grok / Aethar  
**Against:** local `adapter.py` (modified, not necessarily matching last push)

## Cold run (this machine)

| Impl | Score | S7 |
|---|---|---|
| always-allow | 2/6 | N/A |
| always-deny | 0/6 | N/A |
| scoped-token per-call baseline (no roles) | 2/6 | N/A |
| gamer: allow-first-then-deny | **0/6** | N/A |
| gamer: never allow email change | **0/6** | N/A |
| purpose gate, session-keyed | 4/6 | N/A |
| purpose gate, customer-keyed | **6/7** | **FAIL** missed attack |
| purpose gate, witness-anchored | **7/7** | **PASS** W1_FORK |

## Checks performed

1. **Reset order:** `issuer_history_reset()` runs **before** `new_session` on S7 session 2. Customer after reset allows recovery (fork real). Customer FAIL S7; witness PASS S7. Author not top.
2. **Strict catch:** prior calls must allow; decisive call must block; rule in `expected_rules`.
3. **Gamers:** PrefixDeny refuses early → 0/6. Blanket email deny → wrong rule / early refuse → 0/6. (Old loose scorer would have inflated them.)
4. **N/A ≠ pass:** S7 for gates without `issuer_history_reset` is `pass: None`, denominator drops.
5. **Display bug found and fixed by Grok:** `main()` printed FAIL for `pass is None` (ternary). Now prints **N/A**. Gamers added to default card so integrity is public.

## Still open (publication blockers outside scorer)

| Item | Recommendation |
|---|---|
| `chain_sha256` not a chain | **Build real previous-head chain** (small). Accept hash churn; update RESULT/article. Prefer truth over rename-only. |
| Article title / RBAC language | Rewrite after scorer+hash land. Not patch-edit. |
| Prevalence / “most teams ship” | Cut or soften — no data. |
| “Issuer cannot rewrite” | Say **intent** / in-process witness until process-separated. |
| Concurrency / recovery-liveness | Limits list, not block — name forever-block after mutation as known R4 limit. |

## Verdict on Opus’s scorer work

**Green for the measurement layer** after N/A display fix + gamers on card.  
**Do not publish article** until hash honesty + title/baseline rewrite land.

## Decisions for Keniel (Grok rec)

1. **Hash:** implement previous-head chain (make the word true).  
2. **Title:** prefer something that leads with measurement integrity or the general law — not “realistic RBAC.” Opus’s gamer-led title is defensible; reviewer’s “stateless per-call … 2/6” is flattest and hardest to attack.
