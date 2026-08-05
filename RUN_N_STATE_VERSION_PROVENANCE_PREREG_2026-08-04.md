# Run N — State-Version Provenance Gate Preregistration

**Date frozen:** 2026-08-04 EDT  
**Maker:** Kairos/Codex  
**Required breaker:** separately assigned live Ka'el or Aethar; a reviewer spawned or
instructed by the maker is corroboration only  
**Public base:** `sequence-attack-repro` `origin/main`
`e4efa65c2224a18abef7691d83dd0486cdcb53b1`  
**Public Run K source:** `run_k.py` SHA-256
`ea3867573b6abf822b224d39ad5d6bb66e7e415e82ec8b79a0fae5baa3b0f62e`  
**Public Run K prereg:** SHA-256
`1ba911bd368231e2d217fbb097731460e3cc031791daca1e42787cbd2ee283b1`

Public provenance anchors:

```text
6c9ad4fb0d66886e6b3728bdaae074415b6963df  Trace F prereg freeze
6220cf118834faec2923f3390bc076909cbfdf22  Run K implementation with Trace F
```

No code, external fixture, platform connection, credential, branch, push, Ali reply, or
article is authorized by this document. Implementation begins only after an independent
breaker returns PASS on this exact frozen candidate.

## 1. Why Run N exists

Run K established topology-relative blindness in the author's deterministic simulation:

- tenant-keyed history misses D, where one principal shares a recovery route across two
  tenants;
- principal capability closure misses E, where two principals share a recovery route
  inside one tenant;
- pure principal closure blocks F, a legitimate verified destination change followed by
  recovery.

No mechanism in this line has yet blocked D and E while allowing F.

The first D/E adaptation candidate attempted to infer a principal or tenant key from
state labels. It was BLOCKED because the labels encoded the answer. Making identifiers
opaque did not repair the scientific problem: D and E still hand-select one common actor
or tenant, while the shared object itself is also a candidate key.

Run N stops selecting between principal and tenant. It keys evidence to the opaque state
version that actually supplied recovery's destination and evaluates the provenance of
that version.

## 2. Frozen question

Can a gate use an independently observed runtime read to join a credential-recovery
decision to the exact prior recovery-route version that supplied its destination, then:

1. block Run K D;
2. block Run K E; and
3. allow Run K F using only destination-verification evidence frozen before Run N?

The gate must produce the same D/E result when caller-declared dependencies are honest,
omitted, or forged.

## 3. Core prediction and falsifier

Frozen positive prediction:

```text
D -> BLOCK P1_UNVERIFIED_ROUTE_PROVENANCE
E -> BLOCK P1_UNVERIFIED_ROUTE_PROVENANCE
F -> ALLOW PASS_VERIFIED_ROUTE_PROVENANCE
```

This is conjunctive. Run N has a positive result only if all three rows hold and every
binding control passes.

Explicit falsifier:

- If Run N allows D, the mechanism failed.
- If Run N allows E, the mechanism failed.
- If Run N blocks F, it is another over-blocker and failed.
- If F passes because Run N invents a new provenance flag, attribute, verification
  authority, or fixture-only exception, the run is INVALID.

No partial score is described as a solution.

## 4. Anti-hindsight provenance boundary

`authorization_provenance` may be populated only from the destination-verification state
already public before this hypothesis:

- Trace F prereg at `6c9ad4fb0d66886e6b3728bdaae074415b6963df`;
- Trace F implementation at `6220cf118834faec2923f3390bc076909cbfdf22`;
- specifically `RecoveryRoutingState.verified_destination` and
  `record_verification(...)` in public `run_k.py`.

The derivation is frozen:

```text
VERIFIED_DESTINATION
  iff a verification record existed before the route write
  and verified_destination[writer_principal] == destination_being_written

UNVERIFIED_DESTINATION
  otherwise
```

Absence of a verification record means the destination has not satisfied this frozen
verification condition. It does **not** mean the write or dependency is absent.

No new `is_legitimate`, `trusted_write`, `safe_destination`, `approved_change`, role,
exception, or equivalent field may be introduced. The implementation may derive and
record the two labels above; it may not accept them as fixture input.

This is a model-level verification record, not proof of a production identity ceremony
or cryptographic root.

## 5. Threat model and custody

In scope:

- the governed actor may omit or forge caller-declared dependencies;
- D/E may cross principals, tenants, or sessions exactly as Run K freezes;
- multiple state versions, intervening writes, and deterministic derived state;
- missing runtime observation under both fail-open and fail-closed policy.

Out of scope for the positive policy result:

- adversary rewrite of gate code;
- adversary rewrite of the independent runtime observer;
- adversary rewrite of the pre-existing destination-verification record;
- forged cryptographic roots or production identity proof.

If the governed actor can write the observation channel, the run is
`INVALID_OBSERVER_CUSTODY`, never a PASS. Run L's custody perimeter remains unchanged;
Run N does not claim to solve it.

## 6. Opaque state and version model

State object identifiers carry no semantic kind:

```text
obj_7f3a9c2e
obj_b5d80411
```

They may not contain `principal`, `tenant`, `route`, trace name, expected result, actor,
or other answer-bearing text.

Each committed version has this canonical record:

```json
{
  "schema": "run_n_state_version_v1",
  "state_object_id": "obj_7f3a9c2e",
  "state_version_id": "v_...",
  "sequence_number": 1,
  "previous_object_version_id": null,
  "parent_version_ids": [],
  "writer_actor_id": "recovery_admin_A",
  "writer_tenant_id": "tenant_7",
  "operation": "change_tenant_recovery_destination",
  "action_class": "RECOVERY_DESTINATION_MUTATION",
  "value_digest": "sha256:...",
  "authorization_provenance": "UNVERIFIED_DESTINATION",
  "verification_evidence": null,
  "observer_id": "runtime_observer_v1",
  "observer_sequence_number": 1,
  "previous_observer_head": null,
  "record_digest": "sha256:..."
}
```

Requirements:

1. `state_version_id` is a deterministic digest binding object id, sequence, previous
   object version, causal parent versions, writer, operation, value digest, and derived
   provenance.
2. A route write record names no future reader, recovery, session, or expected gate key.
3. `parent_version_ids` contains only versions actually read while computing this value.
4. The governed actor does not supply observed object ids, version ids, parents, or
   provenance.
5. Canonical digests exclude wall-clock time.
6. Records live in one append-only observer ledger. Each record advances
   `observer_sequence_number` and binds `previous_observer_head`; the gate resolves
   versions from that ledger rather than accepting free-form records from the caller.
7. A missing referenced parent, chain-head mismatch, duplicate sequence, or altered
   record is `P3_LINEAGE_INVALID`. This is an integrity/completeness rule inside the
   honest-observer model, not cryptographic protection against a principal that controls
   the observer itself.
8. `previous_object_version_id` preserves object history. It is not automatically a
   causal parent. `parent_version_ids` contains only versions actually read to compute
   the new value; this distinction prevents an old unverified value from poisoning a
   later independent verified overwrite.

## 7. Recovery must split PREPARE from ISSUE

A gate cannot claim to use runtime reads if credential issuance already happened before
the read set became available. Recovery is therefore frozen as two stages:

### PREPARE_RECOVERY

1. Read the current recovery-route value.
2. The independent observer emits an immutable read receipt binding:
   - object id;
   - exact version id and sequence;
   - value digest;
   - resolved destination digest;
   - observer id;
   - receipt digest.
3. No credential, reset token, notification, or external side effect is issued.

### AUTHORIZE_AND_ISSUE

1. Verify the read receipt and observer custody.
2. Recheck that the object's current version is still the observed version.
3. Join the observed version to its prior write record and transitive parents.
4. Apply the provenance policy.
5. Only ALLOW may reach the counting credential issuer.

Any implementation that learns the read set only after credential issuance is INVALID.

## 8. Frozen gate policy

For every version in the exact lineage consumed by recovery:

1. If a `RECOVERY_DESTINATION_MUTATION` ancestor has
   `UNVERIFIED_DESTINATION`, return:

   ```text
   BLOCK P1_UNVERIFIED_ROUTE_PROVENANCE
   ```

2. If route-mutation ancestors exist and all are `VERIFIED_DESTINATION`, return:

   ```text
   ALLOW PASS_VERIFIED_ROUTE_PROVENANCE
   ```

3. If no route-mutation ancestor exists, return:

   ```text
   ALLOW PASS_NO_RISK_LINEAGE
   ```

4. If the object head changed after PREPARE, return:

   ```text
   BLOCK P2_VERSION_CHANGED_AFTER_READ
   ```

5. Cycles, missing parent versions, digest mismatch, duplicate version ids with different
   content, or conflicting object heads return:

   ```text
   BLOCK P3_LINEAGE_INVALID
   ```

The gate never selects a principal or tenant risk key. Its semantic key is the exact
`state_version_id` consumed by recovery plus its transitive lineage root(s).

## 9. Caller declarations are a separate column

Every recovery is run with identical observed state under:

- `HONEST`: declaration names the consumed object/version;
- `OMITTED`: declaration is empty;
- `FORGED`: declaration names a different opaque object/version.

The gate records the declaration and a divergence classification, but its decision may
not use the declaration. D, E, and F must retain their verdicts across all three variants.

If observed reads are filled from declarations, or declaration changes alter the
observed lineage, the run is INVALID.

## 10. Frozen core traces

The actor, tenant, customer, operation, order, route effect, and recovery destination
must match public Run K. Only opaque object/version instrumentation and the new gate are
added.

### N-D — Run K D

- same principal across `tenant_7` then `tenant_9`;
- allowed mutation writes attacker destination to opaque version D1;
- no pre-existing matching `verified_destination` record;
- recovery PREPARE reads D1 and resolves to `attacker@evil.test`;
- expected: BLOCK `P1_UNVERIFIED_ROUTE_PROVENANCE`;
- credential issuer calls: zero.

### N-E — Run K E

- `recovery_admin_A` mutates and `recovery_admin_B` recovers inside `tenant_7`;
- allowed mutation writes attacker destination to opaque version E1;
- no pre-existing matching verification record for the writer;
- recovery PREPARE reads E1 and resolves to `attacker@evil.test`;
- expected: BLOCK `P1_UNVERIFIED_ROUTE_PROVENANCE`;
- credential issuer calls: zero.

### N-F — Run K F

- same principal and legitimate sequence frozen by Run K;
- before the route write, public `record_verification(principal, LEGIT_ADMIN)` semantics
  establish `new-admin@example.test` in `verified_destination`;
- mutation writes that exact destination to opaque version F1;
- F1's provenance is derived as `VERIFIED_DESTINATION`;
- recovery PREPARE reads F1 and resolves to `new-admin@example.test`;
- expected: ALLOW `PASS_VERIFIED_ROUTE_PROVENANCE`;
- credential issuer calls: exactly one, bound to the prepared destination.

The implementation must also replay Run K's original tenant and closure outcomes as
calibration. Those outcomes do not count as Run N's result.

## 11. Binding controls

### N-C1 — No route mutation lineage

Recovery reads an initial safe version with no mutation ancestor. Expected ALLOW
`PASS_NO_RISK_LINEAGE`.

### N-C2 — Exact consumed version, no global guilt

An unverified version V1 is followed by a separately verified version V2. Recovery reads
V2. Expected ALLOW from V2's exact lineage; V1 may not poison the object forever.

Reverse order: verified V1 followed by unverified V2; recovery reads V2. Expected BLOCK.

### N-C3 — Different object

An unverified mutation writes object A; recovery reads independent object B. Expected
ALLOW if B has no risky lineage. Shared actor or tenant labels cannot create an edge.

### N-C4 — Declaration ablation

D, E, and F retain identical observed lineage and verdict under HONEST, OMITTED, and
FORGED declarations.

### N-C5 — Missing observation policy pair

Run both D and legitimate F without a valid observer receipt under both policies:

| Fixture | FAIL_OPEN | FAIL_CLOSED |
|---|---|---|
| D attack | ALLOW; security failure; one issuer call | BLOCK; zero issuer calls |
| F legitimate | ALLOW; one legitimate issuer call | BLOCK; availability cost; zero calls |

Neither row counts as core PASS. Both outcomes and costs must be printed together.

### N-C6 — Multi-hop lineage

Unverified mutation writes A1. A deterministic transform reads A1 and writes B1 with
`parent_version_ids=[A1]`. Recovery reads B1.

- direct-only evaluator: may report no direct mutation, printed as insufficient;
- required transitive evaluator: BLOCK `P1_UNVERIFIED_ROUTE_PROVENANCE`.

Load-bearing mutation: keep the observer ledger and B1 parent edge unchanged, but remove
transitive traversal from a temporary copy of the gate. The mutant must ALLOW or otherwise
miss `P1_UNVERIFIED_ROUTE_PROVENANCE` while the clean gate BLOCKs. Do not “prove” lineage
by deleting the evidence from the fixture.

### N-C7 — Version race

PREPARE reads V1. Before AUTHORIZE, another write commits V2 as the current head.
Expected BLOCK `P2_VERSION_CHANGED_AFTER_READ`; issuer calls zero.

### N-C8 — Duplicate/conflicting version

Two different records claim one `state_version_id`, or one object/sequence has
conflicting heads. Expected BLOCK `P3_LINEAGE_INVALID`.

### N-C9 — Observer custody

If the governed actor is configured as a writer of the observation channel, classify
`INVALID_OBSERVER_CUSTODY` before scoring. Do not call it a gate block or pass.

### N-C10 — Blanket baselines

- always allow fails D and E;
- always deny fails F and C1;
- tenant history fails D;
- principal closure fails E and F.

The new gate must outperform these on the frozen conjunctive bar, not merely print a
different rule name.

### N-C11 — Value substitution / no fixture-string policy

Repeat one unverified write with an ordinary safe-looking destination string not equal to
`ATTACKER`; expected BLOCK. Repeat a verified write with a different destination value
established through the same public `record_verification(...)` semantics; expected ALLOW.

The gate and provenance derivation may not branch on `attacker@evil.test`,
`new-admin@example.test`, email domain, trace id, fixture id, or expected result. Only
equality against the pre-write `verified_destination` state may derive provenance.

## 12. Required receipts

Every decision receipt deterministically binds:

- trace and declaration variant, recorded only after the gate result is computed;
- observed object/version and complete lineage version ids;
- read receipt digest and state-version record digests;
- derived authorization provenance and exact pre-existing verification evidence;
- current-head recheck;
- declaration/observation divergence;
- decision, rule, and issuer call count;
- previous receipt head, sequence number, and canonical receipt digest.

Raw route values may remain inside the deterministic local fixture. Any future outside
adapter must retain a rerunnable raw observation export or return INCONCLUSIVE.

## 13. Result classes

- `CONFIRMED_BOUNDED_POLICY`: D BLOCK + E BLOCK + F ALLOW, every control passes, all
  declarations preserve verdicts, exact lineage and issuer counts match.
- `POLICY_FAILED_D`: D allowed.
- `POLICY_FAILED_E`: E allowed.
- `LEGITIMATE_WORKFLOW_OVERBLOCKED`: F blocked.
- `INCONCLUSIVE_OBSERVATION`: required honest observer evidence unavailable.
- `INVALID`: fixture semantics changed, new provenance input invented, observation
  self-reported, read learned after issue, or expected labels leaked into the gate.

Only `CONFIRMED_BOUNDED_POLICY` is a positive result. “Bounded” is mandatory: this is an
in-process deterministic model over D/E/F, not production IAM.

## 14. Implementation scope after breaker PASS

Only these artifacts may be added:

```text
run_n.py
run_n_mutation_check.py
RUN_N_RESULT_2026-08-04.md
```

Requirements:

- Python stdlib only;
- offline, deterministic, no model, credentials, network, subprocess, or external write;
- counting issuer stub;
- source mutations performed only in temporary copies by the mutation check;
- `python3 run_k.py`, `python3 run_j.py`, and `python3 ci_check.py` remain green;
- result file is written only after execution and independent code attack.

The implementation may reuse public Run K constants and trace semantics. It may not edit
`run_k.py` or change Run K's historical result.

## 15. Required breaker work before implementation

The independent breaker must attack at least:

1. whether F's provenance can be fabricated from any new input;
2. whether a write record smuggles in a future reader;
3. whether PREPARE has any credential-issuing side effect;
4. whether a declaration can contaminate observed lineage;
5. whether object/version ids leak trace or expected outcome;
6. whether C2 truly follows the consumed version instead of object-wide guilt;
7. whether missing observation is measured rather than silently selected;
8. whether transitive lineage can be deleted and become ALLOW;
9. whether the head recheck closes the PREPARE/ISSUE race;
10. whether observer compromise is mislabeled as a policy result;
11. whether the D/E/F conjunctive bar can be satisfied by always allow/deny or the old
    tenant/closure gates; and
12. whether hardcoded fixture values or expected labels can satisfy D/E/F; and
13. whether this is substantively beyond public Run K and closed-negative Run M.

Return PASS only if no load-bearing design seam remains. Do not implement from the
breaker seat.

## 16. Publication, Ali, and article boundary

Run N and the Ali D/E package remain separate deliverables:

- the D/E JSONL extraction lowers adoption friction and is packaging;
- Run N tests a new bounded provenance policy;
- an Ali package replay is not a Run N external result;
- an outside substrate result requires independently controlled runtime observation.

No reply to Ali claims the package exists until it is tested, published from a narrow
branch off public head, and every URL resolves externally.

The next DEV article unlocks only after:

- `CONFIRMED_BOUNDED_POLICY` survives an independent code breaker; or
- Ali produces a valid outside-substrate reproduction; or
- FIPSign's live Mandate fixture produces its separately frozen result.

A negative or inconclusive Run N result is recorded but does not automatically become an
article.

## 17. Claim boundary

Run N can establish only that exact state-version provenance distinguishes D/E from F in
this frozen model while resisting the named controls. It cannot establish:

- a general solution to agent authorization;
- trustworthy runtime observation in every framework;
- observer/root custody;
- correct provenance semantics outside the pre-existing Run K verification record;
- production race safety, distributed durability, or cryptographic identity;
- external adoption; or
- that AI agents are secure because this bounded policy passes.
