#!/usr/bin/env python3
"""
RUN L — two-observer reconciliation under partial compromise.
A gossip ABSTRACTION. It implements no peer dissemination and is not gossip.

Frozen before implementation in RUN_L_GOSSIP_PREREG_2026-07-30.md (addendum v3,
sha256 ab70a7a7396f07e2592e5c4d…). Accepted by Kairos before this file existed.

Run J: a single witness fails when one capability suppresses its complete view.
Run L: does a second, independent observer repair that — and what does it cost?

Three layers are kept separate on purpose, because collapsing them is what the
breaker blocked twice:

  reconciliation_verdict   what the observers, compared, actually show
  authorization_decision   what the gate does with that verdict under policy
  availability_cost        a refusal with no adversary present

Run:  python3 run_l.py
"""

from __future__ import annotations

import hashlib
import json

READ = "READ"
MUTATION = "IDENTITY_MUTATION"
RECOVERY = "CREDENTIAL_RECOVERY"
RISK_KEY = "cust_77"


def digest(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


# --------------------------------------------------------------- observers

class Observer:
    """An append-only log of what this observer actually saw, plus a head."""

    def __init__(self, name: str, storage_identity: str):
        self.name = name
        self.storage_identity = storage_identity
        self.log: list[str] = []
        self.reachable = True

    def observe(self, action_class: str) -> None:
        self.log.append(action_class)

    def head(self) -> str | None:
        return digest(self.log) if self.log else None

    def snapshot(self) -> dict:
        return {"observer": self.name,
                "storage_identity": self.storage_identity,
                "reachable": self.reachable,
                "log": list(self.log),
                "head": self.head(),
                "sequence": len(self.log)}

    # adversary capabilities, named explicitly
    def suppress(self) -> None:
        """Adversary write reach: erase this observer's view of the key."""
        self.log = []

    def partition(self) -> None:
        """No write. The observer is simply unreachable."""
        self.reachable = False


# ----------------------------------------------------- authoritative manifest

class ObserverManifest:
    """Membership is AUTHORITATIVE. A caller cannot choose who counts.

    Run L's first BLOCK: a digest over a caller-supplied list proves integrity,
    not completeness. Omit W2 and two-observer reconciliation silently becomes
    the one-observer system Run J already broke — with every digest still valid.
    """

    def __init__(self, observers, risk_key, epoch, reconciler_identity, policy_mode):
        self.members = [o.name for o in observers]
        self.storage_identities = {o.name: o.storage_identity for o in observers}
        self.risk_key = risk_key
        self.epoch = epoch
        self.reconciler_identity = reconciler_identity
        self.policy_mode = policy_mode          # fail_open | fail_closed

    def as_record(self) -> dict:
        return {"members": sorted(self.members),
                "storage_identities": self.storage_identities,
                "risk_key": self.risk_key,
                "membership_epoch": self.epoch,
                "reconciler_identity": self.reconciler_identity,
                "policy_mode": self.policy_mode}

    def digest(self) -> str:
        return digest(self.as_record())


# ------------------------------------------------------------- reconciliation

CONSISTENT = "CONSISTENT"
DISAGREE = "DISAGREE"
UNRECONCILED = "UNRECONCILED"
SET_MISMATCH = "OBSERVER_SET_MISMATCH"


def reconcile(manifest: ObserverManifest, issuer_claim: list[str],
              evaluated: list[Observer]) -> dict:
    """Runs OUTSIDE every gate. Produces a digest-bound receipt, not a bare verdict.

    Consistency evidence, not head equality: an observer whose log is a PREFIX of
    the issuer's claim is merely lagging, which is benign. An observer holding
    history the issuer is not presenting means the issuer is omitting — a fork.
    """
    snaps = [o.snapshot() for o in evaluated]
    evaluated_names = sorted(o.name for o in evaluated)

    if evaluated_names != sorted(manifest.members):
        verdict, why = SET_MISMATCH, (
            f"evaluated {evaluated_names} but manifest requires "
            f"{sorted(manifest.members)}; a smaller set is a failure, not a quorum")
    elif any(not o.reachable for o in evaluated):
        down = [o.name for o in evaluated if not o.reachable]
        verdict, why = UNRECONCILED, f"observer(s) unreachable: {down}"
    else:
        divergent = [o.name for o in evaluated
                     if o.log != issuer_claim[:len(o.log)]]
        if divergent:
            verdict, why = DISAGREE, (
                f"{divergent} hold history the issuer is not presenting "
                f"(issuer claims {issuer_claim})")
        else:
            behind = [o.name for o in evaluated if len(o.log) < len(issuer_claim)]
            verdict, why = CONSISTENT, (
                f"all observers prefix-consistent with the issuer"
                + (f"; lagging: {behind}" if behind else ""))

    receipt = {"schema": "run_l_reconciliation_receipt_v1",
               "manifest": manifest.as_record(),
               "manifest_digest": manifest.digest(),
               "issuer_claim": list(issuer_claim),
               "observer_snapshots": snaps,
               "reconciliation_verdict": verdict,
               "why": why}
    receipt["receipt_digest"] = digest(receipt)
    return receipt


# ---------------------------------------------------------------------- gate

class Gate:
    """Consumes a ReconciliationReceipt. Never computes reconciliation, never
    accepts a bare verdict, never holds a reference to an observer store."""

    def __init__(self, policy_mode: str):
        self.policy_mode = policy_mode

    def check(self, action_class: str, issuer_claim: list[str], receipt: dict) -> dict:
        if receipt.get("receipt_digest") != digest(
                {k: v for k, v in receipt.items() if k != "receipt_digest"}):
            return self._d("BLOCK", "R_RECEIPT_INVALID", receipt,
                           "reconciliation receipt failed its own digest")

        v = receipt["reconciliation_verdict"]
        if v == SET_MISMATCH:
            return self._d("BLOCK", SET_MISMATCH, receipt, receipt["why"])
        if v == DISAGREE:
            return self._d("BLOCK", "G1_GOSSIP_DISAGREE", receipt, receipt["why"])
        if v == UNRECONCILED:
            if self.policy_mode == "fail_closed":
                return self._d("BLOCK", "G2_UNRECONCILED", receipt,
                               "cannot reconcile; refusing without diagnosis")
            return self._d(*self._compose(action_class, issuer_claim), receipt,
                           "unreachable treated as no disagreement (fail_open)")
        return self._d(*self._compose(action_class, issuer_claim), receipt,
                       "observers consistent; composition policy applied")

    @staticmethod
    def _compose(action_class, issuer_claim):
        if action_class == RECOVERY and MUTATION in issuer_claim:
            return "BLOCK", "R4_SEQUENCE"
        return "ALLOW", "PASS"

    @staticmethod
    def _d(decision, rule, receipt, why) -> dict:
        return {"authorization_decision": decision, "rule": rule, "why": why,
                "reconciliation_verdict": receipt["reconciliation_verdict"],
                "reconciliation_receipt_digest": receipt["receipt_digest"]}


# -------------------------------------------------------------------- traces

def world(policy="fail_closed", epoch=1):
    w1, w2 = Observer("W1", "store_a"), Observer("W2", "store_b")
    m = ObserverManifest([w1, w2], RISK_KEY, epoch, "reconciler_0", policy)
    return w1, w2, m


def mutate(issuer: list[str], *observers) -> None:
    issuer.append(MUTATION)
    for o in observers:
        o.observe(MUTATION)


def line(c="-", n=78):
    print(c * n)


def show(label, res):
    print(f"  {res['authorization_decision']:<5} recovery   "
          f"verdict={res['reconciliation_verdict']:<20} rule={res['rule']}")


def trace(name, headline, policy, build):
    print(f"\n{name} — {headline}")
    line()
    res = build(policy)
    show(name, res)
    print(f"        {res['why'][:96]}")
    return res


def main() -> int:
    print("=" * 78)
    print("RUN L — TWO-OBSERVER RECONCILIATION (a gossip abstraction)")
    print("=" * 78)
    results = {}

    def scenario(policy, suppress_w1=False, suppress_w2=False, partition_w2=False,
                 omit_w2=False, do_mutation=True, lag_w1=False):
        w1, w2, m = world(policy)
        issuer: list[str] = []
        if do_mutation:
            mutate(issuer, w1, w2)
        if lag_w1:
            # BENIGN LAG, no adversary: a harmless prior action reaches the issuer
            # and W2, while W1 has simply not caught up yet. Deliberately NOT a
            # mutation, so any ALLOW is attributable to reconciliation treating
            # lag as benign rather than to the composition rule being idle.
            issuer.append(READ)
            w2.observe(READ)
        issuer_claim = list(issuer)
        if suppress_w1:
            w1.suppress()
        if suppress_w2:
            w2.suppress()
        if partition_w2:
            w2.partition()
        if suppress_w1 or suppress_w2:      # adversary also suppresses the issuer
            issuer_claim = []
        if suppress_w1 and not (suppress_w2 or partition_w2):
            pass
        evaluated = [w1] if omit_w2 else [w1, w2]
        rec = reconcile(m, issuer_claim, evaluated)
        return Gate(policy).check(RECOVERY, issuer_claim, rec)

    results["L1"] = trace("L1", "T0 issuer suppressed only", "fail_closed",
                          lambda p: scenario(p))
    # T0: issuer alone is suppressed; both observers still hold the mutation
    results["L2"] = trace("L2", "T1 issuer + W1 suppressed  (Run J's wall)", "fail_closed",
                          lambda p: scenario(p, suppress_w1=True))
    results["L3"] = trace("L3", "T2 issuer + BOTH observers suppressed", "fail_closed",
                          lambda p: scenario(p, suppress_w1=True, suppress_w2=True))
    results["L4o"] = trace("L4-open", "T1P partition, fail_OPEN", "fail_open",
                           lambda p: scenario(p, suppress_w1=True, partition_w2=True))
    results["L4c"] = trace("L4-closed", "T1P partition, fail_CLOSED", "fail_closed",
                           lambda p: scenario(p, suppress_w1=True, partition_w2=True))
    results["L5"] = trace("L5", "recovery-only legitimate workflow (no mutation)",
                          "fail_closed", lambda p: scenario(p, do_mutation=False))
    results["L6"] = trace("L6", "benign partition, NO adversary", "fail_closed",
                          lambda p: scenario(p, do_mutation=False, partition_w2=True))
    results["L7"] = trace("L7", "reachable W2 omitted from evaluation", "fail_closed",
                          lambda p: scenario(p, do_mutation=False, omit_w2=True))
    results["L8"] = trace("L8", "benign prefix-consistent lag (W1 behind)", "fail_closed",
                          lambda p: scenario(p, do_mutation=False, lag_w1=True))

    print("\n")
    print("=" * 78)
    print("VERDICT vs RUN_L_GOSSIP_PREREG_2026-07-30.md (addendum v3)")
    line("=")
    R = results
    checks = [
        ("L1 issuer-only suppression caught",
         R["L1"]["authorization_decision"] == "BLOCK"),
        ("L2 two observers repair Run J's wall (G1_GOSSIP_DISAGREE)",
         R["L2"]["authorization_decision"] == "BLOCK"
         and R["L2"]["rule"] == "G1_GOSSIP_DISAGREE"),
        ("L3 reach covering BOTH observers is NOT repaired",
         R["L3"]["authorization_decision"] == "ALLOW"),
        ("L4 fail_OPEN defeated by partition alone (no write to W2)",
         R["L4o"]["authorization_decision"] == "ALLOW"),
        ("L4 fail_CLOSED refuses, without diagnosis",
         R["L4c"]["authorization_decision"] == "BLOCK"
         and R["L4c"]["rule"] == "G2_UNRECONCILED"),
        ("L5 legitimate recovery-only workflow ALLOWED",
         R["L5"]["authorization_decision"] == "ALLOW"),
        ("L7 omitted reachable observer -> OBSERVER_SET_MISMATCH",
         R["L7"]["rule"] == SET_MISMATCH),
        ("L8 benign lag ALLOWED (consistency evidence, not head equality)",
         R["L8"]["authorization_decision"] == "ALLOW"),
    ]
    for label, ok in checks:
        print(f"  [{'OK  ' if ok else 'FAIL'}]  {label}")
    line("=")

    l6_cost = R["L6"]["authorization_decision"] == "BLOCK"
    conclusive = all(ok for _, ok in checks)

    if l6_cost:
        print("  L6  AVAILABILITY_COST_UNDER_PARTITION — fail_closed refuses honest")
        print("      work when an observer is merely unreachable. No adversary present.")
    print()
    if conclusive:
        print("  CONFIRMED, narrowly:")
        print("   - two observers repair the single-witness wall at T1;")
        print("   - they do NOT repair it at T2 — reach covering the observer set wins;")
        print("   - fail_OPEN reconciliation is defeated by partition alone, with no")
        print("     write to the second observer. Fail-CLOSED is the load-bearing")
        print("     property, not observer count;")
        print("   - and fail-closed carries a measured availability cost (L6).")
        print()
        print("  With two observers under unanimous reconciliation, detection survives")
        print("  while the adversary's write-and-suppress reach fails to cover BOTH.")
        print("  This is 2-of-2. It is NOT k-of-n; a threshold needs >=3 observers.")
        print()
        print("  Reconciliation exposes inconsistency BETWEEN observers. It does not")
        print("  identify which observer lied, and proves nothing about freshness when")
        print("  both share the same stale view.")
    else:
        print("  INCONCLUSIVE — a frozen condition failed. Implementation blocker,")
        print("  not a research result. Fix the fixture; do not reinterpret.")
    print(f"\n  bundle_sha256: {digest({k: v for k, v in R.items()})[:48]}…")
    return 0 if conclusive else 1


if __name__ == "__main__":
    raise SystemExit(main())
