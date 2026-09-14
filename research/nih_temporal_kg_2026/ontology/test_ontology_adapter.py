from __future__ import annotations

import copy
import json
import os
import tempfile
import unittest
import sys
from pathlib import Path

_PARENT = Path(__file__).resolve().parents[1]
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from temporal_evidence import EvidenceEvent, Fact, TemporalEvidenceGraph
from ontology_adapter import (
    BIOLINK,
    C_ASSERTION,
    C_RETRACT,
    OWL_CLASS,
    P_ACTION,
    P_EVENT_COUNT,
    P_FACT_ID,
    P_PROFILE_VERSION,
    P_SOURCE_SHA,
    P_SUBJECT_NODE,
    P_TARGET,
    PROFILE_NODE,
    PROFILE_VERSION,
    PROV,
    RDF_TYPE,
    TIME,
    XSD_DATETIME_STAMP,
    XSD_DECIMAL,
    XSD_NNI,
    XSD_STRING,
    NTKG,
    OntologyProfileError,
    build_receipt,
    export_ntriples,
    import_ntriples,
    main,
    verify_receipt,
)


def sample_graph() -> tuple[TemporalEvidenceGraph, dict[str, object]]:
    graph = TemporalEvidenceGraph()
    old = Fact.create(
        subject="therapy_A",
        predicate="biolink:precedes",
        object="therapy_B",
        valid_from="2025-01-01T00:00:00Z",
        valid_to="2026-01-01T00:00:00Z",
        observed_at="2025-01-02T00:00:00Z",
        source_id="guideline-v1",
        source_sha256="a" * 64,
        confidence=0.9,
    )
    new = Fact.create(
        subject="therapy_A",
        predicate="biolink:precedes",
        object="therapy_C",
        valid_from="2026-01-01T00:00:00Z",
        valid_to=None,
        observed_at="2025-12-15T00:00:00Z",
        source_id="guideline-v2",
        source_sha256="b" * 64,
        confidence=1.0,
    )
    signal = Fact.create(
        subject="signal_X",
        predicate="supports",
        object="review_Y",
        valid_from="2025-03-01T00:00:00Z",
        valid_to=None,
        observed_at="2025-03-02T00:00:00Z",
        source_id="study-alpha",
        source_sha256="c" * 64,
        confidence=0.75,
    )
    for fact in (old, new, signal):
        graph.add_fact(fact)
    supersede = EvidenceEvent.create(
        action="supersede",
        target_fact_id=old.fact_id,
        replacement_fact_id=new.fact_id,
        observed_at="2025-12-20T00:00:00Z",
        source_id="guideline-v2",
        source_sha256="b" * 64,
    )
    retract = EvidenceEvent.create(
        action="retract",
        target_fact_id=signal.fact_id,
        observed_at="2025-06-01T00:00:00Z",
        source_id="study-correction",
        source_sha256="d" * 64,
    )
    for event in (supersede, retract):
        graph.add_event(event)
    return graph, {
        "old": old,
        "new": new,
        "signal": signal,
        "supersede": supersede,
        "retract": retract,
    }


def normalized(lines: list[str]) -> str:
    return "\n".join(sorted(lines)) + "\n"


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise AssertionError(f"expected one occurrence of {old!r}, found {count}")
    return normalized(text.replace(old, new).splitlines())


def remove_line(text: str, fragment: str) -> str:
    lines = text.splitlines()
    matches = [line for line in lines if fragment in line]
    if len(matches) != 1:
        raise AssertionError(f"expected one line containing {fragment!r}, found {len(matches)}")
    lines.remove(matches[0])
    return normalized(lines)


class OntologyAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph, self.items = sample_graph()
        self.jsonl = self.graph.to_jsonl()
        self.nt = export_ntriples(self.jsonl)

    def assert_rejected(self, text: str) -> None:
        with self.assertRaises(OntologyProfileError):
            import_ntriples(text)

    def test_exact_roundtrip(self) -> None:
        rebuilt = import_ntriples(self.nt)
        self.assertEqual(rebuilt.to_jsonl(), self.jsonl)
        self.assertEqual(len(rebuilt.facts), 3)
        self.assertEqual(len(rebuilt.events), 2)
        self.assertNotIn("_:", self.nt)
        self.assertIn(TIME + "ProperInterval", self.nt)
        self.assertIn(PROV + "wasDerivedFrom", self.nt)
        self.assertIn(BIOLINK + "precedes", self.nt)

    def test_deterministic_across_jsonl_record_order(self) -> None:
        reversed_jsonl = "\n".join(reversed(self.jsonl.splitlines())) + "\n"
        self.assertEqual(export_ntriples(reversed_jsonl), self.nt)

    def test_open_ended_and_finite_intervals_are_distinct(self) -> None:
        old = self.items["old"]
        new = self.items["new"]
        old_end = f"urn:ntkg:instant:{old.fact_id}:valid-to"
        new_end = f"urn:ntkg:instant:{new.fact_id}:valid-to"
        self.assertIn(old_end, self.nt)
        self.assertNotIn(new_end, self.nt)

    def test_unicode_quotes_and_controls_use_canonical_escapes(self) -> None:
        graph = TemporalEvidenceGraph()
        fact = Fact.create(
            subject="node_β",
            predicate="relates_to",
            object='quoted "node"\nline',
            valid_from="2026-01-01T00:00:00Z",
            valid_to=None,
            observed_at="2026-01-02T00:00:00Z",
            source_id="source_β",
            source_sha256="e" * 64,
            confidence=0.5,
        )
        graph.add_fact(fact)
        nt = export_ntriples(graph.to_jsonl())
        self.assertIn("\\u03B2", nt)
        self.assertIn('\\"node\\"\\nline', nt)
        self.assertEqual(import_ntriples(nt).to_jsonl(), graph.to_jsonl())

    def test_fixed_machine_verifiable_axioms_exist(self) -> None:
        self.assertIn(f"<{C_ASSERTION}> <{RDF_TYPE}> <{OWL_CLASS}> .", self.nt)
        self.assertIn(f"<{NTKG}validityInterval> <{RDF_TYPE}> <http://www.w3.org/2002/07/owl#FunctionalProperty> .", self.nt)
        self.assertIn(f"<{NTKG}validityInterval> <http://www.w3.org/2000/01/rdf-schema#range> <{TIME}ProperInterval> .", self.nt)

    def test_receipt_binds_every_layer(self) -> None:
        receipt = build_receipt(self.jsonl, self.nt)
        self.assertTrue(verify_receipt(receipt, self.jsonl, self.nt))
        changed = dict(receipt)
        changed["fact_count"] = 99
        self.assertFalse(verify_receipt(changed, self.jsonl, self.nt))
        changed = dict(receipt)
        changed["receipt_sha256"] = "0" * 64
        self.assertFalse(verify_receipt(changed, self.jsonl, self.nt))

    def test_duplicate_triple_rejected(self) -> None:
        lines = self.nt.splitlines()
        self.assert_rejected(normalized(lines + [lines[0]]))

    def test_unsorted_triples_rejected(self) -> None:
        lines = self.nt.splitlines()
        lines[0], lines[1] = lines[1], lines[0]
        self.assert_rejected("\n".join(lines) + "\n")

    def test_blank_line_crlf_and_missing_final_newline_rejected(self) -> None:
        self.assert_rejected(self.nt.replace("\n", "\n\n", 1))
        self.assert_rejected(self.nt.replace("\n", "\r\n"))
        self.assert_rejected(self.nt.rstrip("\n"))

    def test_blank_node_rejected(self) -> None:
        old = self.items["old"]
        needle = f"<{P_SUBJECT_NODE}> <urn:ntkg:entity:"
        line = next(line for line in self.nt.splitlines() if f"<urn:ntkg:fact:{old.fact_id}>" in line and needle in line)
        start = line.rfind("<urn:ntkg:entity:")
        end = line.find(">", start) + 1
        mutated = line[:start] + "_:subject" + line[end:]
        self.assert_rejected(normalized([mutated if item == line else item for item in self.nt.splitlines()]))

    def test_relative_iri_rejected(self) -> None:
        line = next(
            item for item in self.nt.splitlines()
            if item.startswith(f"<{PROFILE_NODE}> <{P_PROFILE_VERSION}>")
        )
        mutated = line.replace(f"<{PROFILE_NODE}>", "<profile>", 1)
        self.assert_rejected(normalized([
            mutated if item == line else item
            for item in self.nt.splitlines()
        ]))

    def test_unknown_literal_escape_rejected(self) -> None:
        self.assert_rejected(replace_once(self.nt, "guideline-v1", "guideline\\x2Dv1"))

    def test_noncanonical_unicode_escape_rejected(self) -> None:
        graph = TemporalEvidenceGraph()
        fact = Fact.create(
            subject="β",
            predicate="p",
            object="o",
            valid_from="2026-01-01T00:00:00Z",
            valid_to=None,
            observed_at="2026-01-01T00:00:00Z",
            source_id="s",
            source_sha256="f" * 64,
        )
        graph.add_fact(fact)
        nt = export_ntriples(graph.to_jsonl())
        self.assert_rejected(replace_once(nt, "\\u03B2", "\\u03b2"))

    def test_unknown_profile_term_rejected(self) -> None:
        extra = f'<{PROFILE_NODE}> <{NTKG}unknown> "x"^^<{XSD_STRING}> .'
        self.assert_rejected(normalized(self.nt.splitlines() + [extra]))

    def test_conflicting_functional_property_rejected(self) -> None:
        extra = f'<{PROFILE_NODE}> <{P_PROFILE_VERSION}> "other/v1"^^<{XSD_STRING}> .'
        self.assert_rejected(normalized(self.nt.splitlines() + [extra]))

    def test_subject_iri_alias_rejected(self) -> None:
        old = self.items["old"]
        line = next(line for line in self.nt.splitlines() if f"<urn:ntkg:fact:{old.fact_id}>" in line and f"<{P_SUBJECT_NODE}>" in line)
        object_start = line.rfind("<urn:ntkg:entity:")
        object_end = line.find(">", object_start) + 1
        mutated = line[:object_start] + "<urn:ntkg:entity:" + "0" * 64 + ">" + line[object_end:]
        self.assert_rejected(normalized([mutated if item == line else item for item in self.nt.splitlines()]))

    def test_source_digest_transplant_rejected(self) -> None:
        source_line = next(line for line in self.nt.splitlines() if f"<{P_SOURCE_SHA}>" in line and "c" * 64 in line)
        mutated = source_line.replace("c" * 64, "e" * 64)
        self.assert_rejected(normalized([mutated if item == source_line else item for item in self.nt.splitlines()]))

    def test_fact_id_transplant_rejected(self) -> None:
        old = self.items["old"]
        line = next(line for line in self.nt.splitlines() if f"<urn:ntkg:fact:{old.fact_id}>" in line and f"<{P_FACT_ID}>" in line)
        mutated = line.replace(f'"{old.fact_id}"', f'"{"0" * 64}"')
        self.assert_rejected(normalized([mutated if item == line else item for item in self.nt.splitlines()]))

    def test_event_target_replay_rejected(self) -> None:
        retract = self.items["retract"]
        old = self.items["old"]
        signal = self.items["signal"]
        line = next(line for line in self.nt.splitlines() if f"<urn:ntkg:event:{retract.event_id}>" in line and f"<{P_TARGET}>" in line)
        mutated = line.replace(f"urn:ntkg:fact:{signal.fact_id}", f"urn:ntkg:fact:{old.fact_id}")
        self.assert_rejected(normalized([mutated if item == line else item for item in self.nt.splitlines()]))

    def test_noncanonical_decimal_rejected(self) -> None:
        self.assert_rejected(replace_once(self.nt, f'"0.75"^^<{XSD_DECIMAL}>', f'"0.750"^^<{XSD_DECIMAL}>'))

    def test_noncanonical_datetime_rejected(self) -> None:
        self.assert_rejected(replace_once(
            self.nt,
            f'"2025-03-02T00:00:00.000000Z"^^<{XSD_DATETIME_STAMP}>',
            f'"2025-03-02T00:00:00Z"^^<{XSD_DATETIME_STAMP}>',
        ))

    def test_wrong_header_count_rejected(self) -> None:
        self.assert_rejected(replace_once(
            self.nt,
            f'"2"^^<{XSD_NNI}>',
            f'"3"^^<{XSD_NNI}>',
        ))

    def test_missing_axiom_rejected(self) -> None:
        self.assert_rejected(remove_line(self.nt, f"<{C_ASSERTION}> <{RDF_TYPE}> <{OWL_CLASS}>") )

    def test_action_type_mismatch_rejected(self) -> None:
        retract = self.items["retract"]
        line = next(line for line in self.nt.splitlines() if f"<urn:ntkg:event:{retract.event_id}>" in line and f"<{P_ACTION}>" in line)
        mutated = line.replace('"retract"', '"supersede"')
        self.assert_rejected(normalized([mutated if item == line else item for item in self.nt.splitlines()]))

    def test_open_interval_cannot_gain_an_end(self) -> None:
        new = self.items["new"]
        interval = f"urn:ntkg:interval:{new.fact_id}"
        end = f"urn:ntkg:instant:{new.fact_id}:valid-to"
        additions = [
            f'<{interval}> <{TIME}hasEnd> <{end}> .',
            f'<{end}> <{RDF_TYPE}> <{TIME}Instant> .',
            f'<{end}> <{TIME}inXSDDateTimeStamp> "2027-01-01T00:00:00.000000Z"^^<{XSD_DATETIME_STAMP}> .',
        ]
        self.assert_rejected(normalized(self.nt.splitlines() + additions))

    def test_finite_interval_cannot_lose_its_end(self) -> None:
        old = self.items["old"]
        self.assert_rejected(remove_line(self.nt, f"<urn:ntkg:interval:{old.fact_id}> <{TIME}hasEnd>"))

    def test_cli_export_import_verify(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "graph.jsonl"
            output = root / "graph.nt"
            receipt = root / "receipt.json"
            restored = root / "restored.jsonl"
            source.write_text(self.jsonl, encoding="utf-8")
            self.assertEqual(main(["export", str(source), str(output), "--receipt", str(receipt)]), 0)
            self.assertEqual(main(["verify", str(source), str(output), str(receipt)]), 0)
            self.assertEqual(main(["import", str(output), str(restored)]), 0)
            self.assertEqual(restored.read_text(encoding="utf-8"), self.jsonl)

    def test_cli_rejects_symlink_input(self) -> None:
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unsupported")
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            real = root / "real.jsonl"
            link = root / "link.jsonl"
            real.write_text(self.jsonl, encoding="utf-8")
            try:
                link.symlink_to(real)
            except OSError:
                self.skipTest("symlink creation denied")
            self.assertEqual(main(["export", str(link), str(root / "out.nt")]), 2)


if __name__ == "__main__":
    unittest.main()
