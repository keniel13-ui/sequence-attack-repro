#!/usr/bin/env python3
"""Maker checks for the 3d5gi candidate-input listing. Not an independent break."""

from __future__ import annotations

import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import run_l_mutation_check as check


class CandidateInputManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="run_l_manifest_test_")
        self.root = Path(self.tempdir.name)
        self.checker_path = Path(check.__file__)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def write_candidate(self, data: bytes) -> None:
        (self.root / "run_l.py").write_bytes(data)

    def rendered(self, manifest) -> str:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            check.print_candidate_input_manifest(manifest)
        return output.getvalue()

    def test_pinned_run_l_prints_path_content_id_and_digest(self) -> None:
        source = self.checker_path.with_name("run_l.py").read_bytes()
        self.write_candidate(source)
        manifest = check.candidate_input_manifest(self.root, self.checker_path)
        self.assertEqual(manifest.errors, ())
        self.assertEqual(
            manifest.entries,
            (("run_l.py", f"sha256:{check.sha256(source)}"),),
        )
        self.assertEqual(manifest.candidate_sha256, check.EXPECTED_RUN_L_SHA256)
        self.assertEqual(manifest.source_bytes, source)
        self.assertEqual(
            manifest.checker_sha256,
            check.sha256(self.checker_path.read_bytes()),
        )
        text = self.rendered(manifest)
        self.assertIn(
            "candidate_input     000\trun_l.py\t"
            f"sha256:{check.EXPECTED_RUN_L_SHA256}",
            text,
        )
        self.assertIn(f"candidate_sha256    {check.EXPECTED_RUN_L_SHA256}", text)
        self.assertIn(f"checker_sha256      {manifest.checker_sha256}", text)
        self.assertIn("candidate_manifest_verdict  ACCEPT", text)
        self.assertLess(
            text.index("candidate_input"),
            text.index("candidate_sha256"),
        )

    def test_changed_bytes_print_observed_ids_and_halt(self) -> None:
        changed = b"different candidate bytes\r\n"
        self.write_candidate(changed)
        manifest = check.candidate_input_manifest(self.root, self.checker_path)
        text = self.rendered(manifest)
        observed = check.sha256(changed)
        self.assertEqual(manifest.candidate_sha256, observed)
        self.assertIn(f"sha256:{observed}", text)
        self.assertIn(f"candidate_sha256    {observed}", text)
        self.assertIn("candidate_manifest_verdict  HALT", text)
        self.assertNotEqual(observed, check.EXPECTED_RUN_L_SHA256)

    def test_missing_input_halts_with_unavailable(self) -> None:
        manifest = check.candidate_input_manifest(self.root, self.checker_path)
        self.assertEqual(manifest.entries, (("run_l.py", "UNAVAILABLE"),))
        self.assertIsNone(manifest.candidate_sha256)
        self.assertTrue(manifest.errors)
        self.assertIn("candidate_manifest_verdict  HALT", self.rendered(manifest))

    def test_symlink_candidate_is_unavailable(self) -> None:
        real = self.root / "elsewhere.py"
        real.write_bytes(self.checker_path.with_name("run_l.py").read_bytes())
        (self.root / "run_l.py").symlink_to(real)
        manifest = check.candidate_input_manifest(self.root, self.checker_path)
        self.assertEqual(manifest.entries, (("run_l.py", "UNAVAILABLE"),))
        self.assertTrue(manifest.errors)

    def test_main_halts_before_mutation_or_import_on_mismatch(self) -> None:
        self.write_candidate(b"wrong bytes")
        fake_checker = self.root / "run_l_mutation_check.py"
        fake_checker.write_bytes(self.checker_path.read_bytes())
        output = io.StringIO()
        with (
            mock.patch.object(check, "__file__", str(fake_checker)),
            mock.patch.object(check, "replace_once") as replace_once,
            mock.patch.object(check, "load_module") as load_module,
            contextlib.redirect_stdout(output),
        ):
            exit_code = check.main()
        self.assertEqual(exit_code, 2)
        replace_once.assert_not_called()
        load_module.assert_not_called()
        text = output.getvalue()
        self.assertIn("candidate_manifest_verdict  HALT", text)
        self.assertIn("checker_sha256      ", text)

    def test_checker_hash_is_not_the_candidate_digest(self) -> None:
        source = self.checker_path.with_name("run_l.py").read_bytes()
        self.write_candidate(source)
        manifest = check.candidate_input_manifest(self.root, self.checker_path)
        self.assertNotEqual(manifest.checker_sha256, manifest.candidate_sha256)

    def test_digest_input_set_is_exactly_run_l(self) -> None:
        self.assertEqual(check.DIGEST_INPUT_PATHS, ("run_l.py",))


if __name__ == "__main__":
    unittest.main()
