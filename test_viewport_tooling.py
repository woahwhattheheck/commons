# SPDX-License-Identifier: Apache-2.0
#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
HOST = HERE / "host"
sys.path.insert(0, str(HOST))

import viewport_backfill as backfill
import viewport_inventory as inventory


VIEWPORT = '<meta name="viewport" content="width=device-width, initial-scale=1">'


def html(body: str = "<p>x</p>", *, viewport: bool = False,
         charset: str = '<meta charset="utf-8">', newline: str = "\n") -> str:
    lines = ["<!doctype html>", "<html>", "<head>", f"  {charset}"]
    if viewport:
        lines.append(f"  {VIEWPORT}")
    lines.extend(["  <title>x</title>", "</head>", "<body>", body, "</body>", "</html>"])
    return newline.join(lines) + newline


class Repo:
    def __init__(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.run("init", "-q")
        self.run("config", "user.name", "Viewport Tests")
        self.run("config", "user.email", "viewport@example.invalid")

    def close(self) -> None:
        self.temp.cleanup()

    def run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(["git", "-C", str(self.root), *args],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              check=check)

    def write(self, name: str, data: str | bytes, *, mode: int | None = None) -> Path:
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, str):
            target.write_text(data, encoding="utf-8", newline="")
        else:
            target.write_bytes(data)
        if mode is not None:
            target.chmod(mode)
        return target

    def commit(self, message: str = "fixture") -> str:
        self.run("add", "-A")
        self.run("commit", "-q", "-m", message)
        return self.run("rev-parse", "HEAD").stdout.decode().strip()


class RepoTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Repo()
        self.addCleanup(self.repo.close)


class InventoryTests(RepoTestCase):
    def test_recursive_tracked_search_and_deliberate_receipt_skip(self):
        self.repo.write("index.html", html(viewport=True))
        self.repo.write("nested/deeper/missing.html", html())
        self.repo.write("r/plain.html", "RECEIPT\nnot a document\n")
        self.repo.commit()
        self.repo.write("untracked.html", html())
        result = inventory.census(self.repo.root)
        self.assertEqual(result["counts"]["tracked_html"], 3)
        self.assertEqual(result["counts"]["documents"], 2)
        self.assertEqual(result["counts"]["with_viewport"], 1)
        self.assertEqual(result["counts"]["missing_viewport"], 1)
        self.assertEqual(result["counts"]["skipped_non_document"], 1)
        self.assertTrue(result["complete"])
        self.assertNotIn("untracked.html", json.dumps(result))

    def test_viewport_meta_is_case_and_attribute_order_insensitive(self):
        source = html().replace(
            '<meta charset="utf-8">',
            '<meta charset="utf-8">\n  <META CONTENT="width=device-width" NAME="VIEWPORT">',
        )
        self.repo.write("mixed.html", source)
        self.repo.commit()
        result = inventory.census(self.repo.root)
        self.assertEqual(result["counts"]["with_viewport"], 1)
        self.assertEqual(result["counts"]["missing_viewport"], 0)

    def test_comment_script_and_body_text_do_not_fake_viewport(self):
        body = """<!-- <meta name=\"viewport\"> -->
<script>const x = '<meta name="viewport">';</script>
<meta name="viewport" content="wrong-place">
"""
        self.repo.write("false-positive.html", html(body))
        self.repo.commit()
        result = inventory.census(self.repo.root)
        self.assertEqual(result["counts"]["missing_viewport"], 1)

    def test_meta_before_body_without_explicit_head_is_recognized(self):
        self.repo.write("fragment.html", "<meta name='viewport' content='width=device-width'><body>x</body>")
        self.repo.commit()
        result = inventory.census(self.repo.root)
        self.assertEqual(result["counts"]["with_viewport"], 1)

    def test_invalid_utf8_document_makes_census_incomplete(self):
        self.repo.write("invalid.html", b"<html><head>\xff</head></html>")
        self.repo.commit()
        result = inventory.census(self.repo.root)
        self.assertFalse(result["complete"])
        self.assertEqual(result["counts"]["invalid_utf8"], 1)
        self.assertEqual(result["examples"]["incomplete"][0]["path"], "invalid.html")

    def test_tracked_symlink_is_not_followed(self):
        self.repo.write("target.txt", html(viewport=True))
        os.symlink("target.txt", self.repo.root / "link.html")
        self.repo.commit()
        result = inventory.census(self.repo.root)
        self.assertFalse(result["complete"])
        self.assertEqual(result["counts"]["non_regular"], 1)

    def test_source_ref_mismatch_is_structured_error(self):
        self.repo.write("index.html", html(viewport=True))
        self.repo.commit()
        with self.assertRaises(inventory.InventoryError):
            inventory.census(self.repo.root, source_ref="0" * 40)

    def test_bounded_examples_do_not_hide_total(self):
        for number in range(7):
            self.repo.write(f"p/{number}.html", html())
        self.repo.commit()
        result = inventory.census(self.repo.root, examples=2)
        self.assertEqual(result["counts"]["missing_viewport"], 7)
        self.assertEqual(len(result["examples"]["missing_viewport"]), 2)

    def test_newline_in_tracked_path_is_retained(self):
        name = "nested/line\nbreak.html"
        self.repo.write(name, html())
        self.repo.commit()
        result = inventory.census(self.repo.root, include_records=True)
        self.assertEqual(result["records"][0]["path"], name)

    def test_inventory_digest_changes_with_worktree_bytes(self):
        path = self.repo.write("index.html", html())
        self.repo.commit()
        first = inventory.census(self.repo.root)["inventory_sha256"]
        path.write_text(html(viewport=True), encoding="utf-8")
        second = inventory.census(self.repo.root)["inventory_sha256"]
        self.assertNotEqual(first, second)

    def test_cli_exit_codes(self):
        path = self.repo.write("index.html", html())
        self.repo.commit()
        command = [sys.executable, str(HOST / "viewport_inventory.py"),
                   "--root", str(self.repo.root)]
        missing = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(missing.returncode, 1)
        self.assertEqual(json.loads(missing.stdout)["counts"]["missing_viewport"], 1)
        path.write_text(html(viewport=True), encoding="utf-8")
        clean = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(clean.returncode, 0)

    def test_non_repository_cli_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            run = subprocess.run([sys.executable, str(HOST / "viewport_inventory.py"),
                                  "--root", root], capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertFalse(json.loads(run.stdout)["complete"])


class RepairFunctionTests(unittest.TestCase):
    def test_lf_insertion_is_exact_and_reversible(self):
        source = html().encode()
        fixed, meta = backfill.repair_bytes(source)
        self.assertIsNotNone(fixed)
        insertion = b"\n  " + VIEWPORT.encode()
        self.assertEqual(fixed.replace(insertion, b"", 1), source)
        self.assertEqual(meta["newline"], "LF")

    def test_crlf_insertion_preserves_newline_style(self):
        source = html(newline="\r\n").encode()
        fixed, meta = backfill.repair_bytes(source)
        self.assertIsNotNone(fixed)
        insertion = b"\r\n  " + VIEWPORT.encode()
        self.assertEqual(fixed.replace(insertion, b"", 1), source)
        self.assertEqual(meta["newline"], "CRLF")

    def test_existing_viewport_is_idempotent(self):
        source = html(viewport=True).encode()
        fixed, meta = backfill.repair_bytes(source)
        self.assertIsNone(fixed)
        self.assertEqual(meta["reason"], "already_has_viewport")

    def test_commented_charset_is_not_an_anchor(self):
        source = b"<html><head><!-- <meta charset='utf-8'> --></head><body>x</body></html>"
        fixed, meta = backfill.repair_bytes(source)
        self.assertIsNone(fixed)
        self.assertEqual(meta["reason"], "missing_utf8_charset_meta")

    def test_script_charset_is_not_an_anchor(self):
        source = b"<html><head><script>\"<meta charset='utf-8'>\"</script></head></html>"
        fixed, meta = backfill.repair_bytes(source)
        self.assertIsNone(fixed)
        self.assertEqual(meta["reason"], "missing_utf8_charset_meta")

    def test_multiple_charset_anchors_are_unsafe(self):
        source = html().replace("<title>", '<meta charset="UTF8">\n  <title>').encode()
        fixed, meta = backfill.repair_bytes(source)
        self.assertIsNone(fixed)
        self.assertEqual(meta["reason"], "multiple_utf8_charset_meta")

    def test_non_utf8_declaration_is_unsafe(self):
        source = html(charset='<meta charset="iso-8859-1">').encode()
        fixed, meta = backfill.repair_bytes(source)
        self.assertIsNone(fixed)
        self.assertEqual(meta["reason"], "unsupported_charset")

    def test_plain_receipt_is_not_modified(self):
        fixed, meta = backfill.repair_bytes(b"RECEIPT\n<meta charset='utf-8'>")
        self.assertIsNone(fixed)
        self.assertEqual(meta["reason"], "non_document")


class PlanApplyTests(RepoTestCase):
    def add_pages(self, count: int = 4) -> list[Path]:
        paths = []
        for number in range(count):
            paths.append(self.repo.write(f"p/{number:02d}.html", html()))
        self.repo.write("clean.html", html(viewport=True))
        self.repo.write("r/receipt.html", "RECEIPT\n")
        self.repo.commit()
        return paths

    def save_plan(self, value: dict, name: str = "plan.json") -> Path:
        path = Path(self.repo.temp.name).parent / (Path(self.repo.temp.name).name + "-" + name)
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def test_plan_is_deterministic_dry_run_and_bounded(self):
        pages = self.add_pages(4)
        before = [path.read_bytes() for path in pages]
        one = backfill.make_plan(self.repo.root, limit=2)
        two = backfill.make_plan(self.repo.root, limit=2)
        self.assertEqual(one, two)
        self.assertEqual(one["selected"], 2)
        self.assertEqual([row["path"] for row in one["rows"]], ["p/00.html", "p/01.html"])
        self.assertEqual(one["next_cursor"], "p/01.html")
        self.assertFalse(one["complete_for_repairable_pages"])
        self.assertEqual([path.read_bytes() for path in pages], before)

    def test_cursor_resumes_without_overlap(self):
        self.add_pages(5)
        first = backfill.make_plan(self.repo.root, limit=2)
        second = backfill.make_plan(self.repo.root, limit=2, cursor=first["next_cursor"])
        third = backfill.make_plan(self.repo.root, limit=2, cursor=second["next_cursor"])
        paths = [[row["path"] for row in plan["rows"]] for plan in (first, second, third)]
        self.assertEqual(paths, [["p/00.html", "p/01.html"],
                                 ["p/02.html", "p/03.html"], ["p/04.html"]])
        self.assertIsNone(third["next_cursor"])
        self.assertTrue(third["complete_for_repairable_pages"])

    def test_untracked_html_is_not_planned(self):
        self.add_pages(1)
        self.repo.write("p/untracked.html", html())
        plan = backfill.make_plan(self.repo.root, limit=10)
        self.assertEqual([row["path"] for row in plan["rows"]], ["p/00.html"])

    def test_unsafe_pages_are_reported_not_modified(self):
        self.repo.write("missing-anchor.html", "<html><head><title>x</title></head></html>")
        self.repo.write("duplicate.html", html().replace("<title>",
            '<meta charset="utf-8">\n<title>'))
        self.repo.commit()
        plan = backfill.make_plan(self.repo.root, limit=10, examples=10)
        self.assertEqual(plan["selected"], 0)
        self.assertEqual(plan["unsafe_after_cursor"], 2)
        self.assertEqual({row["reason"] for row in plan["unsafe_examples"]},
                         {"missing_utf8_charset_meta", "multiple_utf8_charset_meta"})

    def test_apply_changes_only_planned_pages_and_preserves_mode(self):
        pages = self.add_pages(3)
        pages[0].chmod(0o640)
        plan = backfill.make_plan(self.repo.root, limit=2)
        plan_path = self.save_plan(plan)
        untouched = pages[2].read_bytes()
        receipt = backfill.apply_plan(self.repo.root, plan_path)
        self.assertEqual(receipt["status"], "applied")
        self.assertEqual(receipt["applied"], 2)
        self.assertIn(VIEWPORT, pages[0].read_text())
        self.assertIn(VIEWPORT, pages[1].read_text())
        self.assertEqual(pages[2].read_bytes(), untouched)
        self.assertEqual(stat.S_IMODE(pages[0].stat().st_mode), 0o640)

    def test_apply_is_idempotent_for_exact_postimage(self):
        self.add_pages(1)
        plan = backfill.make_plan(self.repo.root, limit=1)
        plan_path = self.save_plan(plan)
        first = backfill.apply_plan(self.repo.root, plan_path)
        content = (self.repo.root / "p/00.html").read_bytes()
        second = backfill.apply_plan(self.repo.root, plan_path)
        self.assertEqual(first["status"], "applied")
        self.assertEqual(second["status"], "already_applied")
        self.assertEqual((self.repo.root / "p/00.html").read_bytes(), content)

    def test_selected_preimage_mismatch_aborts_before_tool_mutation(self):
        pages = self.add_pages(2)
        plan = backfill.make_plan(self.repo.root, limit=2)
        plan_path = self.save_plan(plan)
        pages[1].write_text(html("<p>changed by peer</p>"), encoding="utf-8")
        snapshot = [path.read_bytes() for path in pages]
        with self.assertRaises(backfill.BackfillError):
            backfill.apply_plan(self.repo.root, plan_path)
        self.assertEqual([path.read_bytes() for path in pages], snapshot)

    def test_unselected_inventory_movement_aborts_batch(self):
        pages = self.add_pages(3)
        plan = backfill.make_plan(self.repo.root, limit=1)
        plan_path = self.save_plan(plan)
        pages[2].write_text(html("<p>concurrent</p>"), encoding="utf-8")
        selected_before = pages[0].read_bytes()
        with self.assertRaises(backfill.BackfillError):
            backfill.apply_plan(self.repo.root, plan_path)
        self.assertEqual(pages[0].read_bytes(), selected_before)

    def test_head_movement_aborts_even_when_html_is_unchanged(self):
        pages = self.add_pages(1)
        plan = backfill.make_plan(self.repo.root, limit=1)
        plan_path = self.save_plan(plan)
        self.repo.write("note.txt", "new commit\n")
        self.repo.commit("move head")
        before = pages[0].read_bytes()
        with self.assertRaises(backfill.BackfillError):
            backfill.apply_plan(self.repo.root, plan_path)
        self.assertEqual(pages[0].read_bytes(), before)

    def test_tampered_plan_is_rejected(self):
        self.add_pages(1)
        plan = backfill.make_plan(self.repo.root, limit=1)
        plan["rows"][0]["after_sha256"] = "0" * 64
        plan_path = self.save_plan(plan)
        with self.assertRaisesRegex(backfill.BackfillError, "plan_sha256"):
            backfill.apply_plan(self.repo.root, plan_path)

    def test_path_traversal_is_rejected_even_with_recomputed_plan_digest(self):
        self.add_pages(1)
        plan = backfill.make_plan(self.repo.root, limit=1)
        plan["rows"][0]["path"] = "../escape.html"
        plan.pop("plan_sha256")
        plan["plan_sha256"] = backfill._plan_digest(plan)
        plan_path = self.save_plan(plan)
        with self.assertRaisesRegex(backfill.BackfillError, "unsafe plan path"):
            backfill.apply_plan(self.repo.root, plan_path)

    def test_stage_failure_before_replace_leaves_all_files_unchanged(self):
        pages = self.add_pages(2)
        plan = backfill.make_plan(self.repo.root, limit=2)
        plan_path = self.save_plan(plan)
        before = [path.read_bytes() for path in pages]
        original = backfill._stage_file
        calls = 0

        def fail_second(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("stage failed")
            return original(*args, **kwargs)

        with mock.patch.object(backfill, "_stage_file", side_effect=fail_second):
            with self.assertRaises(OSError):
                backfill.apply_plan(self.repo.root, plan_path)
        self.assertEqual([path.read_bytes() for path in pages], before)

    def test_first_replace_failure_leaves_all_files_unchanged(self):
        pages = self.add_pages(2)
        plan = backfill.make_plan(self.repo.root, limit=2)
        plan_path = self.save_plan(plan)
        before = [path.read_bytes() for path in pages]
        with mock.patch.object(backfill.os, "replace", side_effect=OSError("replace failed")):
            with self.assertRaises(OSError):
                backfill.apply_plan(self.repo.root, plan_path)
        self.assertEqual([path.read_bytes() for path in pages], before)

    def test_newline_path_can_be_planned_and_applied(self):
        name = "p/a\nb.html"
        target = self.repo.write(name, html())
        self.repo.commit()
        plan = backfill.make_plan(self.repo.root, limit=1)
        self.assertEqual(plan["rows"][0]["path"], name)
        backfill.apply_plan(self.repo.root, self.save_plan(plan))
        self.assertIn(VIEWPORT, target.read_text())

    def test_source_ref_must_match_exact_head(self):
        self.add_pages(1)
        with self.assertRaises(inventory.InventoryError):
            backfill.make_plan(self.repo.root, limit=1, source_ref="f" * 40)

    def test_cli_defaults_to_dry_run_and_requires_explicit_limit(self):
        target = self.repo.write("index.html", html())
        self.repo.commit()
        command = [sys.executable, str(HOST / "viewport_backfill.py"),
                   "--root", str(self.repo.root)]
        missing_limit = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(missing_limit.returncode, 2)
        self.assertNotIn(VIEWPORT, target.read_text())
        planned = subprocess.run(command + ["--limit", "1"], capture_output=True, text=True)
        self.assertEqual(planned.returncode, 0, planned.stderr)
        self.assertEqual(json.loads(planned.stdout)["selected"], 1)
        self.assertNotIn(VIEWPORT, target.read_text())

    def test_cli_write_requires_saved_plan(self):
        self.add_pages(1)
        command = [sys.executable, str(HOST / "viewport_backfill.py"),
                   "--root", str(self.repo.root), "--write"]
        run = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertIn("--write requires --plan", run.stdout)

    def test_plan_output_and_apply_receipt_are_atomic_json_files(self):
        target = self.repo.write("index.html", html())
        head = self.repo.commit()
        plan_file = Path(self.repo.temp.name).parent / (Path(self.repo.temp.name).name + "-cli-plan.json")
        receipt_file = Path(self.repo.temp.name).parent / (Path(self.repo.temp.name).name + "-cli-receipt.json")
        self.addCleanup(lambda: plan_file.unlink(missing_ok=True))
        self.addCleanup(lambda: receipt_file.unlink(missing_ok=True))
        create = subprocess.run([
            sys.executable, str(HOST / "viewport_backfill.py"), "--root", str(self.repo.root),
            "--source-ref", head, "--limit", "1", "--output", str(plan_file),
        ], capture_output=True, text=True)
        self.assertEqual(create.returncode, 0, create.stderr)
        apply = subprocess.run([
            sys.executable, str(HOST / "viewport_backfill.py"), "--root", str(self.repo.root),
            "--plan", str(plan_file), "--write", "--output", str(receipt_file),
        ], capture_output=True, text=True)
        self.assertEqual(apply.returncode, 0, apply.stderr)
        self.assertEqual(json.loads(receipt_file.read_text())["status"], "applied")
        self.assertIn(VIEWPORT, target.read_text())

    def test_apply_receipt_cannot_overwrite_its_plan(self):
        target = self.repo.write("index.html", html())
        self.repo.commit()
        plan = backfill.make_plan(self.repo.root, limit=1)
        plan_file = self.save_plan(plan)
        before = plan_file.read_bytes()
        run = subprocess.run([
            sys.executable, str(HOST / "viewport_backfill.py"),
            "--root", str(self.repo.root), "--plan", str(plan_file),
            "--write", "--output", str(plan_file),
        ], capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertEqual(run.stdout, "")
        self.assertIn("--output must differ from --plan", run.stderr)
        self.assertEqual(plan_file.read_bytes(), before)
        self.assertNotIn(VIEWPORT, target.read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
