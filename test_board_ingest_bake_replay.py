"""Focused coverage for the bounded board projection replay outcome."""
from __future__ import annotations

import importlib.util
import inspect
import os
from pathlib import Path
import unittest
from unittest import mock

MODULE_PATH = Path(os.environ.get("BOARD_INGEST_UNDER_TEST", "board_ingest.py")).resolve()


def load_module():
    name = "board_ingest_bake_replay_" + str(abs(hash(str(MODULE_PATH))))
    spec = importlib.util.spec_from_file_location(name, MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BoundedBakeReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.subject = load_module()

    def classify(self, *, recorded="unchanged", existing=()):
        subject = self.subject
        source = {"sha256": "a" * 64, "files": 9907}
        refreshed = mock.Mock()
        with (
            mock.patch.object(subject, "post_source_snapshot", return_value=source),
            mock.patch.object(
                subject,
                "_projection_receipt_rel",
                side_effect=lambda digest, state: f"projection/{digest}-{state}.json",
            ),
            mock.patch.object(
                subject,
                "_head_has",
                side_effect=lambda rel, env: any(
                    rel.endswith(f"-{state}.json") for state in existing
                ),
            ),
            mock.patch.object(subject, "refresh_projection_status", refreshed),
        ):
            result = subject._classify_bounded_bake_reset({"TEST": "1"}, recorded)
        self.assertEqual(refreshed.call_count, 1)
        return result

    def test_captured_no_record_race_is_deferred_by_matching_pending_receipt(self):
        self.assertEqual(self.classify(existing={"pending"}), "unchanged")

    def test_durable_record_keeps_success_when_projection_is_pending(self):
        self.assertEqual(
            self.classify(recorded="pushed", existing={"pending"}),
            "pushed",
        )

    def test_refreshed_origin_that_already_converged_is_success(self):
        self.assertEqual(self.classify(existing={"converged"}), "unchanged")

    def test_converged_receipt_preserves_durable_record_result(self):
        self.assertEqual(
            self.classify(recorded="pushed", existing={"converged"}),
            "pushed",
        )

    def test_stale_projection_without_source_bound_receipt_stays_failure(self):
        self.assertEqual(self.classify(existing=set()), "push-fail")

    def test_durable_record_without_projection_receipt_keeps_success(self):
        # Run 34399022514: record landed, bake reset twice, missing receipt
        # used to fail the job and stamp a lie. Derived bake loss is deferred.
        self.assertEqual(
            self.classify(recorded="pushed", existing=set()),
            "pushed",
        )

    def test_receipt_lookup_is_bound_to_current_source_digest(self):
        subject = self.subject
        seen = []
        source = {"sha256": "b" * 64, "files": 9907}
        with (
            mock.patch.object(subject, "post_source_snapshot", return_value=source),
            mock.patch.object(
                subject,
                "_projection_receipt_rel",
                side_effect=lambda digest, state: (
                    seen.append((digest, state)) or f"{digest}-{state}"
                ),
            ),
            mock.patch.object(subject, "_head_has", return_value=False),
            mock.patch.object(subject, "refresh_projection_status"),
        ):
            subject._classify_bounded_bake_reset({}, "unchanged")
        self.assertEqual(
            seen,
            [("b" * 64, "converged"), ("b" * 64, "pending")],
        )

    def test_commit_path_uses_classifier_only_for_second_bake_reset(self):
        source = inspect.getsource(self.subject.commit_and_push)
        self.assertIn('if retry == "bake-reset":', source)
        self.assertIn("_classify_bounded_bake_reset(env, recorded)", source)
        self.assertLess(
            source.index('if retry == "pushed":'),
            source.index('if retry == "bake-reset":'),
        )

    def test_classifier_never_starts_another_push_attempt(self):
        source = inspect.getsource(self.subject._classify_bounded_bake_reset)
        self.assertNotIn("push_origin_main", source)
        self.assertNotIn("time.sleep", source)
        self.assertNotIn("_git(", source)


if __name__ == "__main__":
    unittest.main()
