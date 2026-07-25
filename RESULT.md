# KILL TEST — RESULT (run 2026-07-25, read against the locked pre-registration)

Run it yourself: `python3 repro.py` (stdlib only, no network, no model call)

## Verdict against the pre-registered predictions

| # | Prediction | Result |
|---|---|---|
| P1 | A standard guardrail PASSES the attack | **CONFIRMED** — 4/4 steps allowed, account takeover succeeded |
| P2 | The gate BLOCKS it with a replayable receipt | **CONFIRMED** — refused at step 3; receipt hash identical across runs (`6b883b45…`) |
| P3 | 3+ experienced devs say "run that again" | **PENDING** — human test, not run yet |

Honesty check (not pre-registered, added because without it the gate could be a
blanket deny): the **same** `update_contact_email` call, in an honest sequence
with a verified caller, is **ALLOWED**. Same action, same permissions, different
sequence, different verdict.

## Kill criteria

| # | Criterion | Status |
|---|---|---|
| 1 | An off-the-shelf tool already catches it | **PARTIALLY OPEN — see below** |
| 2 | Can't be built in a day | **NOT TRIGGERED** — built in well under a day |
| 3 | Engaged devs shrug | **PENDING** |

### The honest state of kill criterion 1

Run B's attack contains a laundered instruction inside untrusted ticket text. A
prompt-injection classifier *might* flag that — probabilistically. So Run B alone
does not clear criterion 1.

**Run D does.** In Run D the caller is verified, there is no untrusted input at
all, every tool is permitted, and every action class is inside the granted
purpose. There is nothing for a classifier to classify and nothing for RBAC to
deny. The only thing wrong is the **composition** — an identity mutation followed
by a credential recovery in one session. That is refused by R4, deterministically,
with a receipt.

That is the claim that needs to survive developer review: *not* "we catch prompt
injection" — everyone says that — but "we refuse a sequence in which no single
step is wrong, and we hand you the proof."

## What fired, and where

```
RUN A  baseline (RBAC + token + scope + rate limit)  -> 4/4 ALLOW -> takeover
RUN B  purpose gate vs the attack                    -> BLOCK at step 3 [R2_PURPOSE]
RUN C  same action, honest sequence                  -> ALLOW  (not a blanket deny)
RUN D  everything in policy, only composition wrong  -> BLOCK   [R4_SEQUENCE]
```

## Known weaknesses — stated before anyone else finds them

1. **The ablations are shallow.** They are not cumulative, so disabling R3 still
   shows R2 catching first. They demonstrate the catch point moves; they do not
   yet prove each rule is independently load-bearing the way the CLAIM-30
   five-ablation set did.
2. **This is a simulation, not an integration.** No real agent framework is
   wired in. Before showing this to developers as a tool rather than a proof,
   it needs to sit on a real tool-call path (MCP server or an agent SDK).
3. **R4 is currently a hardcoded composition rule.** One pair of action classes.
   A real version needs the dangerous compositions to be declarable, and that
   list is the actual product surface.
4. **P3 is untested.** Two of three predictions are confirmed by code. The third
   is a human judgment and nobody has looked at it yet.
