#!/usr/bin/env python3
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from host import strict_receipt as sr  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "fixtures", "strict_receipt_poison.json")


class StrictReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(FIXTURE, "r", encoding="utf-8") as fh:
            cls.fixture = json.load(fh)

    def test_valid_receipt_exact_cartesian_panel(self):
        fx = self.fixture
        got = sr.validate_receipt(fx["valid_receipt"], fx["requested_panel"], fx["live_canonical_sha"])
        self.assertEqual(len(got["cells"]), 4)
        self.assertEqual([(c["seed"], c["opponent"]) for c in got["cells"]], [(101, "alpha"), (101, "beta"), (102, "alpha"), (102, "beta")])

    def _apply(self, mutation):
        receipt = copy.deepcopy(self.fixture["valid_receipt"])
        if "cell" in mutation:
            receipt["cells"][mutation["cell"]][mutation["field"]] = mutation["value"]
        if "append_cell" in mutation:
            receipt["cells"].append(copy.deepcopy(receipt["cells"][mutation["append_cell"]]))
        if "drop_cell" in mutation:
            del receipt["cells"][mutation["drop_cell"]]
        if "append" in mutation:
            receipt["cells"].append(copy.deepcopy(mutation["append"]))
        if "canonical_sha" in mutation:
            receipt["canonical_sha"] = mutation["canonical_sha"]
        if "panel_seed" in mutation:
            item = mutation["panel_seed"]
            receipt["panel"]["seeds"][item["index"]] = item["value"]
        return receipt

    def test_all_declared_poison_fixtures_fail_closed(self):
        fx = self.fixture
        for poison in fx["poisons"]:
            with self.subTest(poison=poison["name"]):
                receipt = self._apply(poison["mutation"])
                with self.assertRaisesRegex(ValueError, poison["error"]):
                    sr.validate_receipt(receipt, fx["requested_panel"], fx["live_canonical_sha"])

    def test_duplicate_json_key_rejected_before_indexing(self):
        text = '{"schema":"commons-strict-receipt/v1","schema":"poison"}'
        with self.assertRaisesRegex(ValueError, "duplicate JSON key before indexing"):
            sr.loads_strict(text)

    def test_nonfinite_json_score_rejected(self):
        with self.assertRaisesRegex(ValueError, "non-finite JSON value"):
            sr.loads_strict('{"score":NaN}')

    def test_finite_python_score_guard_rejects_inf_and_bool(self):
        fx = self.fixture
        for score in (float("inf"), True):
            receipt = copy.deepcopy(fx["valid_receipt"])
            receipt["cells"][0]["score"] = score
            with self.subTest(score=score):
                with self.assertRaisesRegex(ValueError, "finite numeric score"):
                    sr.validate_receipt(receipt, fx["requested_panel"], fx["live_canonical_sha"])

    def test_requested_panel_itself_rejects_duplicate_members(self):
        with self.assertRaisesRegex(ValueError, "duplicate requested seed"):
            sr.normalize_panel({"seeds": [1, 1], "opponents": ["a"]})
        with self.assertRaisesRegex(ValueError, "duplicate requested opponent"):
            sr.normalize_panel({"seeds": [1], "opponents": ["a", "a"]})

    def test_panel_order_is_literal_not_set_equivalent(self):
        fx = self.fixture
        receipt = copy.deepcopy(fx["valid_receipt"])
        receipt["panel"]["opponents"] = ["beta", "alpha"]
        with self.assertRaisesRegex(ValueError, "literal requested panel"):
            sr.validate_receipt(receipt, fx["requested_panel"], fx["live_canonical_sha"])

    def test_opponent_whitespace_is_literal_identity_not_normalized(self):
        fx = self.fixture
        requested = copy.deepcopy(fx["requested_panel"])
        requested["opponents"][0] = " alpha "

        # This is the predecessor-killing poison: the old implementation
        # stripped the caller's requested opponent to "alpha" and accepted the
        # unmodified receipt. Literal panel identity must reject substitution.
        with self.assertRaisesRegex(ValueError, "literal requested panel"):
            sr.validate_receipt(fx["valid_receipt"], requested, fx["live_canonical_sha"])

        # Whitespace is still permitted when it is actually part of the
        # requested identifier; panel and cell coordinates preserve it exactly.
        receipt = copy.deepcopy(fx["valid_receipt"])
        receipt["panel"] = copy.deepcopy(requested)
        for cell in receipt["cells"]:
            if cell["opponent"] == "alpha":
                cell["opponent"] = " alpha "
        got = sr.validate_receipt(receipt, requested, fx["live_canonical_sha"])
        self.assertEqual(got["panel"]["opponents"][0], " alpha ")
        self.assertIn(" alpha ", {cell["opponent"] for cell in got["cells"]})

    def test_exact_cartesian_requires_all_pairs_even_when_count_matches(self):
        fx = self.fixture
        receipt = copy.deepcopy(fx["valid_receipt"])
        receipt["cells"][-1] = {"seed": 999, "opponent": "beta", "score": 4.0}
        with self.assertRaisesRegex(ValueError, "cartesian membership mismatch"):
            sr.validate_receipt(receipt, fx["requested_panel"], fx["live_canonical_sha"])

    def test_cli_validates_against_literal_panel_and_live_sha(self):
        fx = self.fixture
        with tempfile.TemporaryDirectory() as tmp:
            receipt_path = os.path.join(tmp, "receipt.json")
            panel_path = os.path.join(tmp, "panel.json")
            with open(receipt_path, "w", encoding="utf-8") as fh:
                json.dump(fx["valid_receipt"], fh)
            with open(panel_path, "w", encoding="utf-8") as fh:
                json.dump(fx["requested_panel"], fh)
            script = os.path.join(HERE, "host", "strict_receipt.py")
            result = subprocess.run([sys.executable, script, receipt_path, "--requested-panel", panel_path, "--live-canonical-sha", fx["live_canonical_sha"]], text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["canonical_sha"], fx["live_canonical_sha"])


if __name__ == "__main__":
    unittest.main()
