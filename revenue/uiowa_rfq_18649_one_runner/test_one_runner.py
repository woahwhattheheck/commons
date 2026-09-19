#!/usr/bin/env python3
"""Tests for the OPS-ONE-RUNNER single-runner readiness check.

Built on synthetic lane trees in temp directories, never on the real
repository, so the suite is hermetic and does not change meaning as other
seats land work. That matters here more than usual: the first version of the
state-leakage check was measured against the live tree and produced two false
positives because other writers were landing into it concurrently.

The ones that matter:

  * a lane that depends on the working directory must be caught, and one that
    does not must not be flagged
  * a module name shared by two lanes must be found, and the shadowing
    demonstrated rather than asserted
  * a lane writing outside itself must be caught without watching a tree that
    other writers share
  * a lane with no suite must be UNKNOWN, never a failure

Run:  python3 -m unittest -v test_one_runner
"""

import hashlib
import json
import os
import shutil
import tempfile
import unittest

import one_runner as orr


# A suite that reads its fixture relative to the PROCESS working directory.
# Passes when run from the lane, fails when run from the repository root.
CWD_DEPENDENT = """import unittest
class T(unittest.TestCase):
    def test_reads_fixture(self):
        with open("fixtures/data.txt") as handle:
            self.assertEqual(handle.read().strip(), "ok")
"""

# The same thing, resolved relative to the test file instead.
CWD_INDEPENDENT = """import os, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
class T(unittest.TestCase):
    def test_reads_fixture(self):
        with open(os.path.join(HERE, "fixtures", "data.txt")) as handle:
            self.assertEqual(handle.read().strip(), "ok")
"""

PASSING = """import unittest
class T(unittest.TestCase):
    def test_a(self):
        self.assertTrue(True)
"""

# Writes into a sibling lane directory.
LEAKY = """import os, unittest
class T(unittest.TestCase):
    def test_writes_next_door(self):
        target = os.path.join("..", "uiowa_rfq_18649_zz_neighbour", "leaked.txt")
        with open(target, "w") as handle:
            handle.write("leaked\\n")
        self.assertTrue(os.path.exists(target))
"""

# Writes only inside its own directory.
TIDY = """import os, unittest
class T(unittest.TestCase):
    def test_writes_inside(self):
        with open("scratch.txt", "w") as handle:
            handle.write("fine\\n")
        self.assertTrue(os.path.exists("scratch.txt"))
"""


class Harness(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.revenue = os.path.join(self.root, "revenue")
        os.makedirs(self.revenue)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def lane(self, name, files):
        path = os.path.join(self.revenue, "uiowa_rfq_18649_" + name)
        os.makedirs(path, exist_ok=True)
        for rel, content in files.items():
            full = os.path.join(path, rel)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as handle:
                handle.write(content)
        return path

    def analyse(self, skip_leakage=False, timeout=60):
        return orr.analyse(self.root, "uiowa_rfq_18649_", timeout,
                           "2026-09-19", skip_leakage)

    def by_lane(self, rows):
        return {r["lane"]: r for r in rows}


class WorkingDirectory(Harness):

    def test_a_cwd_dependent_lane_is_caught(self):
        self.lane("dependent", {"test_x.py": CWD_DEPENDENT,
                                "fixtures/data.txt": "ok\n"})
        report = self.analyse(skip_leakage=True)
        row = self.by_lane(report["cwd_independence"])["uiowa_rfq_18649_dependent"]
        self.assertEqual(row["status"], orr.FAIL)
        self.assertEqual(row["from_lane"], 0)
        self.assertNotEqual(row["from_root"], 0)
        self.assertFalse(report["summary"]["cwd_safe"])
        self.assertIn("uiowa_rfq_18649_dependent",
                      report["summary"]["cwd_dependent_lanes"])

    def test_a_cwd_independent_lane_is_not_flagged(self):
        self.lane("independent", {"test_x.py": CWD_INDEPENDENT,
                                  "fixtures/data.txt": "ok\n"})
        report = self.analyse(skip_leakage=True)
        row = self.by_lane(report["cwd_independence"])["uiowa_rfq_18649_independent"]
        self.assertEqual(row["status"], orr.PASS)
        self.assertTrue(report["summary"]["cwd_safe"])

    def test_a_failing_lane_that_fails_both_ways_is_not_a_cwd_problem(self):
        # Consistently broken is a different finding, and not this one.
        self.lane("broken", {"test_x.py":
                             "import unittest\n"
                             "class T(unittest.TestCase):\n"
                             "    def test_a(self):\n"
                             "        self.assertEqual(1, 2)\n"})
        report = self.analyse(skip_leakage=True)
        row = self.by_lane(report["cwd_independence"])["uiowa_rfq_18649_broken"]
        self.assertEqual(row["status"], orr.PASS)
        self.assertEqual(row["from_lane"], row["from_root"])

    def test_a_lane_without_a_suite_is_not_assessed(self):
        self.lane("docs", {"README.md": "# notes\n"})
        report = self.analyse(skip_leakage=True)
        row = self.by_lane(report["cwd_independence"])["uiowa_rfq_18649_docs"]
        self.assertEqual(row["status"], orr.NO_SUITE)
        self.assertEqual(row["from_lane"], "UNKNOWN")
        self.assertEqual(report["summary"]["lanes_assessed"], 0)
        self.assertEqual(report["summary"]["lanes_without_a_suite"], 1)
        self.assertTrue(report["summary"]["cwd_safe"])


class ModuleCollisions(Harness):

    def test_a_shared_module_name_is_found(self):
        self.lane("alpha", {"schema.py": "NAME = 'alpha'\n",
                            "test_x.py": PASSING})
        self.lane("bravo", {"schema.py": "NAME = 'bravo'\n",
                            "test_x.py": PASSING})
        report = self.analyse(skip_leakage=True)
        collisions = report["modules"]["collisions"]
        self.assertEqual(len(collisions), 1)
        self.assertEqual(collisions[0]["module"], "schema")
        self.assertEqual(collisions[0]["lanes"],
                         ["uiowa_rfq_18649_alpha", "uiowa_rfq_18649_bravo"])
        self.assertFalse(report["summary"]["single_process_safe"])

    def test_distinct_module_names_do_not_collide(self):
        self.lane("alpha", {"alpha_schema.py": "NAME = 'a'\n",
                            "test_x.py": PASSING})
        self.lane("bravo", {"bravo_schema.py": "NAME = 'b'\n",
                            "test_x.py": PASSING})
        report = self.analyse(skip_leakage=True)
        self.assertEqual(report["modules"]["collisions"], [])
        self.assertTrue(report["summary"]["single_process_safe"])

    def test_test_modules_are_excluded_from_collision_detection(self):
        # Every lane naming its suite test_x.py is normal and is not a hazard:
        # a runner imports a test module by its own name, and no lane imports
        # another lane's tests.
        self.lane("alpha", {"test_x.py": PASSING})
        self.lane("bravo", {"test_x.py": PASSING})
        report = self.analyse(skip_leakage=True)
        self.assertEqual(report["modules"]["collisions"], [])

    def test_proposed_fixes_name_the_lanes_without_choosing_one(self):
        self.lane("alpha", {"schema.py": "NAME = 'alpha'\n",
                            "test_x.py": PASSING})
        self.lane("bravo", {"schema.py": "NAME = 'bravo'\n",
                            "test_x.py": PASSING})
        fixes = self.analyse(skip_leakage=True)["proposed_fixes"]
        self.assertEqual(len(fixes), 1)
        self.assertEqual(len(fixes[0]["options"]), 2)
        self.assertIn("lane owners", fixes[0]["owner_decision"])


class Crosstalk(Harness):

    def test_the_second_lane_receives_the_first_lanes_module(self):
        self.lane("alpha", {"schema.py": "NAME = 'alpha'\n",
                            "test_x.py": PASSING})
        self.lane("bravo", {"schema.py": "NAME = 'bravo'\n",
                            "test_x.py": PASSING})
        report = self.analyse(skip_leakage=True)
        demo = report["crosstalk"][0]
        self.assertEqual(demo["module"], "schema")
        self.assertEqual(demo["shadowed"], ["uiowa_rfq_18649_bravo"])
        self.assertIn("uiowa_rfq_18649_alpha", demo["resolved_to"])
        # Both observations resolve to the same file: that is the whole point.
        files = {o["resolved_to"] for o in demo["observations"]}
        self.assertEqual(len(files), 1)

    def test_no_collision_means_nothing_to_demonstrate(self):
        self.lane("alpha", {"alpha_schema.py": "NAME = 'a'\n",
                            "test_x.py": PASSING})
        report = self.analyse(skip_leakage=True)
        self.assertEqual(report["crosstalk"], [])
        self.assertEqual(report["summary"]["shadowed_lanes"], [])

    def test_three_lanes_sharing_a_name_shadow_two(self):
        for name in ("alpha", "bravo", "charlie"):
            self.lane(name, {"schema.py": "NAME = %r\n" % name,
                             "test_x.py": PASSING})
        report = self.analyse(skip_leakage=True)
        self.assertEqual(len(report["crosstalk"][0]["shadowed"]), 2)


class StateLeakage(Harness):

    def test_a_lane_writing_next_door_is_caught(self):
        self.lane("leaky", {"test_x.py": LEAKY})
        report = self.analyse()
        row = self.by_lane(report["state_leakage"])["uiowa_rfq_18649_leaky"]
        self.assertEqual(row["status"], orr.FAIL)
        self.assertTrue(any("leaked.txt" in p for p in row["created"]))
        self.assertIn("uiowa_rfq_18649_leaky", report["summary"]["leaking_lanes"])

    def test_a_lane_writing_only_inside_itself_is_clean(self):
        self.lane("tidy", {"test_x.py": TIDY})
        report = self.analyse()
        row = self.by_lane(report["state_leakage"])["uiowa_rfq_18649_tidy"]
        self.assertEqual(row["status"], orr.PASS)
        self.assertEqual(report["summary"]["leaking_lanes"], [])

    def test_the_check_runs_on_a_copy_and_leaves_the_original_alone(self):
        # This is the fix for the live-tree false positives. Running the leaky
        # lane must not write into the real neighbour directory.
        self.lane("leaky", {"test_x.py": LEAKY})
        self.lane("neighbour_real", {"README.md": "# untouched\n"})
        before = self._hash_tree(self.revenue)
        self.analyse()
        after = self._hash_tree(self.revenue)
        self.assertEqual(before, after,
                         "the leakage check must not modify the tree it reads")

    def test_a_lane_without_a_suite_is_not_assessed_for_leakage(self):
        self.lane("docs", {"README.md": "# notes\n"})
        report = self.analyse()
        row = self.by_lane(report["state_leakage"])["uiowa_rfq_18649_docs"]
        self.assertEqual(row["status"], orr.NO_SUITE)
        self.assertEqual(report["summary"]["leakage_assessed"], 0)

    def test_skip_leakage_records_no_leakage_results(self):
        self.lane("tidy", {"test_x.py": TIDY})
        report = self.analyse(skip_leakage=True)
        self.assertEqual(report["state_leakage"], [])
        self.assertEqual(report["summary"]["leakage_assessed"], 0)

    def _hash_tree(self, path):
        digests = {}
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in orr.IGNORED_DIRS]
            for name in sorted(files):
                full = os.path.join(root, name)
                with open(full, "rb") as handle:
                    digests[os.path.relpath(full, path)] = hashlib.sha256(
                        handle.read()).hexdigest()
        return digests


class Outputs(Harness):

    def test_cli_writes_three_artifacts_and_flags_a_hazard_in_the_exit_code(self):
        self.lane("alpha", {"schema.py": "NAME = 'a'\n", "test_x.py": PASSING})
        self.lane("bravo", {"schema.py": "NAME = 'b'\n", "test_x.py": PASSING})
        outdir = os.path.join(self.root, "out")
        code = orr.main(["--root", self.root, "--outdir", outdir,
                         "--observed-on", "2026-09-19", "--skip-leakage",
                         "--quiet"])
        self.assertEqual(code, 1)
        for name in ("one_runner.json", "one_runner.csv", "one_runner_report.md"):
            self.assertTrue(os.path.exists(os.path.join(outdir, name)), name)

    def test_cli_exits_zero_when_no_hazard_fires(self):
        self.lane("alpha", {"alpha_schema.py": "NAME = 'a'\n",
                            "test_x.py": CWD_INDEPENDENT,
                            "fixtures/data.txt": "ok\n"})
        code = orr.main(["--root", self.root,
                         "--outdir", os.path.join(self.root, "out"),
                         "--observed-on", "2026-09-19", "--quiet"])
        self.assertEqual(code, 0)

    def test_missing_root_is_refused(self):
        code = orr.main(["--root", os.path.join(self.root, "nope"),
                         "--outdir", os.path.join(self.root, "out"),
                         "--observed-on", "2026-09-19", "--quiet"])
        self.assertEqual(code, 2)

    def test_observed_on_is_required(self):
        with self.assertRaises(SystemExit):
            orr.main(["--root", self.root])

    def test_csv_never_leaves_a_cell_blank(self):
        self.lane("alpha", {"schema.py": "NAME = 'a'\n", "test_x.py": PASSING})
        self.lane("docs", {"README.md": "# notes\n"})
        outdir = os.path.join(self.root, "out")
        orr.main(["--root", self.root, "--outdir", outdir,
                  "--observed-on", "2026-09-19", "--skip-leakage", "--quiet"])
        import csv as csv_mod
        with open(os.path.join(outdir, "one_runner.csv"), encoding="utf-8",
                  newline="") as handle:
            rows = list(csv_mod.DictReader(handle))
        self.assertEqual(len(rows), 2)
        for row in rows:
            for column, value in row.items():
                self.assertNotEqual(str(value).strip(), "",
                                    "blank %s for %s" % (column, row["lane"]))

    def test_a_clean_hazard_is_published_not_omitted(self):
        # A disproved hypothesis is a finding and must appear in the report.
        self.lane("alpha", {"alpha_schema.py": "NAME = 'a'\n",
                            "test_x.py": CWD_INDEPENDENT,
                            "fixtures/data.txt": "ok\n"})
        text = orr.render_report(self.analyse())
        self.assertIn("No lane differed", text)
        self.assertIn("No name is shared by more than one lane", text)

    def test_report_states_what_a_clean_result_does_not_mean(self):
        self.lane("alpha", {"test_x.py": PASSING})
        text = orr.render_report(self.analyse(skip_leakage=True))
        self.assertIn("not a statement that any component is correct", text)
        self.assertIn("not assessed", text)


class Determinism(Harness):

    def test_classification_is_stable_across_runs(self):
        self.lane("alpha", {"schema.py": "NAME = 'a'\n", "test_x.py": PASSING})
        self.lane("bravo", {"schema.py": "NAME = 'b'\n", "test_x.py": PASSING})

        def shape(report):
            return (report["summary"]["colliding_modules"],
                    report["summary"]["shadowed_lanes"],
                    report["summary"]["cwd_dependent_lanes"],
                    [(r["lane"], r["status"]) for r in report["cwd_independence"]])

        self.assertEqual(shape(self.analyse(skip_leakage=True)),
                         shape(self.analyse(skip_leakage=True)))

    def test_source_reads_no_clock(self):
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "one_runner.py"), encoding="utf-8") as handle:
            source = handle.read()
        for banned in ("datetime.now", "date.today", "random."):
            self.assertNotIn(banned, source,
                             "%s would make the report irreproducible" % banned)

    def test_json_is_serialisable(self):
        self.lane("alpha", {"test_x.py": PASSING})
        json.dumps(self.analyse(skip_leakage=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
