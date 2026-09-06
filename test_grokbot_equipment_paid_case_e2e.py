#!/usr/bin/env python3
"""Hermetic live echo e2e: equipment case → submit → receipt bind."""

from __future__ import annotations

import tempfile
import threading
import time
import unittest
from pathlib import Path

from integrations.grokbot_control.gateway import build_server
from integrations.shared_equipment.peers import GrokBotEquipment


class _Fixture:
    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        db = Path(self.tmp.name) / "runs.sqlite3"
        self.server = build_server(
            host="127.0.0.1", port=0, db_path=db, mode="echo"
        )
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(
            target=self.server.serve_forever, daemon=True
        )
        self.thread.start()
        self.eq = GrokBotEquipment("http://127.0.0.1:%d" % self.port)
        for _ in range(50):
            health = self.eq._request("GET", "/health")
            if health.get("ok"):
                break
            time.sleep(0.05)
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()
        self.server.controller.store.close()
        self.tmp.cleanup()


class TestPaidCaseEquipmentLiveE2E(unittest.TestCase):
    def test_case_submit_receipt_live_echo(self):
        with _Fixture() as fx:
            built = fx.eq.call(
                "grokbot_case_from_autopsy_offer",
                {
                    "case_ref": "opaque-e2e-1",
                    "client_reference_id": "afa29_x_a_v1",
                },
            )
            self.assertTrue(built.get("ok"))
            case = built["case"]
            submitted = fx.eq.call(
                "grokbot_submit",
                {
                    "prompt": "e2e autopsy work",
                    "seat": "SPARK",
                    "async": False,
                    "case": case,
                },
            )
            self.assertEqual(submitted.get("status"), "completed")
            self.assertEqual(submitted["case"]["case_ref"], "opaque-e2e-1")
            receipt = fx.eq.call(
                "grokbot_receipt_row_from_case",
                {"case": case, "submit_response": submitted},
            )
            self.assertTrue(receipt.get("ok"))
            row = receipt["case_row"]
            self.assertEqual(row["g2_run_id"], submitted["run_id"])
            self.assertEqual(row["g2_session_id"], submitted["session_id"])
            self.assertEqual(row["client_reference_id"], "afa29_x_a_v1")
            self.assertEqual(row["state"], "UNVERIFIED")
            inspected = fx.eq.call(
                "grokbot_inspect",
                {"run_id": submitted["run_id"], "wait_ms": 1000},
            )
            self.assertEqual(inspected["case"]["case_ref"], "opaque-e2e-1")


if __name__ == "__main__":
    unittest.main()
