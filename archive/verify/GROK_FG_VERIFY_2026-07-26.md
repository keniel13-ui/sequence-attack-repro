> **STALE HASHES.** Written before receipts became a previous-head chain (commit 311cd58). Every hash below predates that change. The verdicts stand; the digests do not.

# Grok independent verify — Run F / Run G

**When:** 2026-07-26 ~16:48 EDT  
**Who:** Grok / Aethar (builder lane — cold check after Ka'el built F/G)  
**Repo:** `claim30_repro` → public `keniel13-ui/sequence-attack-repro`  
**Command:** `python3 repro.py` (stdlib only; no network; no model)

## Verdict

| Claim | Result |
|---|---|
| Run F — same dangerous pair split across two `PurposeGate` sessions → takeover | **CONFIRMED** |
| Run G — same split with shared `ResourceLedger` / `ResourceGate` → R4 blocks recovery | **CONFIRMED** |
| Run D receipt hash still stable (`chain_sha256` over content fields) | **CONFIRMED** `726f65973fb027640049120971a43ca68300197d56ab2d74d5ca94a977d907a7` |
| Run G block receipt hash (resource-scoped) | **CONFIRMED** `d7e554a36c23cee3d46a1ca3ee0a0cd50abf9ea9eb2c9f778a10d20028a1f643` |
| P1 / P2 / honesty / Run E | all still hold on this run |

## What was checked (not trusted from report)

1. Read `gates.py` — `ResourceLedger` keys history by resource id; `ResourceGate.check` uses `ledger.history(resource)` for R4, not only `self.performed`.
2. Read `repro.py` — F uses two fresh `PurposeGate` instances; G shares one ledger across two `ResourceGate` instances.
3. Cold-ran the full suite once; re-ran G receipt hash recompute over content fields excluding `decided_at`. Stored hash matched recomputed hash.

## Observed F

```
session A  ALLOW  update_contact_email
session B  ALLOW  send_password_reset
→ ACCOUNT TAKEOVER SUCCEEDED — session-scoped R4 is blind to the split
```

## Observed G

```
session A  ALLOW  update_contact_email
session B  BLOCK  send_password_reset  [R4_SEQUENCE]
→ prior_action_classes: ["IDENTITY_MUTATION"]
→ sequence_scope: resource, resource: cust_77
```

## Limits still true (not closed by F/G)

- Still a simulation, not wired into a production agent path.
- R4 is still one hardcoded composition pair (now scoped to the resource when using `ResourceGate`).
- Ledger is in-process memory; not durable storage, multi-host, or multi-agent principals proven yet.
- Fail-closed on "empty history = unobserved" is **not** implemented (named leap, not done).
- P3 (human "run that again") remains **PENDING**.

## Decision

Independent cold verify: **PASS**. Safe to commit and push F/G + docs so ANP2 and others can `python3 repro.py` and see F and G themselves.

No claim that this is production security. Claim is: the session-scoped hole is shown, and the record-scoped fix is shown, both runnable.
