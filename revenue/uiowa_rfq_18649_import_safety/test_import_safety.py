"""Tests for the import-safety audit. Stdlib unittest, no network.

    python3 -m unittest -v test_import_safety.py

The load-bearing test is `test_naive_import_silently_returns_the_wrong_module`.
It asserts that the bug is real, using two fixture lanes that return different
values, because the failure is not an exception -- it is the wrong module
answering plausibly. A fixture where both lanes raise would pass whether or not
the bug existed.

Every test builds its own synthetic tree. Nothing here reads the live
repository: the kit changes every time a seat lands, and a test bound to it
would fail for reasons unrelated to this code.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import reproduce  # noqa: E402
import safe_import  # noqa: E402
import scan  # noqa: E402

ALPHA = os.path.join(HERE, "fixtures", "lane_alpha")
BETA = os.path.join(HERE, "fixtures", "lane_beta")


class _CleanImportState(unittest.TestCase):
    """Each test restores sys.path and sys.modules exactly."""

    def setUp(self):
        self._path = list(sys.path)
        self._modules = dict(sys.modules)

    def tearDown(self):
        sys.path[:] = self._path
        sys.modules.clear()
        sys.modules.update(self._modules)


class ShadowingTests(_CleanImportState):

    def test_the_fixtures_actually_differ(self):
        # If they did not, nothing below could detect the bug.
        with open(os.path.join(ALPHA, "report.py"), encoding="utf-8") as a:
            with open(os.path.join(BETA, "report.py"), encoding="utf-8") as b:
                self.assertNotEqual(a.read(), b.read())

    def test_naive_import_silently_returns_the_wrong_module(self):
        first, second = reproduce.naive(ALPHA, BETA, "report")
        self.assertIs(first, second,
                      "the second lane should have been shadowed by the first")
        self.assertEqual(second.LANE, "alpha")
        self.assertEqual(second.summary(), "ALPHA: 3 findings",
                         "lane BETA asked for its own module and got ALPHA's "
                         "answer, with no exception raised")

    def test_scoped_import_gives_each_lane_its_own_module(self):
        first, second = reproduce.scoped(ALPHA, BETA, "report")
        self.assertIsNot(first, second)
        self.assertEqual(first.summary(), "ALPHA: 3 findings")
        self.assertEqual(second.summary(), "BETA: 7 findings")

    def test_scoped_import_does_not_claim_the_bare_name(self):
        safe_import.load(ALPHA, "report")
        self.assertNotIn("report", sys.modules,
                         "the bare name must stay free for other lanes")

    def test_qualified_names_are_distinct_and_stable(self):
        a = safe_import.qualified_name(ALPHA, "report")
        b = safe_import.qualified_name(BETA, "report")
        self.assertNotEqual(a, b)
        self.assertEqual(a, safe_import.qualified_name(ALPHA + os.sep,
                                                       "report"))
        self.assertTrue(a.startswith(safe_import.NAMESPACE + "."))

    def test_repeat_load_is_cached_not_re_executed(self):
        first = safe_import.load(ALPHA, "report")
        self.assertIs(first, safe_import.load(ALPHA, "report"))

    def test_reload_re_executes(self):
        first = safe_import.load(ALPHA, "report")
        self.assertIsNot(first, safe_import.load(ALPHA, "report", reload=True))

    def test_loaded_lanes_reports_what_is_held(self):
        safe_import.load(ALPHA, "report")
        held = safe_import.loaded_lanes()
        self.assertTrue(any("lane_alpha" in k for k in held))


class SafeImportFailureTests(_CleanImportState):

    def test_missing_module_raises_a_named_error(self):
        with self.assertRaises(safe_import.LaneImportError):
            safe_import.load(ALPHA, "does_not_exist")

    def test_missing_lane_raises_a_named_error(self):
        with self.assertRaises(safe_import.LaneImportError):
            safe_import.load(os.path.join(HERE, "no_such_lane"), "report")

    def test_a_module_that_raises_is_not_left_half_initialised(self):
        # A half-initialised module in sys.modules is this same failure class
        # one level down: the next caller gets an object whose attributes
        # silently do not exist.
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        with open(os.path.join(tmp, "boom.py"), "w", encoding="utf-8") as fh:
            fh.write("VALUE = 1\nraise RuntimeError('boom')\n")
        with self.assertRaises(RuntimeError):
            safe_import.load(tmp, "boom")
        self.assertNotIn(safe_import.qualified_name(tmp, "boom"), sys.modules)

    def test_lane_path_restores_sys_path_even_when_the_body_raises(self):
        before = list(sys.path)
        with self.assertRaises(ValueError):
            with safe_import.lane_path(ALPHA):
                sys.path.insert(0, "/injected/by/a/module")
                raise ValueError("boom")
        self.assertEqual(sys.path, before,
                         "a module that mutates sys.path must not leave its "
                         "entries behind for the next lane")

    def test_isolated_load_resolves_sibling_imports_inside_the_lane(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        lane = os.path.join(tmp, "lane_x")
        os.makedirs(lane)
        with open(os.path.join(lane, "helper.py"), "w", encoding="utf-8") as f:
            f.write("NAME = 'lane_x helper'\n")
        with open(os.path.join(lane, "main.py"), "w", encoding="utf-8") as f:
            f.write("import helper\nNAME = helper.NAME\n")
        module = safe_import.load_lane_isolated(lane, "main")
        self.assertEqual(module.NAME, "lane_x helper")


class ScanTests(unittest.TestCase):

    def _kit(self, spec, path_hack=True):
        """Build a synthetic kit: {lane_suffix: [module names]}."""
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        for suffix, modules in spec.items():
            lane = os.path.join(root, "uiowa_rfq_18649_" + suffix)
            os.makedirs(lane)
            for i, name in enumerate(modules):
                body = "VALUE = 1\n"
                if path_hack and i == 0:
                    body = ("import os, sys\n"
                            "sys.path.insert(0, os.path.dirname(__file__))\n")
                with open(os.path.join(lane, name + ".py"), "w",
                          encoding="utf-8") as fh:
                    fh.write(body)
        return root

    def test_collision_across_lanes_is_found(self):
        root = self._kit({"alpha": ["cli", "alpha_only"],
                          "beta": ["cli", "beta_only"]})
        found = scan.collisions(scan.survey(root))
        names = [c.module_name for c in found]
        self.assertEqual(names, ["cli"])
        self.assertEqual(found[0].lanes,
                         ["uiowa_rfq_18649_alpha", "uiowa_rfq_18649_beta"])

    def test_unique_names_are_not_reported(self):
        root = self._kit({"alpha": ["alpha_only"], "beta": ["beta_only"]})
        self.assertEqual(scan.collisions(scan.survey(root)), [])

    def test_collision_is_active_risk_when_a_path_hack_exists(self):
        root = self._kit({"alpha": ["cli"], "beta": ["cli"]}, path_hack=True)
        found = scan.collisions(scan.survey(root))
        self.assertEqual(found[0].risk, scan.ACTIVE_RISK)

    def test_collision_is_latent_without_a_path_hack(self):
        # A latent collision is not a defect and must not be reported as one.
        root = self._kit({"alpha": ["cli"], "beta": ["cli"]}, path_hack=False)
        found = scan.collisions(scan.survey(root))
        self.assertEqual(found[0].risk, scan.LATENT)

    def test_unparsable_file_forces_unknown_never_clean(self):
        root = self._kit({"alpha": ["cli"], "beta": ["cli"]}, path_hack=False)
        broken = os.path.join(root, "uiowa_rfq_18649_alpha", "broken.py")
        with open(broken, "w", encoding="utf-8") as fh:
            fh.write("def (:\n")
        found = scan.collisions(scan.survey(root))
        self.assertEqual(found[0].risk, scan.UNKNOWN)

    def test_colliding_test_modules_are_always_active_risk(self):
        root = self._kit({"alpha": ["test_thing"], "beta": ["test_thing"]},
                         path_hack=False)
        found = scan.collisions(scan.survey(root))
        self.assertTrue(any(c.module_name == "test_thing"
                            and c.risk == scan.ACTIVE_RISK for c in found))

    def test_nested_modules_do_not_collide_with_top_level_ones(self):
        root = self._kit({"alpha": ["cli"], "beta": ["other"]},
                         path_hack=False)
        nested = os.path.join(root, "uiowa_rfq_18649_beta", "sub")
        os.makedirs(nested)
        with open(os.path.join(nested, "cli.py"), "w", encoding="utf-8") as fh:
            fh.write("VALUE = 1\n")
        self.assertEqual(scan.collisions(scan.survey(root)), [])

    def test_init_py_is_not_counted_as_a_module(self):
        root = self._kit({"alpha": ["cli"], "beta": ["cli"]}, path_hack=False)
        for suffix in ("alpha", "beta"):
            with open(os.path.join(root, "uiowa_rfq_18649_" + suffix,
                                   "__init__.py"), "w",
                      encoding="utf-8") as fh:
                fh.write("")
        result = scan.survey(root)
        self.assertNotIn("__init__", result.top_level_modules)
        self.assertEqual(len(result.packaged_lanes), 2)

    def test_scan_ignores_directories_that_are_not_lanes(self):
        root = self._kit({"alpha": ["cli"]}, path_hack=False)
        other = os.path.join(root, "not_a_lane")
        os.makedirs(other)
        with open(os.path.join(other, "cli.py"), "w", encoding="utf-8") as fh:
            fh.write("VALUE = 1\n")
        self.assertEqual(scan.survey(root).lanes, ["uiowa_rfq_18649_alpha"])

    def test_missing_root_yields_an_empty_survey(self):
        result = scan.survey(os.path.join(HERE, "definitely_not_here"))
        self.assertEqual(result.lanes, [])
        self.assertEqual(scan.collisions(result), [])

    def test_summary_counts_reconcile(self):
        root = self._kit({"alpha": ["cli", "model"], "beta": ["cli", "model"]})
        result = scan.survey(root)
        found = scan.collisions(result)
        summary = scan.summarise(result, found)
        self.assertEqual(summary["collisions"], len(found))
        self.assertEqual(sum(summary["by_risk"].values()), len(found))

    def test_scan_is_deterministic(self):
        root = self._kit({"alpha": ["cli"], "beta": ["cli"]})
        first = [c.as_dict() for c in scan.collisions(scan.survey(root))]
        for _ in range(3):
            self.assertEqual(
                [c.as_dict() for c in scan.collisions(scan.survey(root))],
                first)

    def test_no_score_rating_or_ranking_field_is_emitted(self):
        root = self._kit({"alpha": ["cli"], "beta": ["cli"]})
        payload = json.dumps(
            [c.as_dict() for c in scan.collisions(scan.survey(root))]).lower()
        for banned in ("score", "rating", "percentile", "rank", "grade",
                       "author", "seat", "worst"):
            self.assertNotIn('"%s"' % banned, payload)


class CommandLineTests(unittest.TestCase):

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, os.path.join(HERE, "importsafety.py")]
            + list(args), capture_output=True, text=True, cwd=HERE)

    def test_reproduce_exits_one_and_shows_both_paths(self):
        proc = self._run("reproduce")
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("SAME MODULE OBJECT: True", proc.stdout)
        self.assertIn("BETA: 7 findings", proc.stdout)

    def test_scan_of_a_kitless_directory_exits_zero(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        proc = self._run("scan", tmp)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("No colliding module names.", proc.stdout)

    def test_scan_json_is_machine_readable(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        proc = self._run("scan", tmp, "--json")
        payload = json.loads(proc.stdout)
        self.assertIn("summary", payload)
        self.assertIn("collisions", payload)

    def test_no_arguments_is_a_usage_error_not_a_pass(self):
        self.assertEqual(self._run().returncode, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
