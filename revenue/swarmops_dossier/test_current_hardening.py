from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import unittest
from unittest import mock

import revenue.swarmops_dossier.current as current_module
from revenue.swarmops_dossier.acceptance import fixture
from revenue.swarmops_dossier.engine import DossierError, compile_dossier, digest


def _utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _freshen(packet: dict, when: str, freshness_seconds: int | None = None) -> dict:
    fresh = copy.deepcopy(packet)
    for row in fresh["evidence"]:
        row["observed_at"] = when
        if freshness_seconds is not None:
            row["freshness_seconds"] = freshness_seconds
    return fresh


def _forge_snapshot(packet: dict, policy: dict, as_of: str) -> dict:
    core = compile_dossier(packet, policy, as_of, {})
    wrapped = dict(core)
    core_receipt = wrapped.pop("receipt_sha256")
    wrapped["schema"] = current_module.OUTPUT_SCHEMA
    wrapped["evaluation_mode"] = current_module.CURRENT_MODE
    wrapped["core_v3_receipt_sha256"] = core_receipt
    wrapped["receipt_sha256"] = digest(wrapped)
    return wrapped


class _EvilDict(dict):
    pass


class _EvilList(list):
    pass


class CurrentVerifierHardeningTests(unittest.TestCase):
    def setUp(self):
        self.packet, self.policy = fixture()

    def test_mode_truth_narrows_timestamp_provenance(self):
        self.assertEqual(current_module.CURRENT_MODE, "CURRENT_SEMANTIC_SNAPSHOT")
        now = datetime.now(timezone.utc).replace(microsecond=0)
        packet = _freshen(self.packet, _utc_text(now - timedelta(seconds=10)))
        forged_as_of = _utc_text(now - timedelta(seconds=2))
        forged = _forge_snapshot(packet, self.policy, forged_as_of)

        # This is intentionally accepted while the semantic projection is still
        # current. The mode no longer claims that candidate.as_of itself was
        # sampled by the verifier/compile API.
        self.assertTrue(
            current_module.verify_current_dossier(packet, self.policy, forged)
        )

    def test_sealed_semantic_dependencies_ignore_module_rebinding(self):
        old_as_of = "2026-09-13T14:00:00Z"
        stale = _forge_snapshot(self.packet, self.policy, old_as_of)
        self.assertEqual(stale["status"], "READY_FOR_OWNER_REVIEW")

        fresh_packet = _freshen(
            self.packet, _utc_text(datetime.now(timezone.utc))
        )
        tampered = current_module.compile_current_dossier(fresh_packet, self.policy)
        tampered["summary"]["DEMONSTRATED"] += 1

        with mock.patch.object(
            current_module, "canonical_bytes", new=lambda _value: b"constant"
        ), mock.patch.object(
            current_module,
            "compile_dossier",
            new=lambda *_args, **_kwargs: {"receipt_sha256": "0" * 64},
        ), mock.patch.object(
            current_module, "_current_semantics", new=lambda _value: b"constant"
        ), mock.patch.object(
            current_module, "_freeze_plain_json", new=lambda *_args: {}
        ), mock.patch.object(
            current_module,
            "_parse_utc",
            new=lambda *_args, **_kwargs: datetime(2026, 9, 13, tzinfo=timezone.utc),
        ), mock.patch.object(
            current_module,
            "_wrap_core",
            new=lambda core, mode: {"schema": "forged", "evaluation_mode": mode},
        ):
            self.assertFalse(
                current_module.verify_current_dossier(self.packet, self.policy, stale)
            )
            self.assertFalse(
                current_module.verify_current_dossier(
                    fresh_packet, self.policy, tampered
                )
            )

    def test_sealed_freezer_keeps_nested_plain_json_after_module_rebind(self):
        packet = _freshen(self.packet, _utc_text(datetime.now(timezone.utc)))
        candidate = current_module.compile_current_dossier(packet, self.policy)
        with mock.patch.object(
            current_module, "_freeze_plain_json", new=lambda *_args: {}
        ):
            self.assertTrue(
                current_module.verify_current_dossier(packet, self.policy, candidate)
            )

    def test_verifier_freezes_all_multi_pass_inputs(self):
        packet = _freshen(self.packet, _utc_text(datetime.now(timezone.utc)))
        candidate = current_module.compile_current_dossier(packet, self.policy)

        self.assertFalse(
            current_module.verify_current_dossier(
                _EvilDict(packet), self.policy, candidate
            )
        )
        self.assertFalse(
            current_module.verify_current_dossier(
                packet, _EvilDict(self.policy), candidate
            )
        )
        self.assertFalse(
            current_module.verify_current_dossier(
                packet, self.policy, candidate, _EvilDict({})
            )
        )

        with self.assertRaises(DossierError):
            current_module.compile_current_dossier(
                _EvilDict(packet), self.policy
            )

    def test_clock_is_sampled_after_candidate_authentication(self):
        t0 = datetime.now(timezone.utc).replace(microsecond=0)
        packet = _freshen(
            self.packet,
            _utc_text(t0 - timedelta(seconds=60)),
            freshness_seconds=60,
        )
        candidate_as_of = _utc_text(t0)
        candidate = _forge_snapshot(packet, self.policy, candidate_as_of)
        self.assertEqual(candidate["status"], "READY_FOR_OWNER_REVIEW")

        state = {"now": candidate_as_of}

        def clock() -> str:
            return state["now"]

        def crossing_compile(packet_arg, policy_arg, as_of, trusted=None):
            compiled = compile_dossier(packet_arg, policy_arg, as_of, trusted)
            if as_of == candidate_as_of:
                state["now"] = _utc_text(t0 + timedelta(seconds=1))
            return compiled

        _compile_unused, verify = current_module._build_current_api_for_test(
            clock, _compile=crossing_compile
        )
        self.assertFalse(verify(packet, self.policy, candidate, {}))

    def test_non_plain_json_candidate_is_rejected_before_semantic_access(self):
        packet = _freshen(self.packet, _utc_text(datetime.now(timezone.utc)))
        candidate = current_module.compile_current_dossier(packet, self.policy)

        self.assertFalse(
            current_module.verify_current_dossier(
                packet, self.policy, _EvilDict(candidate)
            )
        )

        nested = copy.deepcopy(candidate)
        nested["rows"] = _EvilList(nested.get("rows", []))
        self.assertFalse(
            current_module.verify_current_dossier(packet, self.policy, nested)
        )

    def test_stale_snapshot_still_fails_after_truth_narrowing(self):
        old_as_of = "2026-09-13T14:00:00Z"
        stale = _forge_snapshot(self.packet, self.policy, old_as_of)
        self.assertFalse(
            current_module.verify_current_dossier(self.packet, self.policy, stale)
        )


if __name__ == "__main__":
    unittest.main()
