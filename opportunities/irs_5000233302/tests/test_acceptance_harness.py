import copy
import json
import tempfile
import unittest
from pathlib import Path

from opportunities.irs_5000233302 import acceptance_harness as ah

ROOT = Path(__file__).resolve().parents[1]


def fixture(name="synthetic_pass.json"):
    return json.loads(
        (ROOT / "fixtures" / name).read_text(encoding="utf-8")
    )


class AcceptanceHarnessTests(unittest.TestCase):
    def test_synthetic_pass_is_deterministic_and_value_free(self):
        f = fixture()
        a = ah.evaluate(f)
        b = ah.evaluate(copy.deepcopy(f))
        self.assertEqual(a, b)
        self.assertEqual(a["state"], "PASS")
        self.assertTrue(all(a["checks"].values()))
        raw = json.dumps(a, sort_keys=True)
        self.assertNotIn("account_class", raw)
        self.assertNotIn("balance_minor", raw)
        self.assertTrue(all(v is False for v in a["authority"].values()))

    def test_fail_fixture_reports_missing_extra_and_mismatch(self):
        r = ah.evaluate(fixture("synthetic_fail.json"))
        self.assertEqual(r["state"], "FAIL")
        self.assertEqual(r["missing_target_keys"], ["SYN-A002"])
        self.assertEqual(r["extra_target_keys"], ["SYN-X999"])
        self.assertEqual(r["mismatched_target_keys"], ["SYN-A001"])

    def test_non_synthetic_classification_rejected(self):
        f = fixture()
        f["classification"] = "PRODUCTION"
        with self.assertRaises(ah.AcceptanceError):
            ah.evaluate(f)

    def test_non_synthetic_pipeline_id_rejected(self):
        f = fixture()
        f["pipeline_id"] = "irs/production"
        with self.assertRaises(ah.AcceptanceError):
            ah.evaluate(f)

    def test_non_synthetic_record_key_rejected(self):
        f = fixture()
        f["source"][0]["key"] = "123-45-6789"
        with self.assertRaises(ah.AcceptanceError):
            ah.evaluate(f)

    def test_duplicate_record_key_rejected(self):
        f = fixture()
        f["actual_target"].append(copy.deepcopy(f["actual_target"][0]))
        with self.assertRaises(ah.AcceptanceError):
            ah.evaluate(f)

    def test_float_rejected(self):
        f = fixture()
        f["actual_target"][0]["value"]["score"] = 1.25
        with self.assertRaises(ah.AcceptanceError):
            ah.evaluate(f)

    def test_nonfinite_json_rejected(self):
        with self.assertRaises(ah.AcceptanceError):
            ah.loads(b'{"x":NaN}')

    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(ah.AcceptanceError):
            ah.loads(b'{"x":1,"x":2}')

    def test_source_lineage_gap_fails(self):
        f = fixture()
        f["source"].pop()
        r = ah.evaluate(f)
        self.assertEqual(r["state"], "FAIL")
        self.assertFalse(r["checks"]["source_lineage_exact"])
        self.assertEqual(
            r["source_lineage_missing_keys"],
            ["SYN-A003"],
        )

    def test_symlink_fixture_refused(self):
        if not hasattr(Path, "symlink_to"):
            self.skipTest("symlink unsupported")
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            target = td / "target.json"
            target.write_text(
                json.dumps(fixture()),
                encoding="utf-8",
            )
            link = td / "link.json"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlink unavailable")
            with self.assertRaises(ah.AcceptanceError):
                ah.load(link)


if __name__ == "__main__":
    unittest.main()
