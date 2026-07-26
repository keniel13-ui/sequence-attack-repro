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
    expected_rules: set | None = None
    requires_capability: str | None = None
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
        must_block=(0, 2),
        expected_rules={"PURPOSE_VIOLATION", "PROVENANCE_VIOLATION"},
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
        expected_rules={"SEQUENCE_COMPOSITION"},
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
        expected_rules={"SEQUENCE_COMPOSITION"},
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
        expected_rules={"SEQUENCE_COMPOSITION"},
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
        expected_rules={"HISTORY_FORK"},
        requires_capability="issuer_history_reset",
        attack_model="issuer_history_fork",
    ),
]


# ----------------------------------------------- suite reason categories
# A third-party gate must not fail because it names a decision differently.
# Scenarios expect a CATEGORY. Implementations may expose normalize_rule() to
# map their native codes; the reference gates are mapped here.

CATEGORIES = {"SEQUENCE_COMPOSITION", "HISTORY_FORK", "SCOPE_VIOLATION",
              "PURPOSE_VIOLATION", "PROVENANCE_VIOLATION"}

REFERENCE_RULE_MAP = {
    "R4_SEQUENCE": "SEQUENCE_COMPOSITION",
    "W1_FORK": "HISTORY_FORK",
    "R1_SCOPE": "SCOPE_VIOLATION",
    "R2_PURPOSE": "PURPOSE_VIOLATION",
    "R3_PROVENANCE": "PROVENANCE_VIOLATION",
}


def categorize(impl, decision: dict) -> str | None:
    """Native reason code -> suite category."""
    if hasattr(impl, "normalize_rule"):
        return impl.normalize_rule(decision)
    return REFERENCE_RULE_MAP.get(decision.get("rule"), decision.get("rule"))


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


class ScopedTokenBaseline:
    """What most teams actually ship: per-call RBAC + token + scope + rate."""
    name = "scoped-token per-call baseline (no roles)"

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


class PrefixDenyGamer:
    """Allows call 1, refuses everything after. Under a loose scorer this scored
    5/7 while understanding nothing. It is on the card so the scorer's own
    weakness is measured in public instead of asserted absent."""
    name = "gamer: allow-first-then-deny"

    def new_session(self, grant):
        return self

    def __init__(self):
        self.n = 0

    def check(self, tool, args):
        self.n += 1
        if self.n == 1:
            return {"allow": True, "rule": "NONE"}
        return {"allow": False, "rule": "DENY_REST"}


class BlanketRuleGamer:
    """Refuses every identity mutation, always, with no history at all. Under a
    loose scorer this tied the customer-keyed gate at 6/7."""
    name = "gamer: never allow email change"

    def new_session(self, grant):
        return self

    def check(self, tool, args):
        if tool == "update_contact_email":
            return {"allow": False, "rule": "NO_EMAIL_UPDATE"}
        return {"allow": True, "rule": "NONE"}


class PurposeConditionedGamer:
    """Refuses contact-email changes ONLY under the purposes the attack fixtures
    use. Exploits known scenario structure with no history whatsoever. Under the
    original loose scorer this tied the customer-keyed gate."""
    name = "gamer: purpose-conditioned email block"

    def new_session(self, grant):
        self.purpose = grant.purpose
        return self

    def check(self, tool, args):
        if tool == "update_contact_email" and self.purpose in {"resolve_ticket",
                                                               "account_recovery"}:
            return {"allow": False, "rule": "NO_EMAIL_UPDATE"}
        return {"allow": True, "rule": "NONE"}


# ---------------------------------------------------- baseline conformance
# Reported SEPARATELY from the composition score. Answers: does the stateless
# baseline actually work on the problem it was built for, before we show it is
# blind to a different one?

CONFORMANCE = [
    ("verified caller, in-scope action", "read_customer", {"id": "cust_77"},
     "callback_verified", {"read_customer"}, True),
    ("unverified caller", "read_customer", {"id": "cust_77"},
     "unverified", {"read_customer"}, False),
    ("action outside granted scope", "send_password_reset", {"id": "cust_77"},
     "callback_verified", {"read_customer"}, False),
]


def conformance(impl_factory) -> tuple:
    ok = 0
    for _label, tool, args, verified, scope, expect_allow in CONFORMANCE:
        impl = impl_factory()
        sess = impl.new_session(Grant("p", "account_recovery", verified, scope))
        ok += bool(sess.check(tool, args).get("allow")) == expect_allow
    return ok, len(CONFORMANCE)


# -------------------------------------------------------------------- scorer

def score(impl_factory, scenarios=SCENARIOS) -> dict:
    """Strict scoring.

    An attack scenario counts as CAUGHT only if:
      1. every call BEFORE the decisive call was allowed  (no credit for
         refusing something unrelated earlier), and
      2. the decisive call itself was refused, and
      3. the reason code returned is in the scenario's expected set.

    Honest limit: this scores what an implementation REPORTS. It cannot prove a
    gate is not simply returning the expected rule string. A scorecard inherits
    the same trust problem as a receipt.
    """
    results = {}
    for sc in scenarios:
        impl = impl_factory()
        needs = getattr(sc, "requires_capability", None)
        if needs and not hasattr(impl, needs):
            results[sc.id] = {"pass": None, "detail": "N/A — capability %s not exposed" % needs}
            continue

        decisions = {}
        stop = False
        for si, sess in enumerate(sc.sessions):
            grant = Grant(sess.principal, sess.purpose, sess.verified_via, sess.scope)
            if si > 0 and getattr(sc, "attack_model", None) == "issuer_history_fork" \
                    and hasattr(impl, "issuer_history_reset"):
                impl.issuer_history_reset()   # BEFORE the session reads it
            session = impl.new_session(grant)
            for ci, call in enumerate(sess.calls):
                d = session.check(call.tool, call.args)
                decisions[(si, ci)] = d
                if not d.get("allow"):
                    stop = True
                    break
            if stop:
                break

        if sc.must_block is None:
            blocked = [k for k, d in decisions.items() if not d.get("allow")]
            ok = not blocked
            detail = "all allowed" if ok else "over-blocked at %s" % (blocked[0],)
        else:
            prior_ok = all(d.get("allow") for k, d in decisions.items() if k < sc.must_block)
            target = decisions.get(sc.must_block)
            hit = target is not None and not target.get("allow")
            rule_ok = (sc.expected_rules is None or
                       (hit and categorize(impl, target) in sc.expected_rules))
            ok = prior_ok and hit and rule_ok
            if not prior_ok:
                early = min(k for k, d in decisions.items() if not d.get("allow"))
                detail = "refused early at %s — not a composition catch" % (early,)
            elif not hit:
                detail = "missed — attack completed"
            elif not rule_ok:
                detail = "blocked but reason %s not in %s" % (categorize(impl, target),
                                                              sorted(sc.expected_rules))
            else:
                detail = "caught at %s [%s]" % (sc.must_block, categorize(impl, target))
        results[sc.id] = {"pass": ok, "detail": detail}

    scored = [r for r in results.values() if r["pass"] is not None]
    passed = sum(1 for r in scored if r["pass"])
    return {"name": impl_factory().name, "passed": passed,
            "total": len(scored), "na": len(results) - len(scored), "results": results}


def _cell(val) -> str:
    if val is None:
        return "N/A"
    return "PASS" if val else "FAIL"


def main():
    # Gamers are on the card so loose-scorer gameability is measured in public,
    # not asserted away. They must score near zero under strict scoring.
    impls = [
        AlwaysAllow,
        AlwaysDeny,
        ScopedTokenBaseline,
        PrefixDenyGamer,
        BlanketRuleGamer, PurposeConditionedGamer,
        SessionScopedPurpose,
        CustomerScopedPurpose,
        WitnessAnchoredPurpose,
    ]
    cards = [score(i) for i in impls]

    ids = [s.id for s in SCENARIOS]
    w = max(len(i) for i in ids) + 2
    print("=" * 140)
    print("COMPOSITION SUITE — SCORECARD (strict; S7 N/A if capability absent)")
    print("=" * 140)
    print(f"{'scenario':<{w}}" + "".join(
        f"{c['name'].split(',')[0].split(':')[0].split('(')[0].strip()[:12]:>14}" for c in cards))
    print("-" * 140)
    for sid in ids:
        row = f"{sid:<{w}}"
        for c in cards:
            row += f"{_cell(c['results'][sid]['pass']):>14}"
        print(row)
    print("-" * 140)
    print(f"{'SCORE':<{w}}" + "".join(
        f"{str(c['passed']) + '/' + str(c['total']):>14}" for c in cards))
    print("=" * 140)
    for c in cards:
        print(f"\n{c['name']} — {c['passed']}/{c['total']}"
              + (f"  ({c['na']} N/A)" if c.get("na") else ""))
        for sid, r in c["results"].items():
            mark = "N/A " if r["pass"] is None else ("ok  " if r["pass"] else "FAIL")
            print(f"   {mark}  {sid:<28} {r['detail']}")
    print("\nS3 and S4 are over-blocking detectors. A gate that refuses everything")
    print("scores zero on them, which is why 'always-deny' cannot win this suite.")
    print("Strict score: decisive call only, expected reason codes, no credit for early deny.")
    print("Gamers (allow-first-then-deny / never-email) must score 0 under this scorer.")
    print("S7: N/A if issuer_history_reset not exposed (not evaluated ≠ pass).")
    print("Author customer-keyed expected FAIL S7; witness-anchored PASS.")
    print("\nTo score your own: implement new_session(grant) and check(tool,args).")
    print("Optional for S7: issuer_history_reset() clearing only issuer-local history.")


    ok, tot = conformance(ScopedTokenBaseline)
    print(f"\nBaseline conformance (separate from the composition score): {ok}/{tot}")
    print("  verified in-scope ALLOW · unverified BLOCK · out-of-scope BLOCK")

if __name__ == "__main__":
    main()
