# Run J — Result

Preregistration: `RUN_J_SHARED_RESET_PREREG_2026-07-28.md`
sha256 `8732e865a1f52b5d490f46b046122c12838929c49daf7c5fdf999057d811904a`
(unchanged since freeze — verify with `shasum -a 256`)

Reproduce: `python3 run_j.py`

## Outcome: PREDICTION 11 v2 CONFIRMED

| # | Frozen condition | Result |
|---|---|---|
| 1 | Both mutations allowed | OK |
| 2 | Control reset leaves witness intact | OK |
| 3 | Control recovery blocks specifically at `W1_FORK` | OK |
| 4 | Reset receipt: witness non-empty before, both stores empty after | OK |
| 5 | Attack recovery ALLOWED — takeover completes | OK |
| 6 | Runs A–I, strict scorecard, gamer checks, CI unchanged | OK |

```
CONTROL  issuer-only reset, witness untouched
         BLOCK send_password_reset [W1_FORK]
         "issuer presents previous_head=None … witness last accepted 6dc8846a…"

ATTACK   admin:history.reset.shared reaches BOTH stores
         ALLOW send_password_reset  — takeover completes
```

Shared-reset receipt: `ffd8b02d12ee4901a88e1990c1ccb6e37ac1a3dfaf65867589c18b8e918f6533`
(deterministic across runs)

The only variable between the two traces is the write reach of the reset
capability. When it reaches one store the fork is caught; when it reaches both,
the two views agree on the same rewritten empty prior and nothing is left to
disagree with.

## What this does and does not establish

**Does:** the witness-anchored defense has a stated boundary, and that boundary
is now a runnable trace rather than a paragraph. A witness is independent only
to the extent that the adversary cannot rewrite or suppress **both** histories
through the same capability. Independent key material is not the line;
independent write capability is.

**Does not:** this is an in-process deterministic simulation. It tests shared
write authority — not key theft, network partition, liveness, concurrency, or
witness suppression. It does not claim every external witness is resettable, and
it does not claim any vendor fails.

Run J is a named experimental run, **not an S8 scorecard row**. The public S1–S7
denominator is unchanged until a separate scoring attack is preregistered.
