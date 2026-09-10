# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "titan_release_admission_guard", HERE / "release_admission" / "guard.py"
)
assert SPEC and SPEC.loader
admission = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(admission)

LAB = Path("revenue/kaggriculture/cloud-execution-lab")
V1_BYTES = b"synthetic-measured-v1-archive\n"
CURRENT_BYTES = b"synthetic-unmeasured-current-archive\n"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_manifest(
    *,
    archive_sha: str,
    new_full_games: int = 0,
    release_admission: dict | None = None,
) -> bytes:
    value = {
        "current": {
            "archive": "exports/titan-current.tar.gz",
            "configuration": "TITAN-CONFIG.json",
            "entrypoint": "main.py::agent",
            "manifest": "runtime/integrated-selected/CURRENT-SOURCE.json",
            "receipt": "runtime/integrated-selected/CURRENT-ARCHIVE.json",
        },
        "game_evidence_for_this_archive": {
            "archive_sha256": archive_sha,
            "new_full_games": new_full_games,
        },
    }
    if release_admission is not None:
        value["release_admission"] = release_admission
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


SOURCE_BYTES = source_manifest(archive_sha=digest(CURRENT_BYTES))


def write(root: Path, relative: Path, data: bytes | str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        path.write_text(data, encoding="utf-8")
    else:
        path.write_bytes(data)
    return path


def write_json(root: Path, relative: Path, value) -> Path:
    return write(root, relative, json.dumps(value, indent=2, sort_keys=True) + "\n")


def policy(v1_sha: str) -> dict:
    return {
        "schema_version": 1,
        "pointer_path": str(LAB / "runtime/integrated-selected/CURRENT-ARCHIVE.json"),
        "champion_path": str(LAB / "release_admission/CHAMPION.json"),
        "gate_tool_path": str(LAB / "titan-v3-paired-game-gate/gate.py"),
        "bootstrap_champion": {
            "champion_name": "titan-v1-submitted",
            "archive_path": f"exports/historical/titan-{v1_sha}.tar.gz",
            "archive_sha256": v1_sha,
            "status": "grandfathered_submitted_baseline",
        },
        "minimum_grid": {"seeds": 2, "opponents": 2, "seats": [0, 1], "expected_cells": 8},
        "required_checks": [
            "mean_own_delta",
            "median_own_delta",
            "mean_margin_delta",
            "positive_cell_fraction",
            "positive_pair_fraction",
            "result_regressions",
            "baseline_win_regressions",
            "new_losses",
            "negative_opponent_strata",
            "negative_seat_strata",
            "any_score_change",
        ],
    }


def pointer(archive: bytes = CURRENT_BYTES, source: bytes = SOURCE_BYTES) -> dict:
    return {
        "path": "exports/titan-current.tar.gz",
        "entrypoint": "main.py::agent",
        "config": "TITAN-CONFIG.json",
        "sha256": digest(archive),
        "bytes": len(archive),
        "runtime_files": 3,
        "source_manifest": "runtime/integrated-selected/CURRENT-SOURCE.json",
        "source_manifest_sha256": digest(source),
    }


def bootstrap_champion(v1_sha: str) -> dict:
    return {
        "schema_version": 1,
        "champion_name": "titan-v1-submitted",
        "archive_path": f"exports/historical/titan-{v1_sha}.tar.gz",
        "archive_sha256": v1_sha,
        "source_manifest_sha256": None,
        "previous_champion_sha256": None,
        "promotion_evidence_dir": None,
        "status": "grandfathered_submitted_baseline",
    }


class RepoPair:
    def __init__(self, root: Path):
        self.base = root / "base"
        self.head = root / "head"
        self.v1_sha = digest(V1_BYTES)
        for checkout in (self.base, self.head):
            write(checkout, LAB / "exports/titan-current.tar.gz", CURRENT_BYTES)
            write(checkout, LAB / "runtime/integrated-selected/CURRENT-SOURCE.json", SOURCE_BYTES)
            write(
                checkout,
                LAB / f"exports/historical/titan-{self.v1_sha}.tar.gz",
                V1_BYTES,
            )
            write_json(checkout, LAB / "runtime/integrated-selected/CURRENT-ARCHIVE.json", pointer())

    def install(self) -> None:
        for checkout in (self.base, self.head):
            write_json(checkout, LAB / "release_admission/POLICY.json", policy(self.v1_sha))
            write_json(
                checkout,
                LAB / "release_admission/CHAMPION.json",
                bootstrap_champion(self.v1_sha),
            )

    def promote(self) -> tuple[dict, bytes, bytes]:
        candidate = b"synthetic-measured-v3-archive\n"
        candidate_sha = digest(candidate)
        evidence_rel = Path("release_admission/evidence") / candidate_sha
        source = source_manifest(
            archive_sha=candidate_sha,
            new_full_games=8,
            release_admission={
                "schema_version": 1,
                "mode": "measured_promotion",
                "archive_sha256": candidate_sha,
                "previous_pointer_sha256": digest(CURRENT_BYTES),
                "champion_sha256": candidate_sha,
                "evidence_dir": evidence_rel.as_posix(),
            },
        )
        write(self.head, LAB / "exports/titan-current.tar.gz", candidate)
        write(self.head, LAB / f"exports/historical/titan-{candidate_sha}.tar.gz", candidate)
        write(self.head, LAB / "runtime/integrated-selected/CURRENT-SOURCE.json", source)
        write_json(
            self.head,
            LAB / "runtime/integrated-selected/CURRENT-ARCHIVE.json",
            pointer(candidate, source),
        )
        champion = {
            "schema_version": 1,
            "champion_name": "synthetic-v3",
            "archive_path": f"exports/historical/titan-{candidate_sha}.tar.gz",
            "archive_sha256": candidate_sha,
            "source_manifest_sha256": digest(source),
            "previous_champion_sha256": self.v1_sha,
            "promotion_evidence_dir": evidence_rel.as_posix(),
            "status": "measured_promotion",
        }
        write_json(self.head, LAB / "release_admission/CHAMPION.json", champion)

        inputs = {
            "contract": b'{"synthetic":"contract"}\n',
            "evidence": b'{"synthetic":"provenance"}\n',
            "baseline_games": b'{"synthetic":"baseline"}\n',
            "candidate_games": b'{"synthetic":"candidate"}\n',
        }
        filenames = {
            "contract": "CONTRACT.json",
            "evidence": "PROVENANCE.json",
            "baseline_games": "baseline.GAMES.jsonl",
            "candidate_games": "candidate.GAMES.jsonl",
        }
        for key, payload in inputs.items():
            write(self.head, LAB / evidence_rel / filenames[key], payload)

        checks = [
            {"name": name, "actual": 1, "op": ">=", "threshold": 0, "pass": True}
            for name in policy(self.v1_sha)["required_checks"]
        ]
        report = {
            "schema_version": 1,
            "verdict": "PROMOTE",
            "valid": True,
            "panel_id": "synthetic-complete-panel",
            "baseline_name": "synthetic-v1",
            "candidate_name": "synthetic-v3",
            "input_sha256": {key: digest(value) for key, value in inputs.items()},
            "input_bytes": {key: len(value) for key, value in inputs.items()},
            "input_binding": "single-open private snapshots; hashes cover exactly parsed bytes",
            "provenance": {
                "engine_commit": "a" * 40,
                "engine_sha256": "b" * 64,
                "runner_commit": "c" * 40,
                "runner_sha256": "d" * 64,
                "baseline_artifact_sha256": self.v1_sha,
                "candidate_artifact_sha256": candidate_sha,
            },
            "exact_command": "synthetic test only",
            "grid": {
                "seeds": [101, 102],
                "opponents": ["arlene", "apex"],
                "seats": [0, 1],
                "expected_cells": 8,
                "observed_baseline_cells": 8,
                "observed_candidate_cells": 8,
            },
            "policy": {"synthetic": True},
            "checks": checks,
            "metrics": {"synthetic": True},
        }
        write_json(self.head, LAB / evidence_rel / "GATE.json", report)
        return report, candidate, source


class AdmissionTests(unittest.TestCase):
    def test_bootstrap_installs_v1_ledger_without_pointer_change(self):
        with tempfile.TemporaryDirectory() as td:
            pair = RepoPair(Path(td))
            write_json(pair.head, LAB / "release_admission/POLICY.json", policy(pair.v1_sha))
            write_json(
                pair.head,
                LAB / "release_admission/CHAMPION.json",
                bootstrap_champion(pair.v1_sha),
            )
            result = admission.evaluate_transition(pair.base, pair.head)
        self.assertEqual(result["verdict"], "BOOTSTRAP_MEASURED_BASELINE")

    def test_bootstrap_cannot_change_pointer(self):
        with tempfile.TemporaryDirectory() as td:
            pair = RepoPair(Path(td))
            write_json(pair.head, LAB / "release_admission/POLICY.json", policy(pair.v1_sha))
            write_json(pair.head, LAB / "release_admission/CHAMPION.json", bootstrap_champion(pair.v1_sha))
            changed = b"changed-during-bootstrap"
            write(pair.head, LAB / "exports/titan-current.tar.gz", changed)
            write_json(pair.head, LAB / "runtime/integrated-selected/CURRENT-ARCHIVE.json", pointer(changed))
            with self.assertRaisesRegex(admission.AdmissionError, "cannot change while.*bootstrapped"):
                admission.evaluate_transition(pair.base, pair.head)

    def test_unchanged_release_passes(self):
        with tempfile.TemporaryDirectory() as td:
            pair = RepoPair(Path(td))
            pair.install()
            result = admission.evaluate_transition(pair.base, pair.head)
        self.assertEqual(result["verdict"], "UNCHANGED_RELEASE")

    def test_policy_may_only_strengthen_without_release_change(self):
        with tempfile.TemporaryDirectory() as td:
            pair = RepoPair(Path(td))
            pair.install()
            stronger = policy(pair.v1_sha)
            stronger["minimum_grid"]["seeds"] = 3
            stronger["minimum_grid"]["expected_cells"] = 12
            stronger["required_checks"].append("worst_cell_own_delta")
            write_json(pair.head, LAB / "release_admission/POLICY.json", stronger)
            result = admission.evaluate_transition(pair.base, pair.head)
        self.assertTrue(result["policy_strengthened"])

    def test_policy_weakening_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            pair = RepoPair(Path(td))
            pair.install()
            weaker = policy(pair.v1_sha)
            weaker["minimum_grid"]["seeds"] = 1
            write_json(pair.head, LAB / "release_admission/POLICY.json", weaker)
            with self.assertRaisesRegex(admission.AdmissionError, "cannot be weakened"):
                admission.evaluate_transition(pair.base, pair.head)

    def test_champion_only_mutation_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            pair = RepoPair(Path(td))
            pair.install()
            value = bootstrap_champion(pair.v1_sha)
            value["champion_name"] = "renamed-without-transition"
            write_json(pair.head, LAB / "release_admission/CHAMPION.json", value)
            with self.assertRaisesRegex(admission.AdmissionError, "cannot change without"):
                admission.evaluate_transition(pair.base, pair.head)

    def test_exact_rollback_to_measured_champion_passes_without_new_claim(self):
        with tempfile.TemporaryDirectory() as td:
            pair = RepoPair(Path(td))
            pair.install()
            rollback_source = source_manifest(
                archive_sha=pair.v1_sha,
                release_admission={
                    "schema_version": 1,
                    "mode": "rollback_to_measured_champion",
                    "archive_sha256": pair.v1_sha,
                    "previous_pointer_sha256": digest(CURRENT_BYTES),
                    "champion_sha256": pair.v1_sha,
                    "evidence_dir": None,
                },
            )
            write(pair.head, LAB / "exports/titan-current.tar.gz", V1_BYTES)
            write(
                pair.head,
                LAB / "runtime/integrated-selected/CURRENT-SOURCE.json",
                rollback_source,
            )
            write_json(
                pair.head,
                LAB / "runtime/integrated-selected/CURRENT-ARCHIVE.json",
                pointer(V1_BYTES, rollback_source),
            )
            result = admission.evaluate_transition(pair.base, pair.head)
        self.assertEqual(result["verdict"], "ROLLBACK_TO_MEASURED_CHAMPION")

    def test_pointer_change_without_ledger_promotion_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            pair = RepoPair(Path(td))
            pair.install()
            changed = b"unmeasured-candidate\n"
            write(pair.head, LAB / "exports/titan-current.tar.gz", changed)
            write_json(pair.head, LAB / "runtime/integrated-selected/CURRENT-ARCHIVE.json", pointer(changed))
            with self.assertRaisesRegex(admission.AdmissionError, "requires a measured_promotion"):
                admission.evaluate_transition(pair.base, pair.head)

    def test_complete_hash_bound_promotion_passes(self):
        with tempfile.TemporaryDirectory() as td:
            pair = RepoPair(Path(td))
            pair.install()
            report, _, _ = pair.promote()
            result = admission.evaluate_transition(
                pair.base,
                pair.head,
                gate_runner=lambda *_args: deepcopy(report),
            )
        self.assertEqual(result["verdict"], "PROMOTE_MEASURED_CHAMPION")
        self.assertEqual(result["expected_cells"], 8)

    def test_pointer_entrypoint_cannot_be_substituted(self):
        with tempfile.TemporaryDirectory() as td:
            pair = RepoPair(Path(td))
            pair.install()
            value = pointer()
            value["entrypoint"] = "alternate.py::agent"
            write_json(pair.head, LAB / "runtime/integrated-selected/CURRENT-ARCHIVE.json", value)
            with self.assertRaisesRegex(admission.AdmissionError, "entrypoint must equal"):
                admission.evaluate_transition(pair.base, pair.head)

    def test_policy_change_cannot_ride_with_promotion(self):
        with tempfile.TemporaryDirectory() as td:
            pair = RepoPair(Path(td))
            pair.install()
            report, _, _ = pair.promote()
            stronger = policy(pair.v1_sha)
            stronger["minimum_grid"]["seeds"] = 3
            stronger["minimum_grid"]["expected_cells"] = 12
            write_json(pair.head, LAB / "release_admission/POLICY.json", stronger)
            with self.assertRaisesRegex(admission.AdmissionError, "same proposal"):
                admission.evaluate_transition(
                    pair.base, pair.head, gate_runner=lambda *_args: deepcopy(report)
                )

    def test_promotion_manifest_requires_explicit_admission_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            pair = RepoPair(Path(td))
            pair.install()
            report, candidate, _ = pair.promote()
            source = source_manifest(
                archive_sha=report["provenance"]["candidate_artifact_sha256"],
                new_full_games=8,
            )
            write(pair.head, LAB / "runtime/integrated-selected/CURRENT-SOURCE.json", source)
            write_json(
                pair.head,
                LAB / "runtime/integrated-selected/CURRENT-ARCHIVE.json",
                pointer(candidate, source),
            )
            champion = json.loads(
                (pair.head / LAB / "release_admission/CHAMPION.json").read_text(encoding="utf-8")
            )
            champion["source_manifest_sha256"] = digest(source)
            write_json(pair.head, LAB / "release_admission/CHAMPION.json", champion)
            with self.assertRaisesRegex(admission.AdmissionError, "must contain release_admission"):
                admission.evaluate_transition(
                    pair.base, pair.head, gate_runner=lambda *_args: deepcopy(report)
                )

    def test_promotion_manifest_game_count_must_cover_panel(self):
        with tempfile.TemporaryDirectory() as td:
            pair = RepoPair(Path(td))
            pair.install()
            report, candidate, _ = pair.promote()
            candidate_sha = report["provenance"]["candidate_artifact_sha256"]
            evidence_dir = f"release_admission/evidence/{candidate_sha}"
            source = source_manifest(
                archive_sha=candidate_sha,
                new_full_games=7,
                release_admission={
                    "schema_version": 1,
                    "mode": "measured_promotion",
                    "archive_sha256": candidate_sha,
                    "previous_pointer_sha256": digest(CURRENT_BYTES),
                    "champion_sha256": candidate_sha,
                    "evidence_dir": evidence_dir,
                },
            )
            write(pair.head, LAB / "runtime/integrated-selected/CURRENT-SOURCE.json", source)
            write_json(
                pair.head,
                LAB / "runtime/integrated-selected/CURRENT-ARCHIVE.json",
                pointer(candidate, source),
            )
            champion = json.loads(
                (pair.head / LAB / "release_admission/CHAMPION.json").read_text(encoding="utf-8")
            )
            champion["source_manifest_sha256"] = digest(source)
            write_json(pair.head, LAB / "release_admission/CHAMPION.json", champion)
            with self.assertRaisesRegex(admission.AdmissionError, "new_full_games is below"):
                admission.evaluate_transition(
                    pair.base, pair.head, gate_runner=lambda *_args: deepcopy(report)
                )

    def test_rejected_gate_cannot_promote(self):
        with tempfile.TemporaryDirectory() as td:
            pair = RepoPair(Path(td))
            pair.install()
            report, _, _ = pair.promote()
            report["verdict"] = "REJECT"
            candidate_sha = report["provenance"]["candidate_artifact_sha256"]
            write_json(
                pair.head,
                LAB / "release_admission/evidence" / candidate_sha / "GATE.json",
                report,
            )
            with self.assertRaisesRegex(admission.AdmissionError, "verdict=PROMOTE"):
                admission.evaluate_transition(pair.base, pair.head, gate_runner=lambda *_: report)

    def test_wrong_baseline_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            pair = RepoPair(Path(td))
            pair.install()
            report, _, _ = pair.promote()
            report["provenance"]["baseline_artifact_sha256"] = "f" * 64
            candidate_sha = report["provenance"]["candidate_artifact_sha256"]
            write_json(pair.head, LAB / "release_admission/evidence" / candidate_sha / "GATE.json", report)
            with self.assertRaisesRegex(admission.AdmissionError, "baseline artifact"):
                admission.evaluate_transition(pair.base, pair.head, gate_runner=lambda *_: report)

    def test_malformed_runner_commit_identity_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            pair = RepoPair(Path(td))
            pair.install()
            report, _, _ = pair.promote()
            report["provenance"]["runner_commit"] = "not-a-git-object"
            candidate_sha = report["provenance"]["candidate_artifact_sha256"]
            write_json(pair.head, LAB / "release_admission/evidence" / candidate_sha / "GATE.json", report)
            with self.assertRaisesRegex(admission.AdmissionError, "40 or 64 hexadecimal"):
                admission.evaluate_transition(pair.base, pair.head, gate_runner=lambda *_: report)

    def test_incomplete_grid_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            pair = RepoPair(Path(td))
            pair.install()
            report, _, _ = pair.promote()
            report["grid"]["observed_candidate_cells"] = 7
            candidate_sha = report["provenance"]["candidate_artifact_sha256"]
            write_json(pair.head, LAB / "release_admission/evidence" / candidate_sha / "GATE.json", report)
            with self.assertRaisesRegex(admission.AdmissionError, "complete baseline/candidate grid"):
                admission.evaluate_transition(pair.base, pair.head, gate_runner=lambda *_: report)

    def test_missing_second_seat_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            pair = RepoPair(Path(td))
            pair.install()
            report, _, _ = pair.promote()
            report["grid"].update(seats=[0], expected_cells=4, observed_baseline_cells=4, observed_candidate_cells=4)
            candidate_sha = report["provenance"]["candidate_artifact_sha256"]
            write_json(pair.head, LAB / "release_admission/evidence" / candidate_sha / "GATE.json", report)
            with self.assertRaisesRegex(admission.AdmissionError, "both candidate seats"):
                admission.evaluate_transition(pair.base, pair.head, gate_runner=lambda *_: report)

    def test_missing_required_check_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            pair = RepoPair(Path(td))
            pair.install()
            report, _, _ = pair.promote()
            report["checks"] = [
                check for check in report["checks"] if check["name"] != "baseline_win_regressions"
            ]
            candidate_sha = report["provenance"]["candidate_artifact_sha256"]
            write_json(pair.head, LAB / "release_admission/evidence" / candidate_sha / "GATE.json", report)
            with self.assertRaisesRegex(admission.AdmissionError, "missing required checks"):
                admission.evaluate_transition(pair.base, pair.head, gate_runner=lambda *_: report)

    def test_failed_check_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            pair = RepoPair(Path(td))
            pair.install()
            report, _, _ = pair.promote()
            report["checks"][0]["pass"] = False
            candidate_sha = report["provenance"]["candidate_artifact_sha256"]
            write_json(pair.head, LAB / "release_admission/evidence" / candidate_sha / "GATE.json", report)
            with self.assertRaisesRegex(admission.AdmissionError, "did not pass"):
                admission.evaluate_transition(pair.base, pair.head, gate_runner=lambda *_: report)

    def test_evidence_digest_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            pair = RepoPair(Path(td))
            pair.install()
            report, _, _ = pair.promote()
            candidate_sha = report["provenance"]["candidate_artifact_sha256"]
            write(
                pair.head,
                LAB / "release_admission/evidence" / candidate_sha / "candidate.GAMES.jsonl",
                b"tampered\n",
            )
            with self.assertRaisesRegex(admission.AdmissionError, "digest mismatch"):
                admission.evaluate_transition(pair.base, pair.head, gate_runner=lambda *_: report)

    def test_archive_digest_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            pair = RepoPair(Path(td))
            pair.install()
            write(pair.head, LAB / "exports/titan-current.tar.gz", b"tampered\n")
            with self.assertRaisesRegex(admission.AdmissionError, "archive size mismatch|archive SHA-256 mismatch"):
                admission.evaluate_transition(pair.base, pair.head)

    def test_source_manifest_digest_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            pair = RepoPair(Path(td))
            pair.install()
            write(pair.head, LAB / "runtime/integrated-selected/CURRENT-SOURCE.json", b"tampered\n")
            with self.assertRaisesRegex(admission.AdmissionError, "source-manifest SHA-256 mismatch"):
                admission.evaluate_transition(pair.base, pair.head)

    def test_evidence_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            pair = RepoPair(Path(td))
            pair.install()
            report, _, _ = pair.promote()
            value = json.loads(
                (pair.head / LAB / "release_admission/CHAMPION.json").read_text(encoding="utf-8")
            )
            value["promotion_evidence_dir"] = "../escape"
            write_json(pair.head, LAB / "release_admission/CHAMPION.json", value)
            with self.assertRaisesRegex(admission.AdmissionError, "unsafe relative path"):
                admission.evaluate_transition(pair.base, pair.head, gate_runner=lambda *_: report)

    def test_symlinked_champion_archive_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            pair = RepoPair(Path(td))
            pair.install()
            path = pair.head / LAB / f"exports/historical/titan-{pair.v1_sha}.tar.gz"
            path.unlink()
            path.symlink_to(pair.head / LAB / "exports/titan-current.tar.gz")
            with self.assertRaisesRegex(admission.AdmissionError, "symbolic links"):
                admission.evaluate_transition(pair.base, pair.head)

    def test_duplicate_json_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            pair = RepoPair(Path(td))
            pair.install()
            target = pair.head / LAB / "release_admission/POLICY.json"
            target.write_text('{"schema_version":1,"schema_version":1}\n', encoding="utf-8")
            with self.assertRaisesRegex(admission.AdmissionError, "duplicate JSON object key"):
                admission.evaluate_transition(pair.base, pair.head)

    def test_hardened_gate_input_binding_is_required(self):
        with tempfile.TemporaryDirectory() as td:
            pair = RepoPair(Path(td))
            pair.install()
            report, _, _ = pair.promote()
            report["input_binding"] = "live paths hashed before parse"
            evidence_dir = json.loads((pair.head / LAB / "release_admission/CHAMPION.json").read_text())["promotion_evidence_dir"]
            write_json(pair.head, LAB / evidence_dir / "GATE.json", report)
            with self.assertRaisesRegex(admission.AdmissionError, "hardened snapshot contract"):
                admission.evaluate_transition(pair.base, pair.head, gate_runner=lambda *_: report)

    def test_hardened_gate_input_byte_counts_are_bound(self):
        with tempfile.TemporaryDirectory() as td:
            pair = RepoPair(Path(td))
            pair.install()
            report, _, _ = pair.promote()
            report["input_bytes"]["candidate_games"] += 1
            evidence_dir = json.loads((pair.head / LAB / "release_admission/CHAMPION.json").read_text())["promotion_evidence_dir"]
            write_json(pair.head, LAB / evidence_dir / "GATE.json", report)
            with self.assertRaisesRegex(admission.AdmissionError, "byte-count mismatch"):
                admission.evaluate_transition(pair.base, pair.head, gate_runner=lambda *_: report)

    def test_trusted_replay_must_match_committed_report(self):
        with tempfile.TemporaryDirectory() as td:
            pair = RepoPair(Path(td))
            pair.install()
            report, _, _ = pair.promote()
            replay = deepcopy(report)
            replay["panel_id"] = "different-replay"
            with self.assertRaisesRegex(admission.AdmissionError, "does not exactly match"):
                admission.evaluate_transition(
                    pair.base, pair.head, gate_runner=lambda *_args: replay
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
