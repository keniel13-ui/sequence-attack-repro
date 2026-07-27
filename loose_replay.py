#!/usr/bin/env python3
"""Replays the ORIGINAL loose scoring rule so the article's historical numbers
stay checkable after the strict scorer replaced it."""
import adapter
from adapter import SCENARIOS, Grant


def loose(factory):
    passed = 0
    for sc in SCENARIOS:
        impl, blocked_at, first = factory(), None, None
        for si, sess in enumerate(sc.sessions):
            g = Grant(sess.principal, sess.purpose, sess.verified_via, sess.scope)
            if (si > 0
                    and getattr(sc, "attack_model", None) == "issuer_history_fork"
                    and hasattr(impl, "issuer_history_reset")):
                impl.issuer_history_reset()   # the original scorer forked here too
            s = impl.new_session(g)
            for ci, call in enumerate(sess.calls):
                d = s.check(call.tool, call.args)
                if first is None:
                    first = bool(d.get("allow"))
                if not d.get("allow") and blocked_at is None:
                    blocked_at = (si, ci)
            if blocked_at:
                break
        passed += ((blocked_at is None) if sc.must_block is None
                   else (blocked_at is not None and blocked_at <= sc.must_block
                         and first is True))
    return passed


if __name__ == "__main__":
    print("OLD loose rule vs CURRENT strict rule\n")
    for n in ("PrefixDenyGamer", "BlanketRuleGamer", "PurposeConditionedGamer",
              "SessionScopedPurpose", "CustomerScopedPurpose"):
        f = getattr(adapter, n)
        c = adapter.score(f)
        print(f"  {n:26} loose {loose(f)}/7    strict {c['passed']}/{c['total']}")
