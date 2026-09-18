"""Malformed artifact metadata stays visible without aborting event batches."""
import copy
import unittest

from protocol.events import parse_event, parse_events


class EventArtifactShapeTests(unittest.TestCase):
    def event(self, **fields):
        return {
            "kind": "CHECKPOINT",
            "event_id": "artifact-shape-test-01",
            "session_id": "KESTREL_SIGMA",
            "task_id": "artifact-shape-task-01",
            "ts": "2026-09-06T23:00:00Z",
            **fields,
        }

    def artifact_evidence(self, event):
        return [row for row in event["evidence"] if row.get("source") == "artifacts"]

    def test_non_array_json_shapes_remain_visible_without_phantom_artifacts(self):
        values = [1, -1, 1.25, True, 0, 0.0, False, "report.txt", "", {},
                  {"path": "report.txt"}]
        for value in values:
            with self.subTest(value=value):
                raw = self.event(artifacts=value)
                event = parse_event(raw)
                self.assertEqual(event["parse_state"], "MALFORMED")
                self.assertEqual(event["artifacts"], [])
                self.assertEqual(event["event_id"], raw["event_id"])
                self.assertEqual(event["session_id"], raw["session_id"])
                self.assertEqual(event["task_id"], raw["task_id"])
                self.assertIn("artifacts", event["fields_observed"])
                self.assertEqual(self.artifact_evidence(event), [{
                    "source": "artifacts", "grade": "UNKNOWN",
                    "detail": "artifacts was not an array",
                    "raw_type": type(value).__name__,
                }])

    def test_missing_null_and_empty_array_keep_existing_optional_behavior(self):
        for fields in ({}, {"artifacts": None}, {"artifacts": []}):
            with self.subTest(fields=fields):
                event = parse_event(self.event(**fields))
                self.assertEqual(event["parse_state"], "OK")
                self.assertEqual(event["artifacts"], [])
                self.assertEqual(self.artifact_evidence(event), [])

    def test_batch_preserves_good_events_on_both_sides_of_bad_metadata(self):
        for wrapped in (False, True):
            with self.subTest(wrapped=wrapped):
                before = self.event(event_id="artifact-before-01", kind="START")
                bad = self.event(event_id="artifact-middle-01", artifacts=1)
                after = self.event(event_id="artifact-after-01", kind="TERMINAL")
                rows = [before, bad, after]
                result = parse_events({"events": rows} if wrapped else rows)
                self.assertEqual([row["event_id"] for row in result],
                                 [row["event_id"] for row in rows])
                self.assertEqual([row["parse_state"] for row in result],
                                 ["OK", "MALFORMED", "OK"])
                self.assertEqual(result[0], parse_event(before))
                self.assertEqual(result[2], parse_event(after))

    def test_malformed_array_entries_keep_positions_and_report_their_indices(self):
        values = [None, 1, True, "bad", [], 1.25]
        raw = self.event(artifacts=[{"path": "before.txt"}, *values,
                                    {"path": "after.txt"}])
        event = parse_event(raw)
        self.assertEqual(event["parse_state"], "MALFORMED")
        self.assertEqual(len(event["artifacts"]), len(raw["artifacts"]))
        self.assertEqual(event["artifacts"][0]["path"], "before.txt")
        self.assertEqual(event["artifacts"][-1]["path"], "after.txt")
        for index, value in enumerate(values, 1):
            with self.subTest(index=index):
                self.assertEqual(event["artifacts"][index]["path"], "UNKNOWN")
                self.assertEqual(self.artifact_evidence(event)[index - 1], {
                    "source": "artifacts", "grade": "UNKNOWN",
                    "detail": "artifact was not an object", "index": index,
                    "raw_type": type(value).__name__,
                })

    def test_valid_artifact_normalization_is_unchanged(self):
        raw = self.event(artifacts=[{
            "path": " reports/result.json ", "sha256": "A" * 64,
            "size_bytes": 0, "url": " https://example.test/result ",
            "provider_private": True, "grade": "VERIFIED",
        }, {"path": "empty.txt"}])
        event = parse_event(raw)
        self.assertEqual(event["parse_state"], "OK")
        self.assertEqual(event["artifacts"], [{
            "path": "reports/result.json", "sha256": "a" * 64,
            "size_bytes": 0, "url": "https://example.test/result",
            "provider_private": True, "grade": "VERIFIED",
        }, {
            "path": "empty.txt", "sha256": "", "size_bytes": None,
            "url": "", "provider_private": False, "grade": "UNKNOWN",
        }])
        self.assertEqual(self.artifact_evidence(event), [])

    def test_existing_invalid_hash_and_size_normalization_is_preserved(self):
        event = parse_event(self.event(artifacts=[{
            "path": "result.json", "sha256": "invalid", "size_bytes": -1,
            "grade": "VERIFIED",
        }]))
        self.assertEqual(event["artifacts"][0]["sha256"], "")
        self.assertEqual(event["artifacts"][0]["grade"], "UNKNOWN")
        self.assertIsNone(event["artifacts"][0]["size_bytes"])

    def test_input_is_not_mutated(self):
        for value in (1, {"path": "report.txt"},
                      [{"path": "report.txt"}, "bad", [1, 2]]):
            with self.subTest(value=value):
                raw = self.event(artifacts=value)
                saved = copy.deepcopy(raw)
                parse_event(raw)
                self.assertEqual(raw, saved)

    def test_generated_identity_does_not_change_with_artifact_shape(self):
        raw = self.event()
        del raw["event_id"]
        expected_id = parse_event(raw)["event_id"]
        for value in (None, [], 1, "bad", ["bad"], [{"path": "report.txt"}]):
            with self.subTest(value=value):
                self.assertEqual(parse_event({**raw, "artifacts": value})["event_id"],
                                 expected_id)

    def test_unknown_kind_keeps_both_diagnostics(self):
        event = parse_event(self.event(kind="NOT_A_KIND", artifacts=1))
        self.assertEqual(event["kind"], "UNKNOWN")
        self.assertEqual(event["parse_state"], "MALFORMED")
        self.assertEqual({row["source"] for row in event["evidence"]},
                         {"event", "artifacts"})

    def test_non_json_iterables_are_not_consumed_as_artifact_lists(self):
        class MustNotIterate:
            def __iter__(self):
                raise AssertionError("non-list metadata must not be consumed")

        for value in (({"path": "tuple.txt"},), MustNotIterate()):
            with self.subTest(raw_type=type(value).__name__):
                event = parse_event(self.event(artifacts=value))
                self.assertEqual(event["parse_state"], "MALFORMED")
                self.assertEqual(event["artifacts"], [])


if __name__ == "__main__":
    unittest.main()
