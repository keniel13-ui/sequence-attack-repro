# CLAUDE.md

Guidance for Claude Code (and other agents) working in this repository.

## What this is

A small, open, runnable suite for one failure family: sequence-composition attacks on agent
authorization ("every step passes a per-call guardrail; the sequence is account takeover"). It is
research with preregistered predictions, dated results, and a public scorecard. See `README.md`
and `docs/ARCHITECTURE.md`.

## Non-negotiables

- **Stdlib only.** No third-party imports, no `requirements.txt`, no network, no model calls.
  Python 3 standard library and nothing else, in every script.
- **Do not edit hash-pinned files.** `run_l.py` is pinned by `run_l_mutation_check.py`
  (`EXPECTED_RUN_L_SHA256`). `run_k.py` is pinned by the Run K fixture on the
  `fixture-run-k-defg` branch. Never reformat, lint-fix, or change line endings in them.
- **Do not edit frozen records**: `PREREG_*.md`, `RUN_*_PREREG_*.md`, `RUN_*_RESULT_*.md`,
  `RESULT.md`, `LOOSE_SCORER_RECEIPT.md`, `archive/verify/**`. If one disagrees with the code,
  report it; corrections go in a new dated file written by the author.
- **Do not change expected values** in `ci_check.py`, or any printed verdict, hash or score, to
  make something pass. A mismatch is a result.
- **Do not count your own run as a reproduction.** The README's reproduction matrix is filled
  by people outside the project, by the author.
- Unmerged upstream branches (`fixture-run-k-defg`, `run-l-candidate-input-manifest`,
  `run-n-state-version-provenance`) are in-flight work. Avoid edits that would conflict with them.
  `run_n.py` is intentionally not on `main` (its result was withdrawn).

## Commands

All from the repository root, with any Python 3.9+ (`python3` on macOS/Linux, `python` on
Windows):

```bash
python3 repro.py                 # ladder A to I
python3 run_j.py                 # exit 0 = PREDICTION 11 v2 CONFIRMED
python3 adapter.py               # strict scorecard, gamers, conformance
python3 loose_replay.py          # historical loose scorer vs strict
python3 ci_check.py              # exact scorecard + Run D asserts (exit 1 on regression)
python3 run_k.py                 # exit 0 = core D/E + A/B/C confirmed
python3 run_l.py                 # exit 0 = conclusive
python3 run_l_mutation_check.py  # exit 0 = both Run L protections load-bearing
```

On Windows set the environment variable `PYTHONUTF8=1` first. Without it, `adapter.py` and
`run_k.py` stop with `UnicodeEncodeError` when output goes to a cp1252 console or pipe.

## Adding a gate to score

Implement `new_session(grant)` and `session.check(tool, args) -> {"allow": bool, "rule": str}`
(optional `issuer_history_reset()`, `normalize_rule()`), then call `adapter.score(YourGate)`.
Do not add it to the public card or to `ci_check.py` without the author.

## Style

Match the surrounding code: `from __future__ import annotations`, type hints, plain functions and
small classes, docstrings that state the failure mode a check exists for.
