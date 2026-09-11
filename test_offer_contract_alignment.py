import json
import tempfile
import unittest
from pathlib import Path

import host.offer_contract_alignment as oca


class OfferContractAlignmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.contract = {
            "id": "demo-offer",
            "terms": {
                "price_usd": 199,
                "deliverables": ["JSON receipt", "Static HTML receipt"],
                "acceptance": ["Hash matches", "Loader exits zero", "Timeout fails closed"],
                "refund": "Refund if the accepted diagnostic misses the delivery window.",
            },
        }
        self.catalog = {
            "listings": [
                {
                    "id": "demo-offer",
                    "source_artifact": {"blob_sha": "0" * 40},
                    "pricing": {"components": [{"amount": "199.00"}]},
                }
            ],
            "funnels": {
                "demo-offer": {
                    "fulfillment": {
                        "deliverables": ["JSON receipt", "Static HTML receipt"],
                        "acceptance": ["Hash matches", "loader exits zero"],
                        "refund": "  Refund if the accepted diagnostic misses the delivery window.  ",
                    }
                }
            },
        }
        self._write("contract.json", self.contract)
        self._write("catalog.json", self.catalog)
        self.catalog["listings"][0]["source_artifact"]["blob_sha"] = oca._git_blob_sha1(
            (self.root / "contract.json").read_bytes()
        )
        self._write("catalog.json", self.catalog)
        self.spec = {
            "schema_version": "offer-contract-alignment/v1",
            "documents": {
                "contract_doc": {"path": "contract.json"},
                "catalog_doc": {"path": "catalog.json"},
            },
            "views": {
                "contract": {"document": "contract_doc", "pointer": ""},
                "listing": {
                    "document": "catalog_doc",
                    "match": {"collection": "/listings", "field": "id", "equals": "demo-offer"},
                },
                "funnel": {"document": "catalog_doc", "pointer": "/funnels/demo-offer"},
            },
            "rules": [
                {
                    "id": "price",
                    "kind": "number_equal",
                    "source": {"view": "contract", "pointer": "/terms/price_usd"},
                    "target": {"view": "listing", "pointer": "/pricing/components/0/amount"},
                },
                {
                    "id": "deliverables",
                    "kind": "normalized_list_equal",
                    "source": {"view": "contract", "pointer": "/terms/deliverables"},
                    "target": {"view": "funnel", "pointer": "/fulfillment/deliverables"},
                },
                {
                    "id": "acceptance",
                    "kind": "target_subset_of_source",
                    "source": {"view": "contract", "pointer": "/terms/acceptance"},
                    "target": {"view": "funnel", "pointer": "/fulfillment/acceptance"},
                },
                {
                    "id": "refund",
                    "kind": "normalized_text_equal",
                    "source": {"view": "contract", "pointer": "/terms/refund"},
                    "target": {"view": "funnel", "pointer": "/fulfillment/refund"},
                },
                {
                    "id": "source-blob",
                    "kind": "git_blob_sha",
                    "document": "contract_doc",
                    "target": {"view": "listing", "pointer": "/source_artifact/blob_sha"},
                },
            ],
        }

    def tearDown(self):
        self.temp.cleanup()

    def _write(self, path, value):
        (self.root / path).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def test_all_alignment_surfaces_pass(self):
        report = oca.check_alignment(self.spec, root=self.root)
        self.assertTrue(report["ok"])
        self.assertEqual([row["id"] for row in report["rules"]], [
            "price", "deliverables", "acceptance", "refund", "source-blob"
        ])
        self.assertTrue(all(row["ok"] for row in report["rules"]))

    def test_price_mismatch_fails_without_spec_error(self):
        self.catalog["listings"][0]["pricing"]["components"][0]["amount"] = "200.00"
        self._write("catalog.json", self.catalog)
        report = oca.check_alignment(self.spec, root=self.root)
        self.assertFalse(report["ok"])
        self.assertFalse(next(row for row in report["rules"] if row["id"] == "price")["ok"])

    def test_refund_mismatch_fails(self):
        self.catalog["funnels"]["demo-offer"]["fulfillment"]["refund"] = "UNKNOWN"
        self._write("catalog.json", self.catalog)
        report = oca.check_alignment(self.spec, root=self.root)
        self.assertFalse(next(row for row in report["rules"] if row["id"] == "refund")["ok"])

    def test_acceptance_subset_rejects_invented_term(self):
        self.catalog["funnels"]["demo-offer"]["fulfillment"]["acceptance"].append("Invented promise")
        self._write("catalog.json", self.catalog)
        report = oca.check_alignment(self.spec, root=self.root)
        self.assertFalse(next(row for row in report["rules"] if row["id"] == "acceptance")["ok"])

    def test_git_blob_rule_detects_stale_source_pin(self):
        self.catalog["listings"][0]["source_artifact"]["blob_sha"] = "f" * 40
        self._write("catalog.json", self.catalog)
        report = oca.check_alignment(self.spec, root=self.root)
        row = next(row for row in report["rules"] if row["id"] == "source-blob")
        self.assertFalse(row["ok"])
        self.assertIn("git blob mismatch", row["detail"])

    def test_missing_pointer_fails_closed(self):
        self.spec["rules"][0]["source"]["pointer"] = "/terms/missing"
        with self.assertRaisesRegex(oca.AlignmentError, "does not resolve"):
            oca.check_alignment(self.spec, root=self.root)

    def test_ambiguous_match_fails_closed(self):
        self.catalog["listings"].append(dict(self.catalog["listings"][0]))
        self._write("catalog.json", self.catalog)
        with self.assertRaisesRegex(oca.AlignmentError, "exactly one row"):
            oca.check_alignment(self.spec, root=self.root)

    def test_path_escape_is_rejected(self):
        self.spec["documents"]["contract_doc"]["path"] = "../contract.json"
        with self.assertRaisesRegex(oca.AlignmentError, "canonical and stay below root"):
            oca.check_alignment(self.spec, root=self.root)

    def test_duplicate_json_key_is_rejected(self):
        bad = self.root / "dupe.json"
        bad.write_text('{"a":1,"a":2}\n', encoding="utf-8")
        with self.assertRaisesRegex(oca.AlignmentError, "duplicate JSON key"):
            oca._load_json_bytes(bad.read_bytes(), "dupe.json")

    def test_cli_exit_codes_distinguish_mismatch_and_invalid_spec(self):
        spec_path = self.root / "spec.json"
        self._write("spec.json", self.spec)
        self.assertEqual(oca.main(["--root", str(self.root), "--spec", str(spec_path)]), 0)

        self.catalog["funnels"]["demo-offer"]["fulfillment"]["refund"] = "different"
        self._write("catalog.json", self.catalog)
        self.assertEqual(oca.main(["--root", str(self.root), "--spec", str(spec_path)]), 1)

        self.spec["schema_version"] = "wrong"
        self._write("spec.json", self.spec)
        self.assertEqual(oca.main(["--root", str(self.root), "--spec", str(spec_path)]), 2)


if __name__ == "__main__":
    unittest.main()
