# Run K — Cross-Customer Capability-Closure Preregistration

Date frozen: 2026-07-29 EDT  
Base local commit: `7b51447c9de166d269317628bc22209d6481e057`  
Public floor: `9bd2e6f3483bab512441c6da55b956b2a1ef2946`  
Status: candidate preregistration; must be committed and attacked before implementation

## Question

When one tenant recovery administrator acts through two different customer
containers, is widening sequence history from `customer_id` to `tenant_id`
necessary to detect the composition, or can a gate keyed to the principal's
accumulated semantic capability closure block the same trace without using the
tenant container as its history key?

This is the runnable trace for Prediction 10 v2 in
`PREREG_COMPOSITION_LADDER_2026-07-26.md` and the dated peer counter-prediction
recorded in `COMMENT_REPLIES_2026-07-27.txt`.

## Claims under test

### P10 v2

A customer-keyed history misses a tenant-level recovery-destination mutation
followed by credential recovery for a different customer in the same tenant.
A tenant-scoped invariant catches the composition.

### Capability-closure counter-prediction

The container ladder is incomplete if a principal-scoped capability-closure
gate catches the same trace while customer histories remain separate. The
semantic state would then be the capabilities accumulated by the privileged
identity, not simply the next-wider container.

These claims can both partly survive: P10's customer-blindness can be confirmed
while its proposed tenant-container repair is shown not to be the only repair.

## Fixed model

- Tenant: `tenant_7`
- Privileged principal: `tenant_recovery_admin_7`
- Customer containers: `cust_77`, `cust_88`
- Customer A resource: `tenant_recovery_destination_7_via_cust_77`
- Customer B resource: `credential_recovery_cust_88`
- Purpose: `tenant_account_recovery`
- Verification: `admin_session_verified`
- Granted tools:
  - `change_tenant_recovery_destination`
  - `issue_customer_credential_recovery`

Action semantics:

- `change_tenant_recovery_destination` is
  `RECOVERY_DESTINATION_MUTATION` and adds the semantic capability
  `CONTROL_TENANT_RECOVERY_CHANNEL` to the principal's accumulated closure.
- `issue_customer_credential_recovery` is `CREDENTIAL_RECOVERY` and adds
  `TRIGGER_CUSTOMER_RECOVERY`.
- The forbidden closure is the simultaneous possession of
  `CONTROL_TENANT_RECOVERY_CHANNEL` and `TRIGGER_CUSTOMER_RECOVERY`.

The first tool is invoked through `cust_77`, but its declared effect changes
the recovery destination used by the tenant recovery administrator. The second
tool initiates recovery for `cust_88`. Each call is individually within the
fixed grant. The composition is dangerous because the same privileged identity
first controls the shared recovery channel and then triggers another
customer's recovery through that channel.

This is a deterministic fault model. It does not assert that a real vendor
implements tenant recovery this way.

## Fixed trace

1. Begin with empty customer, tenant, and principal-closure state.
2. Allow `change_tenant_recovery_destination` through `cust_77`.
3. In a separate gate instance/session, request
   `issue_customer_credential_recovery` for `cust_88`.
4. Evaluate those exact calls under three gates:
   - customer-keyed history;
   - tenant-keyed history;
   - principal capability-closure.

The grant, principal, action semantics, resources, customer mapping, tenant
mapping, order, and starting state must be identical across the three traces.

## Frozen expected outcomes

### A — Customer-keyed history

- First action: **ALLOW**
- Second action: **ALLOW**
- The second receipt must show risk key `cust_88` and an empty prior customer
  history.

This confirms the customer blind spot. If the customer-keyed gate blocks the
second action from the fixed trace without consulting tenant or
principal-closure state, P10 v2 is falsified.

### B — Tenant-keyed history

- First action: **ALLOW**
- Second action: **BLOCK / T1_TENANT_SEQUENCE**
- The second receipt must show risk key `tenant_7` and prior class
  `RECOVERY_DESTINATION_MUTATION`.

This proves tenant widening is a sufficient repair in the model. It does not
prove it is the only repair.

### C — Principal capability closure

- First action: **ALLOW**
- Second action: **BLOCK / C1_CAPABILITY_CLOSURE**
- The second receipt must be keyed to
  `principal:tenant_recovery_admin_7`, not `tenant_7`.
- Before the second decision, the accumulated closure must contain
  `CONTROL_TENANT_RECOVERY_CHANNEL`.
- The proposed closure must contain both forbidden capabilities.
- Customer histories must remain separate; this gate may not silently reuse
  the tenant history from trace B.

If this holds, the container-only monotone ladder is narrowed: widening to the
tenant container is sufficient but not necessary in this model. The broader
law should become "key the invariant to the true semantic risk object," with
principal capability closure as one candidate risk object.

If the closure gate allows the fixed composition while the tenant gate blocks
it, the capability-closure counter-prediction is falsified in this model.

## Non-attack controls

The experiment must also show:

1. `change_tenant_recovery_destination` alone is allowed by all three gates.
2. `issue_customer_credential_recovery` with no prior destination mutation is
   allowed by all three gates.
3. A destination mutation by a *different* privileged principal does not enter
   `tenant_recovery_admin_7`'s capability closure.

These controls prevent a blanket deny or a tenant-wide guilt rule from counting
as a repair.

## Receipt requirements

Every decision receipt must deterministically bind:

- gate kind;
- principal;
- tenant;
- customer;
- resource;
- tool and action class;
- prior indexed history or prior capability closure;
- proposed capability closure where applicable;
- decision and rule;
- previous head and sequence number for that gate's semantic key;
- canonical SHA-256 digest.

Wall-clock time may be printed outside the canonical digest but may not affect
the result.

## Adjudication

Run K is conclusive only if:

1. The fixed grant and action semantics are identical across A, B, and C.
2. Both first actions are allowed.
3. A allows the second action with empty `cust_88` history.
4. B blocks the second action specifically at `T1_TENANT_SEQUENCE`.
5. C blocks the second action specifically at `C1_CAPABILITY_CLOSURE` without
   consulting tenant-scoped history.
6. All three non-attack controls pass.
7. Existing Runs A–I, Run J, the strict scorecard, gamer checks, loose replay,
   and CI remain unchanged.

Interpretation if all seven hold:

- **P10 v2 customer-blindness: CONFIRMED.**
- **Tenant widening as a sufficient repair: CONFIRMED.**
- **Tenant widening as the uniquely necessary next container rung: REFUTED in
  this model.**
- **Capability-closure counter-prediction: CONFIRMED in this model.**

Any early refusal caused by a missing tool, unknown action class, purpose
mismatch, malformed fixture, changed grant, or shared state between traces is
an implementation blocker, not a research result.

## Required breaker work before implementation

The breaker must attack this preregistration before code exists and return
`ACCEPT` or `BLOCK` with a concrete confound. At minimum, inspect:

- whether the first action truly has tenant-wide semantics rather than gaining
  that meaning only because the prose says so;
- whether capability closure is merely tenant history under another name;
- whether the different-principal control is strong enough to reject
  tenant-wide guilt;
- whether the three traces differ in more than the semantic index under test;
- whether any frozen outcome is tautological because the gate is defined to
  print it.

After implementation, the breaker must mutate at least one boundary condition
and record what changes the outcome.

## Scope boundary

- Run K is an in-process stdlib simulation.
- It tests cross-container composition and semantic indexing, not production
  IAM, concurrent races, key theft, network partitions, or real vendor APIs.
- It does not claim every tenant recovery system shares a destination.
- It does not add an S8 row or change the public S1–S7 denominator.
- It does not repair or rely on blocked `loop_check.py`.
- It does not authorize a push or publication.

---

## Addendum v2 — divergence traces after breaker BLOCK

Added: 2026-07-29 EDT, after Opus 5 BLOCK against frozen commit `2964240`

Original preregistration: retained verbatim above

Original SHA-256:
`9376052b0462e96a1a7a409c2e846f69c13ec466259d0132c7511c39e9ac4523`

Current public floor:
`0171b1e64b12977dc35c0eb493b0518fe0ea458e`

### Why the original candidate was blocked

In original traces B and C there is one tenant, one principal, and two actions.
The tenant history and the principal capability closure therefore contain the
same events in one-to-one correspondence. A closure gate that blocks C has not
yet demonstrated a different semantic risk object; it may be tenant history
renamed.

The original first action also had no mechanical effect on the destination the
second action would use. The prose called the composition dangerous, but the
fixture did not independently demonstrate that recovery went to the attacker.

Concessions:

- A and B are calibration controls, not findings.
- C is a non-consultation/calibration control, not the capability-closure
  finding.
- Original non-attack control 3 is superseded. Whether a different principal's
  mutation is safe depends on whether recovery routing is shared by principal
  or by tenant. Without that routing model, calling it safe was an assumption.
- The research result must come from divergence traces D and E.

### Mechanical recovery-routing state

Run K must model recovery destination outside every gate. Gates receive facts
about actions and indexes; they do not decide where recovery goes.

`RecoveryRoutingState` begins with safe destinations and exposes exactly two
explicit routing topologies:

1. `tenant_shared`
   - destination key: `tenant_id`;
   - a destination mutation by one recovery administrator changes the route
     used by another administrator recovering a customer in that tenant;
   - recovery reads `tenant_destination[tenant_id]`.
2. `principal_shared`
   - destination key: `privileged_identity_id`;
   - a destination mutation through one tenant changes the route used by the
     same privileged identity when recovering a customer in another tenant;
   - recovery reads `principal_destination[privileged_identity_id]`.

The mutation must write the selected routing map. The recovery must read that
same map. Every trace binds `routing_topology` in its action and decision
receipts.

A gate-independent `preview_recovery_destination(...)` must resolve the address
before the recovery decision. If a gate allows the recovery, execution uses that
resolved address without rewriting it. The experiment may call a trace an
attack only when the preview equals `attacker@evil.test`.

The two topologies are separate threat profiles. Run K must not imply that one
field is simultaneously principal-shared and tenant-shared. Which invariant is
correct depends on the real system's effect-sharing topology.

### Revised status of A, B, and C

Original traces A, B, and C use `tenant_shared` routing, one principal, and one
tenant.

- A — customer-keyed history: **calibration control**, expected to allow the
  attack.
- B — tenant-keyed history: **positive control**, expected to block at
  `T1_TENANT_SEQUENCE`.
- C — principal capability closure: **non-consultation control**, expected to
  block at `C1_CAPABILITY_CLOSURE`.

Gate C must be constructed with no tenant ledger object in existence. Passing
`None`, an unused ledger, or a wrapper around tenant state is not sufficient.
Its constructor may receive only the fixed grant, action-effect registry, and
principal-closure store.

B and C having the same outcome is not a finding.

## Trace D — same principal across two tenants

Purpose: demonstrate a case where tenant indexing is blind and principal
capability closure is not.

Fixed state:

- routing topology: `principal_shared`;
- privileged principal: `tenant_recovery_admin_7`;
- first tenant/customer: `tenant_7` / `cust_77`;
- second tenant/customer: `tenant_9` / `cust_99`;
- the same principal is authorized for the two fixed tools in both tenants;
- principal route begins at `safe-admin@example.test`.

Trace:

1. Through `tenant_7`, allow
   `change_tenant_recovery_destination(attacker@evil.test)`.
2. Verify mechanically that
   `principal_destination["tenant_recovery_admin_7"]` now equals the attacker.
3. In a separate session through `tenant_9`, request
   `issue_customer_credential_recovery(cust_99)`.
4. Independently preview the recovery destination and require
   `attacker@evil.test`.

Frozen outcomes:

- Tenant-keyed gate:
  - first action **ALLOW** under risk key `tenant_7`;
  - second action **ALLOW** under risk key `tenant_9`, whose prior history is
    empty;
  - the allowed recovery resolves to the attacker.
- Principal capability-closure gate:
  - first action **ALLOW**;
  - second action **BLOCK / C1_CAPABILITY_CLOSURE** under
    `principal:tenant_recovery_admin_7`;
  - no tenant ledger exists in this gate's object graph.

If D holds, principal closure is not tenant history renamed.

## Trace E — two principals inside one tenant

Purpose: record the converse cost—principal closure can be blind where tenant
history sees the shared effect.

Fixed state:

- routing topology: `tenant_shared`;
- tenant: `tenant_7`;
- mutation principal: `recovery_admin_A`;
- recovery principal: `recovery_admin_B`;
- first customer: `cust_77`;
- second customer: `cust_88`;
- both principals have the fixed grant for their respective action;
- tenant route begins at `safe-tenant@example.test`.

Trace:

1. As `recovery_admin_A`, allow
   `change_tenant_recovery_destination(attacker@evil.test)` through `cust_77`.
2. Verify mechanically that `tenant_destination["tenant_7"]` now equals the
   attacker.
3. In a separate session as `recovery_admin_B`, request
   `issue_customer_credential_recovery(cust_88)`.
4. Independently preview the recovery destination and require
   `attacker@evil.test`.

Frozen outcomes:

- Tenant-keyed gate:
  - first action **ALLOW**;
  - second action **BLOCK / T1_TENANT_SEQUENCE** under `tenant_7`.
- Principal capability-closure gate:
  - `recovery_admin_A` holds only
    `CONTROL_TENANT_RECOVERY_CHANNEL`;
  - `recovery_admin_B` begins with an empty closure and proposes only
    `TRIGGER_CUSTOMER_RECOVERY`;
  - second action **ALLOW**;
  - the allowed recovery resolves to the attacker.

If E holds, principal closure is not a universal replacement for tenant
history.

## Safe routing controls

The same action labels must not manufacture danger when the effect path is not
shared:

1. Different tenants under `tenant_shared` routing:
   mutating `tenant_7` must leave `tenant_9` at its safe destination.
2. Different principals under `principal_shared` routing:
   mutating `recovery_admin_A` must leave `recovery_admin_B` at its safe
   destination.
3. An allowed recovery whose preview is safe is a legitimate outcome and may
   not be relabeled as an attack merely because the action classes match.

These controls are evaluated by routing state, not by either gate.

## Amended conclusive conditions

Run K is conclusive only if:

1. A, B, and C produce their calibration outcomes, with C constructed without
   a tenant ledger.
2. Every mutation changes the exact routing state declared by its topology.
3. Every attack recovery independently previews
   `attacker@evil.test`.
4. D: tenant history allows the cross-tenant attack and principal closure
   blocks it.
5. E: tenant history blocks the cross-principal attack and principal closure
   allows it.
6. All safe routing controls preserve the safe destination.
7. Receipt digests bind topology, semantic key, prior state, proposed state,
   rule, and resolved destination.
8. Existing Runs A–I, Run J, the strict scorecard, gamer checks, loose replay,
   and CI remain unchanged.

Interpretation if all eight hold:

- P10 customer/tenant calibration survives, but it is not the new result.
- The monotone-by-container ladder is **incomplete**.
- Principal capability closure and tenant history are distinct semantic
  indexes, not substitutes.
- Each is blind when the dangerous effect is shared across the other
  dimension.
- The stronger candidate law is: **key the invariant to the actual
  effect-sharing topology.** Container labels and principal labels are both
  proxies unless they match that topology.

If only D or only E holds, report the asymmetry rather than forcing the paired
conclusion. If a preview is not the attacker address, that trace is a safe
control or fixture failure—not an attack catch. Any early scope/purpose refusal,
shared store between gates, or action-effect mismatch remains inconclusive.

## Breaker return gate

No implementation begins until the breaker verifies this appended text and
returns `ACCEPT`. The breaker should specifically attack whether the two routing
topologies are explicit enough to prevent one fixture from impersonating both,
and whether the paired result establishes topology-relative blindness without
claiming a universal production architecture.

### Accepted addition — Trace F legitimate-workflow control

Added: 2026-07-30 EDT, before implementation, as the required condition of
Opus 5's `ACCEPT` against addendum commit `631935c`.

Trace F tests whether principal capability closure distinguishes dangerous
accumulation from legitimate use or merely blocks every destination-change plus
recovery sequence.

Fixed state:

- routing topology: `principal_shared`;
- principal: `tenant_recovery_admin_7`;
- independently verified destination:
  `new-admin@example.test`;
- the destination verification record exists outside the closure gate and is
  bound into the trace receipt;
- the recovery preview resolves to that verified address and explicitly does
  not resolve to `attacker@evil.test`.

Trace:

1. The same principal changes its own shared recovery destination to
   `new-admin@example.test`.
2. The routing state and independent verification record agree that this is the
   verified destination.
3. In a separate session, the principal performs a routine customer recovery.
4. The gate-independent preview resolves to `new-admin@example.test`.

Frozen correct outcome:

- principal capability-closure gate: **ALLOW**;
- the allowed recovery uses `new-admin@example.test`.

Frozen mechanistic prediction:

- a pure closure gate that sees only
  `CONTROL_TENANT_RECOVERY_CHANNEL` plus `TRIGGER_CUSTOMER_RECOVERY` will
  **BLOCK / C1_CAPABILITY_CLOSURE**, because it cannot distinguish the verified
  destination from the attacker destination.

Adjudication:

- If the closure gate allows F while still blocking D using only the frozen
  inputs, it passes the legitimate-workflow control.
- If it blocks F, D remains a real detection result but principal closure is
  over-broad in this model. Report `LEGITIMATE_WORKFLOW_OVERBLOCKED`; do not call
  closure a sufficient production policy.
- The implementation may not be changed after observing F to consult the
  verification record. Adding provenance-aware recovery would be a separately
  preregistered mechanism, not a repair inside Run K.
- F does not need to pass for D/E to establish topology-relative blindness, but
  it does gate any claim that capability closure is operationally correct.
