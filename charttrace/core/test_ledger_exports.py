from dataclasses import replace
import json
import unittest

from charttrace.core.exports import export_csv, export_json, export_markdown
from charttrace.core.extraction import analyze_pdf
from charttrace.core.ledger import EvidenceLedger, LedgerIntegrityError
from charttrace.core.pdf import build_minimal_pdf
from charttrace.schema.v1 import GLOBAL_SCOPE_STATEMENT


class LedgerAndExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.result = analyze_pdf(
            build_minimal_pdf(
                [
                    (
                        "CT|FACT|FACT-001|2026-01-02|EXACT|chronology|visit"
                        "|A synthetic event is documented."
                    ),
                    (
                        "CT|LEAD|LEAD-001|Synthetic interval|chronology|follow-up"
                        "|One cited synthetic event exists."
                        "|An interval may warrant professional review."
                        "|Which additional record resolves the interval?|FACT-001"
                    ),
                ]
            ),
            document="SYNTH-DOC-001",
        )

    def test_ledger_is_immutable_deterministic_and_tamper_evident(self) -> None:
        ledger = (
            EvidenceLedger()
            .append("RECORD_FACT", self.result.facts[0])
            .append("INVESTIGATIVE_LEAD", self.result.leads[0])
        )
        ledger.verify()
        encoded = ledger.to_ndjson()
        self.assertEqual(encoded, ledger.to_ndjson())
        self.assertEqual(EvidenceLedger.from_ndjson(encoded).to_ndjson(), encoded)

        changed_entry = replace(
            ledger.entries[0],
            payload={**ledger.entries[0].payload, "statement": "changed"},
        )
        changed = replace(
            ledger, entries=(changed_entry,) + ledger.entries[1:]
        )
        with self.assertRaises(LedgerIntegrityError):
            changed.verify()

    def test_exports_are_byte_stable_and_structured(self) -> None:
        first_json = export_json(self.result)
        self.assertEqual(first_json, export_json(self.result))
        decoded = json.loads(first_json)
        self.assertEqual(decoded["facts"][0]["fact_id"], "FACT-001")
        self.assertEqual(decoded["facts"][0]["citation"]["page"], 1)
        self.assertEqual(decoded["leads"][0]["lead_id"], "LEAD-001")

        first_csv = export_csv(self.result)
        self.assertEqual(first_csv, export_csv(self.result))
        self.assertIn("RECORD_FACT,FACT-001", first_csv)
        self.assertIn("INVESTIGATIVE_LEAD,LEAD-001", first_csv)
        self.assertNotIn("\r\n", first_csv)

        first_markdown = export_markdown(self.result)
        self.assertEqual(first_markdown, export_markdown(self.result))
        self.assertEqual(first_markdown.count(GLOBAL_SCOPE_STATEMENT), 1)
        self.assertIn("page 1", first_markdown)
        self.assertIn("## Investigative leads", first_markdown)


if __name__ == "__main__":
    unittest.main()
