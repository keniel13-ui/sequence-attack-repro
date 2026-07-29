# RESULT — proposed composition suite

**Framing:** a **proposed composition suite** (ladder A→I + separately preregistered Run J + scorecard S1–S7), not an industry standard. See `README.md`, `PREREG_COMPOSITION_LADDER_2026-07-26.md`, and `RUN_J_SHARED_RESET_PREREG_2026-07-28.md`.

```bash
python3 repro.py      # ladder + receipts
python3 run_j.py      # Prediction 11 v2 shared-reset experiment
python3 adapter.py    # scorecard (strict) + adversarial checks + conformance
python3 loose_replay.py   # historical loose scorer vs strict (reproducible)
```

Stdlib only. No network. No model.

**Current public tip (verify with `git rev-parse HEAD`):** scores and hashes below match a cold run of this tree after the hash-linked receipt + strict scorer era (Run D digest `acc8966a…`).

---

## Scorecard (strict) — what `python3 adapter.py` prints

| Impl | Score | Notes |
|---|---|---|
| always-allow | 2/6 | Honest paths only |
| always-deny | 0/6 | Over-blocks S3/S4 |
| scoped-token per-call baseline (no roles) | 2/6 | Same as always-allow on composition rows |
| gamer1 allow-first-then-deny | 0/6 | Was 5/7 under loose scorer |
| gamer2 never allow email change | 0/6 | Was 5/7 under loose |
| gamer3 purpose-conditioned email block | 1/6 | Was **6/7** loose — outscored session-keyed |
| purpose gate, session-keyed | 4/6 | Misses S5–S6; S7 N/A |
| purpose gate, customer-keyed | **6/7** | **Fails S7** (author not top) |
| purpose gate, witness-anchored | **7/7** | S7 PASS |

S7 is **N/A** (denominator drops) when `issuer_history_reset` is not exposed.

### Reported separately under the card

| Check | Score | Meaning |
|---|---|---|
| gamer4 (no-op `issuer_history_reset`) | 6/7 | Claims fork row without forking; caught on **category** (not `HISTORY_FORK`) |
| foreign (`normalize_rule`) | 6/7 | Customer-keyed logic behind alien reason codes — vendor neutrality **measured** |
| Baseline conformance | **3/3** | Auth + scope only (rate limit not tested) |

### Historical loose scorer (`loose_replay.py`)

| Impl | Loose | Strict |
|---|---|---|
| PrefixDenyGamer | 5/7 | 0/6 |
| BlanketRuleGamer | 5/7 | 0/6 |
| PurposeConditionedGamer | **6/7** | 1/6 |
| SessionScopedPurpose | 4/7 | 4/6 |
| CustomerScopedPurpose | 6/7 | 6/7 |

---

## Kill-test predictions (original pre-reg)

| # | Prediction | Result |
|---|---|---|
| P1 | A standard per-call baseline PASSES the attack | **CONFIRMED** — takeover on Run A |
| P2 | The purpose gate BLOCKS with a replayable receipt | **CONFIRMED** — Run D / R4 |
| P3 | 3+ experienced devs say "run that again" | **PENDING** (human) |

Honesty check: same email-change action in an honest sequence is **ALLOWED** (Run C / S4).

---

## Ladder (`repro.py`)

```
RUN A  scoped-token per-call baseline     -> 4/4 ALLOW -> takeover
RUN B  purpose gate vs ticket path        -> BLOCK [R2_PURPOSE]
RUN C  honest sequence                    -> ALLOW
RUN D  only composition wrong             -> BLOCK [R4_SEQUENCE] + receipt
RUN E  same grant, order flipped          -> ALL ALLOW
RUN F  session split                      -> takeover (session-scoped R4 blind)
RUN G  resource-keyed history             -> BLOCK across sessions
RUN H  resource split / customer key      -> resource takeover; customer BLOCK
RUN I  fork alone / external witness      -> takeover alone; W1_FORK with witness
RUN J  issuer-only / shared reset          -> W1_FORK control; takeover under shared write reach
```

### Run J — Prediction 11 v2

The preregistration was frozen at
`8732e865a1f52b5d490f46b046122c12838929c49daf7c5fdf999057d811904a`
before implementation.

- Control: clear issuer history only, keep witness → `BLOCK / W1_FORK`
- Attack: one capability clears issuer and witness → recovery `ALLOW`
- Current deterministic reset receipt:
  `9d10426c725397b3fbf7348423e74b7d6bbb3cb30c4b0344b3b38b543586aea6`

Outcome: **Prediction 11 v2 confirmed in this simulation.** Independent key
material is not sufficient when the same write capability can rewrite both
histories. Full boundary and independent-recheck note:
`RUN_J_RESULT_2026-07-28.md`.

Run J remains separate from the scorecard. It does not create S8 or change the
S1–S7 denominator.

### Receipt digests (content fields; `decided_at` is after the hash)

| Run | `chain_sha256` (current tree) |
|---|---|
| D (session-scoped R4 block) | `acc8966a3bacf42ea4defc454dbda8339630eb571383f1ec124e0223bf8ef2cb` |
| D `previous_head` | `d47046346827788320bf5a64a997d419808c4684b77fc7a1d772dfdf778d7c72` |

Customer-scoped gates key the receipt **head** on the same risk object as the sequence policy so linkage can survive a session boundary. Session-scoped gates chain per session by design.

Older verify notes under `archive/verify/` may cite pre-chain digests (e.g. `726f6597…`); those verdicts are historical.

---

## Known limits (stab first)

1. Simulation — not wired into a production agent framework  
2. One hardcoded composition pair (identity mutation → credential recovery)  
3. Ledgers / witness are in-process (not multi-host, not a notary)  
4. S7 fork is opt-in via `issuer_history_reset` (N/A ≠ pass; no-op reset tested as gamer4)  
5. Author conflict — we ship reference gates; customer-keyed fails S7 in public  
6. R4 can block forever after one mutation without a reauthorization window  
7. No concurrency / atomic compare-and-append scenario yet  
8. Run J models shared reset authority in-process; it does not establish how a production witness should authenticate, replicate, or survive suppression

Predictions 10 & 11: `PREREG_COMPOSITION_LADDER_2026-07-26.md` (original + dated v2 addendum).
