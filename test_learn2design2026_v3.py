from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent / "revenue" / "learn2design2026"
CANDIDATE = ROOT / "submission_v3.py"
MATRIX = ROOT / "public_matrix_v3.py"
EXPECTED_CANDIDATE_SHA256 = "d0a65c01708941220cd8c16accdfd16136c5294a94e2032b4cd68cdf83a360a9"
EXPECTED_CANDIDATE_GIT_BLOB = "78ce195e1779441f2a0c53feef67c8dafd87f240"


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()


class V3SourceContractTests(unittest.TestCase):
    def setUp(self):
        self.raw = CANDIDATE.read_bytes()
        self.source = self.raw.decode("utf-8")
        self.tree = ast.parse(self.source)
        self.cls = next(n for n in self.tree.body if isinstance(n, ast.ClassDef) and n.name == "StagedTrustPortfolio")
        self.optimize = next(n for n in self.cls.body if isinstance(n, ast.FunctionDef) and n.name == "optimize")

    def test_exact_candidate_identity(self):
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), EXPECTED_CANDIDATE_SHA256)
        self.assertEqual(git_blob(self.raw), EXPECTED_CANDIDATE_GIT_BLOB)
        self.assertIn('algorithm_str = "tjlabs_depth_throughput_portfolio_v3"', self.source)

    def test_no_result_call_before_start_logging(self):
        starts = [
            n.lineno for n in ast.walk(self.optimize)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "start_logging"
        ]
        self.assertEqual(len(starts), 1)
        forbidden = {
            "value", "grad", "value_and_grad", "hessian", "log_evaluation",
            "vmap_value", "vmap_value_and_grad", "value_grad_and_hessian", "vmap_value_grad_and_hessian",
        }
        calls = [
            (n.func.attr, n.lineno) for n in ast.walk(self.optimize)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr in forbidden and n.lineno < starts[0]
        ]
        self.assertEqual(calls, [])

    def test_depth_policy_is_materially_earlier_than_v2(self):
        defaults = {
            arg.arg: default for arg, default in zip(
                self.optimize.args.args[-len(self.optimize.args.defaults):], self.optimize.args.defaults
            )
        }
        self.assertEqual(ast.literal_eval(defaults["population_size"]), 8)
        self.assertLessEqual(ast.literal_eval(defaults["snapback_patience"]), 8)
        self.assertLessEqual(ast.literal_eval(defaults["recycle_interval"]), 16)
        self.assertGreaterEqual(self.source.count("budget_exceeded"), 2)

    def test_vectorized_objective_path_is_retained(self):
        attrs = {
            n.func.attr for n in ast.walk(self.optimize)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        }
        self.assertIn("warmup_vmap_value_and_grad", attrs)
        self.assertIn("vmap_value_and_grad", attrs)

    def test_matrix_binds_three_exact_candidates_and_authority_ceiling(self):
        source = MATRIX.read_text(encoding="utf-8")
        for token in (
            "0e5b0141138c471c9b47163aca4f1a01336dfdf1",
            "ac814d1f543529a823f7c3afa2a9c4f54c0bfe12",
            EXPECTED_CANDIDATE_GIT_BLOB,
            "ORGANIZER_PUBLIC_DEVELOPMENT",
            '"officialScore": False',
            '"revenue": False',
        ):
            self.assertIn(token, source)
        compile(source, MATRIX.as_posix(), "exec")


if __name__ == "__main__":
    unittest.main()
