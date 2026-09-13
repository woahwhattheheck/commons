from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("ai_builders_autopsy_demo", HERE / "demo_server.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load demo_server")
demo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(demo)


class DemoTests(unittest.TestCase):
    def test_page_explains_review_boundary(self):
        self.assertIn("PEER_DRAFT", demo.PAGE)
        self.assertIn("Run the public synthetic case", demo.PAGE)
        self.assertNotIn("buyer-ready by automation", demo.PAGE.lower())

    def test_synthetic_payload_validates_real_core(self):
        payload = demo.build_payload()
        self.assertEqual(payload["mode"], "PUBLIC_SYNTHETIC_DEMO")
        self.assertTrue(payload["validation"]["ok"], payload["validation"])
        self.assertFalse(payload["truth"]["buyer_data_used"])
        self.assertFalse(payload["truth"]["payment_claimed"])
        self.assertFalse(payload["truth"]["human_review_claimed"])
        self.assertFalse(payload["truth"]["external_action_authorized"])
        self.assertIsInstance(payload["intake"], dict)
        self.assertIsInstance(payload["report"], dict)

    def test_payload_is_json_serializable(self):
        encoded = json.dumps(demo.build_payload(), sort_keys=True)
        self.assertIn("Agent Failure Autopsy", encoded)

    def test_example_reader_refuses_non_example_path(self):
        with self.assertRaises(ValueError):
            demo._read_json(HERE / "READINESS.json")


if __name__ == "__main__":
    unittest.main()
