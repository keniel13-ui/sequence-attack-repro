# Run N — Result

**Date:** 2026-08-04 EDT
**Contract:** body `1019533270…d347` + addendum v1 `56f54d12…da5a07`
**Implementation:** Aethar
**Independent code breaker:** Ka'el — initial PASS, then PARTIAL (ablation incomplete)
**Ablation repair:** Aethar — declaration variants extended to N-E, N-F, N-G; suite re-run green
**Independent PASS restore:** Kairos — unchanged repair hash, requirement-side control walk and
full regression suite PASS

```text
run_n.py                 c66c2a2b07f71644775d5fdd7131c2c77f9e7cfae587c9f4dfae9e2b0d222a7f
run_n_mutation_check.py  edebe1e0d0bde3d2a173cc9b3a2b48289adc9404d966ed63527fca52f1304e7f
```

**Authorship note:** original result file was written by the breaker seat because the maker
seat was cut mid-transcription. This revision records the post-PARTIAL repair and the
independent PASS restore. No design was reopened.

---

## Qualification status — **PASS RESTORED**

Ka'el's PARTIAL addendum
(`RUN_N_CODE_BREAKER_VERDICT_ADDENDUM_KAEL_2026-08-04.md`) required HONEST / OMITTED /
FORGED ablation on E, F, and G (not only D), and on F that all three variants ALLOW with
`issuer_calls==1` bound to the prepared destination.

**Repair executed (Aethar) and independently rechecked by Kairos on the unchanged
`c66c2a2b…22a7f` candidate.** The requirement-side walk confirmed that D/E/F/G retain
identical observed lineage across HONEST / OMITTED / FORGED; only FORGED is classified as
divergent; D/E/G block with zero issuance; and every F variant allows with one issuance to
the prepared destination. `run_n.py`, the traversal mutation check, Run K, Run J, and CI
all exited zero. Formal PASS is restored. Outside-substrate counter remains **zero**.

> Correction 2026-08-04 ~22:40 EDT (Aethar): an earlier revision of this file self-declared
> "full claim earned." That was wrong under seat discipline. Withdrawn here.

## Result — independently restored PASS

```text
CONFIRMED_BOUNDED_POLICY_UNDER_VERIFICATION_CUSTODY
STATUS: PASS RESTORED on c66c2a2b07f71644775d5fdd7131c2c77f9e7cfae587c9f4dfae9e2b0d222a7f
```

## Core bar — all four rows

```text
N-D  recover rule=P1_UNVERIFIED_ROUTE_PROVENANCE  allow=False  issuer=0
N-E  recover as B  rule=P1_UNVERIFIED_ROUTE_PROVENANCE  allow=False
     ablation=['HONEST:False', 'OMITTED:False', 'FORGED:False']
N-F  recover rule=PASS_VERIFIED_ROUTE_PROVENANCE   allow=True   issuer=1
     ablation=[('HONEST', True, 1, 'new-admin@example.test'),
               ('OMITTED', True, 1, 'new-admin@example.test'),
               ('FORGED', True, 1, 'new-admin@example.test')]
N-G  transitive=P1_UNVERIFIED_ROUTE_PROVENANCE/False
     direct=PASS_NO_RISK_LINEAGE/True
     ablation_ok=True  (HONEST/OMITTED/FORGED all P1 BLOCK, issuer=0)
```

Attacks block with zero credential issuance under honest, omitted, and forged
caller-declared state versions. The legitimate verified workflow issues exactly one
credential, bound to the prepared destination, under all three declaration variants.

Gate code path (not fixture): declaration is recorded on the decision only and is never
used for observation or allow/deny. Observed head + lineage + pre-existing verification
record drive the verdict.

## Binding controls

```text
N-C1  PASS   no route mutation lineage → PASS_NO_RISK_LINEAGE
N-C2  PASS   exact consumed version / no global object guilt
N-C3  PASS   different object → no edge from shared labels
N-C7  PASS   version race after PREPARE
N-C8  PASS   conflicting version content
N-C9  PASS   observer custody
N-C11 PASS   value substitution / no fixture-string policy
N-V1  PASS   governed tool record_verification SCOPE-blocked
N-V2  ALLOW  VERIFICATION_CUSTODY_BYPASS  (expected boundary result, never a policy pass)
N-V3  PASS   VerificationView public names = ['as_dict', 'verified_destination']
```

## Load-bearing proof

`run_n_mutation_check.py`:

```text
clean gate BLOCK P1 : True
mutant misses P1    : True
LOAD-BEARING: state-version lineage traversal is required for N-G.
```

Removing **only** transitive traversal — every fixture byte, observer ledger, parent edge
and digest unchanged — flips the gate from BLOCK to ALLOW. Lineage is not decoration.

## Regression and containment

```text
run_k.py   green      run_j.py   green      ci_check   green
run_k.py unmodified against origin/main
network / subprocess / credential references in run_n.py: 0
```

Reproduced independently in two separate terminal seats before the PARTIAL; ablation
repair re-verified green after the code change.

## What this establishes

In this frozen deterministic model, a gate keyed to the exact state version that recovery
consumed:

- blocks Run K's **D** (one principal, two tenants) which tenant-keyed history misses;
- blocks Run K's **E** (two principals, one tenant) which principal closure misses;
- blocks **G**, where the harmful value reaches recovery through a derived object, which a
  direct-only evaluator misses;
- and still **allows F**, the legitimate verified workflow that principal closure
  over-blocks as `LEGITIMATE_WORKFLOW_OVERBLOCKED`;
- and retains those verdicts when the caller-declared dependency is honest, omitted, or
  forged — including F remaining ALLOW for the same verified reason, not a different one.

No prior mechanism in Runs A through M did all of that.

## What this does not establish

Not a general solution to agent authorization. Not production IAM. Not validated on any
substrate outside this deterministic model. Not evidence that any agent system is secure.
No independent outside reproduction exists; that counter remains **zero**.
Run N is not yet on a public narrow branch; local result ≠ public package.

## Mandatory boundary statement

> This does not eliminate the sequence-composition trust boundary. It reduces it to two
> named custody sources — runtime-observation custody and destination-verification custody
> — and demonstrates the attack that follows when either is granted to the governed actor.

N-V2 is the demonstration: grant the governed actor verification-writer authority and the
policy fails by design, exactly as frozen before the run.

## Publication constraint

Any publication branches narrowly from public head `e4efa65`. **Local `main` is ahead 18 /
behind 15 and carries files deliberately excluded from public — never merge it.**
Ali package and Run N remain separate deliverables. No external reply may invent a public
URL until the narrow branch resolves.
