"""Fixed-width digest normalization must not manufacture a valid prefix."""
from __future__ import annotations

import copy
import json
import unittest

from protocol.events import parse_event, parse_events


class ProtocolDigestWidthTests(unittest.TestCase):
    SHA256 = "0123456789abcdef" * 4
    GIT_SHA = "0123456789abcdef" * 2 + "01234567"

    def event(self, **changes):
        raw = {
            "kind": "CHECKPOINT",
            "event_id": "digest-width-event-0001",
            "session_id": "TERN_SIGMA",
            "ts": "2026-09-06T20:00:00Z",
            "objective": "Preserve evidence identity",
        }
        raw.update(changes)
        return raw

    def artifact(self, digest):
        return {
            "path": "results/report.json",
            "sha256": digest,
            "size_bytes": 12,
            "url": "https://example.invalid/report.json",
            "provider_private": True,
            "grade": "VERIFIED",
        }

    def test_overlong_sha256_is_not_replaced_by_its_prefix(self):
        suffixes = ("0", "f", "g", ":report", "\nnotes", " trailing", "\x00", "\u2603", "f" * 10000)
        for suffix in suffixes:
            with self.subTest(suffix=repr(suffix[:16])):
                result = parse_event(self.event(artifacts=[self.artifact(self.SHA256 + suffix)]))
                artifact = result["artifacts"][0]
                self.assertEqual(artifact["sha256"], "")
                self.assertEqual(artifact["grade"], "UNKNOWN")
                self.assertEqual(artifact["path"], "results/report.json")
                self.assertTrue(artifact["provider_private"])
                self.assertEqual(result["event_id"], "digest-width-event-0001")
                self.assertEqual(result["parse_state"], "OK")

    def test_overlong_head_sha_is_not_replaced_by_its_prefix(self):
        for suffix in ("0", "f", "g", ":commit", "\nnotes", " trailing", "\x00", "\u2603", "f" * 10000):
            with self.subTest(suffix=repr(suffix[:16])):
                result = parse_event(self.event(head_sha=self.GIT_SHA + suffix))
                self.assertEqual(result["head_sha"], "")
                self.assertEqual(result["event_id"], "digest-width-event-0001")
                self.assertEqual(result["parse_state"], "OK")

    def test_overlong_base_sha_alias_is_not_replaced_by_its_prefix(self):
        for suffix in ("0", "g", ":base", "\nnotes", "f" * 10000):
            with self.subTest(suffix=repr(suffix[:16])):
                result = parse_event(self.event(base_sha=self.GIT_SHA + suffix))
                self.assertEqual(result["head_sha"], "")

    def test_longer_digest_algorithms_are_not_silently_reinterpreted(self):
        result = parse_event(self.event(
            head_sha=self.SHA256,
            artifacts=[self.artifact(self.SHA256 * 2)],
        ))
        self.assertEqual(result["head_sha"], "")
        self.assertEqual(result["artifacts"][0]["sha256"], "")
        self.assertEqual(result["artifacts"][0]["grade"], "UNKNOWN")

    def test_exact_width_sha256_and_existing_case_normalization(self):
        for value in (self.SHA256, self.SHA256.upper(), " \t" + self.SHA256.upper() + "\r\n"):
            with self.subTest(value=value):
                result = parse_event(self.event(artifacts=[self.artifact(value)]))
                expected = self.artifact(self.SHA256)
                self.assertEqual(result["artifacts"], [expected])

    def test_exact_width_head_and_base_alias_case_normalization(self):
        for key in ("head_sha", "base_sha"):
            for value in (self.GIT_SHA, self.GIT_SHA.upper(), " \t" + self.GIT_SHA.upper() + "\r\n"):
                with self.subTest(key=key, value=value):
                    result = parse_event(self.event(**{key: value}))
                    self.assertEqual(result["head_sha"], self.GIT_SHA)

    def test_existing_short_and_nonhex_sha256_behavior_is_preserved(self):
        for value in ("a" * 63, "g" * 64, "a" * 63 + "\u2603", "a" * 32 + " " + "a" * 31):
            with self.subTest(value=value):
                result = parse_event(self.event(artifacts=[self.artifact(value)]))
                self.assertEqual(result["artifacts"][0]["sha256"], "")
                self.assertEqual(result["artifacts"][0]["grade"], "UNKNOWN")

    def test_existing_short_nonhex_and_nonscalar_head_behavior_is_preserved(self):
        for value in ("a" * 39, "g" * 40, "a" * 39 + "\u2603", {}, [], True, False, None, 1.5):
            with self.subTest(value=value):
                self.assertEqual(parse_event(self.event(head_sha=value))["head_sha"], "")

    def test_invalid_preferred_head_does_not_select_a_different_base(self):
        result = parse_event(self.event(head_sha=self.GIT_SHA + "f", base_sha="b" * 40))
        self.assertEqual(result["head_sha"], "")

    def test_empty_preferred_head_keeps_existing_base_alias_behavior(self):
        for value in (None, "", False, 0):
            with self.subTest(value=value):
                result = parse_event(self.event(head_sha=value, base_sha=self.GIT_SHA))
                self.assertEqual(result["head_sha"], self.GIT_SHA)

    def test_input_records_are_not_mutated(self):
        raw = self.event(head_sha=self.GIT_SHA + "g", artifacts=[self.artifact(self.SHA256 + "g")])
        before = copy.deepcopy(raw)
        result = parse_event(raw)
        self.assertEqual(raw, before)
        self.assertEqual(result["head_sha"], "")
        self.assertEqual(result["artifacts"][0]["sha256"], "")

    def test_bad_digest_does_not_drop_artifact_positions_or_batch_events(self):
        good = self.artifact(self.SHA256)
        bad = self.artifact(self.SHA256 + "g")
        raw = [
            self.event(artifacts=[good, bad, good]),
            self.event(event_id="digest-width-event-0002", head_sha=self.GIT_SHA + "g"),
            self.event(event_id="digest-width-event-0003", head_sha=self.GIT_SHA),
        ]
        results = parse_events({"events": raw})
        self.assertEqual([event["event_id"] for event in results], [event["event_id"] for event in raw])
        self.assertEqual([artifact["sha256"] for artifact in results[0]["artifacts"]], [self.SHA256, "", self.SHA256])
        self.assertEqual([event["head_sha"] for event in results[1:]], ["", self.GIT_SHA])
        self.assertEqual(len(results), 3)

    def test_derived_event_identity_does_not_depend_on_digest_normalization(self):
        raw = self.event(head_sha=self.GIT_SHA, artifacts=[self.artifact(self.SHA256)])
        del raw["event_id"]
        original_id = parse_event(raw)["event_id"]
        raw["head_sha"] += "g"
        raw["artifacts"][0]["sha256"] += "g"
        result = parse_event(raw)
        self.assertEqual(result["event_id"], original_id)
        self.assertEqual(result["head_sha"], "")
        self.assertEqual(result["artifacts"][0]["sha256"], "")

    def test_json_roundtrip_preserves_unknown_digest_metadata(self):
        raw = self.event(head_sha=self.GIT_SHA + "g", artifacts=[self.artifact(self.SHA256 + "g")])
        result = json.loads(json.dumps(parse_event(json.loads(json.dumps(raw)))))
        self.assertEqual(result["head_sha"], "")
        self.assertEqual(result["artifacts"][0]["sha256"], "")
        self.assertEqual(result["artifacts"][0]["grade"], "UNKNOWN")

    def test_digest_normalization_preserves_unrelated_text_and_tools(self):
        for tools in (["python", "github"], ["y" * 2500]):
            with self.subTest(tool_length=len(tools[0])):
                raw = self.event(objective="x" * 2500, tools=tools)
                baseline = parse_event(raw)
                raw.update(
                    head_sha=self.GIT_SHA + "g",
                    artifacts=[self.artifact(self.SHA256 + "g")],
                )
                result = parse_event(raw)
                self.assertEqual(result["objective"], "x" * 2000)
                # Tool clipping is not this repair's contract. Compare the
                # same environment with and without malformed digests.
                self.assertTrue(baseline["tools"])
                self.assertEqual(result["tools"], baseline["tools"])


if __name__ == "__main__":
    unittest.main()
