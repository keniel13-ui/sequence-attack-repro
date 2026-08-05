# Run N Code Verdict — Ka'el Correction Addendum

**Author:** Ka'el
**Corrects:** `RUN_N_CODE_BREAKER_VERDICT_KAEL_2026-08-04.md` (`66a0800e…`)
**Date:** 2026-08-04 EDT
**Raised by:** Ka'el, while preparing an external reply that would have rested on the result

The frozen verdict is **not edited**. This addendum qualifies it.

## Verdict status: **PASS DOWNGRADED TO PARTIAL — declaration ablation is incomplete.**

I found this while checking what Run N could honestly tell Ali Khater, whose question *is*
declared-versus-observed dependencies. The one control that answers him is the one that is
only partly covered — and I passed it.

## What is actually covered

`trace_n_d` runs the full ablation and asserts it (`run_n.py` 626-654):

```python
("HONEST",  {state_object_id, state_version_id: observer.head(...)}),
("OMITTED", {}),
("FORGED",  {state_object_id: OBJ_OTHER, state_version_id: "v_x"}),
...
all(not variants[k]["allow"]
    and variants[k]["rule"] == "P1_UNVERIFIED_ROUTE_PROVENANCE" for k in variants)
```

All three variants block. For **N-D this control genuinely passes.**

## What is not covered

```text
trace_n_e   HONEST/OMITTED/FORGED references: 0
trace_n_f   HONEST/OMITTED/FORGED references: 0
trace_n_g   HONEST/OMITTED/FORGED references: 0
```

Body §9 froze: *"Every recovery is run with identical observed state under HONEST, OMITTED,
and FORGED... **D, E, and F must retain their verdicts across all three variants.**"*
Addendum §3 then made G a core trace under the same conjunctive bar.

**E, F, and G were never run under declaration ablation.** One of four core traces carries
the control that the contract requires on at least three.

This matters most on **F**. D, E, and G are blocks — a declaration cannot make a blocked
trace worse. **F is the ALLOW**, and an unexercised question sits there: can a forged or
omitted declaration flip the legitimate workflow's verdict, or cause it to allow for the
wrong reason? Nothing in the executed run answers that, and F is the row that makes this
result novel.

## Also noted

`run_declaration_variants` (line 548) is defined and never called — dead code, not a
missing control. Cosmetic. Recording it so a later reader does not mistake it for the gap.

## What this does and does not change

**Unchanged and still earned:** C11 gate cleanliness, the N-G traversal mutation proving
lineage load-bearing, N-V2's custody bypass, N-V1/V3, C1/C2/C3/C7/C8/C9, zero issuer calls
on blocks, regression green, `run_k.py` unmodified. Those I verified by execution and they
stand.

**Downgraded:** `CONFIRMED_BOUNDED_POLICY_UNDER_VERIFICATION_CUSTODY` requires *every*
binding control to pass. Declaration ablation is a binding control and it ran on one of
four core traces. The result is therefore **not yet fully earned** under its own contract.

## Required repair — small

Extend the existing `trace_n_d` ablation pattern to `trace_n_e`, `trace_n_f`, and
`trace_n_g`, asserting each retains its frozen verdict across HONEST, OMITTED, and FORGED.
For F, additionally assert the issuer is called exactly once and bound to the prepared
destination in **all three** variants — a legitimate workflow that allows for a different
reason under a forged declaration is not the same result.

Then re-run and re-report. No design change, no addendum v2, no contract reopening. This is
a code-breaker case exactly as the terminality rule intended.

## Owning it

I passed this candidate after checking gate cleanliness, lineage load-bearing, and custody
bypass — the three things I had personally argued about. I did not check whether every
binding control actually executed. I read the controls that were *printed* and did not ask
which ones were *absent*.

That is the same failure class I flagged in the maker seat twice tonight: **verifying what
is reported rather than what is missing.** A control that never runs prints nothing, and
nothing is exactly what I did not look for.

Third bad call of the session, and the most consequential, because a PASS is what unblocks
publication and an external reply.

## Consequence

`RUN_N_RESULT_2026-08-04.md` must carry this qualification until the repair lands. No
external reply, article, or publication may rest on the full positive claim yet.
