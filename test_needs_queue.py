import unittest

from host.needs_queue import NeedsQueueError, load_registry, reduce_registry


def runner(item_id="R", publisher="seat:publisher"):
    return {
        "id": item_id,
        "kind": "runner",
        "canonical_packet": "pr:12581@head",
        "return_slot": "slack:C0BU51F1PL3:thread",
        "task": "execute the exact packet and return terminal evidence",
        "required_capabilities": ["linux", "network", "python3.11"],
        "publisher": publisher,
    }


def owner(item_id="O"):
    return {
        "id": item_id,
        "kind": "owner",
        "canonical_packet": "pr:12567@head",
        "return_slot": "slack:C0BU51F1PL3:thread",
        "owner_action": "perform the owner-authenticated approval and return its receipt",
    }


def event(seq, event_id, item_id, actor, status="SUCCESS", receipt=None):
    return {
        "seq": seq,
        "event_id": event_id,
        "item_id": item_id,
        "actor": actor,
        "status": status,
        "receipt": receipt or f"receipt:{event_id}",
    }


def payload(items=None, events=None):
    return {"version": 1, "items": list(items or []), "events": list(events or [])}


class NeedsQueueTests(unittest.TestCase):
    def test_runner_requires_named_capabilities_packet_publisher_and_return_slot(self):
        item = runner()
        for field in ("canonical_packet", "return_slot", "task", "publisher"):
            broken = dict(item)
            broken[field] = ""
            with self.subTest(field=field), self.assertRaises(NeedsQueueError) as caught:
                load_registry(payload([broken]))
            self.assertEqual(caught.exception.code, "INVALID_FIELD")

        broken = dict(item)
        broken["required_capabilities"] = []
        with self.assertRaises(NeedsQueueError) as caught:
            load_registry(payload([broken]))
        self.assertEqual(caught.exception.code, "INVALID_CAPABILITIES")

    def test_runner_one_publisher_rule_fails_closed(self):
        data = payload(
            [runner(publisher="seat:A")],
            [event(1, "e1", "R", "seat:B", status="FAILED")],
        )
        with self.assertRaises(NeedsQueueError) as caught:
            load_registry(data)
        self.assertEqual(caught.exception.code, "WRONG_PUBLISHER")
        self.assertEqual(caught.exception.details["expected"], "seat:A")

    def test_runner_failed_attempt_stays_open_then_success_retires(self):
        registry = load_registry(
            payload(
                [runner(publisher="seat:A")],
                [
                    event(1, "e1", "R", "seat:A", status="FAILED"),
                    event(2, "e2", "R", "seat:A", status="SUCCESS"),
                ],
            )
        )
        row = reduce_registry(registry)["items"][0]
        self.assertEqual(row["state"], "RETIRED")
        self.assertEqual(row["first_success"]["event_id"], "e2")
        self.assertEqual(row["attempts"], 2)
        self.assertEqual(row["failed_attempts"], 1)

    def test_first_success_permanently_owns_owner_retirement_receipt(self):
        registry = load_registry(
            payload(
                [owner()],
                [
                    event(10, "first", "O", "owner:browser", status="SUCCESS", receipt="receipt:first"),
                    event(11, "later", "O", "owner:second", status="SUCCESS", receipt="receipt:later"),
                ],
            )
        )
        row = reduce_registry(registry)["items"][0]
        self.assertEqual(row["state"], "RETIRED")
        self.assertEqual(row["first_success"]["receipt"], "receipt:first")
        self.assertEqual([e["event_id"] for e in row["events_after_retirement"]], ["later"])

    def test_owner_failure_does_not_retire_row(self):
        registry = load_registry(
            payload([owner()], [event(1, "fail", "O", "owner:browser", status="FAILED")])
        )
        row = reduce_registry(registry)["items"][0]
        self.assertEqual(row["state"], "OPEN")
        self.assertIsNone(row["first_success"])
        self.assertEqual(row["failed_attempts"], 1)

    def test_events_must_be_append_ordered_and_exact_integer_sequences(self):
        with self.assertRaises(NeedsQueueError) as caught:
            load_registry(
                payload(
                    [owner()],
                    [
                        event(2, "e2", "O", "owner"),
                        event(1, "e1", "O", "owner"),
                    ],
                )
            )
        self.assertEqual(caught.exception.code, "NON_APPEND_ORDER")

        bad = event(True, "e1", "O", "owner")
        with self.assertRaises(NeedsQueueError) as caught:
            load_registry(payload([owner()], [bad]))
        self.assertEqual(caught.exception.code, "INVALID_SEQUENCE")

    def test_duplicate_items_events_sequences_and_capabilities_fail_closed(self):
        with self.assertRaises(NeedsQueueError) as caught:
            load_registry(payload([runner("R"), runner("R")]))
        self.assertEqual(caught.exception.code, "DUPLICATE_ITEM")

        item = runner()
        item["required_capabilities"] = ["linux", "linux"]
        with self.assertRaises(NeedsQueueError) as caught:
            load_registry(payload([item]))
        self.assertEqual(caught.exception.code, "DUPLICATE_CAPABILITY")

        with self.assertRaises(NeedsQueueError) as caught:
            load_registry(
                payload(
                    [owner()],
                    [
                        event(1, "same", "O", "owner", status="FAILED"),
                        event(2, "same", "O", "owner", status="FAILED"),
                    ],
                )
            )
        self.assertEqual(caught.exception.code, "DUPLICATE_EVENT")

        with self.assertRaises(NeedsQueueError) as caught:
            load_registry(
                payload(
                    [owner()],
                    [
                        event(1, "a", "O", "owner", status="FAILED"),
                        event(1, "b", "O", "owner", status="FAILED"),
                    ],
                )
            )
        self.assertEqual(caught.exception.code, "DUPLICATE_SEQUENCE")

    def test_unknown_item_and_unknown_shapes_fail_closed(self):
        with self.assertRaises(NeedsQueueError) as caught:
            load_registry(payload([], [event(1, "e", "missing", "owner")]))
        self.assertEqual(caught.exception.code, "UNKNOWN_ITEM")

        item = runner()
        item["surprise"] = "x"
        with self.assertRaises(NeedsQueueError) as caught:
            load_registry(payload([item]))
        self.assertEqual(caught.exception.code, "INVALID_ITEM_FIELDS")

        bad_event = event(1, "e", "O", "owner")
        bad_event["note"] = "x"
        with self.assertRaises(NeedsQueueError) as caught:
            load_registry(payload([owner()], [bad_event]))
        self.assertEqual(caught.exception.code, "INVALID_EVENT")

    def test_status_normalizes_but_only_success_or_failed_is_accepted(self):
        registry = load_registry(
            payload([owner()], [event(1, "e", "O", "owner", status="success")])
        )
        self.assertEqual(registry["events"][0]["status"], "SUCCESS")

        with self.assertRaises(NeedsQueueError) as caught:
            load_registry(payload([owner()], [event(1, "e", "O", "owner", status="PENDING")]))
        self.assertEqual(caught.exception.code, "INVALID_EVENT_STATUS")

    def test_deterministic_item_order_and_open_counts(self):
        registry = load_registry(
            payload(
                [runner("z", "seat:z"), owner("a"), runner("m", "seat:m")],
                [event(1, "done", "m", "seat:m", status="SUCCESS")],
            )
        )
        out = reduce_registry(registry)
        self.assertEqual([row["id"] for row in out["items"]], ["a", "m", "z"])
        self.assertEqual(
            out["counts"],
            {"open": 2, "retired": 1, "needs_runner_open": 1, "needs_owner_open": 1},
        )

    def test_bool_version_is_rejected(self):
        with self.assertRaises(NeedsQueueError) as caught:
            load_registry({"version": True, "items": [], "events": []})
        self.assertEqual(caught.exception.code, "UNSUPPORTED_VERSION")


if __name__ == "__main__":
    unittest.main()
