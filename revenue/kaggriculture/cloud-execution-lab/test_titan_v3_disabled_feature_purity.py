from __future__ import annotations

import contextlib
import io
import json
import pathlib
import tarfile
import tempfile
import textwrap
import unittest
import zipfile

import titan_v3_disabled_feature_purity as purity


BAD_SPATIAL = """
class SpatialTempo:
    def do_convert(self, state):
        self._continue_weed()
        self._continue_fert()
        if not self.enable:
            return
        self._active_convert(state)
"""

GOOD_SPATIAL = """
class SpatialTempo:
    def do_convert(self, state):
        if not self.enable:
            return
        self._continue_weed()
        self._continue_fert()
        self._active_convert(state)
"""


class PurityUnitTests(unittest.TestCase):
    def scan(self, text: str, *, flags=("enable", "enabled")) -> purity.ScanResult:
        return purity.scan_units(
            [purity.SourceUnit("fixture.py", textwrap.dedent(text))],
            flag_names=flags,
        )

    def test_known_spatial_ordering_bug_has_two_findings(self) -> None:
        result = self.scan(BAD_SPATIAL)
        self.assertEqual(2, len(result.findings))
        self.assertEqual(
            ["pre_guard_call", "pre_guard_call"],
            [item.rule for item in result.findings],
        )
        self.assertEqual([4, 5], [item.line for item in result.findings])
        self.assertEqual([6, 6], [item.guard_line for item in result.findings])
        self.assertEqual("SpatialTempo.do_convert", result.findings[0].function)
        self.assertEqual("self.enable", result.findings[0].feature)

    def test_guard_first_is_clean(self) -> None:
        result = self.scan(GOOD_SPATIAL)
        self.assertEqual((), result.findings)
        self.assertEqual(1, result.guarded_functions)

    def test_side_effect_free_local_work_is_allowed(self) -> None:
        result = self.scan(
            """
            def f(self, count):
                doubled = count * 2
                left, right = doubled, count
                if self.enabled is False:
                    return
                self.commit(left + right)
            """
        )
        self.assertEqual((), result.findings)

    def test_effectful_assignment_is_rejected(self) -> None:
        result = self.scan(
            """
            def f(self):
                route = self.build_route()
                if not self.enable:
                    return
            """
        )
        self.assertEqual(1, len(result.findings))
        self.assertEqual("pre_guard_effectful_assignment", result.findings[0].rule)

    def test_attribute_and_subscript_writes_are_rejected(self) -> None:
        result = self.scan(
            """
            def f(self, cache):
                self.route = []
                cache["route"] = []
                if False == self.enabled:
                    return
            """
        )
        self.assertEqual(
            ["pre_guard_mutation", "pre_guard_mutation"],
            [item.rule for item in result.findings],
        )

    def test_custom_flag_name(self) -> None:
        result = self.scan(
            """
            def f(self):
                self.mutate()
                if not self.active:
                    return
            """,
            flags=("active",),
        )
        self.assertEqual(1, len(result.findings))
        self.assertEqual("self.active", result.findings[0].feature)

    def test_same_statement_suppression_marker(self) -> None:
        result = self.scan(
            """
            def f(self):
                self.required_probe()  # titan-purity: allow -- deterministic telemetry
                if not self.enable:
                    return
            """
        )
        self.assertEqual((), result.findings)

    def test_multiline_suppression_marker(self) -> None:
        result = self.scan(
            """
            def f(self):
                self.required_probe(
                    1,  # titan-purity: allow -- measured and approved
                )
                if not self.enable:
                    return
            """
        )
        self.assertEqual((), result.findings)

    def test_syntax_error_is_fail_closed(self) -> None:
        result = self.scan("def broken(:\n    pass\n")
        self.assertEqual(1, len(result.errors))
        self.assertEqual((), result.findings)

    def test_nested_function_uses_qualified_scope(self) -> None:
        result = self.scan(
            """
            def outer():
                def inner(self):
                    self.mutate()
                    if not self.enable:
                        return
                return inner
            """
        )
        self.assertEqual("outer.inner", result.findings[0].function)


class InputAndCliTests(unittest.TestCase):
    def test_directory_order_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "b.py").write_text(BAD_SPATIAL, encoding="utf-8")
            (root / "a.py").write_text(GOOD_SPATIAL, encoding="utf-8")
            labels = [unit.label for unit in purity.iter_source_units([root])]
            self.assertEqual(sorted(labels), labels)

    def test_zip_is_scanned_without_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = pathlib.Path(tmp) / "bundle.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("pkg/good.py", GOOD_SPATIAL)
                archive.writestr("pkg/bad.py", BAD_SPATIAL)
                archive.writestr("README.txt", "ignored")
            units = tuple(purity.iter_source_units([archive_path]))
            result = purity.scan_units(units)
            self.assertEqual(2, result.scanned_sources)
            self.assertEqual(2, len(result.findings))
            self.assertTrue(result.findings[0].source.endswith("!pkg/bad.py"))

    def test_tar_is_scanned_without_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = pathlib.Path(tmp) / "bundle.tar.gz"
            data = GOOD_SPATIAL.encode("utf-8")
            with tarfile.open(archive_path, "w:gz") as archive:
                info = tarfile.TarInfo("pkg/good.py")
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
            units = tuple(purity.iter_source_units([archive_path]))
            result = purity.scan_units(units)
            self.assertEqual(1, result.scanned_sources)
            self.assertEqual((), result.findings)

    def test_archive_member_limit_is_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = pathlib.Path(tmp) / "bundle.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("large.py", "x" * 100)
            with self.assertRaises(purity.AuditInputError):
                tuple(purity.iter_source_units([archive_path], max_member_bytes=10))

    def run_cli(self, *argv: str) -> tuple[int, dict[str, object]]:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = purity.main(list(argv))
        return code, json.loads(output.getvalue())

    def test_json_cli_violation_exit_code_and_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "bad.py"
            path.write_text(BAD_SPATIAL, encoding="utf-8")
            code, payload = self.run_cli(str(path), "--format", "json")
        self.assertEqual(1, code)
        self.assertEqual(2, payload["summary"]["violations"])
        self.assertEqual("titan-disabled-feature-purity", payload["tool"])
        self.assertEqual(purity.TOOL_VERSION, payload["version"])

    def test_json_cli_clean_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "good.py"
            path.write_text(GOOD_SPATIAL, encoding="utf-8")
            code, payload = self.run_cli(str(path), "--format", "json")
        self.assertEqual(0, code)
        self.assertEqual(0, payload["summary"]["violations"])

    def test_json_cli_input_error_exit_code(self) -> None:
        code, payload = self.run_cli("/definitely/missing.py", "--format", "json")
        self.assertEqual(2, code)
        self.assertEqual(1, payload["summary"]["errors"])

    def test_archive_without_python_is_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = pathlib.Path(tmp) / "empty.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("README.txt", "no executable source")
            code, payload = self.run_cli(str(archive_path), "--format", "json")
        self.assertEqual(2, code)
        self.assertEqual(1, payload["summary"]["errors"])
        self.assertIn("no Python sources", payload["errors"][0]["message"])

    def test_json_is_byte_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "bad.py"
            path.write_text(BAD_SPATIAL, encoding="utf-8")
            first = io.StringIO()
            second = io.StringIO()
            with contextlib.redirect_stdout(first):
                purity.main([str(path), "--format", "json"])
            with contextlib.redirect_stdout(second):
                purity.main([str(path), "--format", "json"])
        self.assertEqual(first.getvalue(), second.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
