# Contributing

Thanks for looking. The most valuable contribution is a run on your machine, reported honestly.

## Report a reproduction

Follow "Reproduce it and tell me what you got" in the README and open an issue with your OS,
Python version, and the last line of each command. A disagreeing result counts under the same
rules as an agreeing one.

## Code and docs changes

- Stdlib only. A change that adds a dependency will not be merged.
- Never edit a hash-pinned file (`run_l.py`, `run_k.py`) or a frozen record (preregistrations,
  results, `LOOSE_SCORER_RECEIPT.md`, `archive/verify/`). See [CLAUDE.md](CLAUDE.md) for the
  full list and the reason.
- A change to scoring, scenarios or gates changes published numbers. Open an issue first and say
  which README or RESULT row it moves.
- Before opening a pull request, run every command in the README "30 seconds" block and the
  `run_k.py`, `run_l.py` and `run_l_mutation_check.py` commands, and confirm each exits 0.

## Branch workflow

Work goes through a `dev` integration branch when one exists:

1. Branch from `dev` (or `main` if `dev` does not exist yet):
   `git switch -c <type>/<short-topic> origin/dev`
2. Keep one purpose per branch, and keep experiment branches (`run-*`, `fixture-*`) separate
   from tooling or docs branches.
3. Open the pull request against `dev`. The maintainer promotes `dev` to `main`.
4. Never force-push a shared branch, and never rewrite `main`: commit hashes are cited in the
   frozen records (for example the README pins `e4efa65` for reproduction).

To create `dev` from `main` (maintainer, one time):

```bash
gh api repos/keniel13-ui/sequence-attack-repro/git/refs \
  -f ref=refs/heads/dev \
  -f sha=$(gh api repos/keniel13-ui/sequence-attack-repro/commits/main -q .sha)
```
