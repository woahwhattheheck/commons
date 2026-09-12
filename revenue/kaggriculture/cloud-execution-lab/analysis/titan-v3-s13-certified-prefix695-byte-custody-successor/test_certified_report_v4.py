# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import certified_report_v4 as v4

H = "a" * 64
E = "b" * 64
D = "c" * 64
G = "d" * 40


def diag(*, source_seat=0, activation_steps=(), checks=None, matches=None):
    activation_steps = list(activation_steps)
    if matches is None:
        matches = len(activation_steps)
    if checks is None:
        checks = matches
    return {
        "source_seat": source_seat,
        "activation_steps": activation_steps,
        "activation_count": len(activation_steps),
        "certificate_checks": checks,
        "certificate_matches": matches,
        "certificate_donor_head": "cbfff2bec813e2c2609ce9c5819b74669e98c566",
        "certificate_donor_blob": "89a3325eb541ae0e8a81e1e0a426292820f10d98",
        "handoff_step": None,
        "handoff_reason": None,
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


def evaluator(rows, *, candidate_sha, evaluator_sha=E, loader_sha=H):
    return {
        "schema_version": 1,
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
        "seeds": [1],
        "agent_rng_seed": 20260907,
        "python": "3.11.synthetic",
        "platform": "linux",
        "limits": {
            "action_rpc_seconds": 1.0,
            "startup_seconds": 10.0,
            "game_seconds_between_steps": 120.0,
            "remaining_overage_time": 0,
        },
        "method": "Official interpreter with explicit driver; synthetic fixture.",
        "games": rows,
    }


class ByteCustodySuccessorTests(unittest.TestCase):
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

    def documents(self):
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
                "arlene",
                1,
                0,
                [110, 90],
                "g0",
                diag(activation_steps=(24,), checks=1, matches=1),
            ),
            game(
                "arlene",
                1,
                1,
                [90, 100],
                "c1",
                diag(source_seat=0, activation_steps=(), checks=0, matches=0),
            ),
        ]
        return (
            evaluator(control_rows, candidate_sha="5" * 64, evaluator_sha=E),
            evaluator(unsafe_rows, candidate_sha="6" * 64, evaluator_sha=E),
            evaluator(certified_rows, candidate_sha="7" * 64, evaluator_sha=D),
        )

    def paths(self):
        control, unsafe, certified = self.documents()
        return (
            self.write("control.json", control),
            self.write("unsafe.json", unsafe),
            self.write("certified.json", certified),
        )

    def build(self, paths):
        return v4.build_report(
            *paths,
            source_seat=0,
            identities={
                "git_head": G,
                "archive_sha256": "8" * 64,
                "source_manifest_sha256": "9" * 64,
            },
            bindings={"carrier_receipt": self.root / "carrier.json"},
        )

    def test_stable_inputs_preserve_parent_scientific_result(self):
        paths = self.paths()
        parent = v4.v3.build_report(
            *paths,
            source_seat=0,
            identities={
                "git_head": G,
                "archive_sha256": "8" * 64,
                "source_manifest_sha256": "9" * 64,
            },
            bindings={"carrier_receipt": self.root / "carrier.json"},
        )
        result = self.build(paths)
        self.assertEqual(result["schema"], v4.SCHEMA)
        self.assertEqual(result["verdict"], parent["verdict"])
        self.assertEqual(result["v2_report_sha256"], parent["v2_report_sha256"])
        self.assertEqual(result["runtime_diagnostics_sha256"], parent["runtime_diagnostics_sha256"])
        self.assertEqual(result["byte_custody"]["mode"], "single-read-immutable-snapshot")

    def test_swap_immediately_after_read_cannot_divorce_hash_from_provenance(self):
        paths = self.paths()
        certified_path = paths[2]
        original = certified_path.read_bytes()
        replacement = json.loads(original.decode("utf-8"))
        replacement["loader_sha256"] = "f" * 64
        replacement_bytes = json.dumps(replacement, sort_keys=True).encode("utf-8")

        real_read_bytes = Path.read_bytes
        swapped = {"done": False}

        def swap_after_read(path):
            data = real_read_bytes(path)
            if path == certified_path and not swapped["done"]:
                certified_path.write_bytes(replacement_bytes)
                swapped["done"] = True
            return data

        with mock.patch.object(Path, "read_bytes", new=swap_after_read):
            result = self.build(paths)

        self.assertTrue(swapped["done"])
        self.assertNotEqual(certified_path.read_bytes(), original)
        self.assertEqual(result["verdict"], "CERTIFIED_SURVIVOR")
        self.assertEqual(
            result["input_reports"]["certified_prefix"]["sha256"],
            hashlib.sha256(original).hexdigest(),
        )
        self.assertEqual(
            result["evaluator_provenance"]["certified_prefix"]["loader_sha256"],
            H,
        )

    def test_swap_after_validation_cannot_change_inherited_v2_math(self):
        paths = self.paths()
        certified_path = paths[2]
        original = certified_path.read_bytes()
        replacement = json.loads(original.decode("utf-8"))
        replacement["games"][0]["scores"] = [1, 90]
        replacement_bytes = json.dumps(replacement, sort_keys=True).encode("utf-8")

        original_validate = v4.v3._validate_activation_bounds
        swapped = {"done": False}

        def validate_then_swap(certified, source_seat):
            original_validate(certified, source_seat)
            if not swapped["done"]:
                certified_path.write_bytes(replacement_bytes)
                swapped["done"] = True

        with mock.patch.object(
            v4.v3,
            "_validate_activation_bounds",
            side_effect=validate_then_swap,
        ):
            result = self.build(paths)

        self.assertTrue(swapped["done"])
        self.assertEqual(result["verdict"], "CERTIFIED_SURVIVOR")
        self.assertTrue(result["source_seat_safe"])
        source_row = next(
            row for row in result["certified_prefix"]["rows"] if row["seat"] == 0
        )
        self.assertEqual(source_row["own_cash"], 110.0)
        self.assertEqual(
            result["input_reports"]["certified_prefix"]["sha256"],
            hashlib.sha256(original).hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()
