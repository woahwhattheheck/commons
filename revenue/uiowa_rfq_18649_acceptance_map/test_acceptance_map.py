#!/usr/bin/env python3
"""Tests for the UIOWA-130 acceptance index.

The failure this suite exists to prevent is an index that looks thorough and is not:
a criterion marked met because a file merely exists, a check that silently returns PASS
when it could not run, or a packet that includes an artifact nobody verified.

    python3 -m unittest -v test_acceptance_map
"""
import hashlib
import json
import os
import shutil
import tempfile
import unittest

import build_index as B
import checks as C
import exhibit_parser

HERE = os.path.dirname(os.path.abspath(__file__))


def _revenue_root():
    """Locate the directory holding the uiowa_rfq_18649_* lanes.

    Normally the parent of this package. The override exists because this lane is
    authored in a staging tree and lands in the repository tree, and a second operator
    may check the repository out anywhere; hard-coding either path would be wrong.
    """
    env = os.environ.get("UIOWA130_REVENUE_ROOT")
    if env:
        return os.path.abspath(env)
    return os.path.abspath(os.path.join(HERE, ".."))


REVENUE = _revenue_root()
EXHIBIT = os.path.join(REVENUE, "uiowa_rfq_18649_workshare", "ACCEPTANCE_EXHIBIT.md")
MAP = os.path.join(HERE, "acceptance_map.json")
# The lanes this index actually reads. Kept explicit so the read-only test is cheap.
BOUND_LANES = ("uiowa_rfq_18649_intake_rehearsal", "uiowa_rfq_18649_workshare",
               "uiowa_rfq_18649_synthetic_collection", "uiowa_rfq_18649_prioritization")


def digest_tree(root):
    out = {}
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fn in sorted(files):
            if fn.endswith(".pyc"):
                continue
            full = os.path.join(dirpath, fn)
            with open(full, "rb") as fh:
                out[os.path.relpath(full, root)] = hashlib.sha256(fh.read()).hexdigest()
    return out


def build_real():
    return B.build(REVENUE, EXHIBIT, MAP)


class TestExhibitParsing(unittest.TestCase):
    def test_criteria_are_extracted_from_the_live_document(self):
        ex = exhibit_parser.parse_exhibit(EXHIBIT)
        self.assertEqual(len(ex["criteria"]), 17)
        self.assertEqual(len(ex["deliverables"]), 20)
        self.assertEqual(ex["commercial_status"], "PROPOSED / NOT ACCEPTED")
        ids = [c["criterion_id"] for c in ex["criteria"]]
        self.assertEqual(len(set(ids)), len(ids), "criterion ids are not unique")
        for c in ex["criteria"]:
            self.assertTrue(c["text"].strip())

    def test_editing_the_exhibit_changes_the_digest_and_the_extraction(self):
        """Drift has to be visible, or the index quietly describes a dead document."""
        before = exhibit_parser.parse_exhibit(EXHIBIT)
        with tempfile.TemporaryDirectory() as tmp:
            copy = os.path.join(tmp, "ACCEPTANCE_EXHIBIT.md")
            with open(EXHIBIT, encoding="utf-8") as fh:
                body = fh.read()
            with open(copy, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(body.replace(
                    "6. the prime can independently identify what is complete",
                    "6. REMOVED-FOR-TEST what is complete"))
            after = exhibit_parser.parse_exhibit(copy)
        self.assertNotEqual(before["digest_sha256"], after["digest_sha256"])
        self.assertIn("REMOVED-FOR-TEST",
                      " ".join(c["text"] for c in after["criteria"]))


class TestIndexIsEarned(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = build_real()

    def test_every_criterion_has_a_binding(self):
        for e in self.index["criteria"]:
            self.assertNotEqual(e["status"], "UNMAPPED",
                                f"{e['criterion_id']} has no binding")

    def test_demonstrable_requires_a_passing_check_with_an_observed_value(self):
        """The core honesty rule: DEMONSTRABLE is never granted without evidence."""
        found = 0
        for e in self.index["criteria"] + self.index["deliverables"]:
            if e["status"] == "DEMONSTRABLE":
                found += 1
                self.assertTrue(e["checks"], "DEMONSTRABLE with no checks at all")
                self.assertTrue(all(c["outcome"] == C.PASS for c in e["checks"]),
                                f"DEMONSTRABLE with a non-passing check: {e}")
                self.assertFalse(e["required_engagement_inputs"],
                                 "DEMONSTRABLE while still needing engagement evidence")
                for c in e["checks"]:
                    self.assertTrue(c["observed"].strip(), "no observed value recorded")
        self.assertGreater(found, 0)

    def test_needs_engagement_evidence_always_names_the_missing_input(self):
        found = 0
        for e in self.index["criteria"] + self.index["deliverables"]:
            if e["status"] == "NEEDS_ENGAGEMENT_EVIDENCE":
                found += 1
                self.assertTrue(e["required_engagement_inputs"],
                                f"{e.get('criterion_id') or e.get('deliverable_id')} "
                                "needs engagement evidence but names no missing input")
        self.assertGreaterEqual(found, 2)

    def test_the_honest_split_actually_splits(self):
        """If everything came back green the index would be worthless."""
        t = self.index["criterion_tally"]
        self.assertGreater(t["DEMONSTRABLE"], 0)
        self.assertGreater(t["NEEDS_ENGAGEMENT_EVIDENCE"], 0)
        self.assertGreater(t["NOT_DEMONSTRATED"] + t["PARTIAL"], 0,
                           "no criterion failed - the checks are probably not checking")

    def test_the_register_schema_gap_names_the_column_that_is_missing(self):
        """The behaviour under test is the NAMING, not a fixed verdict.

        This assertion used to pin AC-5.1.3 to NOT_DEMONSTRATED, because when the index
        was first built neither delivered register carried all six concepts. The
        rehearsal register has since been given custodian_role and authorization_basis
        in response to exactly this finding, so the criterion is now PARTIAL: one
        register satisfies it, one does not. Pinning the old verdict would have made the
        suite fail for a fix, so the test now asserts what the check must always do -
        name the concept it could not find - and that the criterion is not called
        satisfied while any bound register still falls short.
        """
        e = next(x for x in self.index["criteria"] if x["criterion_id"] == "AC-5.1.3")
        outcomes = {c["outcome"] for c in e["checks"]}
        blob = " ".join(c["observed"] for c in e["checks"])
        if C.FAIL in outcomes:
            self.assertIn("NO COLUMN FOR", blob)
            self.assertNotEqual(e["status"], "DEMONSTRABLE",
                                "a register still falls short, so this is not satisfied")
        else:
            self.assertEqual(e["status"], "DEMONSTRABLE")
        # Whatever the verdict, every check must report how many concepts it found.
        for c in e["checks"]:
            self.assertIn("concepts have a column", c["observed"])

    def test_the_rehearsal_register_now_carries_all_six_concepts(self):
        """The half of AC-5.1.3 this fleet owns and fixed."""
        e = next(x for x in self.index["criteria"] if x["criterion_id"] == "AC-5.1.3")
        own = next(c for c in e["checks"]
                   if "intake_rehearsal" in (c["target"] or ""))
        self.assertEqual(own["outcome"], C.PASS, own["observed"])
        self.assertIn("6/6", own["observed"])
        self.assertIn("custodian_or_owner", own["observed"])

    def test_criteria_needing_a_prime_are_never_marked_demonstrable(self):
        for cid in ("AC-5.2.6", "AC-5.3.4"):
            e = next(x for x in self.index["criteria"] if x["criterion_id"] == cid)
            self.assertEqual(e["status"], "NEEDS_ENGAGEMENT_EVIDENCE")
            self.assertEqual(e["checks"], [])


class TestChecksFailWhenTheyShould(unittest.TestCase):
    """A check that cannot fail is decoration."""

    def test_unknown_check_kind_is_unavailable_not_pass(self):
        outcome, detail = C.run_check(REVENUE, {"kind": "no_such_check", "params": {}})
        self.assertEqual(outcome, C.UNAVAILABLE)
        self.assertIn("unknown check kind", detail)

    def test_a_raising_check_is_unavailable_not_pass(self):
        outcome, _ = C.run_check(REVENUE, {"kind": "csv_columns_cover", "params": {}})
        self.assertEqual(outcome, C.UNAVAILABLE)

    def test_missing_file_is_unavailable_not_pass(self):
        outcome, _ = C.run_check(REVENUE, {
            "kind": "csv_covers_cells",
            "params": {"path": "no_such_lane/nope.csv", "group_field": "g",
                       "area_field": "a", "groups": ["ESS"], "areas": ["SD"]}})
        self.assertEqual(outcome, C.UNAVAILABLE)

    def test_no_silent_promotion_catches_an_actual_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "m.csv")
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write("cell_id,state,outstanding_evidence\n"
                         "CELL-A,DEMONSTRATED_STRENGTH,SRC-MISSING-01\n"
                         "CELL-B,UNKNOWN,SRC-MISSING-02\n")
            outcome, detail = C.run_check(tmp, {
                "kind": "no_silent_promotion",
                "params": {"path": "m.csv", "outstanding_field": "outstanding_evidence",
                           "state_field": "state",
                           "supported_states": ["DEMONSTRATED_STRENGTH"]}})
            self.assertEqual(outcome, C.FAIL)
            self.assertIn("CELL-A", detail)

    def test_no_silent_promotion_is_unavailable_when_the_rule_is_untested(self):
        """If no row carries outstanding evidence the rule proves nothing. Say so."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "m.csv")
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write("cell_id,state,outstanding_evidence\nCELL-A,UNKNOWN,\n")
            outcome, detail = C.run_check(tmp, {
                "kind": "no_silent_promotion",
                "params": {"path": "m.csv", "outstanding_field": "outstanding_evidence",
                           "state_field": "state",
                           "supported_states": ["DEMONSTRATED_STRENGTH"]}})
            self.assertEqual(outcome, C.UNAVAILABLE)
            self.assertIn("untested", detail)

    def test_columns_cover_names_the_concept_it_could_not_find(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "r.csv"), "w", encoding="utf-8", newline="\n") as fh:
                fh.write("source_id,path\nS1,a/b.csv\n")
            outcome, detail = C.run_check(tmp, {
                "kind": "csv_columns_cover",
                "params": {"path": "r.csv",
                           "requirements": {"source": ["source_id"],
                                            "custodian_or_owner": ["custodian", "owner"]}}})
            self.assertEqual(outcome, C.FAIL)
            self.assertIn("custodian_or_owner", detail)

    def test_text_excludes_all_catches_forbidden_representation(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "r.md"), "w", encoding="utf-8", newline="\n") as fh:
                fh.write("The University accepted our conclusion and payment received.\n")
            outcome, detail = C.run_check(tmp, {
                "kind": "text_excludes_all",
                "params": {"path": "r.md",
                           "needles": ["university accepted", "payment received"]}})
            self.assertEqual(outcome, C.FAIL)
            self.assertIn("forbidden representation", detail)

    def test_a_failing_command_is_reported_with_its_real_exit_code(self):
        outcome, detail = C.run_check(REVENUE, {
            "kind": "command_exit_zero",
            "params": {"argv": ["python3", "-c", "import sys; sys.exit(3)"], "cwd": "."}})
        self.assertEqual(outcome, C.FAIL)
        self.assertIn("exit 3", detail)


class TestHostileAndReadOnly(unittest.TestCase):
    def _sandbox(self, tmp):
        root = os.path.join(tmp, "revenue")
        os.makedirs(root)
        for lane in BOUND_LANES:
            src = os.path.join(REVENUE, lane)
            if os.path.isdir(src):
                shutil.copytree(src, os.path.join(root, lane),
                                ignore=shutil.ignore_patterns("__pycache__"))
        return root

    def test_deleting_a_bound_artifact_never_leaves_it_demonstrable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._sandbox(tmp)
            target = os.path.join(root, "uiowa_rfq_18649_intake_rehearsal",
                                  "artifacts", "assessment_matrix.csv")
            self.assertTrue(os.path.isfile(target))
            os.remove(target)
            idx = B.build(root, os.path.join(
                root, "uiowa_rfq_18649_workshare", "ACCEPTANCE_EXHIBIT.md"), MAP)
            for cid in ("AC-5.1.4", "AC-5.2.2", "AC-5.2.3"):
                e = next(x for x in idx["criteria"] if x["criterion_id"] == cid)
                self.assertNotEqual(e["status"], "DEMONSTRABLE",
                                    f"{cid} stayed DEMONSTRABLE with its artifact deleted")

    def test_building_the_index_does_not_modify_any_other_lane(self):
        """Strictly read-only against other seats' work. Proven by digest, not by policy."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._sandbox(tmp)
            before = digest_tree(root)
            out = os.path.join(tmp, "out")
            idx = B.build(root, os.path.join(
                root, "uiowa_rfq_18649_workshare", "ACCEPTANCE_EXHIBIT.md"), MAP)
            os.makedirs(out)
            B.sample_packet(idx, root, out)
            after = digest_tree(root)
        changed = [k for k in set(before) | set(after) if before.get(k) != after.get(k)]
        self.assertEqual(changed, [], f"the index modified other lanes: {changed}")


class TestPacketDirectoryIsNotBlindlyDeleted(unittest.TestCase):
    """Reported by seat OP5-MARROW's destructive-call screen against this lane.

    sample_packet() used to shutil.rmtree an --out-derived path unconditionally. The
    screen classified it REVIEW_REQUIRED because the path descends from argv, and it
    was right. These tests pin the refusal so the hazard cannot come back.
    """

    def _index(self):
        return build_real()

    def test_rebuilding_over_our_own_packet_succeeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            idx = self._index()
            B.sample_packet(idx, REVENUE, tmp)
            first = sorted(os.listdir(os.path.join(tmp, "sample_packet")))
            B.sample_packet(idx, REVENUE, tmp)
            self.assertEqual(sorted(os.listdir(os.path.join(tmp, "sample_packet"))), first)

    def test_refuses_to_delete_a_directory_it_did_not_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            victim = os.path.join(tmp, "sample_packet")
            os.makedirs(victim)
            keep = os.path.join(victim, "IMPORTANT.txt")
            with open(keep, "w", encoding="utf-8") as fh:
                fh.write("irreplaceable client evidence")
            with self.assertRaises(B.UnsafePacketDirectory):
                B.sample_packet(self._index(), REVENUE, tmp)
            self.assertTrue(os.path.isfile(keep), "the foreign file was deleted")
            with open(keep, encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "irreplaceable client evidence")

    def test_refuses_when_the_marker_manifest_is_unreadable(self):
        """An unparseable manifest is not proof of ownership."""
        with tempfile.TemporaryDirectory() as tmp:
            victim = os.path.join(tmp, "sample_packet")
            os.makedirs(victim)
            with open(os.path.join(victim, "MANIFEST.json"), "w", encoding="utf-8") as fh:
                fh.write("{ not json")
            with self.assertRaises(B.UnsafePacketDirectory):
                B.sample_packet(self._index(), REVENUE, tmp)
            self.assertTrue(os.path.isfile(os.path.join(victim, "MANIFEST.json")))

    def test_refuses_when_the_manifest_belongs_to_a_different_tool(self):
        with tempfile.TemporaryDirectory() as tmp:
            victim = os.path.join(tmp, "sample_packet")
            os.makedirs(victim)
            with open(os.path.join(victim, "MANIFEST.json"), "w", encoding="utf-8") as fh:
                json.dump({"packet": "some other tool's packet"}, fh)
            with self.assertRaises(B.UnsafePacketDirectory):
                B.sample_packet(self._index(), REVENUE, tmp)

    def test_an_empty_directory_is_safe_to_reuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "sample_packet"))
            manifest = B.sample_packet(self._index(), REVENUE, tmp)
            self.assertTrue(manifest["included"])

    def test_cli_exits_3_instead_of_raising(self):
        with tempfile.TemporaryDirectory() as tmp:
            victim = os.path.join(tmp, "sample_packet")
            os.makedirs(victim)
            with open(os.path.join(victim, "keep.txt"), "w", encoding="utf-8") as fh:
                fh.write("x")
            rc = B.main(["--revenue-root", REVENUE, "--exhibit", EXHIBIT,
                         "--map", MAP, "--out", tmp])
            self.assertEqual(rc, 3)
            self.assertTrue(os.path.isfile(os.path.join(victim, "keep.txt")))


class TestOutputsAndPacket(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="uiowa130-")
        cls.rc = B.main(["--revenue-root", REVENUE, "--exhibit", EXHIBIT,
                         "--map", MAP, "--out", cls.tmp])
        with open(os.path.join(cls.tmp, "acceptance_index.json"), encoding="utf-8") as fh:
            cls.index = json.load(fh)
        with open(os.path.join(cls.tmp, "sample_packet", "MANIFEST.json"),
                  encoding="utf-8") as fh:
            cls.manifest = json.load(fh)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_cli_succeeds_and_writes_every_artifact(self):
        self.assertEqual(self.rc, 0)
        for name in ("acceptance_index.json", "acceptance_index.csv",
                     "needs_engagement_evidence.csv", "ACCEPTANCE_INDEX.md"):
            self.assertTrue(os.path.isfile(os.path.join(self.tmp, name)), name)

    def test_packet_contains_only_verified_artifacts(self):
        """A file gets into the packet only because a check on it passed."""
        self.assertTrue(self.manifest["included"])
        passed = {(c["target"], e["criterion_id"])
                  for e in self.index["criteria"] for c in e["checks"]
                  if c["outcome"] == C.PASS}
        for row in self.manifest["included"]:
            self.assertIn((row["source_path"], row["criterion_id"]), passed,
                          f"{row['packet_file']} is in the packet without a passing check")
            full = os.path.join(self.tmp, "sample_packet", row["packet_file"])
            self.assertTrue(os.path.isfile(full))
            with open(full, "rb") as fh:
                self.assertEqual(hashlib.sha256(fh.read()).hexdigest(), row["sha256"])

    def test_excluded_artifacts_are_listed_with_a_reason_not_dropped(self):
        excluded = self.manifest["excluded_because_the_check_did_not_pass"]
        self.assertTrue(excluded, "nothing was excluded - the packet rule is not biting")
        for row in excluded:
            self.assertIn(row["outcome"], (C.FAIL, C.UNAVAILABLE))
            self.assertTrue(row["observed"].strip())

    def test_no_output_claims_acceptance_award_or_payment(self):
        """Criterion 5.3.5, applied to this package's own outputs."""
        forbidden = ["the university accepted", "university has accepted",
                     "subcontract executed", "executed subcontract", "payment received",
                     "invoice approved", "revenue recognized", "award has been made",
                     "contract is executed"]
        # Scan what this package ASSERTS, not the exhibit text it is required to quote.
        # A naive scan of the rendered file flags criterion 5.3.5, whose own wording
        # contains the phrase inside a prohibition - quoting a rule is not breaking it.
        body = B.authored_prose(self.index).lower()
        for phrase in forbidden:
            self.assertNotIn(phrase, body, f"authored prose contains {phrase!r}")

    def test_the_forbidden_phrase_guard_can_actually_fail(self):
        """Guard the guard: prove the scan is not vacuous after narrowing its surface."""
        poisoned = json.loads(json.dumps(self.index))
        poisoned["criteria"][0]["status_basis"] = "the University accepted this conclusion"
        self.assertIn("the university accepted", B.authored_prose(poisoned).lower())

    def test_quoted_criterion_text_is_preserved_in_the_rendered_index(self):
        """Narrowing the guard must not have quietly dropped the source text."""
        with open(os.path.join(self.tmp, "ACCEPTANCE_INDEX.md"), encoding="utf-8") as fh:
            md = fh.read()
        self.assertIn("no unsupported representation that the University accepted", md)

    def test_every_output_carries_the_proposed_not_accepted_banner(self):
        for name in ("acceptance_index.json", "acceptance_index.csv",
                     "needs_engagement_evidence.csv", "ACCEPTANCE_INDEX.md"):
            with open(os.path.join(self.tmp, name), encoding="utf-8") as fh:
                self.assertIn("PROPOSED / NOT ACCEPTED", fh.read(), name)

    def test_no_scoring_language_anywhere(self):
        blob = json.dumps(self.index).lower()
        for banned in ("maturity score", "percentile", "peer rank", "overall score",
                       "certified compliant", "conformance percentage"):
            self.assertNotIn(banned, blob, f"found scoring language: {banned}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
