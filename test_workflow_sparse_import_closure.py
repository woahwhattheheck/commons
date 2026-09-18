#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "workflow_sparse_import_closure",
    ROOT / "tools" / "workflow_sparse_import_closure.py",
)
assert SPEC and SPEC.loader
wic = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = wic
SPEC.loader.exec_module(wic)


def workflow(patterns: list[str] | None, run: str, *, crlf: bool = False) -> str:
    checkout = "      - uses: actions/checkout@v4\n"
    if patterns is not None:
        checkout += (
            "        with:\n"
            "          sparse-checkout-cone-mode: false\n"
            "          sparse-checkout: |\n"
            + "".join(f"            /{item}\n" for item in patterns)
        )
    text = (
        "name: hostile\n"
        "on: [pull_request]\n"
        "jobs:\n"
        "  audit:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        + checkout
        + "      - name: Execute\n"
        + "        run: |\n"
        + "".join(f"          {line}\n" for line in run.splitlines())
    )
    return text.replace("\n", "\r\n") if crlf else text


class SparseImportClosureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".github" / "workflows").mkdir(parents=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write(self, path: str, text: str) -> Path:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def audit(self, patterns: list[str] | None, run: str, *, crlf: bool = False):
        path = self.write(".github/workflows/a.yml", workflow(patterns, run, crlf=crlf))
        return wic.audit_workflow(self.root, path)

    def only_step(self, report):
        return report["jobs"][0]["steps"][0]

    def test_direct_missing_import_fails_with_chain(self):
        self.write("app.py", "import helper\n")
        self.write("helper.py", "VALUE = 1\n")
        report = self.audit(["app.py"], "python app.py")
        self.assertEqual("FAIL", report["status"])
        missing = [f for f in self.only_step(report)["findings"]
                   if f["code"] == "MISSING_FROM_SPARSE_CHECKOUT"]
        self.assertEqual(["app.py", "helper.py"], missing[0]["chain"])

    def test_selected_direct_import_passes(self):
        self.write("app.py", "import helper\n")
        self.write("helper.py", "VALUE = 1\n")
        report = self.audit(["app.py", "helper.py"], "python3 app.py")
        self.assertEqual("PASS", report["status"])

    def test_directory_selection_is_recursive(self):
        self.write("app/main.py", "from app import helper\n")
        self.write("app/helper.py", "VALUE = 1\n")
        self.write("app/__init__.py", "")
        report = self.audit(["app"], "python app/main.py")
        self.assertEqual("PASS", report["status"])

    def test_transitive_import_chain_is_reported(self):
        self.write("app.py", "import one\n")
        self.write("one.py", "import two\n")
        self.write("two.py", "VALUE = 2\n")
        report = self.audit(["app.py", "one.py"], "python app.py")
        missing = [f for f in self.only_step(report)["findings"]
                   if f["code"] == "MISSING_FROM_SPARSE_CHECKOUT"]
        self.assertEqual(["app.py", "one.py", "two.py"], missing[0]["chain"])

    def test_relative_import_and_package_initializers(self):
        self.write("pkg/__init__.py", "from . import helper\n")
        self.write("pkg/main.py", "from . import helper\n")
        self.write("pkg/helper.py", "VALUE = 1\n")
        report = self.audit(
            ["pkg/__init__.py", "pkg/main.py", "pkg/helper.py"],
            "python -m pkg.main",
        )
        self.assertEqual("PASS", report["status"])

    def test_absolute_sibling_fallback_resolves_from_current_parent(self):
        self.write("host/main.py", "import sibling\n")
        self.write("host/sibling.py", "VALUE = 1\n")
        report = self.audit(["host/main.py"], "python host/main.py")
        missing = [f for f in self.only_step(report)["findings"]
                   if f["code"] == "MISSING_FROM_SPARSE_CHECKOUT"]
        self.assertEqual("host/sibling.py", missing[0]["source"])

    def test_from_package_import_submodule_is_in_closure(self):
        self.write("pkg/__init__.py", "")
        self.write("pkg/main.py", "from pkg import child\n")
        self.write("pkg/child.py", "")
        report = self.audit(["pkg/__init__.py", "pkg/main.py"], "python -m pkg.main")
        sources = {f["source"] for f in self.only_step(report)["findings"]
                   if f["code"] == "MISSING_FROM_SPARSE_CHECKOUT"}
        self.assertEqual({"pkg/child.py"}, sources)

    def test_try_except_importerror_keeps_both_local_roads(self):
        self.write(
            "wrapper.py",
            "try:\n    import primary\nexcept ImportError:\n    import fallback\n",
        )
        self.write("primary.py", "")
        self.write("fallback.py", "")
        report = self.audit(["wrapper.py", "primary.py"], "python wrapper.py")
        sources = {f["source"] for f in self.only_step(report)["findings"]
                   if f["code"] == "MISSING_FROM_SPARSE_CHECKOUT"}
        self.assertEqual({"fallback.py"}, sources)

    def test_module_unittest_pytest_and_pycompile_entrypoints(self):
        self.write("pkg/__init__.py", "")
        self.write("pkg/run.py", "")
        self.write("test_a.py", "")
        self.write("test_b.py", "")
        report = self.audit(
            ["pkg", "test_a.py", "test_b.py"],
            "\n".join([
                "python -m pkg.run",
                "python -O -m unittest -v test_a.py",
                "pytest -q test_b.py::Case::test_x",
                "python3 -m py_compile pkg/run.py test_a.py",
            ]),
        )
        step = self.only_step(report)
        self.assertEqual("PASS", report["status"])
        self.assertEqual(
            {"pkg.run", "test_a.py", "test_b.py", "pkg/run.py"},
            {entry["target"] for entry in step["entries"]},
        )

    def test_unittest_dotted_selector_uses_longest_local_prefix(self):
        self.write("tests/__init__.py", "")
        self.write("tests/test_x.py", "")
        report = self.audit(["tests"], "python -m unittest tests.test_x.Case.test_method")
        self.assertEqual("PASS", report["status"])

    def test_crlf_pattern_and_config_order_are_canonical(self):
        self.write("app.py", "")
        self.write(".github/workflows/a.yml", workflow(["app.py"], "python app.py", crlf=True))
        self.write(".github/workflows/b.yml", workflow(["app.py"], "python app.py"))
        first = self.write(
            "first.json",
            json.dumps({"schema": wic.CONFIG_SCHEMA,
                        "workflows": [".github/workflows/b.yml", ".github/workflows/a.yml"]}),
        )
        second = self.write(
            "second.json",
            json.dumps({"workflows": [".github/workflows/a.yml", ".github/workflows/b.yml"],
                        "schema": wic.CONFIG_SCHEMA}),
        )
        one = wic.audit_repository(self.root, first)
        two = wic.audit_repository(self.root, second)
        self.assertEqual(one, two)

    def test_python_syntax_error_fails(self):
        self.write("broken.py", "def nope(:\n")
        report = self.audit(["broken.py"], "python broken.py")
        codes = {f["code"] for e in self.only_step(report)["entries"] for f in e["findings"]}
        self.assertEqual("FAIL", report["status"])
        self.assertIn("PYTHON_SYNTAX_ERROR", codes)

    def test_dynamic_import_is_unknown_but_not_failure(self):
        self.write("app.py", "import importlib\nname = 'x'\nimportlib.import_module(name)\n")
        report = self.audit(["app.py"], "python app.py")
        self.assertEqual("UNKNOWN", report["status"])
        codes = {f["code"] for e in self.only_step(report)["entries"] for f in e["findings"]}
        self.assertIn("DYNAMIC_IMPORT", codes)

    def test_negative_sparse_pattern_is_unknown(self):
        self.write("app.py", "")
        report = self.audit(["app.py", "!secret.py"], "python app.py")
        self.assertEqual("UNKNOWN", report["status"])
        self.assertIn(
            "UNSUPPORTED_SPARSE_PATTERN",
            {f["code"] for f in self.only_step(report)["findings"]},
        )

    def test_inline_sparse_expression_is_unknown(self):
        self.write("app.py", "")
        text = (
            "jobs:\n  x:\n    steps:\n"
            "      - uses: actions/checkout@v4\n"
            "        with:\n"
            "          sparse-checkout: ${{ matrix.path }}\n"
            "      - run: python app.py\n"
        )
        path = self.write(".github/workflows/a.yml", text)
        report = wic.audit_workflow(self.root, path)
        self.assertEqual("UNKNOWN", report["status"])

    def test_implicit_test_discovery_is_unknown(self):
        self.write("test_a.py", "")
        report = self.audit(["test_a.py"], "python -m unittest discover")
        self.assertEqual("UNKNOWN", report["status"])
        self.assertIn(
            "IMPLICIT_TEST_DISCOVERY",
            {f["code"] for f in self.only_step(report)["findings"]},
        )

    def test_no_python_entrypoint_is_skip(self):
        report = self.audit(["README.md"], "echo hello")
        self.assertEqual("SKIP", report["status"])

    def test_full_checkout_is_skip_not_false_green(self):
        self.write("app.py", "import missing_external_or_local\n")
        report = self.audit(None, "python app.py")
        self.assertEqual("SKIP", report["status"])
        self.assertEqual("FULL_OR_EXTERNAL", self.only_step(report)["coverage"])

    def test_wrapper_core_extraction_regression(self):
        self.write("host/wrapper.py", "from . import core\n")
        self.write("host/core.py", "")
        self.write("host/__init__.py", "")
        self.write("test_wrapper.py", "from host import wrapper\n")
        report = self.audit(
            ["host/wrapper.py", "host/__init__.py", "test_wrapper.py"],
            "python -m unittest -v test_wrapper.py",
        )
        sources = {f["source"] for f in self.only_step(report)["findings"]
                   if f["code"] == "MISSING_FROM_SPARSE_CHECKOUT"}
        self.assertEqual({"host/core.py"}, sources)

    def test_shell_continuation_and_multiple_lines(self):
        self.write("a.py", "")
        self.write("b.py", "")
        report = self.audit(
            ["a.py", "b.py"],
            "python -m py_compile a.py \\\n  b.py\npython a.py",
        )
        self.assertEqual("PASS", report["status"])
        self.assertEqual({"a.py", "b.py"}, {e["target"] for e in self.only_step(report)["entries"]})

    def test_literal_dynamic_import_is_resolved(self):
        self.write("app.py", "import importlib\nimportlib.import_module('helper')\n")
        self.write("helper.py", "")
        report = self.audit(["app.py"], "python app.py")
        sources = {f["source"] for f in self.only_step(report)["findings"]
                   if f["code"] == "MISSING_FROM_SPARSE_CHECKOUT"}
        self.assertEqual({"helper.py"}, sources)

    def test_malformed_config_is_contract_error(self):
        config = self.write("bad.json", '{"schema":"wrong","workflows":[]}')
        with self.assertRaises(wic.ContractError):
            wic.audit_repository(self.root, config)


    def test_checked_current_repository_contract_when_present(self):
        config = ROOT / "ci" / "workflow-sparse-import-closure.json"
        if (not config.is_file()
                or not (ROOT / ".github" / "workflows" / "coordination-state.yml").is_file()):
            self.skipTest("complete repository contract is not present in isolated hostile fixture")
        report = wic.audit_repository(ROOT, config)
        self.assertNotEqual(
            "FAIL",
            report["status"],
            json.dumps(report, sort_keys=True, indent=2),
        )

    def test_receipt_binds_canonical_report(self):
        self.write("app.py", "")
        self.write(".github/workflows/a.yml", workflow(["app.py"], "python app.py"))
        report = wic.audit_repository(self.root)
        receipt = report.pop("receipt_sha256")
        self.assertEqual(
            receipt,
            __import__("hashlib").sha256(wic.canonical_bytes(report)).hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()
