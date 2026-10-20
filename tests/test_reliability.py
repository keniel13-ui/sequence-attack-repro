"""Regression tests for scorer input validation and the repro.py exit status.

Stdlib only (unittest). Run from the repository root:

    python3 -m unittest discover -v
"""

from __future__ import annotations

import contextlib
import io
import runpy
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import adapter  # noqa: E402
import gates  # noqa: E402


def _gate_returning(value):
    class Gate:
        name = f"returns allow={value!r}"

        def new_session(self, grant):
            return self

        def check(self, tool, args):
            return {"allow": value, "rule": "R4_SEQUENCE"}

    return Gate


class ScorerRejectsNonBoolAllow(unittest.TestCase):
    """Failure mode: a gate answering {"allow": None} (or 0, "", "false") was
    read by truthiness. A falsy non-bool on the decisive call counted as a
    refusal, so a gate that never decided anything could score catches."""

    def test_falsy_non_bool_values_are_rejected(self):
        for value in (None, 0, "", "false", [], 0.0):
            with self.subTest(allow=value):
                with self.assertRaises(ValueError) as cm:
                    adapter.score(_gate_returning(value))
                self.assertIn("'allow' is a bool", str(cm.exception))

    def test_truthy_non_bool_values_are_rejected(self):
        for value in (1, "true", "yes", [1]):
            with self.subTest(allow=value):
                with self.assertRaises(ValueError):
                    adapter.score(_gate_returning(value))

    def test_missing_allow_and_non_dict_still_rejected(self):
        class NoAllow:
            name = "no allow key"

            def new_session(self, grant):
                return self

            def check(self, tool, args):
                return {"rule": "R4_SEQUENCE"}

        class NotADict(NoAllow):
            name = "returns a bool"

            def check(self, tool, args):
                return False

        for impl in (NoAllow, NotADict):
            with self.subTest(impl=impl.name), self.assertRaises(ValueError):
                adapter.score(impl)

    def test_reference_card_unchanged(self):
        # The published card (README "Scorecard") must be identical with the
        # stricter check, because every reference gate already returns bools.
        expect = {
            adapter.AlwaysAllow: (2, 6),
            adapter.AlwaysDeny: (0, 6),
            adapter.ScopedTokenBaseline: (2, 6),
            adapter.PrefixDenyGamer: (0, 6),
            adapter.BlanketRuleGamer: (0, 6),
            adapter.PurposeConditionedGamer: (1, 6),
            adapter.SessionScopedPurpose: (4, 6),
            adapter.CustomerScopedPurpose: (6, 7),
            adapter.WitnessAnchoredPurpose: (7, 7),
            adapter.CapabilityLiarGamer: (6, 7),
            adapter.ForeignVocabularyGate: (6, 7),
        }
        for factory, (passed, total) in expect.items():
            card = adapter.score(factory)
            with self.subTest(gate=card["name"]):
                self.assertEqual((card["passed"], card["total"]), (passed, total))


class ReproExitStatus(unittest.TestCase):
    """Failure mode: repro.py printed FAILED verdict lines but always exited 0,
    so the CI step "Ladder (repro.py)" stayed green on a broken ladder."""

    def run_repro(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                runpy.run_path(str(ROOT / "repro.py"), run_name="__main__")
            except SystemExit as exc:
                return exc.code, out.getvalue(), err.getvalue()
        return 0, out.getvalue(), err.getvalue()

    def test_clean_ladder_exits_zero(self):
        code, out, err = self.run_repro()
        self.assertIn(code, (0, None), err)
        self.assertNotIn("FAILED", out.split("VERDICT vs KILL_TEST_PREREG")[1])
        self.assertEqual(err, "")

    def test_broken_gate_exits_nonzero(self):
        def allow_everything(self, tool, args):
            return {"allow": True, "rule": "PASS", "why": "sabotaged", "receipt": {}}

        with mock.patch.object(gates.PurposeGate, "check", allow_everything):
            code, out, err = self.run_repro()
        self.assertEqual(code, 1)
        self.assertIn("P2  gate BLOCKS + replayable receipt ....... FAILED", out)
        self.assertIn("LADDER FAILED: run(s) B", err)


class MutationCheckWritesUtf8(unittest.TestCase):
    """Failure mode: run_l_mutation_check.py wrote its mutant copies with the
    locale encoding. On Windows (cp1252) the non-ASCII characters in run_l.py
    were written as cp1252 bytes, and importing the mutant failed with
    "SyntaxError: (unicode error) 'utf-8' codec can't decode byte 0x97"
    (observed on a windows-2025 runner). Simulated here by making every
    write_text that does not name an encoding use cp1252."""

    def test_mutants_load_when_locale_is_cp1252(self):
        import pathlib

        import run_l_mutation_check

        real_write_text = pathlib.Path.write_text

        def cp1252_default(self, data, encoding=None, errors=None, newline=None):
            return real_write_text(self, data, encoding=encoding or "cp1252", errors=errors)

        out = io.StringIO()
        with mock.patch.object(pathlib.Path, "write_text", cp1252_default), contextlib.redirect_stdout(out):
            code = run_l_mutation_check.main()
        self.assertEqual(code, 0, out.getvalue())
        self.assertIn("MUTATION VERDICT  PASS", out.getvalue())


if __name__ == "__main__":
    unittest.main()
