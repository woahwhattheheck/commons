"""Tests for the filesystem-safety screen.

Several of these are regression tests for bugs the fixtures caught in the screen
itself -- each is named for the wrong answer it prevents. The last class is the
screen applied to its own source: a tool that audits other people's destructive
calls has no business making any.
"""
from __future__ import annotations

import ast
import hashlib
import os
import shutil
import tempfile
import unittest

import fs_safety
import fsaudit
from fsaudit import (
    CLEAN, REVIEW_REQUIRED, SELF_SCOPED, TEST_CONTEXT, UNDETERMINED, UNPARSEABLE,
    WRITE_TO_CALLER_PATH,
)

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")
PRODUCTION_MODULES = ("fsaudit.py", "fs_safety.py")


def classify(source: str, module: str = "mod.py"):
    return fsaudit.scan_source(source, "lane", module)


def only(report, kind=None):
    return [f for f in report.findings if kind is None or f.kind == kind]


def hash_tree(root: str) -> dict:
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            with open(full, "rb") as fh:
                out[os.path.relpath(full, root)] = hashlib.sha256(fh.read()).hexdigest()
    return out


class TestFixtures(unittest.TestCase):
    """The committed fixtures pin one classification each."""

    def setUp(self):
        self.by_module = {r.module: r for r in fsaudit.scan_tree(FIXTURES)}

    def test_clean_module_is_clean(self):
        r = self.by_module[os.path.join("lane_clean", "tool_clean.py")]
        self.assertEqual(r.status, SELF_SCOPED)
        self.assertFalse([f for f in r.findings if f.classification == REVIEW_REQUIRED])

    def test_self_scoped_temp_cleanup(self):
        r = self.by_module[os.path.join("lane_self_scoped", "tool_temp.py")]
        self.assertEqual(r.status, SELF_SCOPED)

    def test_external_paths_are_review_required(self):
        r = self.by_module[os.path.join("lane_external", "tool_argv.py")]
        self.assertEqual(r.status, REVIEW_REQUIRED)
        self.assertEqual(len([f for f in r.findings
                              if f.classification == REVIEW_REQUIRED]), 3)

    def test_subprocess_is_undetermined_never_clean(self):
        r = self.by_module[os.path.join("lane_opaque", "tool_shell.py")]
        self.assertEqual(r.status, UNDETERMINED)
        self.assertEqual(only(r)[0].kind, fsaudit.OPAQUE)


class TestRegressions(unittest.TestCase):
    """Each of these is a wrong answer the screen gave before it was fixed."""

    def test_sys_argv_subscript_is_not_merely_undetermined(self):
        """It reported `shutil.rmtree(sys.argv[1])` as UNDETERMINED.

        ast.Subscript fell through the tracer, so the single most obviously
        external source got the screen's softest verdict.
        """
        r = classify("import shutil, sys\ndef f():\n    shutil.rmtree(sys.argv[1])\n")
        self.assertEqual(r.findings[0].classification, REVIEW_REQUIRED)

    def test_config_subscript_is_external(self):
        r = classify(
            "import json, shutil\n"
            "def f(p):\n"
            "    cfg = json.load(open(p))\n"
            "    shutil.rmtree(cfg['dir'])\n"
        )
        self.assertEqual(r.findings[0].classification, REVIEW_REQUIRED)

    def test_testcase_setup_tempdir_is_self_scoped(self):
        """It reported `self.dir = mkdtemp()` cleanup as caller-supplied.

        That is the single most common shape in any unittest suite, and calling
        it REVIEW_REQUIRED buried the real findings under dozens of false ones.
        """
        r = classify(
            "import shutil, tempfile, unittest\n"
            "class T(unittest.TestCase):\n"
            "    def setUp(self):\n"
            "        self.dir = tempfile.mkdtemp()\n"
            "    def tearDown(self):\n"
            "        shutil.rmtree(self.dir)\n",
            module="test_thing.py",
        )
        self.assertEqual(r.status, TEST_CONTEXT)

    def test_ordinary_report_writer_is_not_review_required(self):
        """32 modules were REVIEW_REQUIRED for `open(path, "w")` on a --out path.

        Every CLI in the kit takes an output option, so that verdict was noise
        that buried the two findings that mattered. Writes get their own class;
        REVIEW_REQUIRED now means "can destroy a path you name".
        """
        r = classify(
            "def write_report(path, text):\n"
            "    with open(path, 'w') as fh:\n"
            "        fh.write(text)\n"
        )
        self.assertEqual(r.findings[0].classification, WRITE_TO_CALLER_PATH)
        self.assertEqual(r.status, WRITE_TO_CALLER_PATH)

    def test_guarded_write_is_downgraded_but_a_guarded_delete_is_not(self):
        """The guard heuristic may soften a write. It must never soften a delete."""
        guarded_write = classify(
            "import os\n"
            "def w(out, rel, text):\n"
            "    root = os.path.realpath(out)\n"
            "    t = os.path.realpath(os.path.join(root, rel))\n"
            "    if not t.startswith(root + os.sep):\n"
            "        raise ValueError('escape')\n"
            "    with open(t, 'w') as fh:\n"
            "        fh.write(text)\n"
        )
        self.assertEqual(guarded_write.status, SELF_SCOPED)

        guarded_delete = classify(
            "import os, shutil\n"
            "def d(out):\n"
            "    root = os.path.realpath(out)\n"
            "    if not root:\n"
            "        raise ValueError('no')\n"
            "    shutil.rmtree(root)\n"
        )
        self.assertEqual(guarded_delete.status, REVIEW_REQUIRED)


class TestHonestyOfAbsentAnswers(unittest.TestCase):
    def test_unparseable_module_is_never_clean(self):
        r = classify("def broken(:\n    pass\n")
        self.assertEqual(r.status, UNPARSEABLE)
        self.assertNotEqual(r.status, CLEAN)
        self.assertFalse(r.parsed)
        self.assertIn("(line", r.parse_error)

    def test_unreadable_file_is_reported_not_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            lane = os.path.join(tmp, "lane_x")
            os.makedirs(lane)
            with open(os.path.join(lane, "bad.py"), "wb") as fh:
                fh.write(b"\xff\xfe\x00 not utf-8 \xff")
            reports = fsaudit.scan_tree(tmp)
            self.assertEqual(len(reports), 1)
            self.assertEqual(reports[0].status, UNPARSEABLE)

    def test_a_delete_in_a_test_module_still_needs_review_if_external(self):
        """Being a test does not excuse removing a path somebody handed in."""
        r = classify(
            "import shutil\ndef helper(p):\n    shutil.rmtree(p)\n",
            module="test_helper.py",
        )
        self.assertEqual(r.findings[0].classification, REVIEW_REQUIRED)

    def test_clean_module_really_is_clean(self):
        r = classify("def add(a, b):\n    return a + b\n")
        self.assertEqual(r.status, CLEAN)
        self.assertEqual(r.findings, [])

    def test_str_replace_is_not_mistaken_for_os_replace(self):
        """`text.replace(...)` is everywhere; flagging it would drown the report."""
        r = classify("def f(s):\n    return s.replace('_', ' ')\n")
        self.assertEqual(r.status, CLEAN)


class TestSummary(unittest.TestCase):
    def test_summary_counts_and_worst_status_per_lane(self):
        reports = fsaudit.scan_tree(FIXTURES)
        s = fsaudit.summarize(reports)
        self.assertEqual(s["modules_scanned"], len(reports))
        self.assertEqual(s["lanes_by_status"]["lane_external"], REVIEW_REQUIRED)
        self.assertEqual(s["lanes_by_status"]["lane_opaque"], UNDETERMINED)
        self.assertGreaterEqual(s["review_required"], 3)

    def test_counts_sum_to_module_total(self):
        reports = fsaudit.scan_tree(FIXTURES)
        s = fsaudit.summarize(reports)
        self.assertEqual(sum(s["modules_by_status"].values()), s["modules_scanned"])


class TestScreenIsItselfNonDestructive(unittest.TestCase):
    """The screen applied to its own source, plus a runtime check."""

    def test_the_screen_passes_its_own_screen(self):
        for name in PRODUCTION_MODULES:
            with open(os.path.join(HERE, name), "r", encoding="utf-8") as fh:
                report = fsaudit.scan_source(fh.read(), "self", name)
            destructive = [f for f in report.findings if f.kind == fsaudit.DESTRUCTIVE]
            self.assertEqual(destructive, [], f"{name} contains a destructive call")
            opaque = [f for f in report.findings if f.kind == fsaudit.OPAQUE]
            self.assertEqual(opaque, [], f"{name} shells out")

    def test_only_the_approved_writer_opens_for_writing(self):
        offenders = []
        for name in PRODUCTION_MODULES:
            with open(os.path.join(HERE, name), "r", encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
            enclosing = {}
            for fn in ast.walk(tree):
                if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for child in ast.walk(fn):
                        enclosing.setdefault(child, fn.name)
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id == "open"):
                    continue
                mode = ""
                if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                    mode = str(node.args[1].value)
                for kw in node.keywords:
                    if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                        mode = str(kw.value.value)
                if set(mode) & fsaudit.WRITE_MODE_CHARS:
                    if enclosing.get(node) != "write_output":
                        offenders.append(f"{name}:{node.lineno}")
        self.assertEqual(offenders, [], f"unapproved write(s): {offenders}")

    def test_scanning_a_tree_leaves_it_byte_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy_root = os.path.join(tmp, "scanned")
            shutil.copytree(FIXTURES, copy_root)
            before = hash_tree(copy_root)
            self.assertGreater(len(before), 0)
            fsaudit.scan_tree(copy_root)
            self.assertEqual(before, hash_tree(copy_root))

    def test_writer_refuses_to_escape_the_output_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "out")
            os.makedirs(out)
            for bad in ("../escaped.md", "a/../../escaped.md", "/tmp/escaped.md"):
                with self.assertRaises(ValueError, msg=f"{bad} must be refused"):
                    fs_safety.write_output(out, bad, "x")
            self.assertFalse(os.path.exists(os.path.join(tmp, "escaped.md")))


class TestCli(unittest.TestCase):
    def test_exit_1_when_something_needs_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc = fs_safety.main(["--root", FIXTURES, "--output-dir", os.path.join(tmp, "o")])
            self.assertEqual(rc, 1)
            self.assertTrue(os.path.isfile(
                os.path.join(tmp, "o", "FILESYSTEM_SAFETY_SCREEN.md")))
            self.assertTrue(os.path.isfile(os.path.join(tmp, "o", "findings.csv")))
            self.assertTrue(os.path.isfile(os.path.join(tmp, "o", "screen.json")))

    def test_exit_0_on_a_tree_with_nothing_to_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            lane = os.path.join(tmp, "src", "lane_ok")
            os.makedirs(lane)
            with open(os.path.join(lane, "m.py"), "w", encoding="utf-8") as fh:
                fh.write("def add(a, b):\n    return a + b\n")
            rc = fs_safety.main(["--root", os.path.join(tmp, "src"),
                                 "--output-dir", os.path.join(tmp, "o")])
            self.assertEqual(rc, 0)

    def test_exit_2_on_a_bad_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc = fs_safety.main(["--root", os.path.join(tmp, "nope"),
                                 "--output-dir", os.path.join(tmp, "o")])
            self.assertEqual(rc, 2)

    def test_report_carries_the_disclaimer(self):
        with tempfile.TemporaryDirectory() as tmp:
            fs_safety.main(["--root", FIXTURES, "--output-dir", tmp])
            with open(os.path.join(tmp, "FILESYSTEM_SAFETY_SCREEN.md"),
                      encoding="utf-8") as fh:
                text = fh.read()
        # The disclaimer must be present...
        self.assertIn("SCREEN, not a proof", text)
        self.assertIn("no lane is marked compliant", text.lower())
        # ...and the report must never actually award a clean bill of health.
        # (The first version of this test asserted the word "compliant" was
        # absent, which the disclaimer itself fails. Assert the real property.)
        # ...and outside that disclaimer the report must never award a clean
        # bill of health. The disclaimer is stripped first because it states
        # these exact phrases in order to deny them -- twice I wrote this
        # assertion against the raw text and twice the denial tripped it.
        body = text.replace(fs_safety.DISCLAIMER, "").upper()
        for verdict in ("CERTIFIED", "COMPLIANT", "SAFETY SCORE", "% SAFE", "GUARANTEE"):
            self.assertNotIn(verdict, body, f"report awards a verdict: {verdict}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
