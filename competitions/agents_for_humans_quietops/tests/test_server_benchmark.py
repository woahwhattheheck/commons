import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from quietops.benchmark import run_benchmark
from quietops.server import make_server


class ServerBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server(port=0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(timeout=2)

    def _get_json(self, path):
        with urlopen(self.base + path, timeout=2) as r:
            return json.loads(r.read())

    def _post_json(self, obj):
        data = json.dumps(obj).encode()
        req = Request(self.base + "/api/process", data=data, headers={"Content-Type":"application/json"}, method="POST")
        with urlopen(req, timeout=2) as r:
            return json.loads(r.read())

    def test_home_is_product_ui(self):
        with urlopen(self.base + "/", timeout=2) as r:
            body = r.read().decode()
        self.assertIn("QuietOps", body)
        self.assertIn("Process item", body)

    def test_autonomous_http_demo_gets_receipt(self):
        item = self._get_json("/demo/autonomous")
        out = self._post_json(item)
        self.assertEqual(out["decision"]["authority"], "AUTONOMOUS_REVERSIBLE")
        self.assertIsNotNone(out["receipt"])
        self.assertTrue(out["followup"]["human_decision_required"])
        self.assertEqual(out["followup"]["kind"], "RECONCILIATION_VARIANCE_DECISION")

    def test_human_http_demo_has_no_receipt(self):
        item = self._get_json("/demo/human")
        out = self._post_json(item)
        self.assertEqual(out["decision"]["authority"], "HUMAN_DECISION_REQUIRED")
        self.assertIsNone(out["receipt"])
        self.assertTrue(out["followup"]["human_decision_required"])

    def test_bad_json_is_400(self):
        req = Request(self.base + "/api/process", data=b'{"a":1,"a":2}', method="POST")
        with self.assertRaises(HTTPError) as cm:
            urlopen(req, timeout=2)
        self.assertEqual(cm.exception.code, 400)

    def test_benchmark_has_zero_boundary_errors(self):
        result = run_benchmark(per_kind=20)
        self.assertTrue(result["pass"])
        self.assertEqual(result["false_autonomous"], 0)
        self.assertEqual(result["false_human"], 0)
        self.assertEqual(result["adversarial_promotion_failures"], 0)
        self.assertEqual(result["outcome_escalation_failures"], 0)
        self.assertEqual(result["outcome_escalation_cases"], 20)


if __name__ == "__main__":
    unittest.main()
