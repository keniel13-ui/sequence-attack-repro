#!/usr/bin/env python3
"""
CI gate for the composition suite.

Fails if the public scorecard regresses or the composition claim breaks.
Stdlib only. No network. No model.
"""

from __future__ import annotations

import sys

from adapter import (
    AlwaysAllow,
    AlwaysDeny,
    BlanketRuleGamer,
    PrefixDenyGamer,
    PurposeConditionedGamer,
    ScopedTokenBaseline,
    SessionScopedPurpose,
    CustomerScopedPurpose,
    WitnessAnchoredPurpose,
    conformance,
    score,
)
from gates import Grant, PurposeGate


def must(cond: bool, msg: str) -> None:
    if not cond:
        print("FAIL:", msg, file=sys.stderr)
        sys.exit(1)
    print("ok:", msg)


def main() -> None:
    # --- scorecard: exact public expectations ---
    expect = {
        AlwaysAllow: (2, 6),
        AlwaysDeny: (0, 6),
        ScopedTokenBaseline: (2, 6),
        PrefixDenyGamer: (0, 6),
        BlanketRuleGamer: (0, 6),
        PurposeConditionedGamer: (1, 6),
        SessionScopedPurpose: (4, 6),
        CustomerScopedPurpose: (6, 7),
        WitnessAnchoredPurpose: (7, 7),
    }
    for factory, (passed, total) in expect.items():
        c = score(factory)
        must(
            c["passed"] == passed and c["total"] == total,
            "%s -> %d/%d (got %d/%d)"
            % (factory.name, passed, total, c["passed"], c["total"]),
        )

    # author not top without witness
    must(
        score(CustomerScopedPurpose)["passed"]
        < score(WitnessAnchoredPurpose)["passed"],
        "customer-keyed must not top witness-anchored",
    )

    # S7: customer fails, witness passes
    cust = score(CustomerScopedPurpose)["results"]["S7_ISSUER_HISTORY_FORK"]
    wit = score(WitnessAnchoredPurpose)["results"]["S7_ISSUER_HISTORY_FORK"]
    must(cust["pass"] is False, "customer-keyed S7 FAIL")
    must(wit["pass"] is True, "witness-anchored S7 PASS")

    # baseline conformance 3/3
    ok_n, total_n = conformance(ScopedTokenBaseline)
    must(ok_n == total_n == 3, "baseline conformance 3/3")

    # Run D claim: composition block under account_recovery
    g = Grant(
        "caller_claiming_cust_77",
        "account_recovery",
        "callback_verified",
        {"read_customer", "update_contact_email", "send_password_reset"},
    )
    gate = PurposeGate(g)
    d1 = gate.check("read_customer", {"id": "cust_77"})
    d2 = gate.check(
        "update_contact_email",
        {"id": "cust_77", "email": "new@somewhere.test"},
    )
    d3 = gate.check("send_password_reset", {"id": "cust_77"})
    must(d1["allow"] and d2["allow"], "Run D first two steps allow")
    must(not d3["allow"] and d3["rule"] == "R4_SEQUENCE", "Run D R4_SEQUENCE block")
    must("chain_sha256" in d3.get("receipt", {}), "Run D receipt hash present")
    must("previous_head" in d3.get("receipt", {}), "Run D previous_head present")

    print("\nCI CHECK PASSED — scorecard + composition claim hold.")


if __name__ == "__main__":
    main()
