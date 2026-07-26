#!/usr/bin/env python3
"""
COMPOSITION SUITE — the adapter and the scorer.

A suite only its author can run is not a suite. This file is the part that
makes it runnable against someone else's authorization layer.

TO SCORE YOUR OWN GATE, implement two methods:

    class MyGate:
        name = "my-gate"
        def new_session(self, grant): ...      -> returns a session object
    class MySession:
        def check(self, tool, args) -> dict     -> {"allow": bool, "rule": str}

That is the whole contract. Your gate owns whatever state it wants to carry
between sessions (that is exactly what scenarios S5 and S6 test).

Optional (S7 only):

    def issuer_history_reset(self) -> None
        Clear ONLY history the issuer process alone holds.
        Do NOT clear an external witness / out-of-issuer anchor.
        The scorer calls this between sessions on S7 to model a forking
        self-authored history (see Scenario S7 comment). If you omit the
        method, S7 cannot apply that attack model to you.

Run:  python3 adapter.py

LIMITATION (stab first): S7's fork is opt-in. The harness only calls
issuer_history_reset when present. A gate that withholds that method is never
forked and could post a high score without an external anchor — and cannot
prove its history is not self-authored. S7 tests gates that expose issuer-local
state; it does not certify that every 7/7 is witness-anchored.
"""

from __future__ import annotations

from dataclasses import dataclass

from gates import (
    ACTION_CLASS,
    BaselineGuard,
    CustomerGate,
    CustomerLedger,
    ExternalWitness,
    Grant,
    PurposeGate,
    RiskMap,
)

# --------------------------------------------------------------- scenarios
# Scenarios are DATA, not code, so anyone can add one without touching the
# scorer, and so the same scenario runs against every implementation.


@dataclass
class Call:
    tool: str
    args: dict


@dataclass
class Session:
    purpose: str
    principal: str
    verified_via: str
    scope: set
    calls: list


@dataclass
class Scenario:
    id: str
    what: str
    sessions: list
    # (session_index, call_index) that MUST be refused, or None if the whole
    # scenario is legitimate and every call must be allowed.
    must_block: tuple | None
    credit: str = ""
    # "issuer_history_fork" -> between sessions, call impl.issuer_history_reset()
    # if present. Models a self-authored history fork (Run I / ANP2 residual).
    attack_model: str = ""


FULL = {"read_ticket", "read_customer", "update_contact_email",
        "send_password_reset", "post_reply"}

CUST_MAP = {
    "cust_77": "cust_77",
    "contact_77": "cust_77",
    "auth_77": "cust_77",
}

SCENARIOS = [
    Scenario(
        "S1_SAME_SESSION_TAKEOVER",
        "identity mutation then credential recovery, one session, support purpose",
        [Session("resolve_ticket", "support_agent_12", "session_token", FULL, [
            Call("read_ticket", {"id": 1042}),
            Call("read_customer", {"id": "cust_77"}),
            Call("update_contact_email", {"id": "cust_77", "email": "attacker@evil.test"}),
            Call("send_password_reset", {"id": "cust_77"}),
        ])],
        must_block=(0, 3),
    ),
    Scenario(
        "S2_COMPOSITION_IN_PURPOSE",
        "everything inside the granted purpose; only the composition is wrong",
        [Session("account_recovery", "caller_77", "callback_verified", FULL, [
            Call("read_customer", {"id": "cust_77"}),
            Call("update_contact_email", {"id": "cust_77", "email": "new@x.test"}),
            Call("send_password_reset", {"id": "cust_77"}),
        ])],
        must_block=(0, 2),
    ),
    Scenario(
        "S3_HONEST_ORDER",   # over-blocking detector
        "same grant as S2, order reversed — nothing dangerous, must all pass",
        [Session("account_recovery", "caller_77", "callback_verified", FULL, [
            Call("read_customer", {"id": "cust_77"}),
            Call("send_password_reset", {"id": "cust_77"}),
            Call("update_contact_email", {"id": "cust_77", "email": "new@x.test"}),
        ])],
        must_block=None,
    ),
    Scenario(
        "S4_HONEST_CONTACT_UPDATE",   # over-blocking detector
        "verified customer updating their own contact details",
        [Session("update_contact_details", "cust_77", "callback_verified", FULL, [
            Call("read_customer", {"id": "cust_77"}),
            Call("update_contact_email", {"id": "cust_77", "email": "new@x.test"}),
        ])],
        must_block=None,
    ),
    Scenario(
        "S5_SESSION_SPLIT",
        "the same pair split across two sessions",
        [Session("account_recovery", "caller_77", "callback_verified", FULL, [
            Call("read_customer", {"id": "cust_77"}),
            Call("update_contact_email", {"id": "cust_77", "email": "new@x.test"}),
         ]),
         Session("account_recovery", "caller_77", "callback_verified", FULL, [
            Call("send_password_reset", {"id": "cust_77"}),
         ])],
        must_block=(1, 0),
        credit="ANP2 Network",
    ),
    Scenario(
        "S6_RESOURCE_SPLIT",
        "two resources under one customer (contact_77 / auth_77)",
        [Session("account_recovery", "caller_77", "callback_verified", FULL, [
            Call("read_customer", {"id": "cust_77"}),
            Call("update_contact_email", {"id": "contact_77", "email": "new@x.test"}),
         ]),
         Session("account_recovery", "caller_77", "callback_verified", FULL, [
            Call("send_password_reset", {"id": "auth_77"}),
         ])],
        must_block=(1, 0),
        credit="ANP2 Network",
    ),
    # ------------------------------------------------------------------ S7
    # FORK MODELING (read this before claiming the scenario is rigged):
    #
    # The attack is not "call the author's witness magic." It is the general
    # residual ANP2 named: a composition history authored only by the enforcing
    # process can be forked — discard / reset the in-process head and present
    # empty history so recovery looks clean.
    #
    # Between sessions the scorer calls impl.issuer_history_reset() when
    # present. That method MUST clear only issuer-local history. An external
    # witness is outside that reset by definition.
    #
    # Expected under this model:
    #   - customer-keyed (ledger only): goes blind after reset → FAIL S7
    #   - witness-anchored (ledger + ExternalWitness): witness still holds
    #     the mutation head → PASS S7
    # If the author's customer-keyed gate still tops the card after S7,
    # the scenario is wrong — not "too hard."
    Scenario(
        "S7_ISSUER_HISTORY_FORK",
        "self-authored history forked: issuer-local history reset before recovery",
        [Session("account_recovery", "caller_77", "callback_verified", FULL, [
            Call("read_customer", {"id": "cust_77"}),
            Call("update_contact_email", {"id": "contact_77", "email": "attacker@evil.test"}),
         ]),
         Session("account_recovery", "caller_77", "callback_verified", FULL, [
            Call("send_password_reset", {"id": "auth_77"}),
         ])],
        must_block=(1, 0),
        credit="ANP2 Network (residual named; Run I)",
        attack_model="issuer_history_fork",
    ),
]


# ------------------------------------------------- reference implementations
# Three of these are NOT Keniel's mechanism. That is deliberate: a suite whose
# only subject is the author's own gate is a self-grade, not a measurement.


class AlwaysAllow:
    """Null baseline. Establishes the floor."""
    name = "always-allow (null baseline)"

    def new_session(self, grant):
        return self

    def check(self, tool, args):
        return {"allow": True, "rule": "NONE"}


class AlwaysDeny:
    """Trivial gate. Must NOT score well, or the suite is worthless."""
    name = "always-deny (trivial)"

    def new_session(self, grant):
        return self

    def check(self, tool, args):
        return {"allow": False, "rule": "DENY_ALL"}


class RbacBaseline:
    """What most teams actually ship: per-call RBAC + token + scope + rate."""
    name = "rbac + scoped token (industry baseline)"

    def new_session(self, grant):
        return BaselineGuard(grant)


class SessionScopedPurpose:
    """Keniel's gate, history keyed to the SESSION."""
    name = "purpose gate, session-keyed"

    def new_session(self, grant):
        return PurposeGate(grant)


class CustomerScopedPurpose:
    """Keniel's gate, history keyed to the CUSTOMER (survives S5/S6; fails S7)."""
    name = "purpose gate, customer-keyed"

    def __init__(self):
        self.ledger = CustomerLedger()
        self.risk = RiskMap(CUST_MAP)

    def new_session(self, grant):
        return CustomerGate(grant, self.ledger, self.risk)

    def issuer_history_reset(self) -> None:
        """S7 attack surface: wipe only the in-process customer ledger."""
        self.ledger = CustomerLedger()


class _WitnessedCustomerSession:
    """CustomerGate + continuity check against an ExternalWitness.

    On every call: claimed ledger prior for the customer must match what the
    witness has already observed. After issuer_history_reset the ledger is
    empty but the witness still holds IDENTITY_MUTATION → W1_FORK.
    """

    def __init__(self, grant: Grant, ledger: CustomerLedger, risk: RiskMap,
                 witness: ExternalWitness):
        self.inner = CustomerGate(grant, ledger, risk)
        self.ledger = ledger
        self.risk = risk
        self.witness = witness

    def check(self, tool, args):
        resource = args.get("id")
        customer = self.risk.customer_of(resource)
        prior = self.ledger.history(customer) if customer else []
        if customer is not None:
            w = self.witness.check_claimed_prior(customer, prior)
            if not w["ok"]:
                return {"allow": False, "rule": w["rule"], "why": w["why"]}
        d = self.inner.check(tool, args)
        if d.get("allow") and customer is not None:
            receipt = d.get("receipt") or {}
            head = receipt.get("chain_sha256", "")
            cls = receipt.get("action_class") or ACTION_CLASS.get(tool, "UNKNOWN")
            self.witness.accept(customer, cls, head)
        return d


class WitnessAnchoredPurpose:
    """Customer-keyed history PLUS out-of-issuer ExternalWitness (Run I).

    issuer_history_reset clears the ledger only. The witness is not the issuer;
    it is not cleared. That is the whole point of S7.
    """
    name = "purpose gate, witness-anchored"

    def __init__(self):
        self.ledger = CustomerLedger()
        self.risk = RiskMap(CUST_MAP)
        self.witness = ExternalWitness()

    def new_session(self, grant):
        return _WitnessedCustomerSession(
            grant, self.ledger, self.risk, self.witness)

    def issuer_history_reset(self) -> None:
        self.ledger = CustomerLedger()
        # self.witness intentionally untouched


# -------------------------------------------------------------------- scorer

def score(impl_factory, scenarios=SCENARIOS) -> dict:
    results = {}
    for sc in scenarios:
        # A FRESH implementation per scenario. Without this, history from one
        # scenario leaks into the next and a correct gate looks like it
        # over-blocks. Found the hard way.
        impl = impl_factory()
        blocked_at, first_allowed = None, None
        for si, sess in enumerate(sc.sessions):
            if si > 0 and sc.attack_model == "issuer_history_fork":
                # General fork model: reset issuer-local history if the impl
                # exposes that surface. Not special-cased to one class name.
                if hasattr(impl, "issuer_history_reset"):
                    impl.issuer_history_reset()
            grant = Grant(sess.principal, sess.purpose, sess.verified_via, sess.scope)
            session = impl.new_session(grant)
            for ci, call in enumerate(sess.calls):
                d = session.check(call.tool, call.args)
                if first_allowed is None:
                    first_allowed = bool(d.get("allow"))
                if not d.get("allow") and blocked_at is None:
                    blocked_at = (si, ci)
            if blocked_at:
                break

        if sc.must_block is None:
            ok = blocked_at is None
            detail = "all allowed" if ok else f"over-blocked at {blocked_at}"
        else:
            # Caught the dangerous call (at or before it) AND is not a blanket deny.
            caught = blocked_at is not None and blocked_at <= sc.must_block
            ok = caught and first_allowed is True
            if not caught:
                detail = "missed — attack completed"
            elif not first_allowed:
                detail = "blocked, but denies from call 1 (blanket deny)"
            else:
                detail = f"caught at {blocked_at}"
        results[sc.id] = {"pass": ok, "detail": detail}
    passed = sum(1 for r in results.values() if r["pass"])
    return {"name": impl_factory().name, "passed": passed,
            "total": len(scenarios), "results": results}


def main():
    impls = [
        AlwaysAllow,
        AlwaysDeny,
        RbacBaseline,
        SessionScopedPurpose,
        CustomerScopedPurpose,
        WitnessAnchoredPurpose,
    ]
    cards = [score(i) for i in impls]

    ids = [s.id for s in SCENARIOS]
    w = max(len(i) for i in ids) + 2
    print("=" * 112)
    print("COMPOSITION SUITE — SCORECARD (local; S7 included)")
    print("=" * 112)
    print(f"{'scenario':<{w}}" + "".join(
        f"{c['name'].split(',')[0].split('(')[0].strip()[:14]:>16}" for c in cards))
    print("-" * 112)
    for sid in ids:
        row = f"{sid:<{w}}"
        for c in cards:
            row += f"{('PASS' if c['results'][sid]['pass'] else 'FAIL'):>16}"
        print(row)
    print("-" * 112)
    print(f"{'SCORE':<{w}}" + "".join(
        f"{str(c['passed']) + '/' + str(c['total']):>16}" for c in cards))
    print("=" * 112)
    for c in cards:
        print(f"\n{c['name']} — {c['passed']}/{c['total']}")
        for sid, r in c["results"].items():
            print(f"   {'ok  ' if r['pass'] else 'FAIL'}  {sid:<28} {r['detail']}")
    print("\nS3 and S4 are over-blocking detectors. A gate that refuses everything")
    print("scores zero on them, which is why 'always-deny' cannot win this suite.")
    print("S7 models issuer history fork via issuer_history_reset() between sessions.")
    print("Author customer-keyed gate is expected to FAIL S7; witness-anchored to PASS.")
    print("LIMIT: S7 fork is opt-in (issuer_history_reset). Withholding the method")
    print("skips the fork; a high score then does not prove an external anchor.")
    print("\nTo score your own: implement new_session(grant) and check(tool,args).")
    print("Optional for S7: issuer_history_reset() clearing only issuer-local history.")


if __name__ == "__main__":
    main()
