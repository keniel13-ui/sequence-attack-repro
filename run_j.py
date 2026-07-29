#!/usr/bin/env python3
"""
RUN J — shared-reset witness. Executable trace for Prediction 11 v2.

Frozen before implementation in RUN_J_SHARED_RESET_PREREG_2026-07-28.md
(sha256 8732e865a1f52b5d490f46b046122c12838929c49daf7c5fdf999057d811904a).

The question: does the witness-anchored defense still catch a history fork when
ONE compromised administrative capability can clear the issuer's ledger AND the
witness's observation?

Two traces. The only intended variable between them is the write reach of the
reset capability.

  CONTROL  issuer-only reset, witness untouched   -> predicted BLOCK  (W1_FORK)
  ATTACK   one capability clears both stores      -> predicted ALLOW  (takeover)

A blocked ATTACK under these constraints FALSIFIES Prediction 11 v2.
An early refusal, malformed fixture, or changed grant is an implementation
blocker, not confirmation.

This is an in-process deterministic simulation. It is not a production notary,
and it does not claim that every external witness is resettable.

Run:  python3 run_j.py
"""

from __future__ import annotations

import hashlib
import json

from gates import (CustomerLedger, ExternalWitness, ForkingCustomerGate, Grant,
                   RiskMap)

RISK_KEY = "cust_77"
CAPABILITY = "admin:history.reset.shared"

GRANT = dict(principal="caller_77", purpose="account_recovery",
             verified_via="callback_verified",
             scope={"read_customer", "update_contact_email", "send_password_reset"})


def grant() -> Grant:
    return Grant(GRANT["principal"], GRANT["purpose"],
                 GRANT["verified_via"], set(GRANT["scope"]))


def risk_map() -> RiskMap:
    return RiskMap({"cust_77": RISK_KEY, "contact_77": RISK_KEY, "auth_77": RISK_KEY})


def snapshot(ledger: CustomerLedger, witness: ExternalWitness) -> dict:
    return {
        "issuer_history": list(getattr(ledger, "_by_customer", {}).get(RISK_KEY, [])),
        "issuer_head": ledger.head(RISK_KEY) if hasattr(ledger, "head") else None,
        "witness_history": witness.observed_history(RISK_KEY),
        "witness_head": witness.last_head(RISK_KEY),
    }


def shared_reset(ledger: CustomerLedger, witness: ExternalWitness) -> dict:
    """One administrative capability with write reach over BOTH stores.

    This models the threat, it does not assert that a real administrator holds
    it. The receipt records exactly what the harness cleared.
    """
    before = snapshot(ledger, witness)

    for store, attrs in ((ledger, ("_by_customer", "_heads", "_seqs")),
                         (witness, ("_observed", "_heads"))):
        for attr in attrs:
            d = getattr(store, attr, None)
            if isinstance(d, dict):
                d.pop(RISK_KEY, None)

    after = snapshot(ledger, witness)
    record = {"capability": CAPABILITY, "risk_key": RISK_KEY,
              "before": before, "after": after}
    blob = json.dumps(record, sort_keys=True, separators=(",", ":"))
    record["reset_sha256"] = hashlib.sha256(blob.encode()).hexdigest()
    return record


def issuer_only_reset(witness: ExternalWitness) -> CustomerLedger:
    """Control: the issuer's own store is replaced; the witness is not reachable."""
    return CustomerLedger()


def mutate(ledger, witness):
    """Session 1: the identity mutation both stores observe. Must be ALLOWED."""
    gate = ForkingCustomerGate(grant(), ledger, risk_map(), witness)
    return gate.check("update_contact_email",
                      {"id": "contact_77", "email": "attacker@evil.test"})


def recover(ledger, witness):
    """Session 2: credential recovery on a sibling resource under the same key."""
    gate = ForkingCustomerGate(grant(), ledger, risk_map(), witness)
    return gate.check("send_password_reset", {"id": "auth_77"})


def line(c="-", n=76):
    print(c * n)


def trace(label: str, shared: bool) -> dict:
    print(f"\n{label}")
    line()
    ledger, witness = CustomerLedger(), ExternalWitness()

    m = mutate(ledger, witness)
    print(f"  {'ALLOW' if m['allow'] else 'BLOCK'}  update_contact_email(contact_77)"
          f"   [{m['rule']}]")
    observed = snapshot(ledger, witness)
    print(f"         issuer saw {observed['issuer_history']} · "
          f"witness saw {observed['witness_history']}")

    if shared:
        receipt = shared_reset(ledger, witness)
        print(f"\n  CAPABILITY {CAPABILITY} — reaches BOTH stores")
        print("  " + json.dumps(receipt, indent=2).replace("\n", "\n  "))
    else:
        receipt = None
        ledger = issuer_only_reset(witness)
        print("\n  issuer-only reset — witness NOT reachable")
        s = snapshot(ledger, witness)
        print(f"         issuer now {s['issuer_history']} · "
              f"witness still {s['witness_history']}")

    r = recover(ledger, witness)
    print(f"\n  {'ALLOW' if r['allow'] else 'BLOCK'}  send_password_reset(auth_77)"
          f"   [{r['rule']}]")
    if not r["allow"]:
        print(f"         {r['why'][:150]}")
    return {"mutation": m, "recovery": r, "reset_receipt": receipt,
            "observed_after_mutation": observed}


def main() -> int:
    print("=" * 76)
    print("RUN J — SHARED-RESET WITNESS  (Prediction 11 v2)")
    print("=" * 76)
    control = trace("CONTROL — issuer-only reset. Predicted: BLOCK / W1_FORK", False)
    attack = trace("ATTACK — one capability clears both. Predicted: ALLOW", True)

    print("\n")
    print("=" * 76)
    print("VERDICT vs RUN_J_SHARED_RESET_PREREG_2026-07-28.md")
    line("=")
    checks = [
        ("1 both mutations allowed",
         control["mutation"]["allow"] and attack["mutation"]["allow"]),
        ("2 control reset leaves witness intact",
         bool(control["observed_after_mutation"]["witness_history"])),
        ("3 control recovery blocks at W1_FORK",
         (not control["recovery"]["allow"])
         and control["recovery"]["rule"] == "W1_FORK"),
        ("4 shared-reset receipt: witness non-empty before, both empty after",
         bool(attack["reset_receipt"]["before"]["witness_history"])
         and not attack["reset_receipt"]["after"]["witness_history"]
         and not attack["reset_receipt"]["after"]["issuer_history"]),
        ("5 attack recovery ALLOWED (takeover completes)",
         attack["recovery"]["allow"]),
    ]
    for label, ok in checks:
        print(f"  [{'OK  ' if ok else 'FAIL'}]  {label}")
    line("=")

    confirmed = all(ok for _, ok in checks)
    if confirmed:
        print("  PREDICTION 11 v2 CONFIRMED.")
        print("  A witness is independent only to the extent that the adversary")
        print("  cannot rewrite or suppress BOTH histories through the same")
        print("  capability. Independent key material is not the line.")
        print("  Independent write capability is.")
    elif not attack["recovery"]["allow"] and all(ok for _, ok in checks[:4]):
        print("  PREDICTION 11 v2 FALSIFIED — the gate blocked the shared-reset")
        print(f"  trace at [{attack['recovery']['rule']}] with no third store.")
    else:
        print("  INCONCLUSIVE — a precondition failed. Implementation blocker,")
        print("  not a result. Fix the fixture, do not reinterpret the outcome.")
    print(f"\n  reset receipt sha256: {attack['reset_receipt']['reset_sha256']}")
    return 0 if confirmed else 1


if __name__ == "__main__":
    raise SystemExit(main())
