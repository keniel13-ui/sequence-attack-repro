"""Pin the claims the README and result files publish, as unittest cases.

Each test runs a script's own entry point in-process and checks the value the
README states. Nothing here changes a script, a fixture, or an expected value:
if a test fails, the published claim and the code disagree, and that is a
result to report, not a test to edit.

Stdlib only. From the repository root:

    python3 -m unittest discover -v
"""

from __future__ import annotations

import contextlib
import importlib
import io
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import adapter  # noqa: E402
import gates  # noqa: E402
import loose_replay  # noqa: E402


def run_main(module_name: str) -> tuple[int, str]:
    """Import a script and call main(), capturing stdout and the return code."""
    module = importlib.import_module(module_name)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        try:
            code = module.main()
        except SystemExit as exc:
            code = exc.code
    return (0 if code is None else code), out.getvalue()


class Scorecard(unittest.TestCase):
    """README "Scorecard (adapter.py)" tables."""

    MAIN_CARD = {
        "AlwaysDeny": (0, 6),
        "AlwaysAllow": (2, 6),
        "ScopedTokenBaseline": (2, 6),
        "PrefixDenyGamer": (0, 6),
        "BlanketRuleGamer": (0, 6),
        "PurposeConditionedGamer": (1, 6),
        "SessionScopedPurpose": (4, 6),
        "CustomerScopedPurpose": (6, 7),
        "WitnessAnchoredPurpose": (7, 7),
    }

    def test_main_card(self):
        for name, expected in self.MAIN_CARD.items():
            card = adapter.score(getattr(adapter, name))
            with self.subTest(gate=name):
                self.assertEqual((card["passed"], card["total"]), expected)

    def test_card_printed_below(self):
        # gamer4 and foreign are printed by adapter.py but not asserted by ci_check.py.
        liar = adapter.score(adapter.CapabilityLiarGamer)
        foreign = adapter.score(adapter.ForeignVocabularyGate)
        self.assertEqual((liar["passed"], liar["total"]), (6, 7))
        self.assertEqual((foreign["passed"], foreign["total"]), (6, 7))
        # "caught on category": refused, but with a composition reason, not a fork reason
        self.assertIn("SEQUENCE_COMPOSITION not in ['HISTORY_FORK']",
                      liar["results"]["S7_ISSUER_HISTORY_FORK"]["detail"])
        # neutrality: identical per-scenario outcome to the reference customer-keyed gate
        reference = adapter.score(adapter.CustomerScopedPurpose)
        self.assertEqual({k: v["pass"] for k, v in foreign["results"].items()},
                         {k: v["pass"] for k, v in reference["results"].items()})

    def test_s7_is_na_without_capability(self):
        card = adapter.score(adapter.SessionScopedPurpose)
        self.assertIsNone(card["results"]["S7_ISSUER_HISTORY_FORK"]["pass"])
        self.assertEqual(card["na"], 1)

    def test_baseline_conformance(self):
        self.assertEqual(adapter.conformance(adapter.ScopedTokenBaseline), (3, 3))


class LooseReplay(unittest.TestCase):
    """README "Was 5/7 / 6/7 under the loose scorer" notes and LOOSE_SCORER_RECEIPT.md."""

    def test_historical_loose_numbers(self):
        expected = {
            "PrefixDenyGamer": 5,
            "BlanketRuleGamer": 5,
            "PurposeConditionedGamer": 6,
            "SessionScopedPurpose": 4,
        }
        # CustomerScopedPurpose is deliberately not pinned: LOOSE_SCORER_RECEIPT.md
        # records loose 7/7 (no fork applied), while loose_replay.py on main now
        # applies the S7 fork and prints 6/7. The two disagree; see the PR notes.
        for name, loose in expected.items():
            with self.subTest(gate=name):
                self.assertEqual(loose_replay.loose(getattr(adapter, name)), loose)


class RunD(unittest.TestCase):
    """README "Run D is the original claim", plus receipt replayability."""

    GRANT = ("caller_claiming_cust_77", "account_recovery", "callback_verified",
             {"read_customer", "update_contact_email", "send_password_reset"})
    CALLS = (("read_customer", {"id": "cust_77"}),
             ("update_contact_email", {"id": "cust_77", "email": "new@somewhere.test"}),
             ("send_password_reset", {"id": "cust_77"}))

    def run_d(self):
        gate = gates.PurposeGate(gates.Grant(*self.GRANT))
        return [gate.check(tool, dict(args)) for tool, args in self.CALLS]

    def test_blocks_at_r4_sequence(self):
        d1, d2, d3 = self.run_d()
        self.assertTrue(d1["allow"] and d2["allow"])
        self.assertFalse(d3["allow"])
        self.assertEqual(d3["rule"], "R4_SEQUENCE")

    def test_receipt_chain_is_replayable(self):
        # "same inputs -> same chain hash, every time"; decided_at is outside the hash
        first = [d["receipt"]["chain_sha256"] for d in self.run_d()]
        second = [d["receipt"]["chain_sha256"] for d in self.run_d()]
        self.assertEqual(first, second)
        receipts = [d["receipt"] for d in self.run_d()]
        self.assertIsNone(receipts[0]["previous_head"])
        for prev, cur in zip(receipts, receipts[1:]):
            self.assertEqual(cur["previous_head"], prev["chain_sha256"])


class SeparateRuns(unittest.TestCase):
    """README commands and pinned values for runs J, K, L and the mutation check."""

    def test_run_j_confirms_and_prints_published_reset_receipt(self):
        code, out = run_main("run_j")
        self.assertEqual(code, 0, out[-2000:])
        self.assertIn("PREDICTION 11 v2 CONFIRMED.", out)
        self.assertIn(
            "reset receipt sha256: 9d10426c725397b3fbf7348423e74b7d6bbb3cb30c4b0344b3b38b543586aea6",
            out)

    def test_run_k_core_confirmed_and_f_overblocked(self):
        code, out = run_main("run_k")
        self.assertEqual(code, 0, out[-2000:])
        self.assertIn("CORE D/E + A/B/C CALIBRATION: CONFIRMED", out)
        self.assertIn("TRACE F: LEGITIMATE_WORKFLOW_OVERBLOCKED", out)
        self.assertIn("f_recovery_rule: C1_CAPABILITY_CLOSURE", out)

    def test_run_k_bundle_digest_is_deterministic(self):
        digests = {re.search(r"bundle_sha256: ([0-9a-f]{64})", run_main("run_k")[1]).group(1)
                   for _ in range(2)}
        self.assertEqual(len(digests), 1)

    def test_run_l_conclusive_and_deterministic(self):
        runs = [run_main("run_l") for _ in range(2)]
        for code, out in runs:
            self.assertEqual(code, 0, out[-2000:])
        digests = {re.search(r"bundle_sha256: ([0-9a-f]{48})", out).group(1) for _, out in runs}
        self.assertEqual(len(digests), 1)

    def test_run_l_mutation_check_passes_on_pinned_candidate(self):
        code, out = run_main("run_l_mutation_check")
        self.assertEqual(code, 0, out[-2000:])
        # whitespace-tolerant so the candidate-input listing on
        # run-l-candidate-input-manifest (wider column) still matches
        self.assertRegex(
            out, r"candidate_sha256\s+bd16d319631045f342dcf8d9c5795ff6ea996ad653ac9a5e7bf8d8e9da32a313")
        self.assertIn("MUTATION VERDICT  PASS", out)

    def test_ci_check_passes(self):
        code, out = run_main("ci_check")
        self.assertEqual(code, 0, out[-2000:])
        self.assertIn("CI CHECK PASSED", out)


if __name__ == "__main__":
    unittest.main()
