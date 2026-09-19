#!/usr/bin/env python3
"""Tests for the RFQ-18649 vocabulary reconciliation.

The failure mode this suite exists to prevent is a crosswalk that looks helpful and
quietly joins things that are not the same: a near-miss term absorbed into the closest
bucket, a compound cell split into rows that double-count, or an unmapped term dropped
out of the totals so the report looks tidier than the tree.

    python3 -m unittest -v test_vocabulary
"""
import hashlib
import json
import os
import shutil
import tempfile
import unittest

import reconcile as R
import scan_vocabulary as SV

HERE = os.path.dirname(os.path.abspath(__file__))


def _revenue_root():
    env = os.environ.get("UIOWA_REVENUE_ROOT")
    return os.path.abspath(env) if env else os.path.abspath(os.path.join(HERE, ".."))


REVENUE = _revenue_root()
CROSSWALK_PATH = os.path.join(HERE, "crosswalk.json")


def load_crosswalk():
    with open(CROSSWALK_PATH, encoding="utf-8") as fh:
        return json.load(fh)


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


class TestNoGuessing(unittest.TestCase):
    """The central guarantee. An undeclared term is never assigned to a bucket."""

    def setUp(self):
        self.cw = load_crosswalk()

    def test_a_near_miss_term_is_unmapped_not_absorbed(self):
        for near_miss in ("securty", "security_practices", "software_dev",
                          "SECURITY-2", "deployment_ops", "ESS2", "ESS "):
            rec = R.classify(near_miss.strip() or near_miss, "area", self.cw)
            if rec["kind"] != "UNMAPPED":
                # Only an exactly declared term may resolve.
                self.assertIn(near_miss.strip(), self.cw["area"],
                              f"{near_miss!r} resolved without being declared")

    def test_no_edit_distance_or_prefix_matching_exists_in_the_source(self):
        """A guess cannot creep back in through a helper.

        Checked structurally rather than by substring: the first version of this test
        grepped for "fuzz" and failed on this module's own docstring saying it does not
        fuzzy-match. A guard that fires on a description of itself teaches you to
        disable it, so it now parses the AST and looks at imports and called names.
        """
        import ast
        banned_modules = {"difflib", "fuzzywuzzy", "rapidfuzz", "Levenshtein",
                          "thefuzz", "jellyfish"}
        banned_calls = {"get_close_matches", "SequenceMatcher", "ratio",
                        "partial_ratio", "token_sort_ratio"}
        for module in ("reconcile.py", "scan_vocabulary.py"):
            with open(os.path.join(HERE, module), encoding="utf-8") as fh:
                tree = ast.parse(fh.read(), filename=module)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertNotIn(alias.name.split(".")[0], banned_modules,
                                         f"{module} imports {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    self.assertNotIn((node.module or "").split(".")[0], banned_modules,
                                     f"{module} imports from {node.module}")
                elif isinstance(node, ast.Call):
                    fn = node.func
                    name = (fn.attr if isinstance(fn, ast.Attribute)
                            else fn.id if isinstance(fn, ast.Name) else "")
                    self.assertNotIn(name, banned_calls, f"{module} calls {name}")

    def test_the_no_guessing_guard_can_actually_fire(self):
        """Guard the guard: prove the AST check is not vacuous."""
        import ast
        tree = ast.parse("import difflib\nx = difflib.get_close_matches('a', ['b'])\n")
        found = [n.names[0].name for n in ast.walk(tree) if isinstance(n, ast.Import)]
        self.assertIn("difflib", found)

    def test_operational_reliability_is_never_mapped_to_deployment(self):
        """Reliability is an outcome; deployment/operations is a practice area."""
        rec = R.classify("operational_reliability", "area", self.cw)
        self.assertIsNone(rec["canonical"])
        self.assertEqual(rec["kind"], "UNRESOLVED_CONCEPT")
        self.assertTrue(rec["question"])

    def test_bare_software_stays_ambiguous(self):
        rec = R.classify("software", "area", self.cw)
        self.assertIsNone(rec["canonical"])
        self.assertEqual(rec["kind"], "AMBIGUOUS")

    def test_origin_qualified_group_joins_only_because_it_is_declared(self):
        rec = R.classify("ESS-SYN", "group", self.cw)
        self.assertEqual(rec["canonical"], "ESS")
        self.assertEqual(rec["kind"], "DECLARED_JUDGMENT")
        self.assertTrue(rec["question"], "a judgment must carry its question")
        # An undeclared sibling must NOT inherit the alias.
        self.assertEqual(R.classify("ESS-SYNTH", "group", self.cw)["kind"], "UNMAPPED")

    def test_a_service_level_term_is_flagged_not_silently_widened(self):
        rec = R.classify("iam-sso", "group", self.cw)
        self.assertEqual(rec["canonical"], "IAM")
        self.assertEqual(rec["kind"], "GRANULARITY_MISMATCH")
        self.assertIn("not interchangeable", rec["basis"])

    def test_every_declared_judgment_carries_a_question(self):
        for slot in ("area", "group"):
            for term, entry in self.cw[slot].items():
                if entry["kind"] in ("DECLARED_JUDGMENT", "AMBIGUOUS",
                                     "UNRESOLVED_CONCEPT"):
                    self.assertTrue(entry.get("question"),
                                    f"{slot}/{term} has no question for its owner")
                self.assertTrue(entry["basis"].strip(), f"{slot}/{term} has no basis")


class TestCompoundCells(unittest.TestCase):
    def setUp(self):
        self.cw = load_crosswalk()

    def test_a_compound_cell_is_not_split_into_independent_rows(self):
        rec = R.classify("ai_readiness|security", "area", self.cw)
        self.assertEqual(rec["kind"], "COMPOUND")
        self.assertIsNone(rec["canonical"])
        self.assertEqual(rec["parts"], ["ai_readiness", "security"])
        self.assertIn("double-count", rec["basis"])

    def test_a_compound_with_an_undeclared_part_says_which_part(self):
        rec = R.classify("security|not_a_real_area", "area", self.cw)
        self.assertEqual(rec["kind"], "COMPOUND")
        self.assertIn("not_a_real_area", rec["basis"])

    def test_slash_prose_is_reported_but_never_split(self):
        """The separator does not mean one thing, so it is not treated as one."""
        rec = R.classify("Deployment / operations", "area", self.cw)
        self.assertEqual(rec["kind"], "UNMAPPED")
        self.assertNotIn("parts", rec)
        note = R.slash_taxonomy_note([
            {"term": "Deployment / operations", "rows": 1, "lanes": ["lane_a"]},
            {"term": "Access / IAM / software delivery", "rows": 2, "lanes": ["lane_a"]},
        ])
        self.assertEqual(note["term_count"], 2)
        self.assertIn("does not carry one meaning", note["why_not_split"])


class TestAgainstTheRealTree(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = R.reconcile(REVENUE, load_crosswalk())

    def test_the_scan_found_a_real_disagreement(self):
        """If every lane agreed, this package would have nothing to say."""
        canon_for = {r["term"]: r["canonical"] for r in self.report["terms"]}
        sd_spellings = [t for t, c in canon_for.items() if c == "SD"]
        self.assertGreater(len(sd_spellings), 2,
                           f"expected several spellings of one area, saw {sd_spellings}")
        self.assertGreater(self.report["counts"]["needing_a_decision"], 0)

    def test_no_observed_term_is_dropped_from_the_totals(self):
        """An unmapped term must stay in the counts, not vanish to tidy the report."""
        observed = {(o["slot"], o["term"]) for o in self.report["observations"]}
        reported = {(r["slot"], r["term"]) for r in self.report["terms"]}
        self.assertEqual(observed, reported)
        self.assertEqual(self.report["counts"]["distinct_terms"], len(reported))
        self.assertEqual(
            self.report["counts"]["resolved"]
            + self.report["counts"]["needing_a_decision"],
            len(reported), "every term must land in exactly one of the two buckets")

    def test_row_counts_are_conserved(self):
        by_term = {}
        for o in self.report["observations"]:
            by_term[(o["slot"], o["term"])] = by_term.get((o["slot"], o["term"]), 0) + o["rows"]
        for r in self.report["terms"]:
            self.assertEqual(r["rows"], by_term[(r["slot"], r["term"])])

    def test_every_term_records_where_it_was_seen(self):
        for r in self.report["terms"]:
            self.assertTrue(r["files"], f"{r['term']} has no file evidence")
            self.assertTrue(r["lanes"])
            self.assertTrue(r["columns"])

    def test_collisions_are_reported_not_resolved(self):
        self.assertTrue(self.report["collisions"])
        for col in self.report["collisions"]:
            self.assertGreater(len(col["distinct_canonical"]), 1)
            self.assertGreater(len(col["terms"]), 1)

    def test_the_deployment_collision_that_caused_the_real_false_failure(self):
        """The concrete case: 'deployment' vs 'deployment_operations'."""
        terms = {r["term"] for r in self.report["terms"]}
        self.assertIn("deployment_operations", terms)
        self.assertIn("DEP", terms)
        for t in ("deployment_operations", "DEP"):
            rec = next(r for r in self.report["terms"] if r["term"] == t)
            self.assertEqual(rec["canonical"], "DEP")

    def test_scanning_writes_nothing_to_any_lane(self):
        """Read-only, proven by digest rather than by policy."""
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.join(tmp, "revenue")
            os.makedirs(root)
            for lane in sorted(os.listdir(REVENUE))[:6]:
                src = os.path.join(REVENUE, lane)
                if lane.startswith(SV.LANE_PREFIX) and os.path.isdir(src):
                    shutil.copytree(src, os.path.join(root, lane),
                                    ignore=shutil.ignore_patterns("__pycache__"))
            before = digest_tree(root)
            R.reconcile(root, load_crosswalk())
            self.assertEqual(digest_tree(root), before)

    def test_no_scoring_or_certification_language(self):
        """Scanned over the CLASSIFICATION data, not the disclaimers.

        The banner necessarily contains the words it disclaims ("no lane is scored,
        ranked or certified"), so a scan of the whole report flags its own promise.
        This looks at what the package actually says about each term.
        """
        parts = []
        for r in self.report["terms"]:
            parts += [r["kind"], r["basis"], r.get("question", ""),
                      str(r["canonical"])]
        for col in self.report["collisions"]:
            parts.append(col["why_it_matters"])
        for note in self.report.get("patterns", []):
            parts += [note["finding"], note["why_not_split"], note["question"]]
        blob = " ".join(parts).lower()
        for banned in ("maturity score", "percentile", "compliant", "certified",
                       "correct spelling", "wrong spelling", "violation", "non-compliant"):
            self.assertNotIn(banned, blob, f"found judgemental language: {banned}")

    def test_the_judgemental_language_guard_can_actually_fire(self):
        poisoned = json.loads(json.dumps(self.report))
        poisoned["terms"][0]["basis"] = "this lane's spelling is a violation"
        parts = [r["basis"] for r in poisoned["terms"]]
        self.assertIn("violation", " ".join(parts).lower())


class TestOutputs(unittest.TestCase):
    def test_cli_writes_all_artifacts_with_the_banner(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc = R.main(["--revenue-root", REVENUE, "--crosswalk", CROSSWALK_PATH,
                         "--out", tmp])
            self.assertEqual(rc, 0)
            for name in ("vocabulary_report.json", "term_crosswalk.csv",
                         "needs_a_decision.csv", "observations.csv",
                         "VOCABULARY_REPORT.md"):
                path = os.path.join(tmp, name)
                self.assertTrue(os.path.isfile(path), name)
                with open(path, encoding="utf-8") as fh:
                    self.assertIn("VOCABULARY RECONCILIATION", fh.read(), name)

    def test_unreadable_crosswalk_exits_2_rather_than_running_with_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = os.path.join(tmp, "bad.json")
            with open(bad, "w", encoding="utf-8") as fh:
                fh.write("{ not json")
            self.assertEqual(
                R.main(["--revenue-root", REVENUE, "--crosswalk", bad,
                        "--out", tmp]), 2)

    def test_missing_tree_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                R.main(["--revenue-root", os.path.join(tmp, "nope"),
                        "--crosswalk", CROSSWALK_PATH, "--out", tmp]), 2)

    def test_scanner_ignores_template_placeholders(self):
        with tempfile.TemporaryDirectory() as tmp:
            lane = os.path.join(tmp, SV.LANE_PREFIX + "fake")
            os.makedirs(lane)
            with open(os.path.join(lane, "w.csv"), "w", encoding="utf-8",
                      newline="\n") as fh:
                fh.write("group,area\n<ESS|RIS|IAM>,<area>\nESS,SD\n")
            obs = SV.scan(tmp)
            self.assertEqual({o["term"] for o in obs}, {"ESS", "SD"})


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestJoinSafety(unittest.TestCase):
    """Can these two files actually be joined? The 'so what' of the crosswalk."""

    def setUp(self):
        import join_safety
        self.JS = join_safety
        self.cw = load_crosswalk()

    def _csv(self, tmp, name, header, rows):
        path = os.path.join(tmp, name)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(header + "\n")
            for r in rows:
                fh.write(r + "\n")
        return path

    def test_identical_spellings_are_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = self._csv(tmp, "a.csv", "group,area", ["ESS,SD", "RIS,SEC"])
            b = self._csv(tmp, "b.csv", "group,area", ["ESS,SD", "RIS,SEC"])
            rep = self.JS.assess(a, b, self.cw)
            self.assertEqual(rep["overall_verdict"], self.JS.SAFE)
            self.assertEqual(rep["rows_at_risk"], 0)

    def test_different_spellings_of_the_same_areas_need_normalising(self):
        """The real case: a raw join here drops rows without saying so."""
        with tempfile.TemporaryDirectory() as tmp:
            a = self._csv(tmp, "a.csv", "group,area", ["ESS,SD", "RIS,SEC"])
            b = self._csv(tmp, "b.csv", "group,assessment_area",
                          ["ESS,software_development", "RIS,security"])
            rep = self.JS.assess(a, b, self.cw)
            self.assertEqual(rep["overall_verdict"], self.JS.NORMALISE)
            self.assertEqual(rep["rows_at_risk"], 4)
            area = next(s for s in rep["slots"] if s["slot"] == "area")
            self.assertIn("software_development", area["right_only"])

    def test_an_unresolved_term_makes_the_join_unsafe_and_names_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = self._csv(tmp, "a.csv", "group,area", ["ESS,SD"])
            b = self._csv(tmp, "b.csv", "group,area",
                          ["ESS,operational_reliability", "ESS,operational_reliability"])
            rep = self.JS.assess(a, b, self.cw)
            self.assertEqual(rep["overall_verdict"], self.JS.UNSAFE)
            area = next(s for s in rep["slots"] if s["slot"] == "area")
            names = {u["term"] for u in area["unresolved"]}
            self.assertEqual(names, {"operational_reliability"})
            self.assertEqual(area["unresolved"][0]["rows"], 2)
            self.assertTrue(area["unresolved"][0]["question"])

    def test_unsafe_outranks_normalise(self):
        """One unresolved term must not be masked by an otherwise tidy comparison."""
        with tempfile.TemporaryDirectory() as tmp:
            a = self._csv(tmp, "a.csv", "group,area", ["ESS,SD", "ESS,SEC"])
            b = self._csv(tmp, "b.csv", "group,area",
                          ["ESS,software_development", "ESS,operational_reliability"])
            rep = self.JS.assess(a, b, self.cw)
            self.assertEqual(rep["overall_verdict"], self.JS.UNSAFE)

    def test_a_missing_slot_is_not_comparable_rather_than_safe(self):
        """An absent column must never read as agreement."""
        with tempfile.TemporaryDirectory() as tmp:
            a = self._csv(tmp, "a.csv", "group,area", ["ESS,SD"])
            b = self._csv(tmp, "b.csv", "area", ["SD"])
            rep = self.JS.assess(a, b, self.cw)
            grp = next(s for s in rep["slots"] if s["slot"] == "group")
            self.assertEqual(grp["verdict"], self.JS.NOT_COMPARABLE)
            self.assertNotEqual(rep["overall_verdict"], self.JS.SAFE)

    def test_the_real_pair_that_caused_the_false_failure(self):
        """intake_rehearsal vs synthetic_collection - the actual incident."""
        left = os.path.join(REVENUE, "uiowa_rfq_18649_intake_rehearsal",
                            "artifacts", "assessment_matrix.csv")
        right = os.path.join(REVENUE, "uiowa_rfq_18649_synthetic_collection",
                             "coverage_matrix.csv")
        if not (os.path.isfile(left) and os.path.isfile(right)):
            self.skipTest("both lanes are not present in this tree")
        rep = self.JS.assess(left, right, self.cw)
        self.assertEqual(rep["overall_verdict"], self.JS.NORMALISE)
        self.assertGreater(rep["rows_at_risk"], 0)
        grp = next(s for s in rep["slots"] if s["slot"] == "group")
        self.assertEqual(grp["verdict"], self.JS.SAFE,
                         "the groups agree; only the area spellings differ")

    def test_cli_reports_and_exits_zero_for_an_unsafe_pair(self):
        """UNSAFE is a finding to report, not a crash."""
        with tempfile.TemporaryDirectory() as tmp:
            a = self._csv(tmp, "a.csv", "group,area", ["ESS,SD"])
            b = self._csv(tmp, "b.csv", "group,area", ["ESS,operational_reliability"])
            self.assertEqual(self.JS.main(["--left", a, "--right", b,
                                           "--crosswalk", CROSSWALK_PATH]), 0)

    def test_cli_exits_2_on_a_missing_file(self):
        self.assertEqual(
            self.JS.main(["--left", "nope_a.csv", "--right", "nope_b.csv",
                          "--crosswalk", CROSSWALK_PATH,
                          "--revenue-root", REVENUE]), 2)


class TestJsonScanAndPackedValues(unittest.TestCase):
    """Added after the CSV-only scan was found to miss whole spelling sets."""

    def setUp(self):
        self.cw = load_crosswalk()

    def test_json_fixtures_are_scanned(self):
        with tempfile.TemporaryDirectory() as tmp:
            lane = os.path.join(tmp, SV.LANE_PREFIX + "j")
            os.makedirs(lane)
            with open(os.path.join(lane, "f.json"), "w", encoding="utf-8") as fh:
                json.dump({"rows": [{"group": "ESS", "area": "SDLC"},
                                    {"group": "RIS", "area": "OPS"}]}, fh)
            obs = SV.scan(tmp)
            self.assertEqual({o["term"] for o in obs},
                             {"ESS", "RIS", "SDLC", "OPS"})
            self.assertTrue(all(o["file"].endswith(".json") for o in obs))

    def test_nested_json_paths_are_reached(self):
        with tempfile.TemporaryDirectory() as tmp:
            lane = os.path.join(tmp, SV.LANE_PREFIX + "j")
            os.makedirs(lane)
            with open(os.path.join(lane, "f.json"), "w", encoding="utf-8") as fh:
                json.dump({"a": {"b": [{"c": {"area": "SEC"}}]}}, fh)
            self.assertEqual({o["term"] for o in SV.scan(tmp)}, {"SEC"})

    def test_unparseable_json_is_skipped_not_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            lane = os.path.join(tmp, SV.LANE_PREFIX + "j")
            os.makedirs(lane)
            with open(os.path.join(lane, "bad.json"), "w", encoding="utf-8") as fh:
                fh.write("{ not json")
            with open(os.path.join(lane, "ok.json"), "w", encoding="utf-8") as fh:
                json.dump({"area": "SD"}, fh)
            self.assertEqual({o["term"] for o in SV.scan(tmp)}, {"SD"})

    def test_csv_only_scan_still_available_and_misses_json(self):
        """The limitation this change closed, pinned so it cannot silently return."""
        with tempfile.TemporaryDirectory() as tmp:
            lane = os.path.join(tmp, SV.LANE_PREFIX + "j")
            os.makedirs(lane)
            with open(os.path.join(lane, "f.json"), "w", encoding="utf-8") as fh:
                json.dump({"area": "SDLC"}, fh)
            self.assertEqual(SV.scan(tmp, formats=("csv",)), [])
            self.assertTrue(SV.scan(tmp, formats=("json",)))

    def test_a_packed_group_area_value_is_reported_not_split(self):
        rec = R.classify("ESS:DEP", "area", self.cw)
        self.assertEqual(rec["kind"], "CROSS_SLOT_PACKED")
        self.assertIsNone(rec["canonical"])
        self.assertEqual(rec["parts"], ["ESS", "DEP"])
        self.assertIn("changes the row's cardinality", rec["basis"])

    def test_a_colon_value_whose_halves_are_not_declared_stays_unmapped(self):
        """The packed class is verified structurally, not assumed from the colon."""
        rec = R.classify("WIDGET:THING", "area", self.cw)
        self.assertEqual(rec["kind"], "UNMAPPED")

    def test_all_is_a_scope_value_not_an_area(self):
        rec = R.classify("ALL", "area", self.cw)
        self.assertIsNone(rec["canonical"])
        self.assertEqual(rec["kind"], "SCOPE_VALUE_AREA")

    def test_ops_and_sdlc_are_declared_judgments_with_questions(self):
        for term, canon in (("OPS", "DEP"), ("SDLC", "SD")):
            rec = R.classify(term, "area", self.cw)
            self.assertEqual(rec["canonical"], canon)
            self.assertEqual(rec["kind"], "DECLARED_JUDGMENT")
            self.assertTrue(rec["question"])


class TestKeyNameCollisions(unittest.TestCase):
    def test_a_key_with_disjoint_value_sets_is_reported(self):
        obs = [
            {"column": "dimension", "lane": "lane_a", "term": "ai_readiness",
             "slot": "area", "rows": 1},
            {"column": "dimension", "lane": "lane_b", "term": "quality",
             "slot": "area", "rows": 1},
        ]
        found = R.key_name_collisions(obs)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["key"], "dimension")
        self.assertIn(["lane_a", "lane_b"],
                      found[0]["lane_pairs_with_no_shared_value"])

    def test_a_key_with_shared_values_is_not_reported(self):
        obs = [
            {"column": "group", "lane": "lane_a", "term": "ESS", "slot": "group",
             "rows": 1},
            {"column": "group", "lane": "lane_b", "term": "ESS", "slot": "group",
             "rows": 1},
        ]
        self.assertEqual(R.key_name_collisions(obs), [])

    def test_a_key_used_by_one_lane_only_is_not_a_collision(self):
        obs = [{"column": "area", "lane": "lane_a", "term": "SD", "slot": "area",
                "rows": 1}]
        self.assertEqual(R.key_name_collisions(obs), [])

    def test_the_real_tree_reports_key_collisions(self):
        report = R.reconcile(REVENUE, load_crosswalk())
        self.assertTrue(report["key_name_collisions"])
        for kc in report["key_name_collisions"]:
            self.assertTrue(kc["lane_pairs_with_no_shared_value"])
            self.assertGreaterEqual(len(kc["values_by_lane"]), 2)
