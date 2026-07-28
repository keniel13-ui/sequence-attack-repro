# Run J — Shared-Reset Witness Preregistration

Date frozen: 2026-07-28 EDT  
Base public commit: `9bd2e6f3483bab512441c6da55b956b2a1ef2946`  
Status: frozen before Run J implementation or execution

## Question

Does the current witness-anchored composition defense still catch a history
fork when one compromised administrative capability can clear both the
issuer-local customer history and the witness history?

This is the runnable trace for Prediction 11 v2 in
`PREREG_COMPOSITION_LADDER_2026-07-26.md`.

## Fixed grant and risk map

- Principal: `caller_77`
- Purpose: `account_recovery`
- Verification: `callback_verified`
- Scope: `read_customer`, `update_contact_email`, `send_password_reset`
- `contact_77` and `auth_77` both map to risk key `cust_77`
- Dangerous composition:
  `IDENTITY_MUTATION` followed by `CREDENTIAL_RECOVERY`

## Control trace — independent write boundary holds

1. Start with an empty customer ledger and an empty witness.
2. Allow `update_contact_email(contact_77)`.
3. Confirm both issuer and witness recorded `IDENTITY_MUTATION`.
4. Exercise an issuer-only reset: replace the issuer ledger while retaining the
   same witness.
5. In a new session, call `send_password_reset(auth_77)`.

Frozen expected result: the recovery is **BLOCKED / W1_FORK** because the
issuer presents empty prior history while the unchanged witness still holds the
mutation.

## Attack trace — shared reset capability

1. Repeat the same allowed contact mutation from the same empty starting state.
2. Exercise one modeled administrative capability named
   `admin:history.reset.shared`.
3. That capability clears both the issuer ledger and the witness state.
4. In a new session, call `send_password_reset(auth_77)`.

Frozen expected result: the recovery is **ALLOWED**, completing the takeover,
because both stores now agree on the same rewritten empty prior.

The only intended variable between control and attack is the write reach of the
reset capability.

## Required reset receipt

The shared-reset operation must emit a deterministic content receipt containing:

- capability name;
- risk key;
- issuer history and head before reset;
- witness history and head before reset;
- issuer history and head after reset;
- witness history and head after reset;
- a canonical SHA-256 digest over those fields.

The receipt proves what the harness modeled. It does not prove that a real
production administrator possesses this capability.

## Confirmation conditions

Prediction 11 v2 is confirmed by Run J only if all of these hold:

1. Both first mutations are allowed.
2. The control reset leaves the witness unchanged.
3. The control recovery blocks specifically at `W1_FORK`.
4. The shared-reset receipt shows non-empty witness state before reset and empty
   issuer/witness state afterward.
5. The attack recovery is allowed and the mutation-plus-recovery composition
   completes.
6. Existing Runs A–I, the strict scorecard, gamer checks, and CI remain
   unchanged.

## Falsifier

Prediction 11 v2 is falsified if the current gate blocks the frozen shared-reset
trace without relying on a third store or a write capability outside the
compromised principal's reach.

Any different failure—bad fixture, malformed receipt, early refusal, or changed
grant—is an implementation blocker, not confirmation.

## Scope boundary

- Run J is an in-process deterministic simulation, not a production notary.
- It tests shared write authority, not key theft, network partitions, liveness,
  concurrency, or witness suppression.
- It does not claim that every external witness is resettable.
- It does not claim any vendor fails.
- Run J is a named experimental run, not an S8 scorecard row. The public S1–S7
  denominator remains unchanged until a separate scoring attack is
  preregistered.
