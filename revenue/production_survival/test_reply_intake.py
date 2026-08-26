from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import reply_intake


ROUTES = (
    ("OPT_OUT", "DNC/CLOSE"),
    ("NEGATIVE", "CLOSE"),
    ("QUESTION", "DRAFT_REPLY"),
    ("POSITIVE_SCOPE", "NEEDS_ACCEPTANCE"),
    ("NEEDS_HUMAN", "ESCALATE_ONLY_IF_BUYER_REQUESTS_BRYCE"),
)
PRIVATE_FIELDS = (
    "body",
    "raw",
    "raw_body",
    "headers",
    "email",
    "from",
    "to",
    "subject",
    "credentials",
    "password",
    "token",
    "secret",
    "content",
    "message",
    "payload",
    "private",
)
FORBIDDEN_CLAIMS = (
    "replied",
    "accepted",
    "invoiced",
    "authorized",
    "settled",
    "delivered",
    "paid",
)


def _sha(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _envelope(
    classification: str,
    *,
    event_ref: str | None = None,
    payload_sha256: str | None = None,
    prospect_key: str | None = None,
) -> dict[str, str]:
    token = classification.lower().replace("_", "-")
    return {
        "event_ref": event_ref or f"opaque:fixture-{token}-event-01",
        "received_at": "2026-08-26T17:32:00Z",
        "prospect_key": prospect_key or f"prospect.{token}.01",
        "payload_sha256": payload_sha256 or _sha(f"opaque-payload-{token}"),
        "classification": classification,
    }


class ReplyIntakeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.store = Path(self.temp.name) / "store"
        self.schema = reply_intake.load_schema()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _record(self, envelope: dict[str, str]) -> bytes:
        return reply_intake.record_envelope(envelope, self.store)

    def test_five_route_fixtures_pass(self) -> None:
        for classification, next_action in ROUTES:
            with self.subTest(classification=classification):
                envelope = _envelope(classification)
                blob = self._record(envelope)
                receipt = json.loads(blob.decode("utf-8"))
                reply_intake.validate_receipt(receipt, self.schema)
                self.assertEqual(receipt["classification"], classification)
                self.assertEqual(receipt["next_action"], next_action)
                self.assertEqual(receipt["status"], "RECORDED")
                self.assertEqual(receipt["event_ref"], envelope["event_ref"])
                self.assertEqual(receipt["payload_sha256"], envelope["payload_sha256"])
                self.assertEqual(
                    receipt["receipt_id"],
                    reply_intake.receipt_id_for(envelope["event_ref"]),
                )
                text = blob.decode("utf-8").lower()
                for claim in FORBIDDEN_CLAIMS:
                    self.assertNotRegex(text, rf"\b{claim}\b")

    def test_identical_replay_is_byte_identical(self) -> None:
        envelope = _envelope("QUESTION")
        first = self._record(envelope)
        second = self._record(dict(envelope))
        self.assertEqual(first, second)
        path = reply_intake.store_path_for(self.store, envelope["event_ref"])
        self.assertEqual(first, path.read_bytes())
        third_store = Path(self.temp.name) / "replay-cli"
        envelope_path = Path(self.temp.name) / "question.json"
        envelope_path.write_bytes(reply_intake.canonical_bytes(envelope))
        command = [
            sys.executable,
            str(Path(__file__).with_name("reply_intake.py")),
            "--envelope",
            str(envelope_path),
            "--store",
            str(third_store),
        ]
        first_cli = subprocess.run(command, check=False, capture_output=True)
        second_cli = subprocess.run(command, check=False, capture_output=True)
        self.assertEqual(first_cli.returncode, 0, first_cli.stderr)
        self.assertEqual(second_cli.returncode, 0, second_cli.stderr)
        self.assertEqual(first_cli.stdout, second_cli.stdout)
        self.assertEqual(
            first_cli.stdout,
            reply_intake.store_path_for(third_store, envelope["event_ref"]).read_bytes(),
        )

    def test_same_event_ref_different_hash_fails_nonzero(self) -> None:
        envelope = _envelope("NEGATIVE")
        self._record(envelope)
        colliding = dict(envelope)
        colliding["payload_sha256"] = _sha("different-opaque-payload")
        self.assertNotEqual(envelope["payload_sha256"], colliding["payload_sha256"])
        with self.assertRaises(reply_intake.CollisionError):
            self._record(colliding)
        envelope_path = Path(self.temp.name) / "negative.json"
        collide_path = Path(self.temp.name) / "negative-collide.json"
        envelope_path.write_bytes(reply_intake.canonical_bytes(envelope))
        collide_path.write_bytes(reply_intake.canonical_bytes(colliding))
        script = str(Path(__file__).with_name("reply_intake.py"))
        store = Path(self.temp.name) / "cli-store"
        first = subprocess.run(
            [sys.executable, script, "--envelope", str(envelope_path), "--store", str(store)],
            check=False,
            capture_output=True,
        )
        second = subprocess.run(
            [sys.executable, script, "--envelope", str(collide_path), "--store", str(store)],
            check=False,
            capture_output=True,
        )
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertNotEqual(second.returncode, 0)
        self.assertEqual(second.returncode, reply_intake.EXIT_COLLISION)

    def test_raw_private_fields_fail_schema(self) -> None:
        envelope = _envelope("OPT_OUT")
        reply_intake.validate_envelope(envelope, self.schema)
        self.assertFalse(self.schema["$defs"]["envelope"]["additionalProperties"])
        self.assertEqual(
            self.schema["$defs"]["envelope"]["propertyNames"]["enum"],
            list(reply_intake.ENVELOPE_FIELDS),
        )
        for field in PRIVATE_FIELDS:
            with self.subTest(field=field):
                dirty = dict(envelope)
                dirty[field] = "redacted-private-value"
                with self.assertRaises(reply_intake.SchemaError):
                    reply_intake.validate_envelope(dirty, self.schema)
                with self.assertRaises(reply_intake.SchemaError):
                    self._record(dirty)
        envelope_path = Path(self.temp.name) / "private.json"
        dirty = dict(envelope)
        dirty["body"] = "do-not-store"
        envelope_path.write_bytes(reply_intake.canonical_bytes(dirty))
        result = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).with_name("reply_intake.py")),
                "--envelope",
                str(envelope_path),
                "--store",
                str(self.store),
            ],
            check=False,
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.returncode, reply_intake.EXIT_SCHEMA)

    def test_positive_scope_stops_only_at_needs_acceptance(self) -> None:
        envelope = _envelope("POSITIVE_SCOPE")
        blob = self._record(envelope)
        receipt = json.loads(blob.decode("utf-8"))
        self.assertEqual(receipt["next_action"], "NEEDS_ACCEPTANCE")
        other_actions = {
            next_action
            for classification, next_action in ROUTES
            if classification != "POSITIVE_SCOPE"
        }
        self.assertNotIn(receipt["next_action"], other_actions)
        mutated = dict(receipt)
        for next_action in other_actions:
            mutated["next_action"] = next_action
            with self.assertRaises(reply_intake.SchemaError):
                reply_intake.validate_receipt(mutated, self.schema)
        text = blob.decode("utf-8").lower()
        for claim in FORBIDDEN_CLAIMS:
            self.assertNotRegex(text, rf"\b{claim}\b")


if __name__ == "__main__":
    unittest.main()
