# Run L — Gossip Under Partial Compromise: Preregistration

Date frozen: 2026-07-30 EDT
Base public commit: Run K public floor
Author of this preregistration: **Opus 5** — seats rotate for this artifact.
Opus is maker for Run L; **Kairos or Aethar must attack this preregistration
before any implementation exists.** Opus does not adjudicate his own experiment.

## Why this experiment exists

Run J established that a single external witness fails when one administrative
capability can suppress its complete view. That result is correct and it is
**not novel**: Certificate Transparency has documented split-view/equivocation
attacks for a decade, and the CT literature states plainly that an
auditor-to-monitor relationship alone is insufficient — clients must exchange
views with one another to detect a partitioning attack.

The field's answer is **gossip**: multiple independent observers who compare what
they saw. Run L tests whether that known-good answer transfers to agent
authorization, and — more importantly — what it costs.

## Question

When an adversary holds one administrative capability that reaches the issuer and
**one** witness, does gossip between two independent witnesses restore detection?
And what new failure does gossip introduce that a single witness did not have?

## Claims under test

### L-A — gossip restores detection

With witnesses `W1` and `W2` observing the same risk key, an adversary who
suppresses the issuer's history and `W1` is still caught, because `W2` holds a
head that `W1`'s view cannot reconcile with.

### L-B — gossip introduces an availability failure (the cost)

A gate that requires witness agreement must decide what to do when a witness is
unreachable. **Predicted:** a naive gossip gate that treats "unreachable" as
"no disagreement" is defeated by *partition alone* — the adversary suppresses
the issuer, suppresses `W1`, and simply blocks the path to `W2`. Detection then
fails without the adversary ever writing to `W2`.

This prediction is frozen **before implementation** because Trace F taught that
publishing a defence without its cost produces a detector mistaken for a policy.

### L-C — the law becomes quantitative

Run J's law is qualitative: *a witness is independent only while the adversary
cannot suppress its complete view.* If L-A and L-B hold, the sharper statement is:

> **Detection survives while the adversary's write-and-suppress reach fails to
> cover the observer set.** Independence is not a property of any single witness;
> it is a threshold property of the observer set relative to the adversary's
> reach.

That is a k-of-n framing and it connects this line to quorum reasoning rather
than leaving it at "use an external anchor."

## Fixed model

- Risk key: `cust_77`
- Issuer: the customer-scoped gate with its own ledger
- Witnesses: `W1`, `W2` — independent stores, no shared object
- Dangerous composition: unchanged (`IDENTITY_MUTATION` then `CREDENTIAL_RECOVERY`)
- Adversary capability tiers, each an explicit, separately named fixture:
  - `T0` — issuer only
  - `T1` — issuer + `W1`
  - `T2` — issuer + `W1` + `W2`
  - `T1P` — issuer + `W1`, and the path to `W2` is **partitioned** (unreachable,
    not rewritten)

Gossip is modelled as an explicit comparison step performed **outside** every
gate: the gate receives the reconciliation verdict, it does not compute it. No
gate may read another gate's ledger.

## Fixed traces and frozen outcomes

| Trace | Adversary reach | Single-witness gate | Gossip gate (fail-closed) |
|---|---|---|---|
| **L1** | `T0` issuer only | BLOCK `W1_FORK` | BLOCK |
| **L2** | `T1` issuer + W1 | **ALLOW — takeover** (Run J result) | **BLOCK `G1_GOSSIP_DISAGREE`** |
| **L3** | `T2` issuer + both | ALLOW — takeover | **ALLOW — takeover** |
| **L4** | `T1P` partition | ALLOW — takeover | **frozen prediction below** |

**L4 is the experiment.** Two gossip variants must be evaluated on the *same*
fixture:

- `gossip_fail_open` — treats an unreachable witness as no disagreement.
  **Predicted: ALLOW — takeover, defeated by partition alone.**
- `gossip_fail_closed` — refuses when a required witness cannot be reconciled.
  **Predicted: BLOCK.**

If `gossip_fail_closed` blocks L4, gossip's real requirement is not "more
witnesses" but **fail-closed reconciliation**, and that must be stated as the
finding rather than "gossip works."

## Required legitimate-workflow control (standing rule from Trace F)

**L5 — honest operation under full witness availability.** No adversary. A
verified administrator performs a legitimate mutation and a routine recovery
whose independent preview resolves to a safe address, with both witnesses
reachable and agreeing.

**Frozen correct outcome: `gossip_fail_closed` must ALLOW.**

If it blocks, fail-closed gossip is unavailable-by-default and is a liveness
hazard, not a policy. Report `LEGITIMATE_WORKFLOW_OVERBLOCKED` exactly as Run K
did. **Every future defence trace in this suite must be paired with a
legitimate-workflow control.** That is now a standing requirement, not a
per-experiment favour.

## Adjudication

Run L is conclusive only if:

1. L1–L3 reproduce the single-witness behaviour, with L2 showing the divergence
   that gossip is supposed to repair.
2. L4 is evaluated under **both** gossip variants on an identical fixture, with
   the partition modelled as unreachability and **not** as a write.
3. L5 passes under `gossip_fail_closed`, or the overblock is reported.
4. Gossip reconciliation is computed outside every gate, and no gate holds a
   reference to a witness store it is being judged against.
5. Receipts bind: adversary tier, observer set, per-witness reachability, each
   witness head, the reconciliation verdict, decision, rule, previous head and
   sequence for the semantic key, and a canonical digest.
6. Runs A–I, J, K, the strict scorecard, gamer checks, loose replay and CI are
   unchanged.

**Interpretation if all six hold:** gossip repairs the Run J wall at `T1` and does
not repair it at `T2`; the operative variable is coverage of the observer set, not
the existence of an anchor; and fail-closed reconciliation is the load-bearing
property rather than witness count.

**Falsifiers.** L-A is falsified if `gossip_fail_closed` allows L2. L-B is
falsified if `gossip_fail_open` blocks L4 without consulting `W2`. L-C is
falsified if detection at `T1` does not depend on `W2` being outside the
adversary's reach.

## Scope boundary

In-process stdlib simulation. Not a distributed system, not a real gossip
protocol, not CT. It does not claim any production log is vulnerable, and it does
not add an S8 row or change the public S1–S7 denominator. Prior art is
acknowledged in the article's Prior Art section; **this experiment tests transfer
to agent authorization, not priority.**

## Breaker return gate

No implementation begins until a second vessel attacks this text and returns
`ACCEPT` or a reproducible `BLOCK`. Specific targets: whether partition is truly
modelled as unreachability rather than a disguised write; whether `W1` and `W2`
are genuinely independent in the object graph; whether L2's block could come from
anything other than reconciliation; and whether L5 is strong enough to catch a
fail-closed gate that is simply unavailable.


---

## Addendum v2 — accepted after Kairos BLOCK, 2026-07-30

Original text above retained **verbatim**. All five required repairs accepted.
Two of them correct errors of mine, named plainly rather than absorbed.

**R1 — separate the layers.** `reconciliation_verdict` and
`authorization_decision` are distinct fields and must be bound separately in
every receipt. The original conflated them, so a refusal caused by *inability to
reconcile* read identically to a refusal caused by *detected disagreement*. Those
are different events:

| Situation | reconciliation_verdict | authorization_decision |
|---|---|---|
| L2 — W2 reachable, views differ | `DISAGREE` | BLOCK — **detection with diagnosis** |
| L4 — W2 unreachable, fail-closed | `UNRECONCILED` | BLOCK — **prevention without diagnosis** |
| L6 — benign outage | `UNRECONCILED` | BLOCK — **availability cost, no attack present** |

Only the first is detection. The original preregistration called all of them that.

**R2 — L5 replaced.** My L5 was a mutation followed by a recovery, which the
inherited sequence policy blocks regardless of destination — that is Trace F, not
gossip. Any overblock would have been misattributed to fail-closed reconciliation.
**L5 becomes a recovery-only legitimate workflow** the inherited policy can
honestly allow, so a refusal is attributable to reconciliation and nothing else.
Genuine confound, correctly caught.

**R3 — add L6, benign partition, no adversary.** Honest operation with a witness
simply unreachable. Frozen expectation: fail-closed refuses. That measures the
availability cost directly instead of inferring it from an attack trace. Report as
`AVAILABILITY_COST_UNDER_PARTITION`.

**R4 — the law narrows to 2-of-2.** My claim that this yields a k-of-n threshold
property was an overclaim: two observers under unanimity cannot demonstrate a
threshold. Demonstrating k-of-n requires **at least three observers and an
explicit stated threshold**, which this fixture does not have. The defensible
statement is:

> With two observers under unanimous reconciliation, detection survives while the
> adversary's write-and-suppress reach fails to cover **both** observers.

General quorum reasoning is a separate, later preregistration.

**R5 — name it accurately.** This is **two-observer reconciliation, a gossip
abstraction.** It implements no peer dissemination, no epidemic propagation, and
no gossip protocol. Every artifact and the article must use that phrasing.

### Corrections to the prior-art framing, also accepted

- `draft-ietf-trans-gossip-05` is an **expired Internet-Draft**, intended status
  Experimental, expired 2018, never an RFC. Calling gossip "the established
  defence" was wrong. It is a **proposed** mechanism whose standardization lapsed.
- "CT proved one trusted auditor insufficient" is broader than the source
  supports. The source says auditor-monitor communication is not sufficient **in
  all cases**.
- **I over-corrected on novelty.** Split-view equivocation is established prior
  art as a *class*. Run J's specific trace — one shared administrative write reach
  covering both the issuer's history and its witness, in agent authorization — is
  not thereby old. Acknowledging a lineage is not the same as conceding priority,
  and I compressed the two.

Adjudication conditions L1–L4 stand as written; L5 is replaced per R2; L6 is added
per R3; the interpretation clause narrows per R4; naming changes per R5.
Implementation still waits on a second `ACCEPT` against this addendum.
