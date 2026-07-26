# Receipt — scores under the ORIGINAL loose scorer

The article states the three gaming gates scored **5/7, 5/7 and 6/7** before the
strict scoring rule landed. That scorer no longer exists on `main`, so the claim
would otherwise be unverifiable. This replays it.

```bash
python3 loose_replay.py
```

Measured 2026-07-26:

```
PrefixDenyGamer           loose 5/7    strict 0/6
BlanketRuleGamer          loose 5/7    strict 0/6
PurposeConditionedGamer   loose 6/7    strict 1/6
SessionScopedPurpose      loose 4/7    strict 4/6
CustomerScopedPurpose     loose 7/7    strict 6/7
```

The load-bearing line: a gate with no history at all (`PurposeConditionedGamer`,
6/7) outscored a real stateful gate (`SessionScopedPurpose`, 4/7) under the loose
rule. That is why the rule changed.
