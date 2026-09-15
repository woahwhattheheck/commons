from __future__ import annotations

import ast
import io
import math
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parent / "revenue" / "learn2design2026"
sys.path.insert(0, str(ROOT))

from core import (
    Candidate,
    ContractError,
    RadiusController,
    better,
    canonical_sha256,
    choose_elites,
    clip_point,
    halton_points,
    jitter_around,
    make_budget_plan,
    make_run_receipt,
    normalized_distance,
    rank_key,
)
from pack import PackageError, build_archive, validate_source_dir, verify_archive, verify_archive_bytes
from synthetic import InfeasibleTrap
import benchmark


class CoreTests(unittest.TestCase):
    def test_feasible_dominates_lower_loss_infeasible(self):
        feasible = Candidate((0.7, 0.1), 10.0, 0.0, True, "x", 0)
        infeasible = Candidate((0.0, 0.0), -100.0, 0.2, False, "x", 1)
        self.assertTrue(better(feasible, infeasible))
        self.assertLess(rank_key(feasible), rank_key(infeasible))

    def test_nonfinite_loss_is_worst(self):
        bad = Candidate((0.0,), math.inf, 0.0, True, "x", 0)
        good = Candidate((0.1,), 999.0, 0.0, True, "x", 1)
        self.assertTrue(better(good, bad))

    def test_candidate_rejects_aliases_and_bad_violation(self):
        with self.assertRaises(ContractError):
            Candidate((0.0,), 1.0, -0.1, False, "x", 0)
        with self.assertRaises(ContractError):
            Candidate((0.0,), 1.0, 0.1, True, "x", 0)
        with self.assertRaises(ContractError):
            Candidate((math.nan,), 1.0, 0.0, True, "x", 0)

    def test_clip_and_distance(self):
        b = [(-1.0, 1.0), (0.0, 10.0)]
        self.assertEqual(clip_point((-3, 30), b), (-1.0, 10.0))
        self.assertAlmostEqual(normalized_distance((-1, 0), (1, 10), b), 1.0)

    def test_halton_deterministic_and_bounded(self):
        bounds = [(-3.0, 2.0), (10.0, 11.0), (0.0, 100.0)]
        a = halton_points(bounds, 24, offset=7)
        b = halton_points(bounds, 24, offset=7)
        self.assertEqual(a, b)
        self.assertEqual(len(set(a)), 24)
        for p in a:
            for x, (lo, hi) in zip(p, bounds):
                self.assertGreaterEqual(x, lo)
                self.assertLessEqual(x, hi)

    def test_jitter_repeatability(self):
        bounds = [(-1.0, 1.0)] * 4
        a = jitter_around((0, 0, 0, 0), bounds, radius=.2, count=10, seed=9)
        b = jitter_around((0, 0, 0, 0), bounds, radius=.2, count=10, seed=9)
        c = jitter_around((0, 0, 0, 0), bounds, radius=.2, count=10, seed=10)
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    def test_radius_grows_and_shrinks_with_caps(self):
        r = RadiusController(radius=.2, minimum=.05, maximum=.3, successes_to_grow=2, failures_to_shrink=2)
        r.observe(True); self.assertEqual(r.radius, .2)
        r.observe(True); self.assertGreater(r.radius, .2)
        for _ in range(20): r.observe(True)
        self.assertLessEqual(r.radius, .3)
        for _ in range(20): r.observe(False)
        self.assertGreaterEqual(r.radius, .05)

    def test_budget_plan_exact_accounting(self):
        p = make_budget_plan(1000, exploration_fraction=.1, restart_count=5)
        self.assertEqual(p.exploration_evaluations + p.local_evaluations, 1000)
        self.assertEqual(p.restart_count, 5)
        self.assertGreater(p.evaluations_per_restart, 0)
        with self.assertRaises(ContractError): make_budget_plan(True)

    def test_elite_tie_determinism(self):
        a = Candidate((0.1,), 1.0, 0, True, "x", 0)
        b = Candidate((0.2,), 1.0, 0, True, "x", 0)
        self.assertEqual(choose_elites([b, a], 2), choose_elites([a, b], 2))

    def test_infeasible_trap_prefers_feasible(self):
        problem = InfeasibleTrap()
        values = [problem.evaluate(p, i) for i, p in enumerate(halton_points(problem.bounds, 64))]
        best = choose_elites(values, 1)[0]
        self.assertTrue(best.feasible)

    def test_receipt_is_deterministic_and_non_authoritative(self):
        p = make_budget_plan(100)
        c = Candidate((.5,), 1.0, 0.0, True, "x", 7)
        r = RadiusController()
        a = make_run_receipt(seed=3, plan=p, best=c, radius=r, evidence_class="SYNTHETIC_LOCAL")
        b = make_run_receipt(seed=3, plan=p, best=c, radius=r, evidence_class="SYNTHETIC_LOCAL")
        self.assertEqual(a, b)
        self.assertFalse(a["authority"]["officialScoreClaimed"])
        unsigned = dict(a); digest = unsigned.pop("receiptSha256")
        self.assertEqual(digest, canonical_sha256(unsigned))


class BenchmarkTests(unittest.TestCase):
    def test_synthetic_benchmark_repeatable(self):
        a = benchmark.run(seed=17, evaluations=160)
        b = benchmark.run(seed=17, evaluations=160)
        self.assertEqual(a, b)
        self.assertTrue(a["bestFeasible"])
        self.assertTrue(a["trapBestFeasible"])
        self.assertFalse(a["authority"]["officialScore"])

    def test_synthetic_benchmark_seed_changes_result(self):
        a = benchmark.run(seed=17, evaluations=160)
        b = benchmark.run(seed=18, evaluations=160)
        self.assertNotEqual(a["resultSha256"], b["resultSha256"])


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="l2d-test-"))
        self.source = self.tmp / "source"
        self.source.mkdir()
        for name in ("submission.py", "requirements.txt"):
            shutil.copy2(ROOT / name, self.source / name)
        (self.source / "helper.py").write_text("VALUE = 3\n", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_source_has_exactly_one_optimizer_subclass(self):
        data = validate_source_dir(self.source)
        self.assertEqual(data["className"], "StagedTrustPortfolio")

    def test_source_symlink_rejected(self):
        target = self.tmp / "external.txt"; target.write_text("x", encoding="utf-8")
        (self.source / "bad.py").symlink_to(target)
        with self.assertRaises(PackageError): validate_source_dir(self.source)

    def test_build_twice_is_byte_deterministic(self):
        p1, p2 = self.tmp / "a.zip", self.tmp / "b.zip"
        r1 = build_archive(self.source, p1)
        r2 = build_archive(self.source, p2)
        self.assertEqual(p1.read_bytes(), p2.read_bytes())
        self.assertEqual(r1, r2)
        self.assertFalse(r1["authority"]["officialSubmission"])

    def test_archive_tamper_changes_receipt(self):
        p = self.tmp / "a.zip"; r1 = build_archive(self.source, p)
        (self.source / "helper.py").write_text("VALUE = 4\n", encoding="utf-8")
        q = self.tmp / "b.zip"; r2 = build_archive(self.source, q)
        self.assertNotEqual(r1["archiveSha256"], r2["archiveSha256"])
        self.assertNotEqual(r1["receiptSha256"], r2["receiptSha256"])

    def _zip(self, rows):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            for name, data, mode in rows:
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = mode << 16
                zf.writestr(info, data)
        return buf.getvalue()

    def test_traversal_rejected(self):
        src = (ROOT / "submission.py").read_bytes(); req = b"optax>=0.2.3,<1\n"
        bad = self._zip([("submission.py", src, 0o100644), ("requirements.txt", req, 0o100644), ("../evil", b"x", 0o100644)])
        with self.assertRaises(PackageError): verify_archive_bytes(bad)

    def test_symlink_member_rejected(self):
        src = (ROOT / "submission.py").read_bytes(); req = b"optax>=0.2.3,<1\n"
        bad = self._zip([("submission.py", src, 0o100644), ("requirements.txt", req, 0o100644), ("link", b"dest", 0o120777)])
        with self.assertRaises(PackageError): verify_archive_bytes(bad)

    def test_duplicate_member_rejected(self):
        src = (ROOT / "submission.py").read_bytes(); req = b"optax>=0.2.3,<1\n"
        bad = self._zip([("submission.py", src, 0o100644), ("submission.py", src, 0o100644), ("requirements.txt", req, 0o100644)])
        with self.assertRaises(PackageError): verify_archive_bytes(bad)

    def test_wrong_optimizer_class_count_rejected(self):
        with open(self.source / "submission.py", "a", encoding="utf-8") as f:
            f.write("\nclass Other(OptimizationAlgorithm):\n    pass\n")
        with self.assertRaises(PackageError): validate_source_dir(self.source)

    def test_requirements_directive_rejected(self):
        (self.source / "requirements.txt").write_text("-r https://example.test/x\n", encoding="utf-8")
        with self.assertRaises(PackageError): validate_source_dir(self.source)

    def test_verify_rederives_from_archive(self):
        p = self.tmp / "submission.zip"
        built = build_archive(self.source, p)
        verified = verify_archive(p)
        self.assertEqual(built, verified)


class SourceContractTests(unittest.TestCase):
    def test_submission_has_no_result_call_before_start_logging(self):
        tree = ast.parse((ROOT / "submission.py").read_text(encoding="utf-8"))
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "StagedTrustPortfolio")
        method = next(n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "optimize")
        start_line = None
        forbidden_before = []
        for node in ast.walk(method):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "start_logging": start_line = node.lineno
        self.assertIsNotNone(start_line)
        for node in ast.walk(method):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in {"value", "grad", "value_and_grad", "hessian", "log_evaluation"} and node.lineno < start_line:
                    forbidden_before.append((node.func.attr, node.lineno))
        self.assertEqual(forbidden_before, [])

    def test_submission_source_mentions_budget_exceeded(self):
        source = (ROOT / "submission.py").read_text(encoding="utf-8")
        self.assertGreaterEqual(source.count("budget_exceeded"), 2)

    def test_authority_language_present(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        for token in ("cannot", "hidden-topology", "Authority ceiling", "no"):
            self.assertIn(token.lower(), text.lower())


if __name__ == "__main__":
    unittest.main()
