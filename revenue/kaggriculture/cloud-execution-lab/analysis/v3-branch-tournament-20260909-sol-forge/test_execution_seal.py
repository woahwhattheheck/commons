#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import titan_branch_tournament as tournament


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tree_identity(files: dict[str, bytes]) -> str:
    return tournament.sha256_bytes(tournament.canonical_json({
        name: {"sha256": sha(data), "bytes": len(data)}
        for name, data in sorted(files.items())
    }))


class ExecutionClosureSealTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="titan-execution-seal-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.scratch = self.root / "scratch"
        self.scratch.mkdir()
        self.engine = self.root / "engine"
        self.engine.mkdir()
        (self.engine / "engine.py").write_bytes(b"pinned engine\n")
        self.engine_sha256 = {"engine.py": sha(b"pinned engine\n")}

        evaluator_root = self.scratch / "evaluator"
        evaluator_root.mkdir()
        script = evaluator_root / "evaluate.py"
        loader = evaluator_root / "loader.py"
        script.write_bytes(b"# evaluator\n")
        loader.write_bytes(b"# loader\n")
        self.evaluator = tournament.EvaluatorMaterial(
            script=script, loader=loader, commit="e" * 40,
            sha256=sha(script.read_bytes()),
            loader_sha256=sha(loader.read_bytes()),
        )
        self.opponents = [
            tournament.Opponent(
                "starter", "official_starter",
                {"kind": "official_starter", "engine_ref": "a" * 40}),
        ]

        self.baseline = self.make_bundle(
            "baseline", "baseline", {"main.py": b"SCORE = 0\n"})
        self.challenger = self.make_bundle(
            "challenger", "challenger",
            {"main.py": b"from dep import SCORE\n", "dep.py": b"SCORE = 1\n"})
        self.bundles = [self.baseline, self.challenger]

    def make_bundle(self, name: str, role: str,
                    files: dict[str, bytes]) -> tournament.CandidateBundle:
        root = self.scratch / "candidates" / name / "bundle"
        root.mkdir(parents=True)
        for relative, data in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return tournament.CandidateBundle(
            name=name, commit=name[0] * 40, ref=name[0] * 40, role=role,
            bundle_root=root, entry_path=root / "main.py", callable_name="agent",
            archive_sha256=("1" if role == "baseline" else "2") * 64,
            archive_bytes=sum(len(data) for data in files.values()),
            source_manifest_sha256=("3" if role == "baseline" else "4") * 64,
            source_manifest_bytes=1, receipt_sha256="5" * 64, receipt_bytes=1,
            runtime_tree_sha256=tree_identity(files), runtime_files=len(files),
            entry_sha256=sha(files["main.py"]),
        )

    def sealed(self):
        return tournament._execute_candidate_sealed(
            self.baseline, all_bundles=self.bundles,
            evaluator=self.evaluator, opponents=self.opponents,
            seeds=[1], rng_seed=7, engine_dir=self.engine,
            engine_ref="a" * 40, engine_sha256=self.engine_sha256,
            limits={"action_timeout": 1.0, "startup_timeout": 1.0,
                    "game_timeout": 1.0, "episode_steps": 2},
            recheck_first=True, output_dir=self.root / "output",
            process_timeout=10.0, scratch=self.scratch)

    def with_fake_execution(self, fake):
        original = tournament.execute_candidate
        tournament.execute_candidate = fake
        self.addCleanup(setattr, tournament, "execute_candidate", original)

    def test_future_candidate_dependency_mutation_fails_closed(self):
        """Predecessor accepted this drift because only main.py was re-fingerprinted."""
        def mutate(*args, **kwargs):
            (self.challenger.bundle_root / "dep.py").write_bytes(b"SCORE = 100\n")
            return object()

        self.with_fake_execution(mutate)
        with self.assertRaisesRegex(
                tournament.TournamentError,
                r"post-execution\[baseline\].*challenger.*runtime closure drift"):
            self.sealed()

    def test_evaluator_mutation_fails_closed(self):
        def mutate(*args, **kwargs):
            self.evaluator.loader.write_bytes(b"# altered loader\n")
            return object()

        self.with_fake_execution(mutate)
        with self.assertRaisesRegex(
                tournament.TournamentError,
                r"post-execution\[baseline\].*evaluator byte drift"):
            self.sealed()

    def test_unchanged_closure_returns_execution(self):
        sentinel = object()

        def unchanged(*args, **kwargs):
            return sentinel

        self.with_fake_execution(unchanged)
        self.assertIs(self.sealed(), sentinel)


if __name__ == "__main__":
    unittest.main()
