# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import certified_report_v3 as report_module
from certified_report_v3 import CertifiedReportError, V2_BLOB, V2_PATH, build_report, git_blob_sha


H = "a" * 64
E = "b" * 64
D = "c" * 64
G = "d" * 40


def diag(*, source_seat=0, steps=(), checks=None, matches=None):
    steps = list(steps)
    if matches is None:
        matches = len(steps)
    if checks is None:
        checks = matches
    return {
        "mode": "post24_full",
        "certificate_mode": "full",
        "source_seat": source_seat,
        "start_step": 24,
        "active": True,
        "handoff_step": None,
        "handoff_reason": None,
        "certificate_checks": checks,
        "certificate_matches": matches,
        "activation_count": len(steps),
        "activation_steps": steps,
        "certificate_donor_head": "cbfff2bec813e2c2609ce9c5819b74669e98c566",
        "certificate_donor_blob": "89a3325eb541ae0e8a81e1e0a426292820f10d98",
        "market_outcome_claim": False,
    }


def game(opponent, seed, seat, scores, trace, runtime_diag=None, *, steps=100, episode_steps=696):
    actors = [{}, {}]
    if runtime_diag is not None:
        actors[seat]["agent_diagnostics"] = runtime_diag
    return {
        "status": "complete",
        "failure": None,
        "opponent": opponent,
        "seed": seed,
        "candidate_seat": seat,
        "scores": scores,
        "trace_sha256": trace,
        "actors": actors,
        "steps": steps,
        "episode_steps": episode_steps,
    }


def evaluator(rows, *, candidate_sha, evaluator_sha=E, loader_sha=H, seeds=(1,)):
    return {
        "schema_version": 1,
        "invocation_id": "synthetic",
        "engine_ref": "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c",
        "engine_sha256": {
            "kaggriculture.py": "1" * 64,
            "kaggriculture.json": "2" * 64,
            "utils.py": "3" * 64,
        },
        "loader_sha256": loader_sha,
        "evaluator_sha256": evaluator_sha,
        "candidate": {"entry": "agent.py", "callable": "agent", "sha256": candidate_sha},
        "opponents": {
            "arlene": {"entry": "opponent.py", "callable": "agent", "sha256": "4" * 64}
        },
        "seeds": list(seeds),
        "agent_rng_seed": 20260907,
        "python": "3.11.synthetic",
        "platform": "linux",
        "resource_usage": {"cpu_seconds": 0.1, "peak_rss_kib": 1},
        "limits": {
            "action_rpc_seconds": 1.0,
            "startup_seconds": 10.0,
            "game_seconds_between_steps": 120.0,
            "remaining_overage_time": 0,
        },
        "method": "Official interpreter with explicit driver; synthetic fixture.",
        "summary": {},
        "games": rows,
        "reproducibility": None,
    }


class ProvenanceSuccessorTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        (self.root / "carrier.json").write_text('{"carrier":1}\n', encoding="utf-8")

    def tearDown(self):
        self.directory.cleanup()

    def write(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
        return path

    def inputs(self, *, activation_steps=(24,), certified_steps=100):
        control_rows = [
            game("arlene", 1, 0, [100, 90], "c0"),
            game("arlene", 1, 1, [90, 100], "c1"),
        ]
        unsafe_rows = [
            game("arlene", 1, 0, [120, 90], "u0"),
            game("arlene", 1, 1, [90, 120], "u1"),
        ]
        certified_rows = [
            game(
                "arlene", 1, 0, [110, 90], "g0",
                diag(steps=activation_steps, checks=max(1, len(activation_steps)), matches=max(1, len(activation_steps))),
                steps=certified_steps,
            ),
            game(
                "arlene", 1, 1, [90, 100], "c1",
                diag(source_seat=0, steps=(), checks=0, matches=0),
                steps=certified_steps,
            ),
        ]
        control = evaluator(control_rows, candidate_sha="5" * 64, evaluator_sha=E)
        unsafe = evaluator(unsafe_rows, candidate_sha="6" * 64, evaluator_sha=E)
        certified = evaluator(certified_rows, candidate_sha="7" * 64, evaluator_sha=D)
        return control, unsafe, certified

    def build(self, *, activation_steps=(24,), certified_steps=100, mutate=None):
        control, unsafe, certified = self.inputs(
            activation_steps=activation_steps,
            certified_steps=certified_steps,
        )
        if mutate is not None:
            mutate(control, unsafe, certified)
        control_path = self.write("control.json", control)
        unsafe_path = self.write("unsafe.json", unsafe)
        certified_path = self.write("certified.json", certified)
        result = build_report(
            control_path,
            unsafe_path,
            certified_path,
            source_seat=0,
            identities={
                "git_head": G,
                "archive_sha256": "8" * 64,
                "source_manifest_sha256": "9" * 64,
            },
            bindings={"carrier_receipt": self.root / "carrier.json"},
        )
        return result, (control_path, unsafe_path, certified_path)

    def test_v2_builder_is_exact_blob(self):
        self.assertEqual(git_blob_sha(V2_PATH.read_bytes()), V2_BLOB)

    def test_matching_provenance_and_raw_hashes_are_emitted(self):
        result, paths = self.build()
        self.assertEqual(result["schema"], "titan-v3-s13-certified-prefix-report/v3")
        self.assertEqual(result["verdict"], "CERTIFIED_SURVIVOR")
        self.assertEqual(result["identities"]["git_head"], G)
        self.assertEqual(result["evaluator_provenance"]["control"]["evaluator_sha256"], E)
        self.assertEqual(result["evaluator_provenance"]["certified_prefix"]["evaluator_sha256"], D)
        for label, path in zip(("control", "unsafe_prefix", "certified_prefix"), paths):
            self.assertEqual(
                result["input_reports"][label]["sha256"],
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        self.assertIn("carrier_receipt", result["companion_bindings"])

    def test_replaced_path_after_validation_cannot_change_captured_verdict(self):
        control, unsafe, certified = self.inputs()
        control_path = self.write("control.json", control)
        unsafe_path = self.write("unsafe.json", unsafe)
        certified_path = self.write("certified.json", certified)
        certified_bytes = certified_path.read_bytes()
        certified_digest = hashlib.sha256(certified_bytes).hexdigest()

        original_validate = report_module._validate_cross_arm

        def validate_then_replace(provenance):
            original_validate(provenance)
            certified_path.write_text("{}\n", encoding="utf-8")

        report_module._validate_cross_arm = validate_then_replace
        try:
            result = build_report(
                control_path,
                unsafe_path,
                certified_path,
                source_seat=0,
                identities={
                    "git_head": G,
                    "archive_sha256": "8" * 64,
                    "source_manifest_sha256": "9" * 64,
                },
                bindings={"carrier_receipt": self.root / "carrier.json"},
            )
        finally:
            report_module._validate_cross_arm = original_validate

        self.assertEqual(result["verdict"], "CERTIFIED_SURVIVOR")
        self.assertEqual(
            result["input_reports"]["certified_prefix"]["sha256"],
            certified_digest,
        )
        self.assertNotEqual(hashlib.sha256(certified_path.read_bytes()).hexdigest(), certified_digest)

    def test_altered_cross_arm_loader_fails_closed(self):
        def mutate(_control, _unsafe, certified):
            certified["loader_sha256"] = "f" * 64
        with self.assertRaisesRegex(CertifiedReportError, "loader_sha256"):
            self.build(mutate=mutate)

    def test_altered_cross_arm_seed_bank_fails_closed(self):
        def mutate(_control, _unsafe, certified):
            certified["seeds"] = [2]
            certified["games"][0]["seed"] = 2
            certified["games"][1]["seed"] = 2
        with self.assertRaisesRegex(CertifiedReportError, "seeds"):
            self.build(mutate=mutate)

    def test_control_and_unsafe_evaluator_must_match(self):
        def mutate(_control, unsafe, _certified):
            unsafe["evaluator_sha256"] = "e" * 64
        with self.assertRaisesRegex(CertifiedReportError, "evaluator identity"):
            self.build(mutate=mutate)

    def test_impossible_activation_step_fails_closed(self):
        with self.assertRaisesRegex(CertifiedReportError, "outside executed game bounds"):
            self.build(activation_steps=(100,), certified_steps=100)

    def test_bad_package_identity_fails_closed(self):
        control, unsafe, certified = self.inputs()
        control_path = self.write("control.json", control)
        unsafe_path = self.write("unsafe.json", unsafe)
        certified_path = self.write("certified.json", certified)
        with self.assertRaisesRegex(CertifiedReportError, "git_head"):
            build_report(
                control_path,
                unsafe_path,
                certified_path,
                source_seat=0,
                identities={
                    "git_head": "not-a-sha",
                    "archive_sha256": "8" * 64,
                    "source_manifest_sha256": "9" * 64,
                },
                bindings={"carrier_receipt": self.root / "carrier.json"},
            )


if __name__ == "__main__":
    unittest.main()
