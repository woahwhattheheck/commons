"""Email egress selects only final authored fields and holds before mutation."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from host import swarm_mail as mail


class _Result:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row


class _DispatchConnection:
    def __init__(self, row, address):
        self.row = row
        self.address = address
        self.rollbacks = 0
        self.commits = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def execute(self, sql, _args=()):
        if sql == "BEGIN IMMEDIATE":
            return _Result(None)
        if "FROM drafts WHERE send_key" in sql:
            return _Result(self.row)
        if "FROM suppressions" in sql:
            return _Result(None)
        if "SELECT address FROM inboxes" in sql:
            return _Result({"address": self.address})
        raise AssertionError("unexpected database access: " + sql)


class SwarmMailOutboundIdentityTests(unittest.TestCase):
    def setUp(self):
        mail._IDENTITY_POLICY = None

    def test_queue_hold_precedes_every_database_mutation(self):
        class NoDatabase:
            def __getattr__(self, name):
                raise AssertionError("blocked draft touched database: " + name)

        with patch.object(mail, "route_sku", return_value={"inbox_id": "sales"}), \
             patch.object(mail, "inbox_by_id", return_value={
                 "inbox_id": "sales",
                 "address_state": "MEASURED",
                 "daily_new_thread_limit": 5,
             }):
            with self.assertRaises(mail.OutboundIdentityError) as raised:
                mail.queue_message(
                    NoDatabase(),
                    recipient="owner@example.invalid",
                    sku_id="sku",
                    prospect_key="private-prospect",
                    subject="Astra update",
                    body="Private offer details. Unsubscribe here.",
                    send_key="private-send",
                    occurred_at="2026-09-20T00:00:00Z",
                )
        decision = raised.exception.decision
        self.assertEqual(decision["matched_fields"], ["subject"])
        self.assertEqual(decision["matched_terms"], ["Astra"])
        self.assertFalse(decision["delivered"])
        self.assertFalse(decision["incident"])
        self.assertNotIn("Private offer details", str(decision))

    def test_model_named_from_rolls_back_before_claim_or_sendmail(self):
        row = {
            "state": "QUEUED",
            "recipient_commitment": "recipient",
            "inbox_id": "sales",
            "recipient": "owner@example.invalid",
            "subject": "Neutral update",
            "body": "Neutral body. Unsubscribe here.",
            "sku_id": "sku",
            "prospect_key": "private-prospect",
            "thread_key": "opaque:thread",
            "message_id": "<message@pending.invalid>",
            "send_key": "private-send",
        }
        connection = _DispatchConnection(row, "astra@example.invalid")
        with tempfile.TemporaryDirectory() as directory:
            adapter = Path(directory) / "sendmail"
            adapter.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            os.chmod(adapter, 0o700)
            with patch.object(mail.subprocess, "run") as run:
                with self.assertRaises(mail.OutboundIdentityError) as raised:
                    mail.dispatch_message(
                        connection,
                        "private-send",
                        adapter,
                        "2026-09-20T00:00:00Z",
                    )
        self.assertEqual(raised.exception.decision["matched_fields"], ["from"])
        self.assertEqual(connection.rollbacks, 1)
        run.assert_not_called()
        self.assertEqual(row["state"], "QUEUED")

    def test_owner_neutral_wire_is_allowed(self):
        row = {
            "inbox_id": "sales",
            "recipient": "recipient@example.invalid",
            "subject": "Neutral update",
            "body": "Neutral body. Unsubscribe here.",
            "sku_id": "sku",
            "send_key": "private-send",
            "message_id": "<message@pending.invalid>",
        }
        connection = _DispatchConnection(row, "owner@example.invalid")
        with patch.object(mail, "opaque_ref", return_value="opaque:send-reference"):
            wire = mail._wire_message(connection, row)
        self.assertIn(b"From: owner@example.invalid", wire)
        self.assertIn(b"Subject: Neutral update", wire)


if __name__ == "__main__":
    unittest.main()
