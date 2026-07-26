#!/usr/bin/env python3
"""
CLAIM-30 REPRO — the two guards under test.

BaselineGuard  = what most teams actually ship today: RBAC allowlist, a valid
                 scoped token, per-call permission check, rate limit.
                 It judges each call ON ITS OWN. That is the whole point.

PurposeGate    = Keniel's mechanism (CLAIM-29 PurposeEnvelope + CLAIM-30
                 sequence composition). It judges a call against the PURPOSE
                 the authority was granted for, the PROVENANCE of the facts
                 justifying it, and the SEQUENCE it completes.

No classifier. No model call. Deterministic rules, replayable receipt.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field

# ---------------------------------------------------------------- action model

# Every tool is legitimately available to a support agent. That is the premise.
ACTION_CLASS = {
    "read_ticket":          "READ",
    "read_customer":        "READ",
    "update_contact_email": "IDENTITY_MUTATION",
    "send_password_reset":  "CREDENTIAL_RECOVERY",
    "post_reply":           "WRITE",
}

# What each granted purpose is actually FOR. Permission != purpose.
PURPOSE_ADMITS = {
    "resolve_ticket":        {"READ", "WRITE"},
    "update_contact_details": {"READ", "WRITE", "IDENTITY_MUTATION"},
    "account_recovery":      {"READ", "IDENTITY_MUTATION", "CREDENTIAL_RECOVERY"},
}


@dataclass
class Grant:
    """Authority as actually issued: by whom, for what, proven how."""
    principal: str
    purpose: str
    verified_via: str          # "callback_verified" | "unverified" | ...
    scope: set[str]            # tools the token permits

    @property
    def principal_is_verified(self) -> bool:
        return self.verified_via != "unverified"


@dataclass
class Fact:
    """Something the agent learned during the session, and where it came from."""
    source: str
    trust: str                 # "trusted" | "untrusted"
    summary: str


# ------------------------------------------------------------ baseline guard

class BaselineGuard:
    """Realistic per-call policy enforcement. Not a strawman.

    Checks: token validity, tool in scope, per-call RBAC, rate limit.
    Judges each call independently — which is exactly how RBAC works.
    """

    def __init__(self, grant: Grant, rate_limit: int = 20):
        self.grant = grant
        self.rate_limit = rate_limit
        self.calls = 0

    def check(self, tool: str, args: dict) -> dict:
        self.calls += 1
        if not self.grant.principal_is_verified:
            return {"allow": False, "rule": "AUTH", "why": "no valid session"}
        if tool not in self.grant.scope:
            return {"allow": False, "rule": "RBAC", "why": f"{tool} not in scope"}
        if self.calls > self.rate_limit:
            return {"allow": False, "rule": "RATE", "why": "rate limit exceeded"}
        return {"allow": True, "rule": "RBAC", "why": f"{tool} permitted for role"}


# -------------------------------------------------------------- purpose gate

class PurposeGate:
    """CLAIM-29 + CLAIM-30. Refuses, and can prove why it refused.

    R1 SCOPE       — tool must be permitted (same floor as baseline)
    R2 PURPOSE     — action class must be admitted by the GRANTED PURPOSE
    R3 PROVENANCE  — an IDENTITY_MUTATION may not be justified by facts whose
                     source is untrusted (CLAIM-24: the source changed / was
                     never entitled to grant it)
    R4 SEQUENCE    — CREDENTIAL_RECOVERY after an IDENTITY_MUTATION in the same
                     session composes to account takeover, regardless of each
                     step being individually permitted (CLAIM-30)
    """

    def __init__(self, grant: Grant):
        self.grant = grant
        self.facts: list[Fact] = []
        self.performed: list[str] = []
        self._head: str | None = None
        self._seq: int = 0
        self.receipts: list[dict] = []

    def observe(self, source: str, trust: str, summary: str) -> None:
        """Record what the agent ingested and how much that source is trusted."""
        self.facts.append(Fact(source, trust, summary))

    def _untrusted(self) -> list[Fact]:
        return [f for f in self.facts if f.trust == "untrusted"]

    def check(self, tool: str, args: dict) -> dict:
        cls = ACTION_CLASS.get(tool, "UNKNOWN")
        admitted = PURPOSE_ADMITS.get(self.grant.purpose, set())

        decision = {"allow": True, "rule": "PASS", "why": "within envelope"}

        if tool not in self.grant.scope:
            decision = {"allow": False, "rule": "R1_SCOPE",
                        "why": f"{tool} not permitted by grant"}
        elif cls not in admitted:
            decision = {"allow": False, "rule": "R2_PURPOSE",
                        "why": (f"{tool} is {cls}; authority was granted for "
                                f"purpose '{self.grant.purpose}' which admits "
                                f"{sorted(admitted)}. Permission is not purpose.")}
        elif cls == "IDENTITY_MUTATION" and self._untrusted():
            src = self._untrusted()[0]
            decision = {"allow": False, "rule": "R3_PROVENANCE",
                        "why": (f"{cls} justified by facts from an untrusted "
                                f"source ({src.source}). That source is not "
                                f"entitled to grant identity changes.")}
        elif cls == "CREDENTIAL_RECOVERY" and "IDENTITY_MUTATION" in self.performed:
            decision = {"allow": False, "rule": "R4_SEQUENCE",
                        "why": ("credential recovery after an identity mutation "
                                "in the same session composes to account "
                                "takeover. Every step was allowed. The sequence "
                                "was the attack.")}

        receipt = self._receipt(tool, args, cls, decision)
        self.receipts.append(receipt)
        if decision["allow"]:
            self.performed.append(cls)
        return {**decision, "receipt": receipt}


    # ---- receipt chain ------------------------------------------------
    # A hash over the current record only is a content digest, not a chain.
    # Each receipt now commits to the previous head, so a rewritten history
    # cannot present a matching chain without redoing every link.
    def _seal(self, record: dict) -> dict:
        record["previous_head"] = getattr(self, "_head", None)
        record["sequence_number"] = getattr(self, "_seq", 0)
        blob = json.dumps(record, sort_keys=True, separators=(",", ":"))
        head = hashlib.sha256(blob.encode()).hexdigest()
        record["chain_sha256"] = head
        record["decided_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        self._head = head
        self._seq = getattr(self, "_seq", 0) + 1
        return record

    def _receipt(self, tool: str, args: dict, cls: str, decision: dict) -> dict:
        """Replayable: same inputs -> same chain hash, every time."""
        record = {
            "tool": tool,
            "args": args,
            "action_class": cls,
            "grant": {
                "principal": self.grant.principal,
                "purpose": self.grant.purpose,
                "verified_via": self.grant.verified_via,
            },
            "facts_in_chain": [
                {"source": f.source, "trust": f.trust, "summary": f.summary}
                for f in self.facts
            ],
            "prior_action_classes": list(self.performed),
            "decision": {"allow": decision["allow"], "rule": decision["rule"]},
            "why": decision["why"],
        }
        return self._seal(record)


# ------------------------------------------------------- record-level fix (ANP2)

class ResourceLedger:
    """Sequence history keyed to the OBJECT being acted on, not the session.

    ANP2 Network's point: "a conversation is one index into that history rather
    than the edge of it." Split the pair across two sessions and a session-scoped
    check goes blind — but the customer record remembers. This is that memory.
    """

    def __init__(self) -> None:
        self._by_resource: dict[str, list[str]] = {}

    def record(self, resource: str, cls: str) -> None:
        self._by_resource.setdefault(resource, []).append(cls)

    def history(self, resource: str) -> list[str]:
        return list(self._by_resource.get(resource, []))


class ResourceGate(PurposeGate):
    """Run G. Identical to PurposeGate except R4_SEQUENCE keys on the RESOURCE
    record (via a shared ledger) instead of this session's own history.

    The only variable that changes vs PurposeGate is WHERE the prior-action
    history comes from. Everything else — scope, purpose, provenance — is the
    same. So splitting the pair across two sessions no longer hides the identity
    mutation, because the invariant lives on the object, not the conversation.
    """

    def __init__(self, grant: Grant, ledger: ResourceLedger):
        super().__init__(grant)
        self.ledger = ledger

    def check(self, tool: str, args: dict) -> dict:
        cls = ACTION_CLASS.get(tool, "UNKNOWN")
        admitted = PURPOSE_ADMITS.get(self.grant.purpose, set())
        resource = args.get("id")
        prior = self.ledger.history(resource)     # cross-session, per-object

        decision = {"allow": True, "rule": "PASS", "why": "within envelope"}
        if tool not in self.grant.scope:
            decision = {"allow": False, "rule": "R1_SCOPE",
                        "why": f"{tool} not permitted by grant"}
        elif cls not in admitted:
            decision = {"allow": False, "rule": "R2_PURPOSE",
                        "why": (f"{tool} is {cls}; authority was granted for "
                                f"purpose '{self.grant.purpose}' which admits "
                                f"{sorted(admitted)}. Permission is not purpose.")}
        elif cls == "IDENTITY_MUTATION" and self._untrusted():
            src = self._untrusted()[0]
            decision = {"allow": False, "rule": "R3_PROVENANCE",
                        "why": (f"{cls} justified by facts from an untrusted "
                                f"source ({src.source}). That source is not "
                                f"entitled to grant identity changes.")}
        elif cls == "CREDENTIAL_RECOVERY" and "IDENTITY_MUTATION" in prior:
            decision = {"allow": False, "rule": "R4_SEQUENCE",
                        "why": ("credential recovery after an identity mutation "
                                "ON THIS RECORD composes to account takeover, even "
                                "across separate sessions. The invariant lives on "
                                "the object, not the conversation.")}

        receipt = self._resource_receipt(tool, args, cls, decision, prior)
        self.receipts.append(receipt)
        if decision["allow"]:
            self.performed.append(cls)
            self.ledger.record(resource, cls)
        return {**decision, "receipt": receipt}

    def _resource_receipt(self, tool, args, cls, decision, prior) -> dict:
        """Record-scoped receipt. The hash covers exactly the fields shown —
        including the resource-scoped prior history — so the receipt can't claim
        one history and be signed over another."""
        record = {
            "tool": tool,
            "args": args,
            "action_class": cls,
            "grant": {
                "principal": self.grant.principal,
                "purpose": self.grant.purpose,
                "verified_via": self.grant.verified_via,
            },
            "facts_in_chain": [
                {"source": f.source, "trust": f.trust, "summary": f.summary}
                for f in self.facts
            ],
            "sequence_scope": "resource",
            "resource": args.get("id"),
            "prior_action_classes": prior,
            "decision": {"allow": decision["allow"], "rule": decision["rule"]},
            "why": decision["why"],
        }
        return self._seal(record)


# --------------------------------------------- customer / risk-object key (ANP2)

class RiskMap:
    """Maps a concrete resource id to the risk object that is actually at stake.

    ANP2's resource-split: contact_77 and auth_77 can each look clean while both
    belong to the same customer. The design decision is the key: not session,
    not resource alone — the human account (customer) being taken over.
    """

    def __init__(self, resource_to_customer: dict[str, str] | None = None):
        self._map = dict(resource_to_customer or {})

    def customer_of(self, resource: str | None) -> str | None:
        if resource is None:
            return None
        return self._map.get(resource, resource)


class CustomerLedger:
    """Also carries the receipt chain head, so cryptographic continuity is keyed
    to the SAME risk object as the sequence policy. Without this the action
    history survives a session boundary but the hash linkage restarts at zero."""

    """Sequence history keyed to the CUSTOMER (risk object), not one resource."""

    def __init__(self) -> None:
        self._by_customer: dict[str, list[str]] = {}

    def head(self, customer: str):
        return getattr(self, "_heads", {}).get(customer)

    def seq(self, customer: str) -> int:
        return getattr(self, "_seqs", {}).get(customer, 0)

    def advance(self, customer: str, new_head: str) -> None:
        if not hasattr(self, "_heads"):
            self._heads, self._seqs = {}, {}
        self._heads[customer] = new_head
        self._seqs[customer] = self._seqs.get(customer, 0) + 1

    def record(self, customer: str, cls: str) -> None:
        self._by_customer.setdefault(customer, []).append(cls)

    def history(self, customer: str) -> list[str]:
        return list(self._by_customer.get(customer, []))


class CustomerGate(PurposeGate):
    def _seal(self, record: dict):
        key = getattr(self, "_risk_key", None)
        if key is None or not hasattr(self.ledger, "head"):
            return PurposeGate._seal(self, record)
        record["risk_key"] = key
        record["previous_head"] = self.ledger.head(key)
        record["sequence_number"] = self.ledger.seq(key)
        blob = json.dumps(record, sort_keys=True, separators=(",", ":"))
        head = hashlib.sha256(blob.encode()).hexdigest()
        record["chain_sha256"] = head
        record["decided_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        self.ledger.advance(key, head)
        return record

    """Run H fix. R4_SEQUENCE keys on the customer via RiskMap + CustomerLedger.

    Two resources under one customer no longer hide each other: mutation on
    contact_77 and recovery on auth_77 share cust_77's history.
    """

    def __init__(self, grant: Grant, ledger: CustomerLedger, risk_map: RiskMap):
        super().__init__(grant)
        self.ledger = ledger
        self.risk_map = risk_map

    def check(self, tool: str, args: dict) -> dict:
        cls = ACTION_CLASS.get(tool, "UNKNOWN")
        admitted = PURPOSE_ADMITS.get(self.grant.purpose, set())
        resource = args.get("id")
        customer = self.risk_map.customer_of(resource)
        self._risk_key = customer
        prior = self.ledger.history(customer) if customer else []

        decision = {"allow": True, "rule": "PASS", "why": "within envelope"}
        if tool not in self.grant.scope:
            decision = {"allow": False, "rule": "R1_SCOPE",
                        "why": f"{tool} not permitted by grant"}
        elif cls not in admitted:
            decision = {"allow": False, "rule": "R2_PURPOSE",
                        "why": (f"{tool} is {cls}; authority was granted for "
                                f"purpose '{self.grant.purpose}' which admits "
                                f"{sorted(admitted)}. Permission is not purpose.")}
        elif cls == "IDENTITY_MUTATION" and self._untrusted():
            src = self._untrusted()[0]
            decision = {"allow": False, "rule": "R3_PROVENANCE",
                        "why": (f"{cls} justified by facts from an untrusted "
                                f"source ({src.source}). That source is not "
                                f"entitled to grant identity changes.")}
        elif cls == "CREDENTIAL_RECOVERY" and "IDENTITY_MUTATION" in prior:
            decision = {"allow": False, "rule": "R4_SEQUENCE",
                        "why": ("credential recovery after an identity mutation "
                                "ON THIS CUSTOMER composes to account takeover, "
                                "even across separate resources. The invariant "
                                "keys on the risk object (the human account), "
                                "not one resource row.")}

        receipt = self._customer_receipt(
            tool, args, cls, decision, prior, resource, customer)
        self.receipts.append(receipt)
        if decision["allow"] and customer is not None:
            self.performed.append(cls)
            self.ledger.record(customer, cls)
        return {**decision, "receipt": receipt}

    def _customer_receipt(self, tool, args, cls, decision, prior,
                          resource, customer) -> dict:
        record = {
            "tool": tool,
            "args": args,
            "action_class": cls,
            "grant": {
                "principal": self.grant.principal,
                "purpose": self.grant.purpose,
                "verified_via": self.grant.verified_via,
            },
            "facts_in_chain": [
                {"source": f.source, "trust": f.trust, "summary": f.summary}
                for f in self.facts
            ],
            "sequence_scope": "customer",
            "resource": resource,
            "customer": customer,
            "prior_action_classes": prior,
            "decision": {"allow": decision["allow"], "rule": decision["rule"]},
            "why": decision["why"],
        }
        return self._seal(record)


# ------------------------------------- external witness (leap ANP2 set down)

class ExternalWitness:
    """Out-of-issuer observer of chain heads per risk key.

    ANP2 named it: a receipt signed only by the gate that enforces can fork —
    keep two valid heads and reveal whichever lets the bad call through. A
    witness held OUTSIDE the issuer is the residual he called out of scope.

    This is the receipt-layer form of: the verifier cannot live inside the
    agent it governs (Truth-First / the Eye).
    """

    def __init__(self) -> None:
        # key -> ordered action classes the witness has actually seen
        self._observed: dict[str, list[str]] = {}
        # key -> last receipt head hash the witness accepted
        self._heads: dict[str, str] = {}

    def observed_history(self, key: str) -> list[str]:
        return list(self._observed.get(key, []))

    def last_head(self, key: str) -> str | None:
        return self._heads.get(key)

    def accept(self, key: str, action_class: str, head_hash: str) -> None:
        """Record a head the witness has independently observed."""
        self._observed.setdefault(key, []).append(action_class)
        self._heads[key] = head_hash

    def check_claimed_prior(self, key: str, claimed_prior: list[str]) -> dict:
        """Reject if the issuer presents a history that is not what the witness saw.

        That is the fork: two heads for the same key; the issuer reveals the
        empty/clean one while the witness already holds the mutation head.
        """
        observed = self.observed_history(key)
        if claimed_prior != observed:
            return {
                "ok": False,
                "rule": "W1_FORK",
                "why": (
                    f"issuer claimed prior_action_classes={claimed_prior} for "
                    f"key '{key}', but external witness already observed "
                    f"{observed} (last head {self.last_head(key)}). "
                    "A self-authored chain can fork; a witness outside the "
                    "issuer cannot be rewritten by the gate that enforces."
                ),
            }
        return {"ok": True, "rule": "W_PASS", "why": "claimed prior matches witness"}


class ForkingCustomerGate(CustomerGate):
    """Dishonest issuer: when honest customer history would block R4, presents
    an empty prior and ALLOWS — a second head for the same key that makes the
    call pass. Alone, the fork succeeds. With ExternalWitness in the loop,
    the witness already holds the mutation head and rejects the rewrite.
    """

    def __init__(self, grant: Grant, ledger: CustomerLedger, risk_map: RiskMap,
                 witness: ExternalWitness | None = None):
        super().__init__(grant, ledger, risk_map)
        self.witness = witness

    def check(self, tool: str, args: dict) -> dict:
        cls = ACTION_CLASS.get(tool, "UNKNOWN")
        admitted = PURPOSE_ADMITS.get(self.grant.purpose, set())
        resource = args.get("id")
        customer = self.risk_map.customer_of(resource)
        self._risk_key = customer
        honest_prior = self.ledger.history(customer) if customer else []

        # Dishonest fork: if recovery would be blocked by real history, present
        # empty history so the composition looks clean.
        forked = (
            cls == "CREDENTIAL_RECOVERY"
            and "IDENTITY_MUTATION" in honest_prior
        )
        presented_prior = [] if forked else honest_prior

        decision = {"allow": True, "rule": "PASS", "why": "within envelope"}
        if tool not in self.grant.scope:
            decision = {"allow": False, "rule": "R1_SCOPE",
                        "why": f"{tool} not permitted by grant"}
        elif cls not in admitted:
            decision = {"allow": False, "rule": "R2_PURPOSE",
                        "why": (f"{tool} is {cls}; authority was granted for "
                                f"purpose '{self.grant.purpose}' which admits "
                                f"{sorted(admitted)}. Permission is not purpose.")}
        elif cls == "IDENTITY_MUTATION" and self._untrusted():
            src = self._untrusted()[0]
            decision = {"allow": False, "rule": "R3_PROVENANCE",
                        "why": (f"{cls} justified by facts from an untrusted "
                                f"source ({src.source}). That source is not "
                                f"entitled to grant identity changes.")}
        elif cls == "CREDENTIAL_RECOVERY" and "IDENTITY_MUTATION" in presented_prior:
            decision = {"allow": False, "rule": "R4_SEQUENCE",
                        "why": ("credential recovery after identity mutation "
                                "on this customer.")}
        elif forked:
            decision = {
                "allow": True,
                "rule": "PASS_FORK",
                "why": (
                    "issuer presented empty prior for this key (forked head) "
                    "so self-authored R4 does not fire — the gate signed the "
                    "history that lets the call through"
                ),
            }

        # External witness: continuity check before the issuer's word is final.
        if (
            self.witness is not None
            and decision["allow"]
            and customer is not None
        ):
            w = self.witness.check_claimed_prior(customer, presented_prior)
            if not w["ok"]:
                decision = {
                    "allow": False,
                    "rule": w["rule"],
                    "why": w["why"],
                }

        if forked:
            # Signed content includes fork disclosure so the receipt cannot hide it.
            record = {
                "tool": tool,
                "args": args,
                "action_class": cls,
                "grant": {
                    "principal": self.grant.principal,
                    "purpose": self.grant.purpose,
                    "verified_via": self.grant.verified_via,
                },
                "facts_in_chain": [
                    {"source": f.source, "trust": f.trust, "summary": f.summary}
                    for f in self.facts
                ],
                "sequence_scope": "customer",
                "resource": resource,
                "customer": customer,
                "prior_action_classes": presented_prior,
                "forked_prior": True,
                "honest_prior_action_classes": honest_prior,
                "decision": {"allow": decision["allow"], "rule": decision["rule"]},
                "why": decision["why"],
            }
            receipt = self._seal(record)
        else:
            receipt = self._customer_receipt(
                tool, args, cls, decision, presented_prior, resource, customer)

        self.receipts.append(receipt)

        if decision["allow"] and customer is not None:
            self.performed.append(cls)
            self.ledger.record(customer, cls)
            if self.witness is not None:
                self.witness.accept(customer, cls, receipt["chain_sha256"])
        return {**decision, "receipt": receipt}
