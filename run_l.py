#!/usr/bin/env python3
"""
RUN L — two-observer reconciliation under partial compromise.
A gossip ABSTRACTION. It implements no peer dissemination and is not gossip.

Frozen before implementation in RUN_L_GOSSIP_PREREG_2026-07-30.md (addendum v3,
sha256 ab70a7a7396f07e2592e5c4d…). Accepted by Kairos before this file existed.

Repair after cold B1–B3 on edc9106 (Aethar PHASE 170; Opus self-diagnosis PHASE 90):
  - Membership is registry-resolved. A caller cannot construct who counts.
  - Receipts carry an HMAC under the reconciler key. Self-digest alone is integrity
    of bytes, not authenticity of provenance (G2 / B3).
  - L1 actually suppresses the issuer claim; it is not a composition-only path.

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
import hmac
import json

READ = "READ"
MUTATION = "IDENTITY_MUTATION"
RECOVERY = "CREDENTIAL_RECOVERY"
RISK_KEY = "cust_77"

# Experiment-local reconciler key. Not a production KMS. Exists so the gate can
# verify provenance of a ReconciliationReceipt. Full key management / public-key
# auth remains a separate prereg; this is the minimum authenticity binding G2
# requires (self-digest alone is forgeable — B3).
RECONCILER_KEY = b"run_l_reconciler_key_v1_experiment_only"


def digest(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def mac_hex(body_digest: str, key: bytes = RECONCILER_KEY) -> str:
    return hmac.new(key, body_digest.encode(), hashlib.sha256).hexdigest()


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


# --------------------------------------------- authoritative membership

class ObserverManifest:
    """Immutable membership record produced ONLY by ObserverRegistry.

    A digest over a caller-chosen list proves integrity, not completeness.
    Naming this class is not enough — construction must be registry-only.
    """

    def __init__(self, members, storage_identities, risk_key, epoch,
                 reconciler_identity, policy_mode):
        self.members = list(members)
        self.storage_identities = dict(storage_identities)
        self.risk_key = risk_key
        self.epoch = epoch
        self.reconciler_identity = reconciler_identity
        self.policy_mode = policy_mode

    def as_record(self) -> dict:
        return {"members": sorted(self.members),
                "storage_identities": self.storage_identities,
                "risk_key": self.risk_key,
                "membership_epoch": self.epoch,
                "reconciler_identity": self.reconciler_identity,
                "policy_mode": self.policy_mode}

    def digest(self) -> str:
        return digest(self.as_record())


class ObserverRegistry:
    """Sole authority for who counts for a (risk_key, epoch).

    Callers may request reconciliation. They may not hand the reconciler a
    custom membership list and call that two-observer security.
    """

    def __init__(self):
        self._slots: dict[tuple[str, int], dict] = {}

    def register(self, risk_key: str, epoch: int, observers: list[Observer],
                 reconciler_identity: str, policy_mode: str) -> ObserverManifest:
        key = (risk_key, epoch)
        if key in self._slots:
            raise ValueError(f"membership already registered for {key}")
        names = [o.name for o in observers]
        if len(names) != len(set(names)):
            raise ValueError("duplicate observer names")
        storage = {o.name: o.storage_identity for o in observers}
        manifest = ObserverManifest(
            members=names,
            storage_identities=storage,
            risk_key=risk_key,
            epoch=epoch,
            reconciler_identity=reconciler_identity,
            policy_mode=policy_mode,
        )
        self._slots[key] = {
            "manifest": manifest,
            "observers": {o.name: o for o in observers},
        }
        return manifest

    def manifest_for(self, risk_key: str, epoch: int) -> ObserverManifest:
        return self._slots[(risk_key, epoch)]["manifest"]

    def observers_for(self, risk_key: str, epoch: int) -> dict[str, Observer]:
        return dict(self._slots[(risk_key, epoch)]["observers"])


# ------------------------------------------------------------- reconciliation

CONSISTENT = "CONSISTENT"
DISAGREE = "DISAGREE"
UNRECONCILED = "UNRECONCILED"
SET_MISMATCH = "OBSERVER_SET_MISMATCH"
REGISTRY_MISS = "REGISTRY_MISS"


def reconcile(registry: ObserverRegistry, risk_key: str, epoch: int,
              issuer_claim: list[str],
              evaluated_names: list[str] | None = None) -> dict:
    """Runs OUTSIDE every gate. Produces a MAC'd receipt, not a bare verdict.

    Membership is always loaded from the registry. evaluated_names is only the
    set the caller claims to have consulted — if it is a proper subset of the
    registered members, that is SET_MISMATCH, not a smaller valid quorum.

    Consistency evidence, not head equality: an observer whose log is a PREFIX of
    the issuer's claim is merely lagging, which is benign. An observer holding
    history the issuer is not presenting means the issuer is omitting — a fork.
    """
    try:
        manifest = registry.manifest_for(risk_key, epoch)
        registered = registry.observers_for(risk_key, epoch)
    except KeyError:
        body = {
            "schema": "run_l_reconciliation_receipt_v2",
            "manifest": None,
            "manifest_digest": None,
            "issuer_claim": list(issuer_claim),
            "observer_snapshots": [],
            "reconciliation_verdict": REGISTRY_MISS,
            "why": f"no membership for risk_key={risk_key!r} epoch={epoch}",
        }
        return _seal(body)

    if evaluated_names is None:
        evaluated = [registered[n] for n in sorted(registered)]
    else:
        # Unknown names are not silently dropped — they cannot invent members.
        unknown = sorted(set(evaluated_names) - set(registered))
        if unknown:
            body = {
                "schema": "run_l_reconciliation_receipt_v2",
                "manifest": manifest.as_record(),
                "manifest_digest": manifest.digest(),
                "issuer_claim": list(issuer_claim),
                "observer_snapshots": [],
                "reconciliation_verdict": SET_MISMATCH,
                "why": f"evaluated unknown observers {unknown}; not in registry",
            }
            return _seal(body)
        evaluated = [registered[n] for n in evaluated_names]

    snaps = [o.snapshot() for o in evaluated]
    evaluated_sorted = sorted(o.name for o in evaluated)

    if evaluated_sorted != sorted(manifest.members):
        verdict, why = SET_MISMATCH, (
            f"evaluated {evaluated_sorted} but registry manifest requires "
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

    body = {
        "schema": "run_l_reconciliation_receipt_v2",
        "manifest": manifest.as_record(),
        "manifest_digest": manifest.digest(),
        "issuer_claim": list(issuer_claim),
        "observer_snapshots": snaps,
        "reconciliation_verdict": verdict,
        "why": why,
    }
    return _seal(body)


def _seal(body: dict) -> dict:
    """Bind integrity (receipt_digest) and authenticity (receipt_mac)."""
    receipt = dict(body)
    receipt["receipt_digest"] = digest(receipt)
    receipt["receipt_mac"] = mac_hex(receipt["receipt_digest"])
    return receipt


# ---------------------------------------------------------------------- gate

class Gate:
    """Consumes a ReconciliationReceipt. Never computes reconciliation, never
    accepts a bare verdict, never holds a reference to an observer store.

    Verifies both self-digest and reconciler MAC. A flipped verdict with a
    recomputed public digest fails the MAC (B3).
    """

    def __init__(self, policy_mode: str, reconciler_key: bytes = RECONCILER_KEY):
        self.policy_mode = policy_mode
        self.reconciler_key = reconciler_key

    def check(self, action_class: str, issuer_claim: list[str], receipt: dict) -> dict:
        if not self._mac_ok(receipt):
            return self._d("BLOCK", "R_RECEIPT_UNAUTHENTIC", receipt,
                           "reconciliation receipt failed reconciler MAC")
        if not self._digest_ok(receipt):
            return self._d("BLOCK", "R_RECEIPT_INVALID", receipt,
                           "reconciliation receipt failed its own digest")

        v = receipt["reconciliation_verdict"]
        if v in (SET_MISMATCH, REGISTRY_MISS):
            return self._d("BLOCK", v, receipt, receipt.get("why", v))
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

    def _digest_ok(self, receipt: dict) -> bool:
        body = {k: v for k, v in receipt.items()
                if k not in ("receipt_digest", "receipt_mac")}
        return receipt.get("receipt_digest") == digest(body)

    def _mac_ok(self, receipt: dict) -> bool:
        d = receipt.get("receipt_digest")
        m = receipt.get("receipt_mac")
        if not d or not m:
            return False
        expected = mac_hex(d, self.reconciler_key)
        return hmac.compare_digest(m, expected)

    @staticmethod
    def _compose(action_class, issuer_claim):
        if action_class == RECOVERY and MUTATION in issuer_claim:
            return "BLOCK", "R4_SEQUENCE"
        return "ALLOW", "PASS"

    @staticmethod
    def _d(decision, rule, receipt, why) -> dict:
        return {"authorization_decision": decision, "rule": rule, "why": why,
                "reconciliation_verdict": receipt.get("reconciliation_verdict"),
                "reconciliation_receipt_digest": receipt.get("receipt_digest"),
                "reconciliation_receipt_mac": receipt.get("receipt_mac")}


# -------------------------------------------------------------------- traces

def world(policy="fail_closed", epoch=1, observers=2):
    """Build a fresh registry-bound observer set for one scenario.

    `observers` exists only for the L2a/L2b count ablation (addendum v5). A
    one-member registry is a COHERENT registry with one observer, not a broken
    two-member one: W2 is still constructed so the adversary's reach is identical,
    it is simply not registered, so it is not part of the authoritative set.
    """
    reg = ObserverRegistry()
    w1, w2 = Observer("W1", "store_a"), Observer("W2", "store_b")
    registered = [w1] if observers == 1 else [w1, w2]
    reg.register(RISK_KEY, epoch, registered, "reconciler_0", policy)
    return reg, w1, w2, epoch


def mutate(issuer: list[str], *observers) -> None:
    issuer.append(MUTATION)
    for o in observers:
        o.observe(MUTATION)


def line(c="-", n=78):
    print(c * n)


def show(label, res):
    print(f"  {res['authorization_decision']:<5} recovery   "
          f"verdict={str(res['reconciliation_verdict']):<20} rule={res['rule']}")


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
                 omit_w2=False, do_mutation=True, lag_w1=False,
                 suppress_issuer_only=False, observers=2):
        reg, w1, w2, epoch = world(policy, observers=observers)
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
        # T0: issuer claim suppressed; observers still hold truth
        if suppress_issuer_only:
            issuer_claim = []
        # T1/T2: adversary also suppresses the issuer claim with the write
        if suppress_w1 or suppress_w2:
            issuer_claim = []
        evaluated_names = ["W1"] if omit_w2 else None
        rec = reconcile(reg, RISK_KEY, epoch, issuer_claim,
                        evaluated_names=evaluated_names)
        return Gate(policy).check(RECOVERY, issuer_claim, rec)

    results["L1"] = trace("L1", "T0 issuer suppressed only", "fail_closed",
                          lambda p: scenario(p, suppress_issuer_only=True))
    results["L2"] = trace("L2", "T1 issuer + W1 suppressed  (Run J's wall)", "fail_closed",
                          lambda p: scenario(p, suppress_w1=True))
    # --- addendum v5: observer-count ablation, one variable ---------------------
    # Identical registry, reconcile(), receipt, Gate, policy, risk key, epoch,
    # mutation and adversary reach. ONLY the registered observer set differs.
    results["L2a"] = trace("L2a", "COUNT ABLATION registry=[W1]      issuer + W1 suppressed",
                           "fail_closed", lambda p: scenario(p, suppress_w1=True, observers=1))
    results["L2b"] = trace("L2b", "COUNT ABLATION registry=[W1,W2]   issuer + W1 suppressed",
                           "fail_closed", lambda p: scenario(p, suppress_w1=True, observers=2))

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
    print("VERDICT vs RUN_L_GOSSIP_PREREG_2026-07-30.md (addendum v3 + v4 repair)")
    line("=")
    R = results
    checks = [
        ("L1 issuer-only suppression caught by RECON (G1_GOSSIP_DISAGREE)",
         R["L1"]["authorization_decision"] == "BLOCK"
         and R["L1"]["rule"] == "G1_GOSSIP_DISAGREE"),
        ("L2 two observers repair Run J's wall (G1_GOSSIP_DISAGREE)",
         R["L2"]["authorization_decision"] == "BLOCK"
         and R["L2"]["rule"] == "G1_GOSSIP_DISAGREE"),
        ("L2a COUNT ABLATION registry=[W1] ALLOWS (nothing survives to disagree)",
         R["L2a"]["authorization_decision"] == "ALLOW"
         and R["L2a"]["reconciliation_verdict"] == CONSISTENT),
        ("L2b COUNT ABLATION registry=[W1,W2] BLOCKS — only the count differs",
         R["L2b"]["authorization_decision"] == "BLOCK"
         and R["L2b"]["rule"] == "G1_GOSSIP_DISAGREE"),
        ("L3 reach covering BOTH observers is NOT repaired",
         R["L3"]["authorization_decision"] == "ALLOW"),
        ("L4 fail_OPEN defeated at T1 when W2 is partitioned (no write to W2)",
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
        print("   - observer count is independently load-bearing at T1: on an")
        print("     OTHERWISE IDENTICAL reconciliation path, registry=[W1] allows")
        print("     the takeover and registry=[W1,W2] blocks it (L2a/L2b);")
        print("   - count does NOT repair T2 — reach covering the observer set wins;")
        print("   - fail-closed handling is SEPARATELY load-bearing at fixed count:")
        print("     once the adversary already holds the issuer and W1, merely")
        print("     partitioning W2 defeats fail_OPEN. No write to W2 is required;")
        print("   - neither property substitutes for the other;")
        print("   - and fail-closed carries a measured availability cost (L6).")
        print()
        print("  Membership is registry-resolved; receipts are MAC-bound under the")
        print("  reconciler key. A one-observer caller list and a flipped public")
        print("  digest no longer produce a valid authorization path.")
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
