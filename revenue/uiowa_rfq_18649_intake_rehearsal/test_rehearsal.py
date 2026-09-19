#!/usr/bin/env python3
"""Tests for the UIOWA-092 intake-to-assessment rehearsal.

Two jobs:
  1. Prove the shipped synthetic collection is internally consistent and exercises
     all twelve cells with both strengths and real gaps.
  2. Prove that missing and malformed input has OBSERVABLE handling - and, the part
     that actually matters, that a missing input never silently becomes a zero, a
     pass, or a maturity judgement.

    python3 -m unittest -v test_rehearsal
"""
import copy
import json
import os
import shutil
import tempfile
import unittest

import intake_schema as S
import rehearse_intake as R

HERE = os.path.dirname(os.path.abspath(__file__))
COLLECTION = os.path.join(HERE, "sources")


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


class Sandbox:
    """A writable copy of the shipped collection, so hostile edits never touch the fixture."""

    def __init__(self):
        self.root = None

    def __enter__(self):
        self.tmp = tempfile.mkdtemp(prefix="uiowa092-")
        self.root = os.path.join(self.tmp, "sources")
        shutil.copytree(COLLECTION, self.root)
        return self

    def __exit__(self, *exc):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _edit(self, rel, mutate):
        path = os.path.join(self.root, rel)
        doc = load(path)
        mutate(doc)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(doc, fh, indent=2)

    def edit_register(self, mutate):
        self._edit("source-register.json", mutate)

    def edit_observations(self, mutate):
        self._edit(os.path.join("analyst", "observations.json"), mutate)

    def edit_interviews(self, mutate):
        self._edit(os.path.join("analyst", "interview-excerpts.json"), mutate)

    def run(self, extra=None):
        dataset, _ = R.run(self.root, extra)
        return dataset


def codes(dataset):
    return {d["reason_code"] for d in dataset["diagnostics"]}


def cell(dataset, cell_id):
    for c in dataset["matrix"]:
        if c["cell_id"] == cell_id:
            return c
    raise AssertionError(f"no cell {cell_id}")


class TestShippedCollection(unittest.TestCase):
    """The collection as committed."""

    @classmethod
    def setUpClass(cls):
        cls.dataset, _ = R.run(COLLECTION)
        assert cls.dataset is not None, "shipped collection failed to load"

    def test_all_twelve_cells_present_and_valid(self):
        self.assertEqual(len(self.dataset["matrix"]), 12)
        seen = {(c["group"], c["area"]) for c in self.dataset["matrix"]}
        self.assertEqual(seen, {(g, a) for g in S.GROUPS for a in S.AREAS})
        for c in self.dataset["matrix"]:
            self.assertIn(c["state"], S.CELL_STATES)
            self.assertTrue(c["basis"].strip(), f"{c['cell_id']} has no basis")

    def test_both_a_strength_and_a_gap_are_demonstrable(self):
        states = [c["state"] for c in self.dataset["matrix"]]
        self.assertIn("DEMONSTRATED_STRENGTH", states)
        self.assertIn("OBSERVED_GAP", states)
        self.assertIn("MIXED", states)
        self.assertIn("CONFLICT", states)

    def test_every_accepted_observation_is_traceable_to_a_real_file(self):
        """An evidence citation has to point at bytes that exist, with a digest."""
        by_id = {s["source_id"]: s for s in self.dataset["sources"]}
        for obs in self.dataset["observations"]:
            for loc in obs["locators"]:
                src = by_id[loc["source_id"]]
                self.assertEqual(loc["version"], src["version"])
                if src["resolution"] == "RESOLVED":
                    full = os.path.join(COLLECTION, src["path"])
                    self.assertTrue(os.path.isfile(full), f"{src['path']} missing")
                    with open(full, "rb") as fh:
                        self.assertEqual(R.sha256_bytes(fh.read()), src["content_sha256"])

    def test_declared_counts_are_internally_consistent(self):
        """No shipped observation may carry arithmetic that does not add up."""
        checked = 0
        for obs in self.dataset["observations"]:
            if obs.get("count_assertion"):
                self.assertEqual(S.check_count_assertion(obs["count_assertion"]), [],
                                 f"{obs['observation_id']} arithmetic is inconsistent")
                checked += 1
        self.assertGreaterEqual(checked, 8)
        self.assertNotIn("OBS_ARITHMETIC_INCONSISTENT", codes(self.dataset))

    def test_iam_recert_parts_match_the_source_file(self):
        """Cross-check one fixture's prose against the actual bytes it cites."""
        obs = next(o for o in self.dataset["observations"]
                   if o["observation_id"] == "OBS-SYN-IAM-SEC-001")
        parts, whole = obs["count_assertion"]["parts"], obs["count_assertion"]["whole"]
        path = os.path.join(COLLECTION, "iam", "iam-recert-campaign-2026Q2.csv")
        with open(path, encoding="utf-8") as fh:
            rows = [ln for ln in fh.read().splitlines() if ln and not ln.startswith("#")]
        counts = [int(ln.split(",")[1]) for ln in rows[1:]]
        self.assertEqual(sorted(counts), sorted(parts))
        self.assertEqual(sum(counts), whole)

    def test_nothing_is_presented_as_a_university_finding(self):
        arts = R.build_artifacts(self.dataset)
        for name, text in arts.items():
            self.assertIn("SYNTHETIC", text,
                          f"{name} carries no synthetic label")
        report = arts["REHEARSAL_REPORT.md"]
        self.assertIn("Nothing here is a University of Iowa finding", report)
        for obs in self.dataset["observations"]:
            self.assertIn("-SYN-", obs["observation_id"])

    def test_csv_artifacts_stay_machine_readable_with_the_banner(self):
        """The synthetic banner must not break a downstream consumer."""
        arts = R.build_artifacts(self.dataset)
        with tempfile.TemporaryDirectory() as tmp:
            R.write_artifacts(arts, tmp)
            for name in [n for n in arts if n.endswith(".csv")]:
                path = os.path.join(tmp, name)
                with open(path, encoding="utf-8") as fh:
                    self.assertTrue(fh.readline().startswith("# SYNTHETIC"),
                                    f"{name} line 1 is not the synthetic banner")
                rows = R.read_csv_artifact(path)
                self.assertTrue(rows, f"{name} parsed to zero rows")
                self.assertNotIn("#", "".join(rows[0].keys()))
            matrix = R.read_csv_artifact(os.path.join(tmp, "assessment_matrix.csv"))
            self.assertEqual(len(matrix), 12)
            self.assertEqual({r["cell_id"] for r in matrix},
                             {c["cell_id"] for c in self.dataset["matrix"]})

    def test_no_score_rating_or_percentile_anywhere(self):
        """Guardrail: this package must never emit a maturity number."""
        blob = json.dumps(self.dataset).lower()
        for banned in ("maturity_score", "maturity score", "percentile", "peer rank",
                       "overall score", "grade:", "level 1 of", "certified"):
            self.assertNotIn(banned, blob, f"found scoring language: {banned}")


class TestUnknownIsNeverManufactured(unittest.TestCase):
    """The single most important behaviour: absence of evidence stays absence."""

    def test_cell_with_no_evidence_is_unknown(self):
        dataset, _ = R.run(COLLECTION)
        c = cell(dataset, "CELL-ESS-AI")
        self.assertEqual(c["state"], "UNKNOWN")
        self.assertEqual(c["observation_count"], 0)
        self.assertIn("No evidence", c["basis"])

    def test_requested_but_unprovided_evidence_is_unknown_not_a_gap(self):
        dataset, _ = R.run(COLLECTION)
        c = cell(dataset, "CELL-IAM-DEP")
        self.assertEqual(c["state"], "UNKNOWN")
        self.assertNotEqual(c["state"], "OBSERVED_GAP")
        self.assertIn("SRC-SYN-IAM-05", c["outstanding_evidence"])
        self.assertIn("SRC_MISSING", codes(dataset))

    def test_deleting_a_strengths_evidence_downgrades_it_rather_than_passing_it(self):
        """Hostile case: remove the bytes behind a demonstrated strength."""
        with Sandbox() as sb:
            before = cell(sb.run(), "CELL-IAM-SEC")
            self.assertEqual(before["state"], "DEMONSTRATED_STRENGTH")
            os.remove(os.path.join(sb.root, "iam", "iam-recert-campaign-2026Q2.csv"))
            os.remove(os.path.join(sb.root, "iam", "iam-privileged-access-standard-v4.md"))
            after_ds = sb.run()
            after = cell(after_ds, "CELL-IAM-SEC")
            self.assertNotEqual(after["state"], "DEMONSTRATED_STRENGTH")
            self.assertEqual(after["state"], "PARTIAL")
            self.assertIn("SRC_MISSING", codes(after_ds))

    def test_interview_only_support_cannot_demonstrate_a_practice(self):
        dataset, _ = R.run(COLLECTION)
        c = cell(dataset, "CELL-ESS-SEC")
        self.assertEqual(c["state"], "PARTIAL")
        self.assertIn("not demonstrated", c["basis"])

    def test_availability_only_excerpt_contributes_no_support(self):
        dataset, _ = R.run(COLLECTION)
        self.assertIn("INT_NO_CLAIM", codes(dataset))
        obs = next(o for o in dataset["observations"]
                   if o["observation_id"] == "OBS-SYN-IAM-DEP-001")
        self.assertEqual(obs["support"]["interview_support"], [])
        self.assertEqual(obs["support"]["directness"], "NONE")

    def test_conflicting_sources_are_retained_not_resolved(self):
        dataset, _ = R.run(COLLECTION)
        c = cell(dataset, "CELL-IAM-SD")
        self.assertEqual(c["state"], "CONFLICT")
        self.assertIn("retained", c["basis"])
        self.assertEqual(len(c["observation_ids"]), 2)


class TestMalformedInputHandling(unittest.TestCase):
    """Every hostile input must be observable, and must not corrupt the matrix."""

    def test_dangling_source_citation_is_reported_and_degrades(self):
        with Sandbox() as sb:
            def mutate(doc):
                for o in doc["observations"]:
                    if o["observation_id"] == "OBS-SYN-RIS-SD-001":
                        o["source_refs"] = [{"source_id": "SRC-DOES-NOT-EXIST", "locator": "row 1"}]
            sb.edit_observations(mutate)
            ds = sb.run()
            self.assertIn("OBS_DANGLING_SOURCE", codes(ds))
            obs = next(o for o in ds["observations"]
                       if o["observation_id"] == "OBS-SYN-RIS-SD-001")
            self.assertEqual(obs["support"]["directness"], "NONE")

    def test_broken_count_arithmetic_is_caught_and_suppressed(self):
        with Sandbox() as sb:
            def mutate(doc):
                for o in doc["observations"]:
                    if o["observation_id"] == "OBS-SYN-IAM-SEC-001":
                        o["count_assertion"] = {"parts": [71, 19, 8, 4], "whole": 999,
                                                "unit": "accounts"}
            sb.edit_observations(mutate)
            ds = sb.run()
            self.assertIn("OBS_ARITHMETIC_INCONSISTENT", codes(ds))
            obs = next(o for o in ds["observations"]
                       if o["observation_id"] == "OBS-SYN-IAM-SEC-001")
            self.assertIsNone(obs["count_assertion"])
            # An observation whose arithmetic does not hold must not carry a strength.
            self.assertNotEqual(cell(ds, "CELL-IAM-SEC")["state"], "DEMONSTRATED_STRENGTH")

    def test_digest_mismatch_blocks_corroboration(self):
        with Sandbox() as sb:
            def mutate(doc):
                for s in doc["sources"]:
                    if s["source_id"] == "SRC-SYN-IAM-01":
                        s["declared_sha256"] = "0" * 64
            sb.edit_register(mutate)
            ds = sb.run()
            self.assertIn("SRC_DIGEST_MISMATCH", codes(ds))
            src = next(s for s in ds["sources"] if s["source_id"] == "SRC-SYN-IAM-01")
            self.assertEqual(src["resolution"], "UNVERIFIED_DIGEST_MISMATCH")
            self.assertNotEqual(cell(ds, "CELL-IAM-SEC")["state"], "DEMONSTRATED_STRENGTH")

    def test_path_escape_is_rejected(self):
        """A register that points outside the collection root must not be followed."""
        with Sandbox() as sb:
            def mutate(doc):
                doc["sources"].append({
                    "source_id": "SRC-SYN-EVIL-01", "group": "ESS",
                    "source_type": "document", "path": "../../../../etc/passwd",
                    "version": "v1",
                })
            sb.edit_register(mutate)
            ds = sb.run()
            self.assertIn("SRC_PATH_ESCAPE", codes(ds))
            self.assertNotIn("SRC-SYN-EVIL-01", {s["source_id"] for s in ds["sources"]})

    def test_unknown_group_and_area_are_rejected_not_coerced(self):
        with Sandbox() as sb:
            def mutate(doc):
                doc["observations"].append({
                    "observation_id": "OBS-SYN-XXX-001", "group": "NOPE", "area": "SD",
                    "direction": "STRENGTH", "claim": "x", "scope_limit": "x",
                    "source_refs": [],
                })
                doc["observations"].append({
                    "observation_id": "OBS-SYN-ESS-ZZZ-001", "group": "ESS", "area": "ZZZ",
                    "direction": "STRENGTH", "claim": "x", "scope_limit": "x",
                    "source_refs": [],
                })
            sb.edit_observations(mutate)
            ds = sb.run()
            self.assertIn("OBS_UNKNOWN_GROUP", codes(ds))
            self.assertIn("OBS_UNKNOWN_AREA", codes(ds))
            self.assertEqual(len(ds["matrix"]), 12)
            accepted = {o["observation_id"] for o in ds["observations"]}
            self.assertNotIn("OBS-SYN-XXX-001", accepted)

    def test_duplicate_ids_are_rejected(self):
        with Sandbox() as sb:
            def mutate(doc):
                doc["observations"].append(copy.deepcopy(doc["observations"][0]))
            sb.edit_observations(mutate)
            ds = sb.run()
            self.assertIn("OBS_DUPLICATE_ID", codes(ds))

    def test_missing_required_field_is_rejected_with_its_locator(self):
        with Sandbox() as sb:
            def mutate(doc):
                doc["observations"][0].pop("scope_limit")
            sb.edit_observations(mutate)
            ds = sb.run()
            self.assertIn("OBS_MISSING_FIELD", codes(ds))
            row = next(d for d in ds["diagnostics"] if d["reason_code"] == "OBS_MISSING_FIELD")
            self.assertIn("scope_limit", row["detail"])
            self.assertEqual(row["effect"], "observation rejected")

    def test_dangling_interview_attachment_is_reported(self):
        with Sandbox() as sb:
            def mutate(doc):
                doc["excerpts"][0]["supports_observation"] = "OBS-SYN-NOWHERE-999"
            sb.edit_interviews(mutate)
            ds = sb.run()
            self.assertIn("INT_DANGLING_OBSERVATION", codes(ds))

    def test_unparseable_manifest_fails_loudly_not_silently(self):
        with Sandbox() as sb:
            with open(os.path.join(sb.root, "source-register.json"), "w",
                      encoding="utf-8") as fh:
                fh.write("{ this is not json")
            dataset, diags = R.run(sb.root)
            self.assertIsNone(dataset)
            self.assertIn("MANIFEST_UNPARSEABLE",
                          {d["reason_code"] for d in diags.sorted_rows()})

    def test_every_diagnostic_carries_a_severity_and_an_effect(self):
        dataset, _ = R.run(COLLECTION)
        for d in dataset["diagnostics"]:
            self.assertIn(d["severity"], (S.REJECT, S.DEGRADE, S.NOTE))
            self.assertTrue(d["effect"].strip())
            self.assertTrue(d["reason_description"].strip())

    def test_absent_external_collection_is_noted_and_the_run_continues(self):
        dataset, _ = R.run(COLLECTION, extra_collection=os.path.join(HERE, "no-such-dir"))
        self.assertIsNotNone(dataset)
        self.assertIn("COLLECTION_UNAVAILABLE", codes(dataset))
        self.assertEqual(len(dataset["matrix"]), 12)


class TestSecondOperatorReproducibility(unittest.TestCase):
    """'A second operator can reproduce the workflow' - made mechanical."""

    def test_two_runs_produce_byte_identical_artifacts(self):
        a = R.build_artifacts(R.run(COLLECTION)[0])
        b = R.build_artifacts(R.run(COLLECTION)[0])
        self.assertEqual(sorted(a), sorted(b))
        for name in a:
            self.assertEqual(R.sha256_bytes(a[name].encode()),
                             R.sha256_bytes(b[name].encode()),
                             f"{name} differs between runs")

    def test_a_copy_of_the_collection_reproduces_the_same_digests(self):
        """Operator #2 checks the tree out somewhere else and gets the same bytes."""
        original = R.build_artifacts(R.run(COLLECTION)[0])
        with Sandbox() as sb:
            copied = R.build_artifacts(sb.run())
            for name in original:
                self.assertEqual(R.sha256_bytes(original[name].encode()),
                                 R.sha256_bytes(copied[name].encode()),
                                 f"{name} is not path-independent")

    def test_committed_artifacts_match_a_fresh_run(self):
        out = os.path.join(HERE, "artifacts")
        if not os.path.isfile(os.path.join(out, R.RUN_DIGEST_NAME)):
            self.skipTest("no committed artifacts to compare against")
        arts = R.build_artifacts(R.run(COLLECTION)[0])
        ok, problems = R.check_digest(arts, out)
        self.assertTrue(ok, "committed artifacts are stale: " + "; ".join(problems))

    def test_cli_round_trip_writes_and_verifies(self):
        with Sandbox() as sb:
            out = os.path.join(sb.tmp, "out")
            self.assertEqual(R.main(["--collection", sb.root, "--out", out]), 0)
            self.assertTrue(os.path.isfile(os.path.join(out, "assessment_matrix.csv")))
            self.assertEqual(
                R.main(["--collection", sb.root, "--out", out, "--check-digest"]), 0)

    def test_check_digest_fails_when_evidence_changes(self):
        """The check must actually catch drift, or it is decoration."""
        with Sandbox() as sb:
            out = os.path.join(sb.tmp, "out")
            R.main(["--collection", sb.root, "--out", out])
            with open(os.path.join(sb.root, "ris", "ris-vuln-scan-2026-09.csv"), "a",
                      encoding="utf-8") as fh:
                fh.write("VUL-SYN-RIS-7006,ris-award-tracker,LOW,2026-09-01,2026-12-01,,\n")
            self.assertEqual(
                R.main(["--collection", sb.root, "--out", out, "--check-digest"]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
