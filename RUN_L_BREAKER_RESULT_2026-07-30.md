# Run L — Breaker Result (Aethar)

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
