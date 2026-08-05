# Run N Code — Independent Breaker Verdict

**Breaker:** Ka'el (live terminal seat)
**Maker:** Aethar (implementation), Kairos (contract)
**Date:** 2026-08-04 EDT

```text
run_n.py                 79f70f37d877f198f9143c82ff3eb587711130385c0c8a4646680debbfd80d43
run_n_mutation_check.py  edebe1e0d0bde3d2a173cc9b3a2b48289adc9404d966ed63527fca52f1304e7f
```

Hashes match the maker's claim. Candidate not edited during this attack.

## Verdict: **PASS.**

`CONFIRMED_BOUNDED_POLICY_UNDER_VERIFICATION_CUSTODY` is earned.

**This is the first positive mechanism result in this research line.**

---

## What I attacked, and what I found

### C11 — does the gate cheat on fixture strings? (the attack that would void everything)

If the decision logic branched on `attacker@evil.test`, `new-admin@example.test`, a domain,
or a trace label, the whole result would be theatre.

I extracted `ProvenanceGate` (164 lines) and `derive_provenance` (16 lines) and searched
both for every forbidden token:

```text
ProvenanceGate      CLEAN
derive_provenance   CLEAN
```

`ATTACKER` and `LEGIT_ADMIN` appear **only** at their constant definitions (26, 29) and
inside `trace_n_*` / `control_*` fixture setup — first occurrence at line 620, well below
the gate. No trace id, no expected outcome, no domain string reaches the decision path.

The derivation is exactly what the contract froze:

```python
verified = view.verified_destination(writer)
if verified is not None and verified == destination:
    return "VERIFIED_DESTINATION", {...}
return "UNVERIFIED_DESTINATION", None
```

Equality against the pre-existing public record. Nothing else. **PASS.**

*Method note: my first search used a function-name regex, found nothing, and would have
reported a clean result from a bad query. A null result from a failed search is not
evidence. I re-ran against the actual file structure.*

### N1 — is state-version lineage load-bearing, or still the boolean?

This was my original BLOCK, and it is the claim most likely to be hollow. The mutation
check answers it directly:

```text
transitive  P1_UNVERIFIED_ROUTE_PROVENANCE / allow=False
direct-only PASS_NO_RISK_LINEAGE           / allow=True
clean BLOCK P1: True   ·   mutant misses P1: True
```

Remove **only** transitive traversal, keep every fixture byte, and the gate flips from
BLOCK to ALLOW. Lineage is doing real work, not decorating a boolean. **N1 closed.**

### N2 — is verification custody proven rather than assumed?

```text
N-V2  bypass ALLOW=True  tag=VERIFICATION_CUSTODY_BYPASS
N-V3  view public names=['as_dict','verified_destination']  write-free
```

Granting the attacker verification-writer authority **does** defeat the policy, exactly as
frozen — and it is tagged as a boundary result, never as a pass. The read view exposes no
write path. The custody wall is demonstrated instead of excluded. **N2 closed.**

### The core bar

```text
N-D  P1_UNVERIFIED_ROUTE_PROVENANCE  allow=False  issuer=0
N-E  P1_UNVERIFIED_ROUTE_PROVENANCE  allow=False
N-G  P1 via transitive A1 lineage    allow=False
N-F  PASS_VERIFIED_ROUTE_PROVENANCE  allow=True   issuer=1
```

Blocks emit **zero** issuer calls. The legitimate workflow issues exactly one, bound to the
prepared destination.

### Containment and regression

```text
run_k.py  green      run_j.py  green      ci_check  green
run_k.py unmodified vs origin/main
network / subprocess / credential references in run_n.py:  0
```

---

## What this result actually means

**Earned:** in this frozen deterministic model, a gate keyed to the exact state version
recovery consumed blocks Run K's D and E, follows transitive lineage through a derived
object, and still allows the legitimate verified workflow F that principal closure
over-blocks. No prior mechanism in this line did all four.

**Not earned:** this is not a general solution to agent authorization, not production IAM,
not validated outside this model, and not secure. The result is explicitly bounded by two
named custody assumptions — runtime-observation custody and destination-verification
custody — and N-V2 proves the second one is load-bearing by defeating the policy when it
is removed.

The honest sentence, which must appear in any publication:

> This does not eliminate the sequence-composition trust boundary. It reduces it to two
> named custody sources, and demonstrates the attack that follows when either is granted
> to the governed actor.

## Authorized next

`RUN_N_RESULT_2026-08-04.md` may be written from this execution. Publication goes through a
narrow branch from public head `e4efa65` — **never a merge of local main.**

The article gate stays where the spine put it: this is a positive *internal* result. It is
not an outside reproduction, and the independent-run counter remains **zero**.
