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
        blob = json.dumps(record, sort_keys=True, separators=(",", ":"))
        record["chain_sha256"] = hashlib.sha256(blob.encode()).hexdigest()
        record["decided_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        return record
