import json
import tempfile
import unittest
from pathlib import Path

import host.offer_contract_alignment as oca


class OfferContractAlignmentDecimalParsingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.huge_number = "1e999999999999999999999999999999999999999"

    def tearDown(self):
        self.temp.cleanup()

    def test_extreme_decimal_exponent_in_spec_returns_exit_two(self):
        spec_path = self.root / "extreme-spec.json"
        spec_path.write_text('{"value":' + self.huge_number + '}\n', encoding="utf-8")
        self.assertEqual(oca.main(["--root", str(self.root), "--spec", str(spec_path)]), 2)

    def test_extreme_decimal_exponent_in_document_returns_exit_two(self):
        document_path = self.root / "extreme-document.json"
        document_path.write_text('{"value":' + self.huge_number + '}\n', encoding="utf-8")
        spec = {
            "schema_version": "offer-contract-alignment/v1",
            "documents": {"extreme_doc": {"path": "extreme-document.json"}},
            "views": {"extreme": {"document": "extreme_doc", "pointer": ""}},
            "rules": [
                {
                    "id": "self",
                    "kind": "equal",
                    "source": {"view": "extreme", "pointer": "/value"},
                    "target": {"view": "extreme", "pointer": "/value"},
                }
            ],
        }
        spec_path = self.root / "document-spec.json"
        spec_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
        self.assertEqual(oca.main(["--root", str(self.root), "--spec", str(spec_path)]), 2)


if __name__ == "__main__":
    unittest.main()
