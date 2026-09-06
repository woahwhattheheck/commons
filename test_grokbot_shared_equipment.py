#!/usr/bin/env python3
"""Hermetic tests: shared_equipment GrokBot lifecycle (Astra SPARK leftover)."""

from __future__ import annotations

import tempfile
import threading
import time
import unittest
from pathlib import Path

from integrations.grokbot_control.gateway import build_server
from integrations.shared_equipment.peers import GrokBotEquipment
from integrations.shared_equipment.services import CombinedCatalog


class _FakeCommons:
    def tools(self, **_kwargs):
        return [{"name": "commons_noop", "description": "", "inputSchema": {}}]

    def call(self, name, arguments):
        return {"name": name, "arguments": arguments}


class GrokBotEquipmentFixture:
    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        db = Path(self.tmp.name) / "runs.sqlite3"
        self.server = build_server(
            host="127.0.0.1", port=0, db_path=db, mode="echo"
        )
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = "http://127.0.0.1:%d" % self.port
        self.eq = GrokBotEquipment(self.base)
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


class TestGrokBotSharedEquipment(unittest.TestCase):
    def test_tool_names_and_catalog_extension(self):
        names = {t["name"] for t in GrokBotEquipment().tools()}
        expected = {
            "grokbot_submit",
            "grokbot_inspect",
            "grokbot_follow_up",
            "grokbot_cancel",
            "grokbot_session",
            "grokbot_events",
            "grokbot_pools",
            "grokbot_health",
            "grokbot_case_from_autopsy_offer",
            "grokbot_receipt_row_from_case",
            "diagnostic_contract_card",
            "diagnostic_receipt_card",
            "diagnostic_fulfill_deadline_card",
            "diagnostic_fulfill_sla_card",
            "autopsy_fulfill_deadline_card",
            "autopsy_fulfill_sla_card",
            "autopsy_case_card",
            "autopsy_receipt_card",
            "open_obligations_cash_card",
        }
        self.assertEqual(names, expected)
        catalog = CombinedCatalog(_FakeCommons())
        catalog.extensions.append(GrokBotEquipment("http://127.0.0.1:9"))
        catalog_names = {t["name"] for t in catalog.tools()}
        self.assertTrue(expected.issubset(catalog_names))
        self.assertIn("commons_noop", catalog_names)
        submit = next(
            t for t in GrokBotEquipment().tools() if t["name"] == "grokbot_submit"
        )
        self.assertIn("case", submit["inputSchema"]["properties"])

    def test_submit_inspect_follow_up_cancel_attribution(self):
        with GrokBotEquipmentFixture() as fx:
            pools = fx.eq.call("grokbot_pools", {})
            self.assertIn("grokbot", pools.get("pools", []))

            submitted = fx.eq.call(
                "grokbot_submit",
                {
                    "prompt": "equipment ping",
                    "pool_id": "grokbot",
                    "seat": "SPARK",
                    "async": False,
                },
            )
            self.assertEqual(submitted.get("status"), "completed")
            self.assertEqual(
                submitted["attribution"],
                {
                    "pool_id": "grokbot",
                    "seat": "SPARK",
                    "harness": "grokbot",
                    "model": "Grok",
                },
            )
            run_id = submitted["run_id"]
            session_id = submitted["session_id"]

            inspected = fx.eq.call(
                "grokbot_inspect", {"run_id": run_id, "wait_ms": 1000}
            )
            self.assertEqual(inspected["run_id"], run_id)

            followed = fx.eq.call(
                "grokbot_follow_up",
                {"run_id": run_id, "prompt": "second turn", "async": False},
            )
            self.assertEqual(followed["session_id"], session_id)
            self.assertNotEqual(followed["run_id"], run_id)

            session = fx.eq.call("grokbot_session", {"session_id": session_id})
            self.assertGreaterEqual(len(session.get("runs", [])), 2)

            async_sub = fx.eq.call(
                "grokbot_submit",
                {"prompt": "cancel target", "async": True},
            )
            cancelled = fx.eq.call(
                "grokbot_cancel", {"run_id": async_sub["run_id"]}
            )
            self.assertTrue(cancelled.get("ok"))
            self.assertIn(
                cancelled.get("status"),
                ("cancelled", "completed", "queued", "running"),
            )

            events = fx.eq.call(
                "grokbot_events", {"after": 0, "pool_id": "grokbot"}
            )
            self.assertGreaterEqual(len(events.get("events") or []), 1)

    def test_submit_case_round_trip(self):
        with GrokBotEquipmentFixture() as fx:
            submitted = fx.eq.call(
                "grokbot_submit",
                {
                    "prompt": "paid case ping",
                    "async": False,
                    "case": {
                        "offer_id": "sku-autopsy-29",
                        "case_ref": "case-demo-1",
                        "client_reference_id": "cref-demo",
                        "sku": "sku-autopsy-29",
                    },
                },
            )
            self.assertEqual(submitted.get("status"), "completed")
            self.assertEqual(submitted["case"]["offer_id"], "sku-autopsy-29")
            followed = fx.eq.call(
                "grokbot_follow_up",
                {
                    "run_id": submitted["run_id"],
                    "prompt": "follow",
                    "async": False,
                },
            )
            self.assertEqual(followed["case"]["case_ref"], "case-demo-1")

    def test_health_reports_memory_guard(self):
        with GrokBotEquipmentFixture() as fx:
            health = fx.eq.call("grokbot_health", {})
            self.assertTrue(health.get("ok"))
            self.assertEqual(health.get("service"), "commons-grokbot-control")
            self.assertIn("memory_guard", health)
            self.assertIn("holding", health["memory_guard"])

    def test_unreachable_control_is_honest(self):
        eq = GrokBotEquipment("http://127.0.0.1:9")
        out = eq.call("grokbot_pools", {})
        self.assertEqual(out.get("error"), "grokbot_control_unreachable")
        self.assertIn("note", out)

    def test_paid_case_equipment_helpers(self):
        eq = GrokBotEquipment("http://127.0.0.1:9")
        built = eq.call(
            "grokbot_case_from_autopsy_offer",
            {
                "case_ref": "opaque-equip-1",
                "client_reference_id": "afa29_x_a_v1",
            },
        )
        self.assertTrue(built.get("ok"))
        case = built["case"]
        self.assertEqual(case["case_ref"], "opaque-equip-1")
        self.assertEqual(case["offer_id"], "agent-failure-autopsy-29")
        receipt = eq.call(
            "grokbot_receipt_row_from_case",
            {
                "case": case,
                "submit_response": {
                    "run_id": "run_equip_1",
                    "session_id": "sess_equip_1",
                },
            },
        )
        self.assertTrue(receipt.get("ok"))
        row = receipt["case_row"]
        self.assertEqual(row["g2_run_id"], "run_equip_1")
        self.assertEqual(row["g2_session_id"], "sess_equip_1")
        self.assertEqual(row["state"], "UNVERIFIED")
        bad = eq.call("grokbot_case_from_autopsy_offer", {"case_ref": ""})
        self.assertFalse(bad.get("ok"))
        self.assertEqual(bad.get("error"), "invalid_case")

    def test_paid_case_equipment_live_e2e(self):
        """Live echo: case_from_autopsy_offer → submit(case) → receipt bind."""
        with GrokBotEquipmentFixture() as fx:
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
            self.assertEqual(submitted["case"], case)
            self.assertEqual(submitted["case"]["case_ref"], "opaque-e2e-1")
            receipt = fx.eq.call(
                "grokbot_receipt_row_from_case",
                {"case": case, "submit_response": submitted},
            )
            self.assertTrue(receipt.get("ok"))
            row = receipt["case_row"]
            self.assertEqual(row["g2_run_id"], submitted["run_id"])
            self.assertEqual(row["g2_session_id"], submitted["session_id"])
            self.assertEqual(row["state"], "UNVERIFIED")
            inspected = fx.eq.call(
                "grokbot_inspect",
                {"run_id": submitted["run_id"], "wait_ms": 1000},
            )
            self.assertEqual(inspected["case"]["case_ref"], case["case_ref"])

    def test_role_equipment_route_present(self):
        import json

        path = (
            Path(__file__).resolve().parent
            / "integrations"
            / "shared_equipment"
            / "role_equipment.json"
        )
        data = json.loads(path.read_text(encoding="utf-8"))
        routes = {r["name"]: r for r in data["access_routes"]}
        g2 = routes["owner_pc_grokbot_control"]
        self.assertEqual(g2["kind"], "grokbot_control")
        self.assertEqual(g2["base_url"], "http://127.0.0.1:8881")
        self.assertEqual(g2["pool_id"], "grokbot")
        self.assertIn("grokbot_submit", g2["equipment_tools"])
        self.assertIn("grokbot_health", g2["equipment_tools"])
        self.assertIn("grokbot_case_from_autopsy_offer", g2["equipment_tools"])
        self.assertIn("grokbot_receipt_row_from_case", g2["equipment_tools"])
        self.assertIn("diagnostic_contract_card", g2["equipment_tools"])
        self.assertIn("diagnostic_receipt_card", g2["equipment_tools"])
        self.assertIn("diagnostic_fulfill_deadline_card", g2["equipment_tools"])
        self.assertIn("diagnostic_fulfill_sla_card", g2["equipment_tools"])
        self.assertIn("autopsy_fulfill_deadline_card", g2["equipment_tools"])
        self.assertIn("autopsy_fulfill_sla_card", g2["equipment_tools"])
        self.assertIn("autopsy_case_card", g2["equipment_tools"])
        self.assertIn("autopsy_receipt_card", g2["equipment_tools"])
        self.assertIn("open_obligations_cash_card", g2["equipment_tools"])


if __name__ == "__main__":
    unittest.main()
