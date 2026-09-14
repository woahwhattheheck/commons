"""Compatibility + hardening tests for the bidder qualification vault facade."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest

from . import _tests_v1 as legacy
from . import vault as hardened


# Run the shipped v1 regression suite against the byte-preserved v1 engine.
# That suite defines legacy evidence semantics, including cases the hardened
# facade now rejects earlier on trust-boundary grounds.  The facade itself is
# attacked separately below, so stricter gates cannot rewrite v1 test intent.
legacy.compile_vault = hardened._core.compile_vault
legacy.verify_bundle = hardened._core.verify_bundle
VaultTests = legacy.VaultTests


class HardeningTests(unittest.TestCase):
    def _ready(self, *, at: str = "2026-09-13T21:00:00Z"):
        a, r, q = legacy.fixture()
        ar, rr = hardened.roots(a, r)
        bundle = hardened.compile_vault(
            a,
            r,
            q,
            expected_subject_id="synthetic-bidder",
            expected_authority_sha256=ar,
            expected_registry_sha256=rr,
            evaluated_at=at,
        )
        self.assertEqual(bundle["result"]["status"], "EVIDENCE_READY")
        return a, r, q, ar, rr, bundle

    def test_trusted_subject_matches(self):
        self._ready()

    def test_subject_transplant_rejected(self):
        a, r, q = legacy.fixture()
        ar, rr = hardened.roots(a, r)
        q["subject_id"] = "different-bidder"
        with self.assertRaisesRegex(hardened.VaultError, "trusted subject mismatch"):
            hardened.compile_vault(
                a,
                r,
                q,
                expected_subject_id="synthetic-bidder",
                expected_authority_sha256=ar,
                expected_registry_sha256=rr,
                evaluated_at="2026-09-13T21:00:00Z",
            )

    def test_verify_subject_transplant_rejected(self):
        a, r, q, ar, rr, bundle = self._ready()
        q["subject_id"] = "different-bidder"
        with self.assertRaisesRegex(hardened.VaultError, "trusted subject mismatch"):
            hardened.verify_bundle(
                a,
                r,
                q,
                bundle,
                expected_subject_id="synthetic-bidder",
                expected_authority_sha256=ar,
                expected_registry_sha256=rr,
                verified_at="2026-09-13T21:00:00Z",
            )

    def test_registry_before_bound_authority_rejected(self):
        a, r, q = legacy.fixture()
        a["issued_at"] = "2026-09-13T20:30:00Z"
        ar, rr = hardened.roots(a, r)
        with self.assertRaisesRegex(hardened.VaultError, "predates bound authority"):
            hardened.compile_vault(
                a,
                r,
                q,
                expected_subject_id=q["subject_id"],
                expected_authority_sha256=ar,
                expected_registry_sha256=rr,
                evaluated_at="2026-09-13T21:00:00Z",
            )

    def test_observation_after_registry_generation_rejected(self):
        a, r, q = legacy.fixture()
        r["items"][0]["observed_at"] = "2026-09-13T20:30:00Z"
        ar, rr = hardened.roots(a, r)
        with self.assertRaisesRegex(hardened.VaultError, "observation postdates registry"):
            hardened.compile_vault(
                a,
                r,
                q,
                expected_subject_id=q["subject_id"],
                expected_authority_sha256=ar,
                expected_registry_sha256=rr,
                evaluated_at="2026-09-13T21:00:00Z",
            )

    def test_snapshot_equality_boundaries_remain_valid(self):
        # The shipped fixture has authority issued == registry generated and
        # every evidence observation == registry generated.
        self._ready()

    def test_subject_anchor_is_strict_token(self):
        a, r, q = legacy.fixture()
        ar, rr = hardened.roots(a, r)
        with self.assertRaises(hardened.VaultError):
            hardened.compile_vault(
                a,
                r,
                q,
                expected_subject_id="bad subject with spaces",
                expected_authority_sha256=ar,
                expected_registry_sha256=rr,
                evaluated_at="2026-09-13T21:00:00Z",
            )

    def test_cli_roots_emits_subject_anchor(self):
        a, r, q = legacy.fixture()
        env = {"authority": a, "registry": r, "subject_id": q["subject_id"]}
        proc = subprocess.run(
            [sys.executable, "-m", "revenue.bidder_qualification_vault.vault", "roots"],
            input=hardened.canonical(env),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        out = json.loads(proc.stdout)
        self.assertEqual(out["expected_subject_id"], q["subject_id"])
        ar, rr = hardened.roots(a, r)
        self.assertEqual(out["authority_sha256"], ar)
        self.assertEqual(out["registry_sha256"], rr)

    def test_cli_compile_fails_closed_without_subject_anchor(self):
        a, r, q = legacy.fixture()
        ar, rr = hardened.roots(a, r)
        env = {
            "authority": a,
            "registry": r,
            "query": q,
            "expected_authority_sha256": ar,
            "expected_registry_sha256": rr,
        }
        proc = subprocess.run(
            [sys.executable, "-m", "revenue.bidder_qualification_vault.vault", "compile"],
            input=hardened.canonical(env),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(proc.returncode, 3)
        self.assertIn(b"expected_subject_id", proc.stderr)


if __name__ == "__main__":
    unittest.main()
