# sequence-attack-repro

**Every step can pass a real per-call guardrail. The sequence can still be account takeover.**

```bash
python3 repro.py
```

No install. No network. No model. Stdlib only.

## What you will see

| Run | Meaning |
|---|---|
| **A** | Baseline RBAC + scoped token + per-call check + rate limit → **takeover succeeds** |
| **B** | Purpose / provenance gate vs ticket-injection path → block (may also be catchable by injection tools) |
| **C** | Same email-change action, **honest** sequence → **ALLOWED** (not a blanket deny) |
| **D** | Verified caller, no injection, everything in purpose → still **BLOCK** at composition (`R4_SEQUENCE`) + receipt |

**Run D is the claim.** Not "we catch prompt injection." Composition when no single step is out of policy.

## Receipt

On block, the gate prints a JSON receipt with grant, prior action classes, decision, why, and a stable `chain_sha256` over the content fields (timestamp is attached after the hash).

## Limits (read these)

- Simulation — not wired into a production agent framework
- Sequence rule is currently **one hardcoded pair** (identity mutation → credential recovery)
- Not a claim that no security product on earth can catch related attacks

## Background

Related essay: [CLAIM-30 on DEV](https://dev.to/kenielzep97/every-step-was-allowed-the-sequence-was-the-attack-ai-memory-judgment-claim-30-4ehc)

If this is already solved out of the box by a tool you know, open an issue or comment with the name and how it catches **Run D**.
