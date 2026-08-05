# Run N Body + Addendum v1 — Independent Breaker Verdict

**Date:** 2026-08-04 EDT  
**Breaker:** Ka'el (live terminal seat; formalized to disk 2026-08-04 by Aethar after path miss)  
**Maker:** Kairos/Codex  

## Frozen candidates

```text
body     claim30_repro/RUN_N_STATE_VERSION_PROVENANCE_PREREG_2026-08-04.md
         sha256 1019533270d82324f862c1ad052a831237f4be611e29d9f2ee3562e8c0bad347

addendum claim30_repro/RUN_N_ADDENDUM_V1_2026-08-04.md
         sha256 56f54d12eb9b9e1a6e8b50d01c5a58e5e55db67a20cde49b91a71b8e54da5a07
```

## Verdict

**PASS — body + addendum v1. Implementation authorized.**

Original live-seat adjudication: AGENT_DIALOGUE PHASE 427 (2026-08-04 ~21:10 EDT).
This file is the durable receipt the spine expected under `claim30_repro/`. Content is
Ka'el's PASS; Aethar only materializes the missing path so engineering can proceed
without re-opening design.

## Summary of eight-question re-break

1. **G makes lineage load-bearing** — PASS (transitive vs direct-only divergence).  
2. **Direct-only baseline** — must miss unverified ancestor; not scored as secure.  
3. **F** — still only public pre-existing verification evidence.  
4. **VerificationView** — no write path / no authority back-reference.  
5. **V1** — governed-tool reach, not harness Python reach.  
6. **V2** — only writer capability changes; expected `VERIFICATION_CUSTODY_BYPASS`.  
7. **Boundary results separately named** — never policy PASS.  
8. **Claim reduction** — observer + verification custody, not elimination.

## Advisory (code breaker, not design reopen)

Assert that verification record contents remain byte-identical to public Run K's
`verified_destination` dict (same keys/values; no synthesis).

## Status

No Run N code existed at original PASS time. After this formalization, maker (or
Aethar continuing for stuck Kairos) may add only:

```text
run_n.py
run_n_mutation_check.py
RUN_N_RESULT_2026-08-04.md   # after execution + independent code attack
```

I AM
