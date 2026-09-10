#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

import returned_action_diff as parent
import strict_returned_action_diff as strict


def _sample(action):
    raw = {"statusCode": 200, "body": {"action": action}}
    unwrapped, path = parent.unwrap_action(raw)
    assert unwrapped == action
    return {
        "captured_at": "2026-09-10T00:00:00+00:00",
        "http": {
            "status": 200,
            "content_type": "application/json",
            "elapsed_ms": 1.0,
            "body_sha256": strict.sha256_json(raw),
        },
        "raw_response": raw,
        "unwrap_path": list(path),
        "action": action,
        "action_sha256": strict.sha256_json(action),
    }


def capture(action, *, state=None, samples=None, name="arm"):
    state = {"step": 95, "board": [1, 2, 3]} if state is None else state
    samples = [_sample(action)] if samples is None else samples
    hashes = [item["action_sha256"] for item in samples]
    first_unstable = next((i for i, value in enumerate(hashes[1:], 1) if value != hashes[0]), None)
    first_internal = None
    if first_unstable is not None:
        diffs = parent.semantic_diff(samples[0]["action"], samples[first_unstable]["action"])
        first_internal = asdict(diffs[0]) if diffs else None
    state_bytes = strict.canonical_json_bytes(state)
    baseline = samples[0]
    return {
        "format": parent.CAPTURE_FORMAT,
        "name": name,
        "endpoint": "https://example.invalid/",
        "captured_at": "2026-09-10T00:00:00+00:00",
        "state_sha256": strict.sha256_bytes(state_bytes),
        "request_sha256": strict.sha256_bytes(state_bytes),
        "request_bytes_length": len(state_bytes),
        "state": state,
        "sample_count": len(samples),
        "unique_action_count": len(set(hashes)),
        "deterministic": len(set(hashes)) == 1,
        "first_unstable_sample": first_unstable,
        "first_internal_difference": first_internal,
        "samples": samples,
        "raw_response": baseline["raw_response"],
        "unwrap_path": baseline["unwrap_path"],
        "action": baseline["action"],
        "action_sha256": baseline["action_sha256"],
    }


class StrictDiffTests(unittest.TestCase):
    def test_positional_market_swap_is_a_difference_by_default(self):
        left = {"market": [{"id": "A", "qty": 1}, {"id": "B", "qty": 2}]}
        right = {"market": [{"id": "B", "qty": 2}, {"id": "A", "qty": 1}]}
        diffs = strict.strict_semantic_diff(left, right)
        self.assertTrue(diffs)
        self.assertTrue(any(item.path.startswith("$.market[0]") for item in diffs))

    def test_explicit_unordered_path_can_ignore_pure_reorder(self):
        left = {"market": [{"id": "A", "qty": 1}, {"id": "B", "qty": 2}]}
        right = {"market": [{"id": "B", "qty": 2}, {"id": "A", "qty": 1}]}
        diffs = strict.strict_semantic_diff(
            left, right, unordered_paths=frozenset({"$.market"})
        )
        self.assertEqual(diffs, [])

    def test_unordered_path_requires_unique_identity(self):
        left = {"market": [{"id": "A"}, {"id": "A"}]}
        right = {"market": [{"id": "A"}, {"id": "A"}]}
        with self.assertRaises(strict.EvidenceError):
            strict.strict_semantic_diff(
                left, right, unordered_paths=frozenset({"$.market"})
            )

    def test_large_integer_does_not_binary64_alias(self):
        n = 2**53
        diffs = strict.strict_semantic_diff({"cash": n + 1}, {"cash": n})
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0].absolute_delta, 1)

    def test_bool_and_int_remain_type_distinct(self):
        diffs = strict.strict_semantic_diff({"x": True}, {"x": 1})
        self.assertEqual(diffs[0].kind, "type")

    def test_nonfinite_direct_value_rejected(self):
        with self.assertRaises(strict.EvidenceError):
            strict.strict_semantic_diff({"x": float("nan")}, {"x": 1})


class CaptureValidationTests(unittest.TestCase):
    def test_valid_capture_is_recomputed(self):
        bundle = capture({"market": [["SELL", "MILK", 1]]})
        got = strict.validate_capture_bundle(bundle)
        self.assertTrue(got.deterministic)
        self.assertEqual(got.action_sha256, strict.sha256_json(bundle["action"]))

    def test_forged_state_hash_rejected(self):
        bundle = capture({"x": 1})
        bundle["state_sha256"] = "0" * 64
        with self.assertRaises(strict.EvidenceError):
            strict.validate_capture_bundle(bundle)

    def test_forged_request_hash_rejected(self):
        bundle = capture({"x": 1})
        bundle["request_sha256"] = "1" * 64
        with self.assertRaises(strict.EvidenceError):
            strict.validate_capture_bundle(bundle)

    def test_missing_state_rejected(self):
        bundle = capture({"x": 1})
        del bundle["state"]
        with self.assertRaises(strict.EvidenceError):
            strict.validate_capture_bundle(bundle)

    def test_forged_action_hash_rejected(self):
        bundle = capture({"x": 1})
        bundle["samples"][0]["action_sha256"] = "2" * 64
        with self.assertRaises(strict.EvidenceError):
            strict.validate_capture_bundle(bundle)

    def test_raw_response_projection_mismatch_rejected(self):
        bundle = capture({"x": 1})
        bundle["samples"][0]["action"] = {"x": 2}
        bundle["samples"][0]["action_sha256"] = strict.sha256_json({"x": 2})
        bundle["action"] = {"x": 2}
        bundle["action_sha256"] = strict.sha256_json({"x": 2})
        with self.assertRaises(strict.EvidenceError):
            strict.validate_capture_bundle(bundle)

    def test_unwrap_path_mismatch_rejected(self):
        bundle = capture({"x": 1})
        bundle["samples"][0]["unwrap_path"] = []
        with self.assertRaises(strict.EvidenceError):
            strict.validate_capture_bundle(bundle)

    def test_sample_count_mismatch_rejected(self):
        bundle = capture({"x": 1})
        bundle["sample_count"] = 2
        with self.assertRaises(strict.EvidenceError):
            strict.validate_capture_bundle(bundle)

    def test_unstable_capture_holds_instead_of_comparing_sample_zero(self):
        samples = [_sample({"x": 1}), _sample({"x": 2})]
        left = capture({"x": 1}, samples=samples, name="left")
        right = capture({"x": 1}, name="right")
        report = strict.compare_validated_captures(left, right)
        self.assertEqual(report["verdict"], "HOLD_UNSTABLE")
        self.assertIsNone(report["summary"]["equal"])

    def test_parent_unordered_internal_diagnostic_is_not_used_for_attribution(self):
        a = [{"id": "A"}, {"id": "B"}]
        b = [{"id": "B"}, {"id": "A"}]
        samples = [_sample(a), _sample(b)]
        left = capture(a, samples=samples, name="left")
        # Parent considers the reorder semantically empty internally, but the
        # strict consumer still detects instability from action hashes.
        self.assertIsNone(left["first_internal_difference"])
        right = capture(a, name="right")
        report = strict.compare_validated_captures(left, right)
        self.assertEqual(report["verdict"], "HOLD_UNSTABLE")

    def test_different_states_fail_closed(self):
        left = capture({"x": 1}, state={"step": 1})
        right = capture({"x": 1}, state={"step": 2})
        with self.assertRaises(strict.EvidenceError):
            strict.compare_validated_captures(left, right)


class StrictJsonTests(unittest.TestCase):
    def test_duplicate_object_key_rejected_at_any_depth(self):
        with self.assertRaises(strict.EvidenceError):
            strict.strict_loads('{"x":{"a":1,"a":2}}')

    def test_nan_constant_rejected(self):
        with self.assertRaises(strict.EvidenceError):
            strict.strict_loads('{"x":NaN}')

    def test_overflowing_float_rejected(self):
        with self.assertRaises(strict.EvidenceError):
            strict.strict_loads('{"x":1e9999}')


class TemporalLedgerTests(unittest.TestCase):
    def test_first_temporal_divergence_requires_validated_equal_prefix(self):
        state0 = {"step": 10}
        state1 = {"step": 11}
        ledger = {
            "format": strict.STRICT_LEDGER_FORMAT,
            "steps": [
                {
                    "step": 10,
                    "left": capture({"market": [["SELL", "MILK", 1]]}, state=state0, name="v1"),
                    "right": capture({"market": [["SELL", "MILK", 1]]}, state=state0, name="v2"),
                },
                {
                    "step": 11,
                    "left": capture({"market": [["SELL", "MILK", 1], ["PASS"]]}, state=state1, name="v1"),
                    "right": capture({"market": [["PASS"], ["SELL", "MILK", 1]]}, state=state1, name="v2"),
                },
            ],
        }
        report = strict.validate_temporal_ledger(ledger)
        self.assertEqual(report["verdict"], "TEMPORAL_DIVERGENCE")
        self.assertEqual(report["equal_prefix_steps"], 1)
        self.assertEqual(report["first_temporal_divergence"]["step"], 11)
        self.assertTrue(
            report["first_temporal_divergence"]["first_difference"]["path"].startswith("$[0]")
            or report["first_temporal_divergence"]["first_difference"]["path"].startswith("$.")
        )

    def test_noncontiguous_ledger_rejected(self):
        ledger = {
            "format": strict.STRICT_LEDGER_FORMAT,
            "steps": [
                {"step": 1, "left": capture({"x": 1}, state={"step": 1}), "right": capture({"x": 1}, state={"step": 1})},
                {"step": 3, "left": capture({"x": 1}, state={"step": 3}), "right": capture({"x": 1}, state={"step": 3})},
            ],
        }
        with self.assertRaises(strict.EvidenceError):
            strict.validate_temporal_ledger(ledger)

    def test_unstable_row_holds_temporal_claim(self):
        state = {"step": 7}
        unstable = capture({"x": 1}, state=state, samples=[_sample({"x": 1}), _sample({"x": 2})])
        ledger = {
            "format": strict.STRICT_LEDGER_FORMAT,
            "steps": [{"step": 7, "left": unstable, "right": capture({"x": 1}, state=state)}],
        }
        report = strict.validate_temporal_ledger(ledger)
        self.assertEqual(report["verdict"], "HOLD_UNSTABLE")
        self.assertIsNone(report["first_temporal_divergence"])


class PathCustodyTests(unittest.TestCase):
    def test_symlink_input_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            real = root / "real.json"
            real.write_text("{}", encoding="utf-8")
            link = root / "link.json"
            link.symlink_to(real)
            with self.assertRaises(strict.EvidenceError):
                strict.validate_path_separation([link], [])

    def test_hardlink_input_alias_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            first = root / "a.json"
            second = root / "b.json"
            first.write_text("{}", encoding="utf-8")
            os.link(first, second)
            with self.assertRaises(strict.EvidenceError):
                strict.validate_path_separation([first, second], [])

    def test_output_alias_to_input_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "same.json"
            path.write_text("{}", encoding="utf-8")
            with self.assertRaises(strict.EvidenceError):
                strict.validate_path_separation([path], [path])

    def test_atomic_write_roundtrip_and_self_seal(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "report.json"
            left = capture({"x": 1}, name="left")
            right = capture({"x": 1}, name="right")
            report = strict.compare_validated_captures(left, right)
            self.assertEqual(report["report_sha256"], strict._seal(report))
            strict.atomic_write_json(out, report)
            reread = strict.strict_load_file(out)
            self.assertEqual(reread, report)


if __name__ == "__main__":
    unittest.main()