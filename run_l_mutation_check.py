#!/usr/bin/env python3
"""Reproduce Run L's two load-bearing mutation checks.

The production candidate is never edited. Two temporary copies are made from the
exact published run_l.py bytes:

1. remove only the Gate receipt-MAC rejection;
2. remove only the authoritative observer-set mismatch rejection.

Each old attack must stay blocked in the clean control and become allowed only
when its corresponding protection is removed.

The candidate-input listing follows
RUN_L_CANDIDATE_INPUT_MANIFEST_PARAGRAPH_2026-08-21.md
SHA-256 3730fa5be678ee8764287f8a89806e22f676803e9829148c5e32bc765174b0d1.
"""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import tempfile
from typing import NamedTuple


EXPECTED_RUN_L_SHA256 = (
    "bd16d319631045f342dcf8d9c5795ff6ea996ad653ac9a5e7bf8d8e9da32a313"
)

# Fixed-order digest input set for candidate_sha256. One path. Mutants are
# generated at runtime from these same bytes and are not inputs.
DIGEST_INPUT_PATHS = ("run_l.py",)

MAC_GUARD = """\
        if not self._mac_ok(receipt):
            return self._d("BLOCK", "R_RECEIPT_UNAUTHENTIC", receipt,
                           "reconciliation receipt failed reconciler MAC")
"""

SET_GUARD = "    if evaluated_sorted != sorted(manifest.members):"
SET_MUTANT = "    if False and evaluated_sorted != sorted(manifest.members):"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class CandidateInputManifest(NamedTuple):
    entries: tuple[tuple[str, str], ...]
    candidate_sha256: str | None
    source_bytes: bytes | None
    checker_sha256: str
    errors: tuple[str, ...]


def _read_regular_nonsymlink(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise OSError("missing, not a regular file, or symlink")
    return path.read_bytes()


def candidate_input_manifest(
    root: Path, checker_path: Path
) -> CandidateInputManifest:
    checker_hash = sha256(Path(checker_path).read_bytes())
    entries: list[tuple[str, str]] = []
    errors: list[str] = []
    source_bytes: bytes | None = None

    for relative_path in DIGEST_INPUT_PATHS:
        target = root / relative_path
        try:
            raw_bytes = _read_regular_nonsymlink(target)
        except OSError as exc:
            entries.append((relative_path, "UNAVAILABLE"))
            errors.append(f"cannot read {relative_path}: {exc}")
            continue
        entries.append((relative_path, f"sha256:{sha256(raw_bytes)}"))
        if relative_path == "run_l.py":
            source_bytes = raw_bytes

    candidate = sha256(source_bytes) if source_bytes is not None else None
    if candidate is not None and candidate != EXPECTED_RUN_L_SHA256:
        errors.append(
            f"candidate hash mismatch: expected {EXPECTED_RUN_L_SHA256}, "
            f"found {candidate}"
        )

    return CandidateInputManifest(
        entries=tuple(entries),
        candidate_sha256=candidate,
        source_bytes=source_bytes,
        checker_sha256=checker_hash,
        errors=tuple(errors),
    )


def print_candidate_input_manifest(manifest: CandidateInputManifest) -> None:
    for index, (path, content_id) in enumerate(manifest.entries):
        print(f"candidate_input     {index:03d}\t{path}\t{content_id}")
    print(f"candidate_sha256    {manifest.candidate_sha256 or 'UNAVAILABLE'}")
    print(f"checker_sha256      {manifest.checker_sha256}")
    if manifest.errors:
        print("candidate_manifest_verdict  HALT")
    else:
        print("candidate_manifest_verdict  ACCEPT")


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise AssertionError(f"{label}: expected one mutation target, found {count}")
    return source.replace(old, new, 1)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fresh(module):
    w1 = module.Observer("W1", "store_a")
    w2 = module.Observer("W2", "store_b")
    registry = module.ObserverRegistry()
    registry.register(
        module.RISK_KEY,
        1,
        [w1, w2],
        "reconciler_0",
        "fail_closed",
    )
    return w1, w2, registry


def forged_receipt_attack(module) -> tuple[bool, dict]:
    """Forge DISAGREE -> CONSISTENT while keeping the self-digest valid."""
    w1, w2, registry = fresh(module)
    issuer_claim: list[str] = []
    module.mutate(issuer_claim, w1, w2)
    w1.suppress()
    issuer_claim = []

    honest = module.reconcile(registry, module.RISK_KEY, 1, issuer_claim)
    if honest["reconciliation_verdict"] != module.DISAGREE:
        raise AssertionError("B3 setup did not produce an honest DISAGREE receipt")

    body = {
        key: value
        for key, value in honest.items()
        if key not in ("receipt_digest", "receipt_mac")
    }
    body["reconciliation_verdict"] = module.CONSISTENT
    body["why"] = "mutation probe: forged consistent verdict"

    forged = dict(body)
    forged["receipt_digest"] = module.digest(body)
    forged["receipt_mac"] = honest["receipt_mac"]

    gate = module.Gate("fail_closed")
    digest_ok = gate._digest_ok(forged)
    return digest_ok, gate.check(module.RECOVERY, issuer_claim, forged)


def omitted_observer_attack(module) -> dict:
    """Claim only W1 was evaluated while omitted W2 retains the mutation."""
    w1, w2, registry = fresh(module)
    issuer_claim: list[str] = []
    module.mutate(issuer_claim, w1, w2)
    w1.suppress()
    issuer_claim = []

    receipt = module.reconcile(
        registry,
        module.RISK_KEY,
        1,
        issuer_claim,
        evaluated_names=["W1"],
    )
    return module.Gate("fail_closed").check(
        module.RECOVERY,
        issuer_claim,
        receipt,
    )


def compact(result: dict) -> str:
    return f"{result['authorization_decision']} [{result['rule']}]"


def main() -> int:
    checker_path = Path(__file__)
    manifest = candidate_input_manifest(checker_path.parent, checker_path)
    print_candidate_input_manifest(manifest)
    if manifest.errors:
        return 2

    assert manifest.source_bytes is not None
    assert manifest.candidate_sha256 is not None
    source_bytes = manifest.source_bytes

    source = source_bytes.decode()
    mac_mutant = replace_once(source, MAC_GUARD, "", "MAC guard")
    set_mutant = replace_once(source, SET_GUARD, SET_MUTANT, "observer-set guard")

    with tempfile.TemporaryDirectory(prefix="run_l_mutation_check_") as tmp:
        root = Path(tmp)
        clean_path = root / "run_l_clean.py"
        mac_path = root / "run_l_no_mac.py"
        set_path = root / "run_l_no_set_check.py"
        clean_path.write_bytes(source_bytes)
        mac_path.write_text(mac_mutant)
        set_path.write_text(set_mutant)

        clean = load_module(clean_path, "run_l_clean")
        no_mac = load_module(mac_path, "run_l_no_mac")
        no_set = load_module(set_path, "run_l_no_set_check")

        clean_digest_ok, clean_b3 = forged_receipt_attack(clean)
        mutant_digest_ok, mutant_b3 = forged_receipt_attack(no_mac)
        clean_b2 = omitted_observer_attack(clean)
        mutant_b2 = omitted_observer_attack(no_set)

        # Cross-controls: removing one protection must not disable the other.
        no_mac_b2 = omitted_observer_attack(no_mac)
        no_set_digest_ok, no_set_b3 = forged_receipt_attack(no_set)

        print(
            "receipt_auth      "
            f"clean={compact(clean_b3):<34} "
            f"mutant={compact(mutant_b3):<18} "
            f"digest_ok={clean_digest_ok}/{mutant_digest_ok}"
        )
        print(
            "observer_members  "
            f"clean={compact(clean_b2):<34} "
            f"mutant={compact(mutant_b2)}"
        )
        print(
            "cross_controls    "
            f"no_mac_B2={compact(no_mac_b2):<34} "
            f"no_set_B3={compact(no_set_b3):<34} "
            f"digest_ok={no_set_digest_ok}"
        )

        expected = [
            clean_digest_ok is True,
            mutant_digest_ok is True,
            compact(clean_b3) == "BLOCK [R_RECEIPT_UNAUTHENTIC]",
            compact(mutant_b3) == "ALLOW [PASS]",
            compact(clean_b2) == "BLOCK [OBSERVER_SET_MISMATCH]",
            compact(mutant_b2) == "ALLOW [PASS]",
            compact(no_mac_b2) == "BLOCK [OBSERVER_SET_MISMATCH]",
            compact(no_set_b3) == "BLOCK [R_RECEIPT_UNAUTHENTIC]",
            no_set_digest_ok is True,
        ]
        if not all(expected):
            print("MUTATION VERDICT  BLOCK")
            return 1

    print("MUTATION VERDICT  PASS — both protections independently load-bearing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
