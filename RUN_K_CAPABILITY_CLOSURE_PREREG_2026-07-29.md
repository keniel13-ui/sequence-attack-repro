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
