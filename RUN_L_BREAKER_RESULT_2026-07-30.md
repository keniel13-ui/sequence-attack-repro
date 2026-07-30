# Run L — Breaker Result (Aethar)

> **Hash note (added 2026-07-30).** This record was written against **local**
> commits. Run L was published by cherry-pick, which rewrote every hash, so the
> identifiers below do not resolve in the public repository. The narrative is left
> verbatim rather than rewritten, because the local hashes are what was actually
> attacked. Use this map to resolve anything publicly:
>
> ```
> local     public     commit
> 4ce4de5   fec3d89    Preregister Run L
> 396df42   5a69bd0    addendum v2
> 3f664f3   23c1b7e    addendum v3
> edc9106   90638b8    Run L implementation (the broken candidate)
> 2df9d7b   bfd10b6    Run L repair (registry membership + MAC receipt)
> dbf047c   2a519af    portable mutation check
> ```
>
> Citing an identifier a reader cannot resolve is the same failure as citing a
> digest nobody can recompute.

Date: 2026-07-30 ~11:05–11:15 EDT  
Breaker seat: **Aethar / Grok** (Kairos filtered; seat rotation live)  
Candidate under first attack: `edc9106`  
`run_l.py` at attack: sha256 `227329cdb5f2eff0f7f087bbdc534736eaa81907b1315cd69ee9ae2132eabbf2`

## Method

Did not inherit Opus or Kairos verdicts. Cold-ran `python3 run_l.py` (self-test exit 0), then attacked outside the harness with direct imports. Same three blockers Opus named in PHASE 90 — re-executed, not reported.

## First attack — `edc9106` — **BLOCK**

| ID | Attack | Result |
|---|---|---|
| **B1** | L1 headline "issuer suppressed only"; scenario suppresses nothing | OPEN — BLOCK on `R4_SEQUENCE` with recon `CONSISTENT`. Composition, not reconciliation. Real issuer-only suppress (claim `[]`, W1+W2 hold MUTATION) correctly yields `G1_GOSSIP_DISAGREE`. Fixture lied. |
| **B2** | Construct `ObserverManifest([W1])` only; W2 holds MUTATION; never consulted | OPEN — `ALLOW` / `PASS`. L7 catches omit when manifest still lists both; B2 is the weaker path: caller chooses a smaller *manifest*. Integrity≠completeness, exactly as pre-registration warned. |
| **B3** | Honest `DISAGREE` path; flip verdict → `CONSISTENT`; recompute public `receipt_digest` | OPEN — `ALLOW` / `PASS`. Self-digest is integrity of bytes, not authenticity of provenance (G2). |

**Self-test green while all three attack surfaces open.** Green harness is not a security result.

## Repair under filter (emergency maker)

Opus was cut mid-repair. Keniel ordered leadership / forward motion. Aethar implemented the repair that Opus named (registry-resolved membership + MAC'd receipt + L1 fixture truth).  

**Seat note:** Aethar was breaker on `edc9106` and temporary maker on the repair. **Formal PASS requires an independent breaker (Kairos or Opus) against the new file.** First-pass re-attack below is engineering confidence only, not seat-closed adjudication.

## Repair contents (local working tree; pre-commit at write time)

- `ObserverRegistry` — sole authority for `(risk_key, epoch)` membership  
- `reconcile(registry, risk_key, epoch, issuer_claim, evaluated_names=…)` — no free-form caller manifest  
- Receipt schema `run_l_reconciliation_receipt_v2` with `receipt_digest` + `receipt_mac` (HMAC-SHA256 under experiment-local reconciler key)  
- Gate rejects missing/wrong/stale MAC (`R_RECEIPT_UNAUTHENTIC`)  
- L1 uses `suppress_issuer_only=True`; expects `G1_GOSSIP_DISAGREE`

## First-pass re-attack (same seat — not formal)

| ID | Result |
|---|---|
| B1 | CLOSED — L1 → `G1_GOSSIP_DISAGREE` |
| B2 | CLOSED — omit W2 → `OBSERVER_SET_MISMATCH` / BLOCK |
| B3 | CLOSED — flip+rehash / no-mac / wrong-key / stale-mac → `R_RECEIPT_UNAUTHENTIC` or digest fail / BLOCK |

**Residual (honest, deploy-shaped):** if the adversary *owns the registry object* and registers a one-observer set, reconciliation over that world ALLOWs. Same class as Employee Stage 1 root-of-trust: **registry custody is the perimeter**, not the reconcile algorithm. Not closed by Run L; name it, do not paper it.

## Frozen-scope note on MAC

Addendum v3 stop condition deferred "cryptographic authentication" to a later prereg. B3 proved G2 was unfixed without *some* authenticity binding: a public self-digest is forgeable. The experiment-local HMAC is the minimum binding that makes "gate consumes a receipt, not a bare verdict" true under an adversarial pipe. Full KMS / public-key / key rotation remain separate preregs. Documented as **addendum v4** below the prereg if appended.

## Required next seat action

1. Independent cold breaker (Kairos or Opus) against repaired `run_l.py` hash.  
2. Mutation: delete MAC check → B3 must re-open; delete registry path restore free-form manifest → B2 must re-open.  
3. No public push of Run L until independent PASS + Keniel go.

## Bundle

Self-test after repair: all L1–L8 checks OK, exit 0, L6 availability cost published.  
Repaired file sha256 (at first-pass re-attack): `16928f05c5850c13b3447d02d750b04d93c4029331d16111e0b9ea9bee0f8e98`

---

## Addendum — Opus formal breaker, 2026-07-30 PHASE 92

**Seat:** Opus authored `edc9106` (broken); Aethar authored repair `2df9d7b`. Opus breaking the repair is clean.

**Verified match:** commit `2df9d7b`, sha256 `16928f05…`, cold archive, candidate untouched.

| Check | Result |
|---|---|
| L1 | BLOCK `verdict=DISAGREE` `rule=G1_GOSSIP_DISAGREE` (was composition) |
| B3 flip+rehash | BLOCK `R_RECEIPT_UNAUTHENTIC` — CLOSED |
| B2 caller only W1 | BLOCK `OBSERVER_SET_MISMATCH` — CLOSED |
| B2b invent W_FAKE | BLOCK `OBSERVER_SET_MISMATCH` — CLOSED |

**Mechanism note (Opus):** membership always loads from registry; caller list is only what they claim to have consulted — subset is mismatch, never a smaller valid quorum.

**Mutations:** Opus's two mutation tests were unclean isolations (second check still caught forgery when MAC disabled; partial registry shrink). **PASS on blockers; incomplete on mutations.** Kairos runs clean isolations when unfiltered. Do not claim which check carries the weight until then.

**API misuse (not a finding):** first attack TypeError — `evaluated_names` wants strings, not Observer objects.

**Formal status (superseded by mutation close below):** blockers **PASS**. Mutations were OPEN at PHASE 92.

---

## Addendum — mutations CLOSED, 2026-07-30

### Opus PHASE 93

Kairos had prepared three disposable archives (one variable per mutant) under `/private/tmp` and was cut after applying mutations, not before setup. Opus ran them. That is seat rotation + disk artifacts, not luck.

| Protection | Clean | Mutant (protection removed) | Verdict |
|---|---|---|---|
| Receipt authenticity (MAC) | BLOCK `R_RECEIPT_UNAUTHENTIC` | ALLOW | **LOAD-BEARING** |
| Authoritative membership (set check) | BLOCK `OBSERVER_SET_MISMATCH` | ALLOW | **LOAD-BEARING** |

Neither is redundant with the digest self-check. Isolation cleanliness: forge path keeps `_digest_ok == True` so only authenticity varies.

Opus self-catch: earlier dirty MAC attempt forged wrong field names (`body_digest`/`mac` vs `receipt_digest`/`receipt_mac`) — gate caught malformation, not the attack. Corrected before claim.

### Aethar PHASE 172 — independent re-run

Same commit `2df9d7b` / sha256 `16928f05…`. Disposable temps, one mutation each:

- MAC disabled only → forge with valid digest + stale mac → clean BLOCK UNAUTHENTIC; mutant ALLOW; `digest_ok True`
- Set-mismatch disabled only → evaluate W1 only → clean BLOCK SET_MISMATCH; mutant ALLOW

**Match Opus. Run L research gate CLOSED.** Residual: registry custody = perimeter (not closed by this experiment). No public push without Keniel.

---

## Addendum 2 — mutations CLOSED, 2026-07-30 PHASE 93

**Seat:** Kairos (PHASE 1087) built the three disposable archives and applied both
mutations, then was cut mid-run by an automated filter. Archives survived on disk.
Opus ran them. Neither vessel edited the candidate.

```
runl_clean.kTeSGi        16928f05…   both protections present
runl_mut_mac.FFN2t6      MAC check deleted, nothing else changed
runl_mut_membership.3zC0r1   `if False and evaluated_sorted != …`
```

Each protection must **fail open under its own attack when removed**, or it does
not get to be called load-bearing.

| Isolation | clean control | mutant | verdict |
|---|---|---|---|
| Receipt authenticity (MAC) | BLOCK `R_RECEIPT_UNAUTHENTIC` | **ALLOW `PASS`** | **load-bearing** |
| Authoritative membership | BLOCK `OBSERVER_SET_MISMATCH` | **ALLOW `PASS`** | **load-bearing** |

**Cleanliness proof for the MAC isolation.** The forged receipt recomputes
`receipt_digest` with the module's own `digest()` over the forged body, and carries
the **stale** `receipt_mac`. `Gate._digest_ok(forged) == True` is printed by the
harness. Integrity is intact by construction; authenticity is the only variable.
Without that line the isolation is not clean — see the correction below.

**Correction to Addendum 1.** My first MAC attempt forged fields named
`body_digest`/`mac`. The scheme uses `receipt_digest`/`receipt_mac`. The
`R_RECEIPT_INVALID` I reported was the digest check catching **my malformed
receipt**, not the attack. Same class as the earlier `TypeError`: reading the API
instead of guessing it is the fix. Not a finding against the candidate.

**Consequence for the claim.** `R_RECEIPT_UNAUTHENTIC` and `OBSERVER_SET_MISMATCH`
are each individually necessary — neither is redundant with the digest check, and
neither is decoration. The self-digest → HMAC change (B3) and the
registry-authoritative membership change (B2) both bought real coverage.

**Residual, unchanged and still disclosed:** registry custody is the root of
trust. Whoever writes the registry defines the quorum. Nothing here defends that.

**Formal status: Run L blockers PASS, mutations CLOSED, residual disclosed.**
No public push without Keniel.

### Portable reproduction

The disposable archives used for the independent close are preserved as a
single deterministic public check:

```text
python3 run_l_mutation_check.py
```

`run_l_mutation_check.py` verifies the candidate hash, creates two temporary
source mutants without editing `run_l.py`, runs the clean and mutated attacks,
and checks the cross-controls. This converts the mutation receipt from a
machine-local report into a clonable result.
