#!/usr/bin/env python3
"""LATCH canary: BUILDABLE CURRENT_WORK rows close from 40-hex SHA + claimed paths.

Close fields are the instrument projection keys already used by
host/current_work.py reconcile_item: status CLOSED and main_sha 40 hex.
DEVICE_PINNED stays pinned. Chat is not close evidence.
"""
from __future__ import annotations

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "host"))
import current_work as cw

ROOT = os.path.dirname(os.path.abspath(__file__))
CLOSE_IDS = (
    "current-work-ledger-20260828-01",
    "opportunity-registry-20260828-02",
)
PIN_ID = "device-pin-no-fire-20260828-01"
RECEIPT = os.path.join("p", "latch-current-work-close-20260917-01.md")
SIDECAR = os.path.join("revenue", "ip", "opportunity_current_work_item.json")


class LatchCurrentWorkCloseTests(unittest.TestCase):
    def catalog(self):
        data = cw.load_catalog(cw._read(ROOT, cw.DEFAULT_CATALOG))
        self.assertNotIn("error", data)
        self.assertEqual(cw.validate_catalog(data), [])
        return data

    def items_by_id(self):
        catalog = self.catalog()
        rows = {}
        for item in catalog.get("items") or []:
            if isinstance(item, dict) and item.get("id"):
                rows[item["id"]] = item
        return rows

    def test_buildable_rows_persist_instrument_close_fields(self):
        rows = self.items_by_id()
        for job_id in CLOSE_IDS:
            item = rows.get(job_id)
            self.assertIsInstance(item, dict, job_id)
            self.assertEqual(item.get("kind"), "BUILDABLE", job_id)
            self.assertEqual(item.get("status"), "CLOSED", job_id)
            main_sha = str(item.get("main_sha") or "")
            self.assertRegex(main_sha, r"^[0-9a-f]{40}$", job_id)
            claimed = list(item.get("claimed_paths") or [])
            self.assertTrue(claimed, job_id)
            for path in claimed:
                self.assertTrue(
                    os.path.isfile(os.path.join(ROOT, path)),
                    "%s missing %s" % (job_id, path),
                )
            closed = cw.reconcile_item(
                item,
                {
                    "main_sha": main_sha,
                    "main_paths": {path: True for path in claimed},
                },
            )
            self.assertEqual(closed["status"], "CLOSED", job_id)
            self.assertEqual(closed["main_sha"], main_sha, job_id)
            chatter = cw.reconcile_item(
                item,
                {"chat_said_done": True, "ntfy_200": True, "slack_text": "done"},
            )
            self.assertEqual(chatter["status"], "OPEN", job_id)

    def test_device_pin_is_unchanged(self):
        pin = self.items_by_id().get(PIN_ID)
        self.assertIsInstance(pin, dict)
        self.assertEqual(pin.get("kind"), "DEVICE_PINNED")
        self.assertNotEqual(pin.get("status"), "CLOSED")
        self.assertFalse(bool(pin.get("main_sha")))
        pinned = cw.reconcile_item(
            pin,
            {"main_sha": "a" * 40, "chat_said_done": True},
        )
        self.assertEqual(pinned["status"], "PINNED")
        self.assertFalse(pinned["executable"])

    def test_receipt_and_opportunity_sidecar_match_close(self):
        self.assertTrue(os.path.isfile(os.path.join(ROOT, RECEIPT)))
        text = cw._read(ROOT, RECEIPT)
        self.assertIn("id: latch-current-work-close-20260917-01", text)
        self.assertIn("current-work-ledger-20260828-01", text)
        self.assertIn("opportunity-registry-20260828-02", text)
        self.assertIn("device-pin-no-fire-20260828-01", text)
        sidecar = json.loads(cw._read(ROOT, SIDECAR))
        item = self.items_by_id()["opportunity-registry-20260828-02"]
        self.assertEqual(sidecar, item)


if __name__ == "__main__":
    unittest.main()
