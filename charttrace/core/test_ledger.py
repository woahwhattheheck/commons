from dataclasses import replace
import unittest

from charttrace.core.ledger import EvidenceLedger, rows_to_csv_bytes, validate_citation
from charttrace.schema.evidence import RecordFact, SourceCitation


SHA = "b" * 64


class LedgerTests(unittest.TestCase):
    def test_rerun_is_byte_identical_and_chain_verifies(self) -> None:
        fact = RecordFact(
            "fact-01",
            "Synthetic result recorded.",
            SourceCitation("doc-01", 2, SHA, span_start=3, span_end=9),
        )
        first = EvidenceLedger()
        second = EvidenceLedger()
        first.append("record_fact", fact.fact_id, fact)
        second.append("record_fact", fact.fact_id, fact)
        self.assertTrue(first.verify())
        self.assertEqual(first.to_json_bytes(), second.to_json_bytes())

    def test_duplicate_record_fails_closed(self) -> None:
        ledger = EvidenceLedger()
        ledger.append("record_fact", "fact-01", {"text": "synthetic"})
        with self.assertRaises(ValueError):
            ledger.append("record_fact", "fact-01", {"text": "changed"})

    def test_tampered_entry_breaks_chain(self) -> None:
        ledger = EvidenceLedger()
        entry = ledger.append("record_fact", "fact-01", {"text": "synthetic"})
        ledger._entries[0] = replace(entry, payload_json='{"text":"tampered"}')
        self.assertFalse(ledger.verify())

    def test_citation_resolves_exact_hash_and_page(self) -> None:
        citation = SourceCitation("doc-01", 2, SHA, span_start=0, span_end=4)
        validate_citation(citation, {"doc-01": (SHA, 2)})
        with self.assertRaises(ValueError):
            validate_citation(citation, {"doc-01": ("c" * 64, 2)})
        with self.assertRaises(ValueError):
            validate_citation(citation, {"doc-01": (SHA, 1)})

    def test_csv_export_is_stable_and_strict(self) -> None:
        rows = ({"id": "fact-01", "text": "synthetic"},)
        self.assertEqual(
            rows_to_csv_bytes(rows, ("id", "text")),
            b"id,text\nfact-01,synthetic\n",
        )
        with self.assertRaises(ValueError):
            rows_to_csv_bytes(({"id": "fact-01"},), ("id", "text"))


if __name__ == "__main__":
    unittest.main()
