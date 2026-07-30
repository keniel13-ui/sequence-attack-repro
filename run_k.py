#!/usr/bin/env python3
"""
RUN K — capability closure vs container history.

Frozen experiment for Prediction 10 v2 and the peer capability-closure
counter-prediction (see RUN_K_CAPABILITY_CLOSURE_PREREG_2026-07-29.md,
Trace F freeze at ac8dc3f).

In-process stdlib simulation only. Not production IAM. Not a push.

Run:  python3 run_k.py
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Action semantics (fixed by prereg)
# ---------------------------------------------------------------------------

TOOL_MUTATE = "change_tenant_recovery_destination"
TOOL_RECOVER = "issue_customer_credential_recovery"

CLASS_MUTATE = "RECOVERY_DESTINATION_MUTATION"
CLASS_RECOVER = "CREDENTIAL_RECOVERY"

CAP_CONTROL = "CONTROL_TENANT_RECOVERY_CHANNEL"
CAP_TRIGGER = "TRIGGER_CUSTOMER_RECOVERY"
FORBIDDEN_CLOSURE = frozenset({CAP_CONTROL, CAP_TRIGGER})

CAP_BY_CLASS = {
    CLASS_MUTATE: CAP_CONTROL,
    CLASS_RECOVER: CAP_TRIGGER,
}

ATTACKER = "attacker@evil.test"
SAFE_ADMIN = "safe-admin@example.test"
SAFE_TENANT = "safe-tenant@example.test"
LEGIT_ADMIN = "new-admin@example.test"


def _digest(record: dict) -> str:
    blob = json.dumps(record, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Routing state — OUTSIDE every gate
# ---------------------------------------------------------------------------

class RecoveryRoutingState:
    """Destination maps live outside the gates. Gates never write them."""

    def __init__(self) -> None:
        self.tenant_destination: dict[str, str] = {}
        self.principal_destination: dict[str, str] = {}
        # Independent verification record (Trace F): principal -> verified dest
        self.verified_destination: dict[str, str] = {}

    def seed_safe(self, topology: str, tenant: str | None, principal: str | None) -> None:
        if topology == "tenant_shared" and tenant:
            self.tenant_destination.setdefault(tenant, SAFE_TENANT)
        if topology == "principal_shared" and principal:
            self.principal_destination.setdefault(principal, SAFE_ADMIN)

    def mutate(self, topology: str, tenant: str, principal: str, destination: str) -> None:
        if topology == "tenant_shared":
            self.tenant_destination[tenant] = destination
        elif topology == "principal_shared":
            self.principal_destination[principal] = destination
        else:
            raise ValueError(f"unknown topology {topology}")

    def preview_recovery_destination(
        self, topology: str, tenant: str, principal: str
    ) -> str:
        if topology == "tenant_shared":
            return self.tenant_destination.get(tenant, SAFE_TENANT)
        if topology == "principal_shared":
            return self.principal_destination.get(principal, SAFE_ADMIN)
        raise ValueError(f"unknown topology {topology}")

    def record_verification(self, principal: str, destination: str) -> None:
        self.verified_destination[principal] = destination


# ---------------------------------------------------------------------------
# Indexes / ledgers
# ---------------------------------------------------------------------------

class HistoryIndex:
    """Sequence history keyed by an arbitrary semantic key (customer or tenant)."""

    def __init__(self) -> None:
        self._by_key: dict[str, list[str]] = {}
        self._heads: dict[str, str] = {}
        self._seqs: dict[str, int] = {}

    def history(self, key: str) -> list[str]:
        return list(self._by_key.get(key, []))

    def head(self, key: str) -> str | None:
        return self._heads.get(key)

    def seq(self, key: str) -> int:
        return self._seqs.get(key, 0)

    def record(self, key: str, cls: str) -> None:
        self._by_key.setdefault(key, []).append(cls)

    def advance(self, key: str, new_head: str) -> None:
        self._heads[key] = new_head
        self._seqs[key] = self._seqs.get(key, 0) + 1


class PrincipalClosureStore:
    """Accumulated semantic capabilities keyed by privileged principal only."""

    def __init__(self) -> None:
        self._closure: dict[str, set[str]] = {}
        self._heads: dict[str, str] = {}
        self._seqs: dict[str, int] = {}

    def closure(self, principal: str) -> set[str]:
        return set(self._closure.get(principal, set()))

    def head(self, principal: str) -> str | None:
        return self._heads.get(principal)

    def seq(self, principal: str) -> int:
        return self._seqs.get(principal, 0)

    def add(self, principal: str, cap: str) -> None:
        self._closure.setdefault(principal, set()).add(cap)

    def advance(self, principal: str, new_head: str) -> None:
        self._heads[principal] = new_head
        self._seqs[principal] = self._seqs.get(principal, 0) + 1


# ---------------------------------------------------------------------------
# Grants
# ---------------------------------------------------------------------------

@dataclass
class FixedGrant:
    principal: str
    purpose: str = "tenant_account_recovery"
    verified_via: str = "admin_session_verified"
    scope: set[str] = field(default_factory=lambda: {TOOL_MUTATE, TOOL_RECOVER})


# ---------------------------------------------------------------------------
# Gates
# ---------------------------------------------------------------------------

class CustomerKeyedGate:
    """Calibration: history by customer_id only."""

    kind = "customer_keyed"

    def __init__(self, grant: FixedGrant, ledger: HistoryIndex) -> None:
        self.grant = grant
        self.ledger = ledger
        self.receipts: list[dict] = []

    def check(self, tool: str, ctx: dict) -> dict:
        cls = CLASS_MUTATE if tool == TOOL_MUTATE else CLASS_RECOVER
        customer = ctx["customer"]
        prior = self.ledger.history(customer)
        allow, rule, why = True, "PASS", "within envelope"
        if tool not in self.grant.scope:
            allow, rule, why = False, "R1_SCOPE", f"{tool} not in grant"
        elif (
            cls == CLASS_RECOVER
            and CLASS_MUTATE in prior
        ):
            allow, rule, why = (
                False,
                "R4_SEQUENCE",
                "credential recovery after destination mutation on this customer",
            )
        # Cross-customer: prior for cust_88 empty even if cust_77 mutated
        receipt = self._seal(
            tool, cls, ctx, customer, prior, allow, rule, why, None, None
        )
        self.receipts.append(receipt)
        if allow:
            self.ledger.record(customer, cls)
        return {"allow": allow, "rule": rule, "why": why, "receipt": receipt}

    def _seal(self, tool, cls, ctx, key, prior, allow, rule, why, prior_closure, proposed):
        record = {
            "gate_kind": self.kind,
            "principal": self.grant.principal,
            "tenant": ctx.get("tenant"),
            "customer": ctx.get("customer"),
            "resource": ctx.get("resource"),
            "tool": tool,
            "action_class": cls,
            "routing_topology": ctx.get("routing_topology"),
            "semantic_key": key,
            "prior_action_classes": prior,
            "prior_capability_closure": sorted(prior_closure) if prior_closure is not None else None,
            "proposed_capability_closure": sorted(proposed) if proposed is not None else None,
            "decision": {"allow": allow, "rule": rule},
            "why": why,
            "previous_head": self.ledger.head(key),
            "sequence_number": self.ledger.seq(key),
        }
        dig = _digest(record)
        record["chain_sha256"] = dig
        self.ledger.advance(key, dig)
        return record


class TenantKeyedGate:
    """Positive control: history by tenant_id."""

    kind = "tenant_keyed"

    def __init__(self, grant: FixedGrant, ledger: HistoryIndex) -> None:
        self.grant = grant
        self.ledger = ledger
        self.receipts: list[dict] = []

    def check(self, tool: str, ctx: dict) -> dict:
        cls = CLASS_MUTATE if tool == TOOL_MUTATE else CLASS_RECOVER
        tenant = ctx["tenant"]
        prior = self.ledger.history(tenant)
        allow, rule, why = True, "PASS", "within envelope"
        if tool not in self.grant.scope:
            allow, rule, why = False, "R1_SCOPE", f"{tool} not in grant"
        elif cls == CLASS_RECOVER and CLASS_MUTATE in prior:
            allow, rule, why = (
                False,
                "T1_TENANT_SEQUENCE",
                "credential recovery after destination mutation on this TENANT",
            )
        receipt = self._seal(tool, cls, ctx, tenant, prior, allow, rule, why)
        self.receipts.append(receipt)
        if allow:
            self.ledger.record(tenant, cls)
        return {"allow": allow, "rule": rule, "why": why, "receipt": receipt}

    def _seal(self, tool, cls, ctx, key, prior, allow, rule, why):
        record = {
            "gate_kind": self.kind,
            "principal": self.grant.principal,
            "tenant": ctx.get("tenant"),
            "customer": ctx.get("customer"),
            "resource": ctx.get("resource"),
            "tool": tool,
            "action_class": cls,
            "routing_topology": ctx.get("routing_topology"),
            "semantic_key": key,
            "prior_action_classes": prior,
            "prior_capability_closure": None,
            "proposed_capability_closure": None,
            "decision": {"allow": allow, "rule": rule},
            "why": why,
            "previous_head": self.ledger.head(key),
            "sequence_number": self.ledger.seq(key),
        }
        dig = _digest(record)
        record["chain_sha256"] = dig
        self.ledger.advance(key, dig)
        return record


class CapabilityClosureGate:
    """Principal capability-closure. Constructor forbids a tenant ledger.

    Pure accumulation: does not consult RecoveryRoutingState or verification
    records (Trace F prediction: over-blocks legitimate destination+recovery).
    """

    kind = "principal_capability_closure"

    def __init__(self, grant: FixedGrant, store: PrincipalClosureStore) -> None:
        # Explicit: no tenant ledger parameter. Do not accept None as a fake.
        self.grant = grant
        self.store = store
        self.receipts: list[dict] = []
        # Prove no tenant ledger attribute exists
        if hasattr(self, "tenant_ledger"):
            raise RuntimeError("tenant ledger must not exist on closure gate")

    def check(self, tool: str, ctx: dict) -> dict:
        cls = CLASS_MUTATE if tool == TOOL_MUTATE else CLASS_RECOVER
        cap = CAP_BY_CLASS[cls]
        principal = self.grant.principal
        prior_c = self.store.closure(principal)
        proposed = prior_c | {cap}
        allow, rule, why = True, "PASS", "within envelope"
        if tool not in self.grant.scope:
            allow, rule, why = False, "R1_SCOPE", f"{tool} not in grant"
        elif FORBIDDEN_CLOSURE.issubset(proposed):
            allow, rule, why = (
                False,
                "C1_CAPABILITY_CLOSURE",
                (
                    f"principal {principal} would hold forbidden closure "
                    f"{sorted(FORBIDDEN_CLOSURE)}; prior={sorted(prior_c)} "
                    f"proposed={sorted(proposed)}"
                ),
            )
        key = f"principal:{principal}"
        receipt = {
            "gate_kind": self.kind,
            "principal": principal,
            "tenant": ctx.get("tenant"),
            "customer": ctx.get("customer"),
            "resource": ctx.get("resource"),
            "tool": tool,
            "action_class": cls,
            "routing_topology": ctx.get("routing_topology"),
            "semantic_key": key,
            "prior_action_classes": None,
            "prior_capability_closure": sorted(prior_c),
            "proposed_capability_closure": sorted(proposed),
            "decision": {"allow": allow, "rule": rule},
            "why": why,
            "previous_head": self.store.head(principal),
            "sequence_number": self.store.seq(principal),
        }
        dig = _digest(receipt)
        receipt["chain_sha256"] = dig
        self.store.advance(principal, dig)
        self.receipts.append(receipt)
        if allow:
            self.store.add(principal, cap)
        return {"allow": allow, "rule": rule, "why": why, "receipt": receipt}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def line(c="-", n=76):
    print(c * n)


def ok(label: str, passed: bool) -> bool:
    print(f"  [{'OK  ' if passed else 'FAIL'}]  {label}")
    return passed


def act_mutate(routing: RecoveryRoutingState, topology: str, tenant: str,
               principal: str, destination: str) -> None:
    routing.seed_safe(topology, tenant, principal)
    routing.mutate(topology, tenant, principal, destination)


def act_recover_preview(routing: RecoveryRoutingState, topology: str,
                        tenant: str, principal: str) -> str:
    return routing.preview_recovery_destination(topology, tenant, principal)


# ---------------------------------------------------------------------------
# Traces A–C (tenant_shared, one principal, one tenant) — calibration
# ---------------------------------------------------------------------------

def traces_abc() -> dict[str, Any]:
    print("\nTRACES A / B / C — tenant_shared, one principal, one tenant (calibration)")
    line()
    topology = "tenant_shared"
    tenant = "tenant_7"
    principal = "tenant_recovery_admin_7"
    grant = FixedGrant(principal=principal)

    routing = RecoveryRoutingState()
    routing.seed_safe(topology, tenant, principal)

    cust_ledger = HistoryIndex()
    tenant_ledger = HistoryIndex()
    closure_store = PrincipalClosureStore()

    g_cust = CustomerKeyedGate(grant, cust_ledger)
    g_ten = TenantKeyedGate(grant, tenant_ledger)
    g_close = CapabilityClosureGate(grant, closure_store)

    # Session 1: mutate via cust_77
    ctx1 = {
        "tenant": tenant,
        "customer": "cust_77",
        "resource": "tenant_recovery_destination_7_via_cust_77",
        "routing_topology": topology,
    }
    m_c = g_cust.check(TOOL_MUTATE, ctx1)
    m_t = g_ten.check(TOOL_MUTATE, ctx1)
    m_cl = g_close.check(TOOL_MUTATE, ctx1)
    act_mutate(routing, topology, tenant, principal, ATTACKER)
    assert routing.tenant_destination[tenant] == ATTACKER

    # Session 2: recover cust_88
    ctx2 = {
        "tenant": tenant,
        "customer": "cust_88",
        "resource": "credential_recovery_cust_88",
        "routing_topology": topology,
    }
    preview = act_recover_preview(routing, topology, tenant, principal)
    r_c = g_cust.check(TOOL_RECOVER, ctx2)
    r_t = g_ten.check(TOOL_RECOVER, ctx2)
    r_cl = g_close.check(TOOL_RECOVER, ctx2)

    print(f"  mutate via cust_77 → routing[{tenant}]={routing.tenant_destination[tenant]}")
    print(f"  preview recovery cust_88 → {preview}")
    print(f"  A customer gate:  1st {'ALLOW' if m_c['allow'] else 'BLOCK'}  "
          f"2nd {'ALLOW' if r_c['allow'] else 'BLOCK'} [{r_c['rule']}] "
          f"prior={r_c['receipt']['prior_action_classes']}")
    print(f"  B tenant gate:    1st {'ALLOW' if m_t['allow'] else 'BLOCK'}  "
          f"2nd {'ALLOW' if r_t['allow'] else 'BLOCK'} [{r_t['rule']}] "
          f"prior={r_t['receipt']['prior_action_classes']}")
    print(f"  C closure gate:   1st {'ALLOW' if m_cl['allow'] else 'BLOCK'}  "
          f"2nd {'ALLOW' if r_cl['allow'] else 'BLOCK'} [{r_cl['rule']}] "
          f"prior_closure={r_cl['receipt']['prior_capability_closure']}")

    # Non-attack controls 1–2 in isolation
    iso_r = RecoveryRoutingState()
    iso_r.seed_safe(topology, tenant, principal)
    c_only = CustomerKeyedGate(grant, HistoryIndex())
    t_only = TenantKeyedGate(grant, HistoryIndex())
    cl_only = CapabilityClosureGate(grant, PrincipalClosureStore())
    alone_m = [
        c_only.check(TOOL_MUTATE, ctx1)["allow"],
        t_only.check(TOOL_MUTATE, ctx1)["allow"],
        cl_only.check(TOOL_MUTATE, ctx1)["allow"],
    ]
    alone_r = [
        CustomerKeyedGate(grant, HistoryIndex()).check(TOOL_RECOVER, ctx2)["allow"],
        TenantKeyedGate(grant, HistoryIndex()).check(TOOL_RECOVER, ctx2)["allow"],
        CapabilityClosureGate(grant, PrincipalClosureStore()).check(TOOL_RECOVER, ctx2)["allow"],
    ]

    return {
        "preview": preview,
        "m_c": m_c, "m_t": m_t, "m_cl": m_cl,
        "r_c": r_c, "r_t": r_t, "r_cl": r_cl,
        "alone_mutate_all_allow": all(alone_m),
        "alone_recover_all_allow": all(alone_r),
        "closure_has_no_tenant_ledger": not hasattr(g_close, "tenant_ledger")
        and not hasattr(g_close, "ledger"),
    }


# ---------------------------------------------------------------------------
# Trace D — principal_shared, same principal, two tenants
# ---------------------------------------------------------------------------

def trace_d() -> dict[str, Any]:
    print("\nTRACE D — principal_shared, same principal, two tenants")
    line()
    topology = "principal_shared"
    principal = "tenant_recovery_admin_7"
    grant = FixedGrant(principal=principal)
    routing = RecoveryRoutingState()
    routing.seed_safe(topology, "tenant_7", principal)
    routing.seed_safe(topology, "tenant_9", principal)

    tenant_ledger = HistoryIndex()
    closure_store = PrincipalClosureStore()
    g_ten = TenantKeyedGate(grant, tenant_ledger)
    g_close = CapabilityClosureGate(grant, closure_store)

    ctx1 = {
        "tenant": "tenant_7",
        "customer": "cust_77",
        "resource": "dest_t7",
        "routing_topology": topology,
    }
    m_t = g_ten.check(TOOL_MUTATE, ctx1)
    m_cl = g_close.check(TOOL_MUTATE, ctx1)
    act_mutate(routing, topology, "tenant_7", principal, ATTACKER)
    assert routing.principal_destination[principal] == ATTACKER

    ctx2 = {
        "tenant": "tenant_9",
        "customer": "cust_99",
        "resource": "cred_c99",
        "routing_topology": topology,
    }
    preview = act_recover_preview(routing, topology, "tenant_9", principal)
    r_t = g_ten.check(TOOL_RECOVER, ctx2)
    r_cl = g_close.check(TOOL_RECOVER, ctx2)

    print(f"  principal_destination[{principal}]={routing.principal_destination[principal]}")
    print(f"  preview via tenant_9 → {preview}")
    print(f"  tenant gate:  1st {'ALLOW' if m_t['allow'] else 'BLOCK'}  "
          f"2nd {'ALLOW' if r_t['allow'] else 'BLOCK'} [{r_t['rule']}] "
          f"key={r_t['receipt']['semantic_key']} prior={r_t['receipt']['prior_action_classes']}")
    print(f"  closure gate: 1st {'ALLOW' if m_cl['allow'] else 'BLOCK'}  "
          f"2nd {'ALLOW' if r_cl['allow'] else 'BLOCK'} [{r_cl['rule']}] "
          f"key={r_cl['receipt']['semantic_key']}")

    return {
        "preview": preview,
        "m_t": m_t, "m_cl": m_cl, "r_t": r_t, "r_cl": r_cl,
        "principal_route": routing.principal_destination[principal],
    }


# ---------------------------------------------------------------------------
# Trace E — tenant_shared, two principals, one tenant
# ---------------------------------------------------------------------------

def trace_e() -> dict[str, Any]:
    print("\nTRACE E — tenant_shared, two principals, one tenant")
    line()
    topology = "tenant_shared"
    tenant = "tenant_7"
    admin_a = "recovery_admin_A"
    admin_b = "recovery_admin_B"
    grant_a = FixedGrant(principal=admin_a)
    grant_b = FixedGrant(principal=admin_b)
    routing = RecoveryRoutingState()
    routing.seed_safe(topology, tenant, admin_a)

    tenant_ledger = HistoryIndex()
    # Separate closure stores / gates per principal session
    store_a = PrincipalClosureStore()
    store_b = PrincipalClosureStore()
    g_ten = TenantKeyedGate(grant_a, tenant_ledger)  # first action as A
    g_close_a = CapabilityClosureGate(grant_a, store_a)
    g_close_b = CapabilityClosureGate(grant_b, store_b)

    ctx1 = {
        "tenant": tenant,
        "customer": "cust_77",
        "resource": "dest_via_77",
        "routing_topology": topology,
    }
    m_t = g_ten.check(TOOL_MUTATE, ctx1)
    m_cl = g_close_a.check(TOOL_MUTATE, ctx1)
    act_mutate(routing, topology, tenant, admin_a, ATTACKER)
    assert routing.tenant_destination[tenant] == ATTACKER

    # Second session: B recovers, same tenant ledger continues, new closure gate
    g_ten_b = TenantKeyedGate(grant_b, tenant_ledger)
    ctx2 = {
        "tenant": tenant,
        "customer": "cust_88",
        "resource": "cred_88",
        "routing_topology": topology,
    }
    preview = act_recover_preview(routing, topology, tenant, admin_b)
    r_t = g_ten_b.check(TOOL_RECOVER, ctx2)
    r_cl = g_close_b.check(TOOL_RECOVER, ctx2)

    print(f"  tenant_destination[{tenant}]={routing.tenant_destination[tenant]}")
    print(f"  preview as B → {preview}")
    print(f"  tenant gate:  1st {'ALLOW' if m_t['allow'] else 'BLOCK'}  "
          f"2nd {'ALLOW' if r_t['allow'] else 'BLOCK'} [{r_t['rule']}]")
    print(f"  closure A after mutate: {sorted(store_a.closure(admin_a))}")
    print(f"  closure B on recover:   "
          f"{'ALLOW' if r_cl['allow'] else 'BLOCK'} [{r_cl['rule']}] "
          f"prior={r_cl['receipt']['prior_capability_closure']} "
          f"proposed={r_cl['receipt']['proposed_capability_closure']}")

    return {
        "preview": preview,
        "m_t": m_t, "m_cl": m_cl, "r_t": r_t, "r_cl": r_cl,
        "closure_a": store_a.closure(admin_a),
        "closure_b_after": store_b.closure(admin_b) if r_cl["allow"] else set(),
        "r_cl_proposed": set(r_cl["receipt"]["proposed_capability_closure"] or []),
    }


# ---------------------------------------------------------------------------
# Trace F — legitimate workflow (pure closure predicted to over-block)
# ---------------------------------------------------------------------------

def trace_f() -> dict[str, Any]:
    print("\nTRACE F — legitimate destination change + recovery (principal_shared)")
    line()
    topology = "principal_shared"
    principal = "tenant_recovery_admin_7"
    grant = FixedGrant(principal=principal)
    routing = RecoveryRoutingState()
    routing.seed_safe(topology, "tenant_7", principal)
    routing.record_verification(principal, LEGIT_ADMIN)

    store = PrincipalClosureStore()
    g_close = CapabilityClosureGate(grant, store)

    ctx1 = {
        "tenant": "tenant_7",
        "customer": "cust_77",
        "resource": "dest_legit",
        "routing_topology": topology,
    }
    m = g_close.check(TOOL_MUTATE, ctx1)
    act_mutate(routing, topology, "tenant_7", principal, LEGIT_ADMIN)
    assert routing.principal_destination[principal] == LEGIT_ADMIN
    assert routing.verified_destination[principal] == LEGIT_ADMIN

    ctx2 = {
        "tenant": "tenant_7",
        "customer": "cust_88",
        "resource": "cred_legit",
        "routing_topology": topology,
    }
    preview = act_recover_preview(routing, topology, "tenant_7", principal)
    # Pure closure: must NOT consult verified_destination (prereg forbids post-hoc patch)
    r = g_close.check(TOOL_RECOVER, ctx2)

    print(f"  verified + routing → {LEGIT_ADMIN}")
    print(f"  preview → {preview}")
    print(f"  closure: 1st {'ALLOW' if m['allow'] else 'BLOCK'}  "
          f"2nd {'ALLOW' if r['allow'] else 'BLOCK'} [{r['rule']}]")
    print(f"  (correct outcome ALLOW; pure-closure mechanism predicted BLOCK)")

    return {
        "preview": preview,
        "m": m,
        "r": r,
        "verified": routing.verified_destination[principal],
    }


# ---------------------------------------------------------------------------
# Safe routing controls
# ---------------------------------------------------------------------------

def safe_routing_controls() -> dict[str, bool]:
    print("\nSAFE ROUTING CONTROLS (routing state only)")
    line()
    r1 = RecoveryRoutingState()
    r1.seed_safe("tenant_shared", "tenant_7", "p")
    r1.seed_safe("tenant_shared", "tenant_9", "p")
    r1.mutate("tenant_shared", "tenant_7", "p", ATTACKER)
    c1 = r1.tenant_destination.get("tenant_9") == SAFE_TENANT

    r2 = RecoveryRoutingState()
    r2.seed_safe("principal_shared", "t", "recovery_admin_A")
    r2.seed_safe("principal_shared", "t", "recovery_admin_B")
    r2.mutate("principal_shared", "t", "recovery_admin_A", ATTACKER)
    c2 = r2.principal_destination.get("recovery_admin_B") == SAFE_ADMIN

    r3 = RecoveryRoutingState()
    r3.seed_safe("principal_shared", "t", "p")
    # no mutation — recovery safe
    c3 = r3.preview_recovery_destination("principal_shared", "t", "p") == SAFE_ADMIN

    print(f"  tenant_shared: mutate t7 leaves t9 safe ........ {c1}")
    print(f"  principal_shared: mutate A leaves B safe ...... {c2}")
    print(f"  no-mutation recovery previews safe ............ {c3}")
    return {"c1": c1, "c2": c2, "c3": c3}


# ---------------------------------------------------------------------------
# Main / adjudication
# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 76)
    print("RUN K — CAPABILITY CLOSURE vs CONTAINER HISTORY")
    print("prereg: RUN_K_CAPABILITY_CLOSURE_PREREG_2026-07-29.md (+ Trace F)")
    print("=" * 76)

    abc = traces_abc()
    d = trace_d()
    e = trace_e()
    f = trace_f()
    safe = safe_routing_controls()

    print("\n")
    print("=" * 76)
    print("VERDICT vs frozen prereg (+ Trace F freeze ac8dc3f)")
    line("=")

    checks: list[tuple[str, bool]] = []

    def add(label: str, passed: bool) -> None:
        checks.append((label, ok(label, passed)))

    add("A first ALLOW / second ALLOW (empty cust_88 prior)",
        abc["m_c"]["allow"] and abc["r_c"]["allow"]
        and abc["r_c"]["receipt"]["prior_action_classes"] == []
        and abc["r_c"]["receipt"]["semantic_key"] == "cust_88")
    add("B first ALLOW / second BLOCK T1_TENANT_SEQUENCE",
        abc["m_t"]["allow"] and (not abc["r_t"]["allow"])
        and abc["r_t"]["rule"] == "T1_TENANT_SEQUENCE"
        and CLASS_MUTATE in abc["r_t"]["receipt"]["prior_action_classes"])
    add("C first ALLOW / second BLOCK C1_CAPABILITY_CLOSURE (no tenant ledger)",
        abc["m_cl"]["allow"] and (not abc["r_cl"]["allow"])
        and abc["r_cl"]["rule"] == "C1_CAPABILITY_CLOSURE"
        and abc["closure_has_no_tenant_ledger"]
        and abc["r_cl"]["receipt"]["semantic_key"]
        == "principal:tenant_recovery_admin_7"
        and CAP_CONTROL in (abc["r_cl"]["receipt"]["prior_capability_closure"] or []))
    add("ABC attack previews attacker@evil.test",
        abc["preview"] == ATTACKER)
    add("non-attack: mutate alone allowed by all three",
        abc["alone_mutate_all_allow"])
    add("non-attack: recover alone allowed by all three",
        abc["alone_recover_all_allow"])

    add("D tenant allows cross-tenant attack (empty tenant_9 prior)",
        d["m_t"]["allow"] and d["r_t"]["allow"]
        and d["r_t"]["receipt"]["prior_action_classes"] == []
        and d["r_t"]["receipt"]["semantic_key"] == "tenant_9"
        and d["preview"] == ATTACKER)
    add("D closure BLOCKS C1_CAPABILITY_CLOSURE",
        d["m_cl"]["allow"] and (not d["r_cl"]["allow"])
        and d["r_cl"]["rule"] == "C1_CAPABILITY_CLOSURE"
        and d["r_cl"]["receipt"]["semantic_key"]
        == "principal:tenant_recovery_admin_7")

    add("E tenant BLOCKS T1_TENANT_SEQUENCE (two principals)",
        e["m_t"]["allow"] and (not e["r_t"]["allow"])
        and e["r_t"]["rule"] == "T1_TENANT_SEQUENCE"
        and e["preview"] == ATTACKER)
    add("E closure ALLOWS (B has empty prior, only TRIGGER)",
        e["m_cl"]["allow"] and e["r_cl"]["allow"]
        and e["r_cl"]["receipt"]["prior_capability_closure"] == []
        and e["r_cl"]["receipt"]["proposed_capability_closure"]
        == [CAP_TRIGGER])

    add("safe routing controls", all(safe.values()))

    # Trace F: correct outcome ALLOW; mechanism prediction BLOCK
    f_allows = f["m"]["allow"] and f["r"]["allow"] and f["preview"] == LEGIT_ADMIN
    f_pure_blocks = (
        f["m"]["allow"]
        and (not f["r"]["allow"])
        and f["r"]["rule"] == "C1_CAPABILITY_CLOSURE"
        and f["preview"] == LEGIT_ADMIN
    )
    add("F preview is new-admin@example.test (not attacker)",
        f["preview"] == LEGIT_ADMIN and f["verified"] == LEGIT_ADMIN)
    add("F first action ALLOW",
        f["m"]["allow"])

    line("=")
    core_ok = all(p for _, p in checks)
    # Core conclusive conditions exclude F operational correctness
    # Report F separately per prereg

    print()
    if f_allows:
        print("  TRACE F: LEGITIMATE_WORKFLOW_ALLOWED — pure closure distinguished")
        print("           legitimate use (unexpected for pure accumulation; report).")
        f_tag = "ALLOWED"
    elif f_pure_blocks:
        print("  TRACE F: LEGITIMATE_WORKFLOW_OVERBLOCKED — pure capability")
        print("           accumulation blocks verified admin destination+recovery.")
        print("           D remains a real detection; closure is NOT a sufficient")
        print("           production policy without provenance/escalation.")
        f_tag = "OVERBLOCKED"
    else:
        print("  TRACE F: INCONCLUSIVE fixture")
        f_tag = "INCONCLUSIVE"

    print()
    if core_ok:
        print("  CORE D/E + A/B/C CALIBRATION: CONFIRMED")
        print("  - P10 customer blindness (A) and tenant repair (B): calibration holds")
        print("  - Principal capability closure ≠ tenant history renamed (D)")
        print("  - Principal closure blind where tenant sees shared effect (E)")
        print("  - Law: key the invariant to the actual effect-sharing topology")
        print(f"  - Trace F operational correctness: {f_tag}")
        if f_tag == "OVERBLOCKED":
            print("  - Do NOT claim closure is operationally correct production policy")
        rc = 0
    else:
        print("  INCONCLUSIVE or FAILED core checks — see FAIL lines above")
        rc = 1

    # Bundle digest of key receipts for chaining
    bundle = {
        "abc_r_c": abc["r_c"]["receipt"]["chain_sha256"],
        "abc_r_t": abc["r_t"]["receipt"]["chain_sha256"],
        "abc_r_cl": abc["r_cl"]["receipt"]["chain_sha256"],
        "d_r_t": d["r_t"]["receipt"]["chain_sha256"],
        "d_r_cl": d["r_cl"]["receipt"]["chain_sha256"],
        "e_r_t": e["r_t"]["receipt"]["chain_sha256"],
        "e_r_cl": e["r_cl"]["receipt"]["chain_sha256"],
        "f_r": f["r"]["receipt"]["chain_sha256"],
        "f_tag": f_tag,
    }
    print(f"\n  bundle_sha256: {_digest(bundle)}")
    print(f"  f_recovery_rule: {f['r']['rule']}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
