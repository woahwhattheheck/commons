import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import host.experience_compiler as compiler


class ExperienceRetrievalTests(unittest.TestCase):
    def setUp(self):
        # Pin retrieval examples while allowing the real experience corpus to grow.
        ids = {"ai-village-discovery-4945", "command-center-shared-operation-state-9987",
               "experience-compiler-generated-source-drift", "experience-compiler-generator-repair-11950"}
        self.records = [r for r in compiler.load_records() if r["id"] in ids]

    def test_generator_repair_preserves_failure_and_success_sources(self):
        result = compiler.retrieve_experience(self.records, "generated artifacts")
        match = result["matches"][0]
        self.assertEqual("change-generator-with-generated-output", match["id"])
        self.assertEqual((1, 1), (match["success_count"], match["failure_count"]))
        self.assertEqual({"failed", "passed"}, {o["outcome"] for o in match["observations"]})
        for observation in match["observations"]:
            path = compiler.ROOT / observation["source"]
            record = json.loads(path.read_text())
            self.assertEqual(record["evidence"], observation["evidence"])

    def test_shared_handoff_retrieves_distinct_workloads(self):
        result = compiler.retrieve_experience(self.records, skill="cross-agent-handoff")
        self.assertEqual({"publish-discovery-before-interaction", "share-operation-identity-across-carriers"},
                         {m["id"] for m in result["matches"]})

    def test_unknown_context_does_not_invent_experience(self):
        result = compiler.retrieve_experience(self.records, "volcanology")
        self.assertEqual(0, result["matched_pattern_count"])
        self.assertEqual([], result["matches"])
        self.assertEqual([], compiler.retrieve_experience(self.records, skill="absent-skill")["matches"])

    def test_selection_is_deterministic_and_reports_pattern_limit(self):
        left = compiler.retrieve_experience(self.records, skill="cross-agent-handoff", limit=1)
        right = compiler.retrieve_experience(list(reversed(self.records)), skill="cross-agent-handoff", limit=1)
        self.assertEqual(left, right)
        self.assertEqual(2, left["matched_pattern_count"])
        self.assertEqual(1, left["returned_pattern_count"])

    def test_many_successes_do_not_hide_the_failed_intervention(self):
        records = copy.deepcopy(self.records)
        source = next(r for r in records if r["id"] == "experience-compiler-generator-repair-11950")
        for i in range(5):
            fixture = copy.deepcopy(source)
            fixture["id"] = f"fixture-new-success-{i}"
            fixture["recorded_at"] = f"2026-09-{20 + i}T00:00:00Z"
            records.append(fixture)
        match = compiler.retrieve_experience(records, skill="generated-artifacts")["matches"][0]
        self.assertEqual(7, match["source_record_count"])
        self.assertEqual(4, match["omitted_observation_count"])
        self.assertEqual(3, len(match["observations"]))
        self.assertEqual({"failure", "success"}, {o["kind"] for o in match["observations"]})

    def test_newest_observation_orders_parsed_utc_instants(self):
        failed = copy.deepcopy(next(
            r for r in self.records if r["id"] == "experience-compiler-generated-source-drift"
        ))
        failed["id"] = "fixture-failed-observation"
        failed["recorded_at"] = "2026-09-19T23:59:59Z"
        source = next(r for r in self.records if r["id"] == "experience-compiler-generator-repair-11950")
        whole_second = copy.deepcopy(source)
        whole_second["id"] = "fixture-success-whole-second"
        whole_second["recorded_at"] = "2026-09-20T00:00:00Z"
        fractional = copy.deepcopy(source)
        fractional["id"] = "fixture-success-fractional"
        fractional["recorded_at"] = "2026-09-20T00:00:00.500000Z"

        match = compiler.retrieve_experience(
            [whole_second, failed, fractional], skill="generated-artifacts", limit=20
        )["matches"][0]
        success = next(o for o in match["observations"] if o["kind"] == "success")
        self.assertEqual("2026-09-20T00:00:00.500000Z", success["recorded_at"])

    def test_validation_rejects_retrieval_unsafe_packet_fields(self):
        seed = next(r for r in self.records if r["id"] == "ai-village-discovery-4945")
        cases = (
            ("recorded_at", 7, "recorded_at"),
            ("recorded_at", "2026-09-12T23:00:00+00:00", "recorded_at"),
            ("recorded_at", "2026-09-31T23:00:00Z", "recorded_at"),
            ("applies_to", ["cross-agent-handoff", 7], "applies_to"),
            ("applies_to", ["cross-agent-handoff", "cross-agent-handoff"], "unique"),
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for i, (field, value, message) in enumerate(cases):
                with self.subTest(field=field, value=value):
                    record = copy.deepcopy(seed)
                    record["id"] = f"fixture-invalid-retrieval-{i}"
                    if field == "recorded_at":
                        record["recorded_at"] = value
                    else:
                        record["patterns"][0][field] = value
                    path = root / f"{record['id']}.json"
                    with self.assertRaisesRegex(compiler.ExperienceError, message):
                        compiler.validate_record(record, path)

            duplicate = copy.deepcopy(seed)
            duplicate["id"] = "fixture-duplicate-pattern"
            duplicate["patterns"].append(copy.deepcopy(duplicate["patterns"][0]))
            with self.assertRaisesRegex(compiler.ExperienceError, "duplicate pattern id"):
                compiler.validate_record(duplicate, root / "fixture-duplicate-pattern.json")

    def test_validation_fails_closed_on_unhashable_schema_values(self):
        seed = next(r for r in self.records if r["id"] == "ai-village-discovery-4945")
        mutations = (
            ("outcome", lambda r: r.__setitem__("outcome", []), "outcome"),
            ("pattern-kind", lambda r: r["patterns"][0].__setitem__("kind", []), "pattern kind"),
            ("skill-decision", lambda r: r["skill_impacts"][0].__setitem__("decision", []),
             "skill decision"),
            ("commit-value", lambda r: r["evidence"][1].__setitem__("value", []), "malformed evidence"),
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, mutate, message in mutations:
                with self.subTest(name=name):
                    record = copy.deepcopy(seed)
                    record["id"] = f"fixture-unhashable-{name}"
                    mutate(record)
                    path = root / f"{record['id']}.json"
                    with self.assertRaisesRegex(compiler.ExperienceError, message):
                        compiler.validate_record(record, path)

            with self.assertRaisesRegex(compiler.ExperienceError, "must be an object"):
                compiler.validate_record([], root / "not-an-object.json")

    def test_loader_accepts_new_valid_records_without_replacing_seed(self):
        seed = next(r for r in self.records if r["id"] == "ai-village-discovery-4945")
        extra = copy.deepcopy(seed)
        extra["id"] = "fixture-additional-outcome"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw = root / "experience/raw"
            raw.mkdir(parents=True)
            for record in (seed, extra):
                (raw / f"{record['id']}.json").write_text(json.dumps(record))
            with patch.object(compiler, "ROOT", root), patch.object(compiler, "RAW_DIR", raw):
                loaded = compiler.load_records()
        self.assertEqual({seed["id"], extra["id"]}, {r["id"] for r in loaded})

    def test_invalid_retrieval_options_are_explicit(self):
        for options in ({}, {"query": "..."}, {"query": "agent", "limit": 0},
                        {"query": "agent", "limit": True}, {"query": "agent", "limit": 21}):
            with self.subTest(options=options), self.assertRaises(compiler.ExperienceError):
                compiler.retrieve_experience(self.records, **options)

    def test_cli_retrieves_fresh_raw_evidence_without_mutation(self):
        paths = list(compiler.RAW_DIR.glob("*.json")) + list(compiler.WIKI_DIR.rglob("*"))
        before = {p: p.read_bytes() for p in paths if p.is_file()}
        run = subprocess.run([sys.executable, str(compiler.ROOT / "host/experience_compiler.py"),
                              "retrieve", "--query", "share-operation-identity-across-carriers",
                              "--skill", "provider-operations", "--limit", "20"],
                             cwd=compiler.ROOT, capture_output=True, text=True, check=True)
        result = json.loads(run.stdout)
        self.assertIn("share-operation-identity-across-carriers", {m["id"] for m in result["matches"]})
        self.assertEqual(before, {p: p.read_bytes() for p in before})


if __name__ == "__main__":
    unittest.main()
