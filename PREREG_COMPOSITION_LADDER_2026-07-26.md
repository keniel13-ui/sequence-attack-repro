# PRE-REGISTRATION — The Composition-Scope Ladder and its Predicted Failures
*Locked 2026-07-26, BEFORE anyone reports holes #10 or #11. CLAIM method applied to the ladder itself.*

## The law (stated as a falsifiable claim)
> A composition check is blind to any attacker whose reach exceeds the scope its history is keyed to. And when the attacker's reach includes the issuer, the anchor must sit outside the issuer.

## The ladder observed so far (each rung is a run in the suite)
| Key the history is scoped to | Blind when the attacker… | Run |
|---|---|---|
| SESSION | spans two sessions | F |
| RESOURCE | spans two resources under one customer | H |
| CUSTOMER | forges the issuer's own history (fork) | I (fork alone) |
| Anchored OUTSIDE the issuer | — holds against all of the above | I (with witness) |

Monotone: every defense is defeated by widening the attacker's reach by exactly one scope level, and every fix widens the key by exactly one level.

## Pre-registered predictions (dated, before observation)
**PREDICTION 10 — cross-customer / org scope.**
The customer-keyed check will be blind to an attacker whose reach spans *multiple customers under one org* — e.g. a compromised admin or service account acting across accounts. The fix will require keying the invariant at the org/tenant risk-object level.
*Falsifier:* a customer-keyed check that catches a cross-customer composition WITHOUT widening the key.

**PREDICTION 11 — shared-trust-root witness.**
The external witness will be blind if the witness and the issuer share a trust root (same key material / same operator). Detecting issuer↔witness collusion requires an *independent* trust root.
*Falsifier:* a witness sharing a trust root with the issuer that provably catches a colluding fork.

## What the law claims beyond these two
It claims the SHAPE of every future hole: widen attacker reach one scope level → the current key goes blind → the fix widens the key one level → repeat, until the key names the true risk object AND the anchor sits outside the issuer. The terminal rung is not a coincidence — it is the general result that a verifier cannot certify its own history to a non-issuer. (This is the Truth-First principle: the verifier cannot live inside the agent it governs, here proven at the receipt layer with a hash rather than asserted in prose.)

## Honest conflict disclosure
We author both this benchmark and a gate (PurposeGate/ResourceGate/CustomerGate + witness) scored by it. Defense, held in the open: we score our own gate including its known weaknesses (the six already written down), and the suite is runnable against ANY gate via an adapter. A benchmark that only its author can run is not a benchmark.

## The rule
No moving these predictions after the fact. When hole #10 or #11 is reported by anyone, it is read against THIS file. If the law holds, the reporter finds a hole we already named. If a falsifier lands, the law is wrong and we say so, dated.

---

## ADDENDUM v2 — refined 2026-07-26 evening, after external review

The original Prediction 10 and 11 text above is **retained verbatim and unchanged**.
Both were criticised for the same defect: they named a *scope* rather than a
*runnable trace*, and Prediction 11 as written was close to a tautology — if the
adversary can rewrite both histories and no third store exists, "provably catches"
contradicts its own threat model.

Refined below. Still dated before anyone has reported either hole. Where the
article and this file differ in wording, **this file is the record and the
article is the restatement.**

**PREDICTION 10 v2 — shared tenant recovery authority.**
A customer-keyed history will miss a tenant-level recovery-administrator mutation
followed by credential recovery for a *different* customer under that tenant. The
customer gate sees clean history for the second customer. The semantic risk key is
`tenant_id` (or `privileged_identity_id`), not merely a wider label.
*Falsifier:* a customer-keyed check that catches that trace without widening the key.

**PREDICTION 11 v2 — shared-reset witness.**
A fault injection that clears issuer-local history *and* witness history through one
compromised administrative capability. The witness-anchored gate will fail to detect
the fork, because both views agree on the rewritten empty prior.
*Falsifier:* the current gate blocks that frozen trace without relying on a third
store or a capability outside the compromised principal's reach.

**Stated separately, as a boundary rather than a prediction:** a witness is
independent only to the extent that the adversary cannot rewrite or suppress both
histories through the same capability. Independent key material is not the line.
Independent write capability is.
