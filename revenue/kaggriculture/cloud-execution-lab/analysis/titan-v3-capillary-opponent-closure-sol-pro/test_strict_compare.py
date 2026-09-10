# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import hashlib
import unittest

import bind_opponents as binding_core
import strict_compare

PARENT = strict_compare.PARENT
CONTROL_SHA = "1" * 64
CANDIDATE_SHA = "2" * 64
EVALUATOR_SOURCE_SHA = "3" * 64
PATCHED_SHA = "4" * 64
LOADER_SHA = "5" * 64
ARLENE_WRAPPER_SHA = "c" * 64
V1_WRAPPER_SHA = "d" * 64


def identity(*, path: str | None, size: int, sha: str, blob: str) -> dict:
    result = {"bytes": size, "sha256": sha, "git_blob_sha1": blob}
    if path is not None:
        result["path"] = path
    return result


def audit_fixture() -> dict:
    return {
        "schema_version": 1,
        "operation": PARENT.OPERATION,
        "git_head": "a" * 40,
        "archive": {"sha256": "6" * 64},
        "control": {"sha256": CONTROL_SHA},
        "candidate": {"sha256": CANDIDATE_SHA},
        "evaluator_source": {
            "git_blob_sha1": "b" * 40,
            "sha256": EVALUATOR_SOURCE_SHA,
            "bytes": 123,
        },
        "loader": {"sha256": LOADER_SHA},
        "engine": {
            name: {"sha256": value}
            for name, value in {
                "kaggriculture.py": "7" * 64,
                "kaggriculture.json": "8" * 64,
                "utils.py": "9" * 64,
            }.items()
        },
        "opponents": {
            "arlene": identity(
                path=(
                    "revenue/kaggriculture/cloud-execution-lab/runtime/variants/"
                    "v1/reference/next-panel/vendor/arlene.py"
                ),
                size=46342,
                sha="1dc166ae2bf0c56a44fac4482f469b8812968c4cb32459cb9860f5077897a7d4",
                blob="e" * 40,
            ),
            "v1": identity(
                path=(
                    "revenue/kaggriculture/cloud-execution-lab/runtime/variants/"
                    "v1/candidate.py"
                ),
                size=66,
                sha="2e4897fb3aa8b0bee3e97709808c3aa25fa5055bcf5ce7d433b493eb334870f2",
                blob="8db1262a2d38cc3115d06732383e18e1132ccfba",
            ),
        },
    }


def evaluator_receipt_fixture() -> dict:
    return {
        "schema_version": 1,
        "operation": PARENT.OPERATION,
        "source": {
            "git_blob_sha1": "b" * 40,
            "sha256": EVALUATOR_SOURCE_SHA,
            "bytes": 123,
        },
        "patched": {
            "sha256": PATCHED_SHA,
            "capture_phase": "after both returned actions, before interpreter",
            "candidate_action_field": "candidate_action_sha256",
            "candidate_action_count_field": "candidate_action_count",
            "patches": [
                {
                    "old_occurrences_before": 1,
                    "old_occurrences_after": 0,
                    "new_occurrences_after": 1,
                }
                for _ in range(3)
            ],
        },
    }


def _payload_rows() -> tuple[list[dict], list[dict]]:
    arlene = [
        {
            "path": "arlene.py",
            "bytes": 46342,
            "sha256": "1dc166ae2bf0c56a44fac4482f469b8812968c4cb32459cb9860f5077897a7d4",
            "git_blob_sha1": "e" * 40,
        }
    ]
    v1 = [
        {
            "path": path,
            "bytes": metadata["bytes"],
            "sha256": metadata["sha256"],
            "git_blob_sha1": f"{index + 1:040x}",
        }
        for index, (path, metadata) in enumerate(
            sorted(binding_core.EXPECTED_FILES.items())
        )
    ]
    return arlene, v1


def binding_fixture(audit: dict) -> tuple[dict, dict]:
    arlene_files, v1_files = _payload_rows()
    arlene_closure = binding_core.closure_sha256(arlene_files)
    v1_closure = binding_core.closure_sha256(v1_files)
    binder = strict_compare._identity(
        strict_compare.HERE / "bind_opponents.py", "fixture binder"
    )
    wrappers = {
        "arlene": identity(
            path="arlene/arlene.py", size=1001,
            sha=ARLENE_WRAPPER_SHA, blob="f" * 40,
        ),
        "v1": identity(
            path="v1/candidate.py", size=2002,
            sha=V1_WRAPPER_SHA, blob="1" * 40,
        ),
    }
    sidecars = {
        "arlene": identity(
            path="arlene/BINDING.json", size=501,
            sha="a" * 64, blob="2" * 40,
        ),
        "v1": identity(
            path="v1/BINDING.json", size=502,
            sha="b" * 64, blob="3" * 40,
        ),
    }
    files = {"arlene": arlene_files, "v1": v1_files}
    closures = {"arlene": arlene_closure, "v1": v1_closure}
    opponents = {}
    for label in ("arlene", "v1"):
        probe = {
            "binding": {
                "label": label,
                "git_head": audit["git_head"],
                "closure_sha256": closures[label],
                "entry": strict_compare.EXPECTED_SOURCE_ENTRIES[label]["entry"],
                "verified_origins": copy.deepcopy(strict_compare.EXPECTED_ORIGINS[label]),
            },
            "agent_module": "scheduler" if label == "v1" else "arlene-bound",
        }
        opponents[label] = {
            "entry_name": strict_compare.EXPECTED_SOURCE_ENTRIES[label]["entry"],
            "source_entry": copy.deepcopy(audit["opponents"][label]),
            "source_closure_sha256": closures[label],
            "payload": {
                "root": f"{label}/payload",
                "closure_sha256": closures[label],
                "files": files[label],
            },
            "wrapper": wrappers[label],
            "sidecar": sidecars[label],
            "probe": probe,
        }
    binding = {
        "schema_version": 1,
        "operation": binding_core.OPERATION,
        "git_head": audit["git_head"],
        "source_parent_head": binding_core.PARENT_HEAD,
        "freeze": {
            "path": "revenue/kaggriculture/cloud-execution-lab/runtime/variants/v1/FREEZE.json",
            "bytes": binding_core.EXPECTED_FREEZE_BYTES,
            "sha256": binding_core.EXPECTED_FREEZE_SHA256,
            "runtime_files": len(binding_core.EXPECTED_FILES),
            "source_closure_sha256": v1_closure,
        },
        "binder": binder,
        "opponents": opponents,
    }
    verification = {
        "schema_version": 1,
        "operation": binding_core.VERIFY_OPERATION,
        "git_head": audit["git_head"],
        "source_parent_head": binding_core.PARENT_HEAD,
        "binding_object_sha256": binding_core.object_sha256(binding),
        "binder": binder,
        "opponents": {
            label: {
                "source_entry": copy.deepcopy(opponents[label]["source_entry"]),
                "source_closure_sha256": closures[label],
                "payload_closure_sha256": closures[label],
                "wrapper": copy.deepcopy(wrappers[label]),
                "sidecar": copy.deepcopy(sidecars[label]),
                "probe": copy.deepcopy(opponents[label]["probe"]),
            }
            for label in ("arlene", "v1")
        },
        "verified": True,
    }
    return binding, verification


def report_fixture(
    entry_sha: str,
    *,
    own_delta: float,
    changed: bool,
    wrapper_hashes: bool = True,
) -> dict:
    audit = audit_fixture()
    opponents = {
        "arlene": {
            "entry": "arlene.py",
            "callable": "agent",
            "sha256": (
                ARLENE_WRAPPER_SHA
                if wrapper_hashes
                else audit["opponents"]["arlene"]["sha256"]
            ),
        },
        "v1": {
            "entry": "candidate.py",
            "callable": "agent",
            "sha256": (
                V1_WRAPPER_SHA
                if wrapper_hashes
                else audit["opponents"]["v1"]["sha256"]
            ),
        },
    }
    games = []
    for opponent in PARENT.EXPECTED_OPPONENTS:
        for seed in PARENT.EXPECTED_SEEDS:
            for seat in (0, 1):
                scores = [100.0, 100.0]
                scores[seat] += own_delta
                token = (
                    f"{opponent}:{seed}:{seat}:"
                    f"{'candidate' if changed else 'control'}"
                ).encode()
                games.append(
                    {
                        "opponent": opponent,
                        "seed": seed,
                        "candidate_seat": seat,
                        "status": "complete",
                        "failure": None,
                        "steps": PARENT.EXPECTED_STEPS,
                        "episode_steps": PARENT.EXPECTED_EPISODE_STEPS,
                        "scores": scores,
                        "bank_snapshot": list(scores),
                        "candidate_action_count": PARENT.EXPECTED_STEPS,
                        "candidate_action_sha256": hashlib.sha256(token).hexdigest(),
                        "trace_sha256": hashlib.sha256(b"trace:" + token).hexdigest(),
                        "actors": [
                            {"calls": PARENT.EXPECTED_STEPS},
                            {"calls": PARENT.EXPECTED_STEPS},
                        ],
                    }
                )
    return {
        "schema_version": 1,
        "engine_ref": PARENT.EXPECTED_ENGINE_REF,
        "engine_sha256": {
            name: row["sha256"] for name, row in audit["engine"].items()
        },
        "loader_sha256": LOADER_SHA,
        "evaluator_sha256": PATCHED_SHA,
        "candidate": {
            "entry": "candidate.py",
            "callable": "agent",
            "sha256": entry_sha,
        },
        "opponents": opponents,
        "seeds": list(PARENT.EXPECTED_SEEDS),
        "agent_rng_seed": PARENT.EXPECTED_AGENT_RNG_SEED,
        "limits": {
            "action_rpc_seconds": 1.0,
            "startup_seconds": 15.0,
            "game_seconds_between_steps": 180.0,
            "remaining_overage_time": 0,
        },
        "progress": {
            "state": "complete",
            "phase": "finalize",
            "planned_games": PARENT.EXPECTED_GAMES_PER_ARM,
            "recorded_games": PARENT.EXPECTED_GAMES_PER_ARM,
            "active_game": None,
        },
        "games": games,
    }


class StrictClosureTests(unittest.TestCase):
    def setUp(self):
        self.audit = audit_fixture()
        self.evaluator = evaluator_receipt_fixture()
        self.binding, self.verification = binding_fixture(self.audit)
        self.control = report_fixture(
            CONTROL_SHA, own_delta=0.0, changed=False
        )
        self.candidate = report_fixture(
            CANDIDATE_SHA, own_delta=5.0, changed=True
        )

    def classify(self):
        return strict_compare.classify(
            self.control,
            self.candidate,
            self.audit,
            self.evaluator,
            self.binding,
            self.verification,
        )

    def test_valid_closure_bound_positive_panel_advances(self):
        result = self.classify()
        self.assertTrue(result["advance"])
        self.assertTrue(
            result["criteria"]["opponent_transitive_closure_bound"]
        )
        self.assertEqual(
            result["opponent_binding"]["v1"]["wrapper_sha256"],
            V1_WRAPPER_SHA,
        )
        self.assertEqual(result["parent_operation"], PARENT.OPERATION)
        self.assertEqual(result["operation"], strict_compare.OPERATION)

    def test_parent_entry_only_report_is_rejected(self):
        self.control["opponents"] = report_fixture(
            CONTROL_SHA,
            own_delta=0.0,
            changed=False,
            wrapper_hashes=False,
        )["opponents"]
        self.candidate["opponents"] = copy.deepcopy(self.control["opponents"])
        with self.assertRaisesRegex(PARENT.CompareError, "opponents"):
            self.classify()

    def test_source_entry_hash_rebinding_is_rejected(self):
        self.binding["opponents"]["v1"]["source_entry"]["sha256"] = "f" * 64
        self.verification["binding_object_sha256"] = binding_core.object_sha256(
            self.binding
        )
        with self.assertRaisesRegex(
            strict_compare.ClosureCompareError, "audit/source sha256"
        ):
            self.classify()

    def test_post_game_payload_closure_drift_is_rejected(self):
        self.verification["opponents"]["v1"]["payload_closure_sha256"] = "f" * 64
        with self.assertRaisesRegex(
            strict_compare.ClosureCompareError, "post-game payload closure"
        ):
            self.classify()

    def test_wrapper_alias_is_rejected(self):
        self.binding["opponents"]["v1"]["wrapper"] = copy.deepcopy(
            self.binding["opponents"]["arlene"]["wrapper"]
        )
        self.binding["opponents"]["v1"]["wrapper"]["path"] = "v1/candidate.py"
        self.verification["binding_object_sha256"] = binding_core.object_sha256(
            self.binding
        )
        self.verification["opponents"]["v1"]["wrapper"] = copy.deepcopy(
            self.binding["opponents"]["v1"]["wrapper"]
        )
        with self.assertRaisesRegex(
            strict_compare.ClosureCompareError, "wrapper hashes alias"
        ):
            self.classify()

    def test_probe_origin_drift_is_rejected(self):
        self.binding["opponents"]["v1"]["probe"]["binding"][
            "verified_origins"
        ]["scheduler"] = "ambient/scheduler.py"
        self.verification["binding_object_sha256"] = binding_core.object_sha256(
            self.binding
        )
        self.verification["opponents"]["v1"]["probe"] = copy.deepcopy(
            self.binding["opponents"]["v1"]["probe"]
        )
        with self.assertRaisesRegex(
            strict_compare.ClosureCompareError, "probe module origins"
        ):
            self.classify()

    def test_binding_object_digest_drift_is_rejected(self):
        self.verification["binding_object_sha256"] = "0" * 64
        with self.assertRaisesRegex(
            strict_compare.ClosureCompareError, "verification binding digest"
        ):
            self.classify()

    def test_strict_classifier_does_not_mutate_inputs(self):
        before = copy.deepcopy(
            (
                self.control,
                self.candidate,
                self.audit,
                self.evaluator,
                self.binding,
                self.verification,
            )
        )
        self.classify()
        self.assertEqual(
            (
                self.control,
                self.candidate,
                self.audit,
                self.evaluator,
                self.binding,
                self.verification,
            ),
            before,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
