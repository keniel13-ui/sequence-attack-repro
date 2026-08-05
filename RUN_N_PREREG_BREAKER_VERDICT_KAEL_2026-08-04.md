# Run N Preregistration — Independent Breaker Verdict

**Breaker:** Ka'el (live terminal seat)
**Maker:** Kairos
**Candidate SHA-256:** `1019533270d82324f862c1ad052a831237f4be611e29d9f2ee3562e8c0bad347`
**Date:** 2026-08-04 EDT

Candidate not edited. No implementation, branch, push, reply, or article.

## Verdict: **BLOCK — two findings.** Neither kills the experiment; both change what it
can claim.

This is a materially better document than anything in the D/E line. The PREPARE-before-ISSUE
seam, the conjunctive bar frozen before code, the value-substitution control, and the
blanket-baseline comparison are all real and should survive. The two findings are about
what the result would *mean*, not about sloppiness.

---

## N1 (BLOCK) — the headline mechanism is not what produces the headline result

§13 names the positive outcome `CONFIRMED_BOUNDED_POLICY`, and the document is titled
**state-version provenance**. But I checked whether version lineage does any work in the
three traces that constitute the bar:

```text
grep for parent_version_ids | transitive | multi-hop | lineage
  within §10's N-D, N-E, N-F trace definitions   →  0 matches
```

N-D, N-E, and N-F are each **single-hop**: one allowed mutation, one recovery reading it.
`parent_version_ids` is empty throughout. No transitive traversal, no multi-version
history, no lineage join beyond "the one version that was written."

So the entire apparatus — opaque object ids, version ids, parent edges, the append-only
observer chain, transitive traversal — is **unexercised by the core result.** D BLOCK, E
BLOCK, F ALLOW are produced by exactly one thing: §4's boolean.

```text
VERIFIED_DESTINATION iff verified_destination[writer] == destination_written
```

A mechanism with **no state versions at all** — "block recovery if the destination in
force was written without prior verification" — passes D, E, and F identically.

The lineage machinery is tested only by controls C2, C6, C7, and C8. That is where the
version-specific novelty actually lives, and those controls are not part of the bar.

**Repair — pick one:**

1. **Promote lineage into the core bar.** Make N-D or N-E multi-hop so the harmful value
   reaches recovery through a derived version, and the direct-only evaluator must miss it
   while the transitive one blocks. Then version lineage is load-bearing in the result.
2. **Or narrow the claim.** Retitle to destination-verification provenance, move the
   version machinery to "additional controls," and state plainly that D/E/F are decided by
   the provenance boolean.

Option 1 makes the stronger paper. Option 2 is honest and costs a rename. What is not
acceptable is a result headlined "state-version provenance" that would be identical
without the state versions.

## N2 (BLOCK) — §5 excludes the attack that defeats the policy

§5 places out of scope:

> *adversary rewrite of the pre-existing destination-verification record*

I checked what protects that record in public Run K:

```python
def record_verification(self, principal: str, destination: str) -> None:
    self.verified_destination[principal] = destination
```

**An unguarded dict write. No access control, no authority check, no caller binding.**

Under §4's derivation, an attacker in D or E who calls
`record_verification(own_principal, "attacker@evil.test")` before the mutation obtains
`VERIFIED_DESTINATION` — and §8 rule 2 returns **ALLOW**. The policy collapses completely.

That attack is excluded by §5 rather than defended against. **Out-of-scoping the single
attack that defeats a mechanism is not a threat model; it is an assumption.**

This is not the generic trusted-computing-base argument. If gate code is compromised every
gate fails — uninteresting, and correctly out of scope. But the verification record is
different: **it is this mechanism's unique single point of failure.** Tenant history and
principal closure both still function if `verified_destination` is writable. Run N does
not. Excluding the one thing that is uniquely fatal to the candidate is the load-bearing
problem.

**Repair — pick one:**

1. **Freeze a control** demonstrating the governed actor cannot write the verification
   record — a separate authority for `record_verification`, with a control where the actor
   attempts it and the run classifies `INVALID_VERIFICATION_CUSTODY`.
2. **Or state the reduction honestly** in §17 and in the eventual article: *this policy
   does not eliminate the sequence-composition failure; it reduces it to write-authority
   over destination-verification records.* That is a legitimate result — it is the same
   shape as every prior finding in this line, and saying so plainly is stronger than
   implying the wall was removed.

I lean to option 2 with a control from option 1 attached. "We moved the trust boundary
from sequence-tracking to verification-record custody, and here is the exact attack that
proves it" is a real contribution and it is consistent with everything Runs J through M
established.

## What survives and should not be touched

The two-stage **PREPARE before ISSUE** seam is the best idea in the document — it makes
"the gate used the runtime read" checkable rather than asserted, and the requirement that
learning the read set after issuance is INVALID closes a gap I have not seen named
elsewhere in this line.

Also keep: the conjunctive bar frozen before code with four stated ways to lose; C10's
blanket baselines (always-allow fails D/E, always-deny fails F/C1, tenant fails D, closure
fails E and F); C11's value-substitution control barring branches on `attacker@evil.test`
or domain strings; C5's fail-open/fail-closed matrix now covering **both** D and F; and
C9's `INVALID_OBSERVER_CUSTODY` classification.

The decision not to write a separate handoff file was right. §15 is the matrix.

## Answers to §15

Q1 — **can F's provenance be fabricated?** Yes, and that is N2. `record_verification` is
unguarded.
Q3 — PREPARE side effects: correctly frozen to zero.
Q6 — C2 does follow the consumed version rather than object-wide guilt. Good.
Q7 — missing observation is measured, not selected. Correctly repaired from Run M.
Q11 — the blanket baselines are properly excluded by the conjunctive bar.
Q13 — **substantively beyond Run K and Run M: yes, conditionally.** The PREPARE/ISSUE seam
and the D+E+F conjunctive bar are genuinely new. But under N1 the result would be
attributable to destination provenance, not versions; and under N2 it reduces to custody
rather than closing it.

## Conditions for re-review

1. Resolve N1 — promote lineage into the bar, or narrow the title and claim.
2. Resolve N2 — add a verification-custody control, or state the reduction explicitly in
   §17 and bind the article to that framing.

Nothing else. With both closed, this is the first mechanism in this line with a defined
way to win and four defined ways to lose.
