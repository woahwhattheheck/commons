from __future__ import annotations

import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("v2_legacy_bisect", HERE / "run_bisect.py")
assert SPEC and SPEC.loader
B = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(B)


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def synthetic_harness(opponents=("arlene",)) -> dict:
    return {
        "schema_version": 1,
        "engine_ref": B.EXPECTED_ENGINE_REF,
        "engine_sha256": dict(B.EXPECTED_ENGINE_SHA256),
        "loader_sha256": B.EXPECTED_LOADER_SHA256,
        "evaluator_sha256": B.EXPECTED_EVALUATOR_SHA256,
        "agent_rng_seed": B.EXPECTED_AGENT_RNG_SEED,
        "limits": dict(B.EXPECTED_LIMITS),
        "opponents": {name: B.EXPECTED_OPPONENT_SHA256[name] for name in opponents},
    }


def synthetic_identity(config_sha: str = "1" * 64) -> dict:
    return {
        "file_count": 3,
        "file_manifest_sha256": "2" * 64,
        "main_py_sha256": "3" * 64,
        "config_sha256": config_sha,
    }


def scores_for_margin(margin: float, seat: int) -> list[float]:
    rival = 1000.0
    own = rival + margin
    return [own, rival] if seat == 0 else [rival, own]


def synthetic_report(*, opponent: str, seed: int, margin: float, identity: dict, trace_tag: str) -> dict:
    games = []
    for seat in (0, 1):
        trace = hashlib.sha256(f"{trace_tag}:{seat}".encode()).hexdigest()
        games.append({
            "seed": seed,
            "candidate_seat": seat,
            "status": "complete",
            "scores": scores_for_margin(margin, seat),
            "failure": None,
            "steps": 719,
            "episode_steps": 720,
            "daily_bank": [],
            "actors": [],
            "wall_seconds": 1.0,
            "driver_cpu_seconds": 0.1,
            "bank_snapshot": scores_for_margin(margin, seat),
            "trace_sha256": trace,
            "opponent": opponent,
        })
    return {
        "schema_version": 1,
        "engine_ref": B.EXPECTED_ENGINE_REF,
        "engine_sha256": dict(B.EXPECTED_ENGINE_SHA256),
        "loader_sha256": B.EXPECTED_LOADER_SHA256,
        "evaluator_sha256": B.EXPECTED_EVALUATOR_SHA256,
        "candidate": {"entry": "main.py", "callable": "agent", "sha256": identity["main_py_sha256"]},
        "opponents": {
            opponent: {
                "entry": "main.py",
                "callable": "agent",
                "sha256": B.EXPECTED_OPPONENT_SHA256[opponent],
            }
        },
        "seeds": [seed],
        "agent_rng_seed": B.EXPECTED_AGENT_RNG_SEED,
        "python": "test",
        "platform": "test",
        "resource_usage": {},
        "limits": dict(B.EXPECTED_LIMITS),
        "method": "synthetic contract fixture",
        "summary": {
            opponent: {
                "scheduled": 2,
                "completed": 2,
                "failed": 0,
                "wins": 2 if margin > 0 else 0,
                "ties": 2 if margin == 0 else 0,
                "losses": 2 if margin < 0 else 0,
                "mean_margin": margin,
                "candidate_failures": 0,
                "opponent_failures": 0,
            }
        },
        "games": games,
        "reproducibility": None,
    }


class ExtractionAndIsolationTests(unittest.TestCase):
    def test_safe_extract_rejects_parent_escape(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            archive = Path(td) / "bad.tar.gz"
            with tarfile.open(archive, "w:gz") as bundle:
                info = tarfile.TarInfo("../escape.txt")
                payload = b"escape"
                info.size = len(payload)
                bundle.addfile(info, io.BytesIO(payload))
            with self.assertRaisesRegex(ValueError, "escapes destination"):
                B.safe_extract(archive, Path(td) / "out")

    def test_safe_extract_rejects_links(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            archive = Path(td) / "bad.tar.gz"
            with tarfile.open(archive, "w:gz") as bundle:
                info = tarfile.TarInfo("link")
                info.type = tarfile.SYMTYPE
                info.linkname = "main.py"
                bundle.addfile(info)
            with self.assertRaisesRegex(ValueError, "links are not accepted"):
                B.safe_extract(archive, Path(td) / "out")

    def test_prepare_variants_changes_only_config_and_preserves_baseline_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source"
            source.mkdir()
            (source / "main.py").write_text("def agent(obs, cfg=None):\n    return {}\n", encoding="utf-8")
            baseline_config = b'{\n  "redundant_hire": true,\n  "market_pressure": true\n}\n'
            (source / "TITAN-CONFIG.json").write_bytes(baseline_config)
            (source / "dependency.py").write_text("VALUE = 7\n", encoding="utf-8")
            archive = root / "source.tar.gz"
            with tarfile.open(archive, "w:gz") as bundle:
                for path in sorted(source.iterdir()):
                    bundle.add(path, arcname=path.name)
            with mock.patch.object(B, "EXPECTED_SOURCE_SHA256", B.sha256(archive)):
                proof = B.prepare_variants(archive, root / "variants")
            self.assertEqual((root / "variants/baseline/TITAN-CONFIG.json").read_bytes(), baseline_config)
            self.assertEqual(proof["variants"]["baseline"]["changed_from_baseline"], [])
            for name in ("no_redundant_hire", "no_market_pressure", "no_legacy_features"):
                row = proof["variants"][name]
                self.assertEqual(row["changed_from_baseline"], ["TITAN-CONFIG.json"])
                self.assertTrue(row["all_non_config_bytes_equal"])
                self.assertEqual(row["main_py_sha256"], proof["variants"]["baseline"]["main_py_sha256"])


class ReportContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.identity = synthetic_identity()
        self.harness = synthetic_harness()
        self.report = synthetic_report(
            opponent="arlene", seed=2609098601, margin=10, identity=self.identity, trace_tag="base"
        )

    def validate(self, report: dict | None = None) -> None:
        B.validate_report_contract(
            report or self.report,
            variant="baseline",
            opponent="arlene",
            seed=2609098601,
            identity=self.identity,
            harness_identity=self.harness,
        )

    def test_accepts_exact_two_seat_report(self) -> None:
        self.validate()

    def test_rejects_engine_drift(self) -> None:
        report = copy.deepcopy(self.report)
        report["engine_ref"] = "0" * 40
        with self.assertRaisesRegex(ValueError, "engine_ref drift"):
            self.validate(report)

    def test_rejects_duplicate_seat_even_when_count_is_two(self) -> None:
        report = copy.deepcopy(self.report)
        report["games"][1]["candidate_seat"] = 0
        with self.assertRaisesRegex(ValueError, "duplicate game cell"):
            self.validate(report)

    def test_rejects_candidate_hash_drift(self) -> None:
        report = copy.deepcopy(self.report)
        report["candidate"]["sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "candidate entry hash mismatch"):
            self.validate(report)

    def test_rejects_partial_horizon(self) -> None:
        report = copy.deepcopy(self.report)
        report["games"][0]["steps"] = 718
        with self.assertRaisesRegex(ValueError, "horizon mismatch"):
            self.validate(report)

    def test_receipt_detects_report_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "baseline--arlene--2609098601.json"
            write_json(path, self.report)
            receipt = B.make_receipt(
                path,
                variant="baseline",
                opponent="arlene",
                seed=2609098601,
                identity=self.identity,
                harness_identity=self.harness,
            )
            B.validate_receipt(
                receipt,
                path,
                variant="baseline",
                opponent="arlene",
                seed=2609098601,
                identity=self.identity,
                harness_identity=self.harness,
            )
            self.report["games"][0]["scores"][0] += 1
            write_json(path, self.report)
            with self.assertRaisesRegex(ValueError, "receipt mismatch"):
                B.validate_receipt(
                    receipt,
                    path,
                    variant="baseline",
                    opponent="arlene",
                    seed=2609098601,
                    identity=self.identity,
                    harness_identity=self.harness,
                )


class AggregationTests(unittest.TestCase):
    def build_panel(self, root: Path) -> tuple[list[Path], dict, dict]:
        opponent = "arlene"
        seed = 2609098601
        harness = synthetic_harness((opponent,))
        margins = {
            "baseline": 100.0,
            "no_redundant_hire": 98.0,
            "no_market_pressure": 50.0,
            "no_legacy_features": 48.0,
        }
        isolation = {
            "baseline_file_manifest_sha256": "9" * 64,
            "variants": {},
        }
        paths = []
        for index, (variant, margin) in enumerate(margins.items()):
            identity = synthetic_identity(config_sha=f"{index + 1:x}" * 64)
            isolation["variants"][variant] = identity
            report = synthetic_report(
                opponent=opponent,
                seed=seed,
                margin=margin,
                identity=identity,
                trace_tag=variant,
            )
            path = root / f"{variant}--{opponent}--{seed}.json"
            write_json(path, report)
            write_json(
                B.receipt_path(path),
                B.make_receipt(
                    path,
                    variant=variant,
                    opponent=opponent,
                    seed=seed,
                    identity=identity,
                    harness_identity=harness,
                ),
            )
            paths.append(path)
        return paths, isolation, harness

    def test_aggregate_preserves_every_seed_qualified_report(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            paths, isolation, harness = self.build_panel(Path(td))
            result = B.aggregate(
                paths,
                variants=B.VARIANTS,
                opponents=("arlene",),
                seeds=(2609098601,),
                isolation=isolation,
                harness_identity=harness,
            )
            self.assertEqual(len(result["reports"]), 4)
            self.assertIn("baseline/arlene/2609098601", result["reports"])
            self.assertEqual(result["total_completed_games"], 8)
            self.assertEqual(result["decisions"]["market_pressure"]["recommendation"], "keep")
            self.assertEqual(result["decisions"]["market_pressure"]["regression_cause_assessment"], "ruled_out_on_this_panel")

    def test_aggregate_rejects_duplicate_shard(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            paths, isolation, harness = self.build_panel(Path(td))
            with self.assertRaisesRegex(ValueError, "duplicate run shard"):
                B.aggregate(
                    paths + [paths[0]],
                    variants=B.VARIANTS,
                    opponents=("arlene",),
                    seeds=(2609098601,),
                    isolation=isolation,
                    harness_identity=harness,
                )

    def test_aggregate_rejects_missing_shard(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            paths, isolation, harness = self.build_panel(Path(td))
            with self.assertRaisesRegex(ValueError, "run shard mismatch"):
                B.aggregate(
                    paths[:-1],
                    variants=B.VARIANTS,
                    opponents=("arlene",),
                    seeds=(2609098601,),
                    isolation=isolation,
                    harness_identity=harness,
                )

    def test_aggregate_rejects_mislabeled_candidate_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            paths, isolation, harness = self.build_panel(Path(td))
            path = paths[1]
            receipt = json.loads(B.receipt_path(path).read_text(encoding="utf-8"))
            receipt["invocation"]["variant"] = "baseline"
            write_json(B.receipt_path(path), receipt)
            with self.assertRaisesRegex(ValueError, "run receipt mismatch"):
                B.aggregate(
                    paths,
                    variants=B.VARIANTS,
                    opponents=("arlene",),
                    seeds=(2609098601,),
                    isolation=isolation,
                    harness_identity=harness,
                )


class ClassificationTests(unittest.TestCase):
    def test_no_trace_change_is_no_effect(self) -> None:
        row = {"x": {"enabled_margin_effect": {"mean": 0.0}}}
        decision = B.classify_feature([0.0, 0.0], 0, row)
        self.assertEqual(decision["recommendation"], "no_effect_in_panel")

    def test_large_negative_effect_marks_plausible_regression_cause(self) -> None:
        row = {"x": {"enabled_margin_effect": {"mean": -400.0}}}
        decision = B.classify_feature([-500.0, -300.0], 2, row)
        self.assertEqual(decision["recommendation"], "remove")
        self.assertEqual(decision["regression_cause_assessment"], "plausible")


if __name__ == "__main__":
    unittest.main(verbosity=2)
