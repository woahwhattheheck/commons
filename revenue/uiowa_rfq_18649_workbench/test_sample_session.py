#!/usr/bin/env python3
"""Real Chromium tests of checked-in UI bytes; transport fixtures are synthetic.

No University data or compiler execution is implied. Existing server tests own the
HTTP/compiler integration. Assertions remain active under python -O.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from playwright.sync_api import sync_playwright

ROOT = Path(os.environ.get("UIOWA_UI_ROOT", Path(__file__).resolve().parent))


class SampleSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        chromium = os.environ.get("CHROMIUM_BIN") or shutil.which("chromium")
        options = {"headless": True, "args": ["--no-sandbox"]}
        if chromium:
            options["executable_path"] = chromium
        cls.browser = cls.playwright.chromium.launch(**options)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.context = self.browser.new_context(accept_downloads=True)
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()
        self.page.set_default_timeout(3000)
        self.errors = []
        self.page.on("pageerror", lambda err: self.errors.append(str(err)))
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        html = html.replace('<link rel="stylesheet" href="/style.css">', '')
        for asset in ("handoff.js", "handoff_import.js", "app.js"):
            html = html.replace(f'<script src="/{asset}" defer></script>', '')
        self.page.set_content(html)
        self.page.add_style_tag(content=(ROOT / "style.css").read_text(encoding="utf-8"))
        for asset in ("handoff.js", "handoff_import.js", "app.js"):
            self.page.add_script_tag(content=(ROOT / asset).read_text(encoding="utf-8"))

    def tearDown(self):
        self.assertEqual(self.errors, [])

    def load(self):
        self.page.locator("#demoBtn").click()

    def snapshot(self):
        return self.page.evaluate("""() => ({
            report: state.report, notes: [...state.notes], dispositions: [...state.dispositions],
            selected: state.selectedKey, search: el.search.value, status: el.statusFilter.value,
            count: el.matrix.dataset.renderedCells, detail: el.detail.textContent,
            note: el.note.value, disposition: el.disposition.value,
            exported: el.exportStatus.textContent, error: el.error.textContent
        })""")

    def edit(self, note="Fictional reviewer note — retain exactly"):
        self.page.locator('.cell[data-key="ESS|security"]').click()
        self.page.locator("#note").fill(note)
        self.page.locator("#disposition").select_option("NEEDS_EVIDENCE")
        self.page.locator("#search").fill("ESS")
        self.page.locator("#statusFilter").select_option("HOLD_MISSING_EVIDENCE")

    def choose_inputs(self):
        for field, name in (("candidateFile", "candidate"), ("authorityFile", "authority")):
            self.page.locator(f"#{field}").set_input_files({
                "name": f"synthetic-{name}.json", "mimeType": "application/json",
                "buffer": b'{"synthetic_test_fixture":true}'})

    def import_fixture(self):
        self.choose_inputs()
        self.page.evaluate("""() => {
            const report = syntheticReport();
            report.receipt_sha256 = 'a'.repeat(64);
            report.synthetic_demo = false; // Test import mode, not a University report.
            report.assessment_matrix.forEach(cell => {
                if (cell.dimension === 'software_development') cell.dimension = 'software';
            });
            report.test_fixture = 'SYNTHETIC_TRANSPORT_NOT_COMPILER_OUTPUT';
            window.fetch = async () => ({ok: true, json: async () => ({report})});
        }""")
        self.page.locator("#inspectBtn").click()
        self.page.wait_for_function("state.report?.receipt_sha256 === 'a'.repeat(64)")

    def pending_inspection(self):
        self.choose_inputs()
        self.page.evaluate("""() => {
            window.pending = [];
            window.fetch = () => new Promise((resolve, reject) => pending.push({resolve, reject}));
        }""")
        self.page.locator("#inspectBtn").click()
        self.page.wait_for_function("pending.length === 1")

    def resolve_pending(self, index=0, error=False):
        self.page.evaluate("""({index, error}) => {
            if (error) pending[index].reject(new Error('obsolete transport error'));
            else {
                const report = syntheticReport(); report.receipt_sha256 = 'b'.repeat(64);
                pending[index].resolve({ok: true, json: async () => ({report})});
            }
        }""", {"index": index, "error": error})
        self.page.evaluate("async () => { await new Promise(resolve => setTimeout(resolve, 0)); }")

    def export(self, name):
        with self.page.expect_download() as info:
            self.page.locator("#exportBtn").click()
        destination = Path(self.temp.name) / name
        info.value.save_as(destination)
        return destination

    def test_repeat_load_resets_status_filter(self):
        self.load()
        self.page.locator("#statusFilter").select_option("HOLD_MISSING_EVIDENCE")
        self.assertEqual(self.page.locator(".cell").count(), 3)
        self.load()
        self.assertEqual(self.page.locator(".cell").count(), 12)
        self.assertEqual(self.page.locator("#statusFilter").input_value(), "")

    def test_initial_controls_are_explicit_and_disabled(self):
        self.assertEqual(self.page.locator("#demoResetBtn").count(), 1)
        self.assertTrue(self.page.locator("#demoResetBtn").is_disabled())
        self.assertTrue(self.page.locator("#demoExitBtn").is_disabled())
        self.assertIn("Synthetic", self.page.locator("#demoStatus").inner_text())

    def test_two_consecutive_edit_reset_runs_are_identical(self):
        self.load()
        before = self.snapshot()
        for cycle in range(2):
            self.edit(f"Synthetic edit {cycle}")
            self.page.locator("#demoResetBtn").click()
            self.assertEqual(self.snapshot(), before)
            self.assertTrue(self.page.locator("#note").is_disabled())
            self.assertTrue(self.page.locator("#disposition").is_disabled())

    def test_imported_work_restored_exactly_after_repeated_sample_runs(self):
        self.import_fixture()
        self.edit()
        self.export("before.json")
        before = self.snapshot()
        self.load()
        for _ in range(2):
            self.edit("SAMPLE ONLY — do not copy to the parked import")
            self.page.locator("#demoResetBtn").click()
        self.page.locator("#demoExitBtn").click()
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.page.locator("#resetBtn").is_disabled())

    def test_clear_and_import_cannot_discard_parked_work(self):
        self.import_fixture()
        self.edit()
        before = self.snapshot()
        self.load()
        self.assertTrue(self.page.locator("#resetBtn").is_disabled())
        self.assertTrue(self.page.locator("#inspectBtn").is_disabled())
        self.assertIn("restore", self.page.locator("#demoStatus").inner_text().lower())
        self.page.evaluate("inspectFiles()")  # Public function also respects the boundary.
        self.assertTrue(self.page.evaluate("state.report.synthetic_demo"))
        self.page.locator("#demoExitBtn").click()
        self.assertEqual(self.snapshot(), before)

    def test_leave_sample_returns_to_empty_when_no_prior_report(self):
        self.load()
        self.edit()
        self.page.locator("#demoExitBtn").click()
        self.assertEqual(self.page.locator(".cell").count(), 0)
        self.assertTrue(self.page.locator("#exportBtn").is_disabled())
        self.assertTrue(self.page.locator("#demoResetBtn").is_disabled())

    def test_downloaded_exports_and_unrelated_file_survive_reset(self):
        unrelated = Path(self.temp.name) / "unrelated.txt"
        unrelated.write_text("not part of the synthetic session", encoding="utf-8")
        self.load()
        self.edit()
        export = self.export("edited.json")
        digest = hashlib.sha256(export.read_bytes()).hexdigest()
        for _ in range(2):
            self.page.locator("#demoResetBtn").click()
        self.page.locator("#demoExitBtn").click()
        self.assertEqual(hashlib.sha256(export.read_bytes()).hexdigest(), digest)
        self.assertEqual(unrelated.read_text(), "not part of the synthetic session")
        self.assertIn("Fictional", json.loads(export.read_text())["cell_notes"][1]["analyst_note"])

    def test_clean_exports_byte_identical_and_non_authoritative(self):
        self.load()
        first = self.export("first.json").read_bytes()
        self.edit()
        self.page.locator("#demoResetBtn").click()
        second = self.export("second.json").read_bytes()
        self.assertEqual(first, second)
        result = json.loads(second)
        self.assertTrue(result["synthetic_demo"])
        self.assertEqual(result["status"], "DRAFT_NON_AUTHORITATIVE")
        self.assertEqual(len(result["cell_notes"]), 12)
        self.assertTrue(all(value is False for value in result["authority"].values()))
        self.assertTrue(all(row["analyst_note"] == "" for row in result["cell_notes"]))

    def test_selected_input_files_unchanged_by_sample_session(self):
        self.choose_inputs()
        before = self.page.evaluate("[el.candidateFile.files[0].name, el.authorityFile.files[0].name]")
        self.load()
        self.page.locator("#demoResetBtn").click()
        self.page.locator("#demoExitBtn").click()
        self.assertEqual(self.page.evaluate("[el.candidateFile.files[0].name, el.authorityFile.files[0].name]"), before)

    def test_late_import_cannot_replace_restarted_sample(self):
        self.pending_inspection()
        self.load()
        self.resolve_pending()
        self.assertEqual(self.page.evaluate("state.report.receipt_sha256"), "d" * 64)
        self.assertEqual(self.page.locator("#error").inner_text(), "")

    def test_late_success_cannot_resurrect_cleared_report(self):
        self.pending_inspection()
        self.page.locator("#resetBtn").click()
        self.resolve_pending()
        self.assertIsNone(self.page.evaluate("state.report"))
        self.assertTrue(self.page.locator("#exportBtn").is_disabled())

    def test_late_error_cannot_pollute_sample(self):
        self.pending_inspection()
        self.load()
        self.resolve_pending(error=True)
        self.assertEqual(self.page.locator("#error").inner_text(), "")

    def test_old_finally_cannot_enable_new_pending_inspection(self):
        self.pending_inspection()
        self.page.locator("#resetBtn").click()
        self.page.locator("#inspectBtn").click()
        self.page.wait_for_function("pending.length === 2")
        self.resolve_pending(index=0)
        self.assertTrue(self.page.locator("#inspectBtn").is_disabled())
        self.assertIsNone(self.page.evaluate("state.report"))
        self.resolve_pending(index=1)
        self.assertFalse(self.page.locator("#inspectBtn").is_disabled())
        self.assertEqual(self.page.evaluate("state.report.receipt_sha256"), "b" * 64)

    def test_failed_replacement_retains_existing_generation_boundary(self):
        self.load()
        self.edit()
        self.page.locator("#candidateFile").set_input_files({
            "name": "broken.json", "mimeType": "application/json", "buffer": b'{not-json'})
        self.page.locator("#inspectBtn").click()
        self.assertEqual(self.page.locator(".cell").count(), 0)
        self.assertIsNone(self.page.evaluate("state.report"))
        self.assertTrue(self.page.locator("#exportBtn").is_disabled())
        self.assertEqual(self.page.locator("#note").input_value(), "")
        self.assertNotEqual(self.page.locator("#error").inner_text(), "")
        self.assertTrue(self.page.locator("#demoExitBtn").is_disabled())

    def test_generation_never_rewinds_on_restore(self):
        self.import_fixture()
        before = self.page.evaluate("[state.generation, state.draftLoadSequence]")
        self.load()
        self.page.locator("#demoResetBtn").click()
        self.page.locator("#demoExitBtn").click()
        after = self.page.evaluate("[state.generation, state.draftLoadSequence]")
        self.assertTrue(all(end > start for start, end in zip(before, after)))

    def test_deferred_draft_cannot_replace_restored_review_same_receipt(self):
        self.import_fixture()
        self.edit("Current review to preserve")
        self.page.locator("#handoffFile").set_input_files({
            "name": "synthetic-draft.json", "mimeType": "application/json", "buffer": b'{}'})
        self.page.evaluate("""() => {
            const draft = WorkbenchHandoff.buildDraft(state.report);
            draft.cell_notes[1].analyst_note = 'OBSOLETE ASYNC DRAFT';
            window.delayedDraftText = JSON.stringify(draft);
            Object.defineProperty(el.handoffFile.files[0], 'text', {
                value: () => new Promise(resolve => { window.releaseDraft = resolve; })
            });
        }""")
        self.page.locator("#importDraftBtn").click()
        self.page.wait_for_function("typeof releaseDraft === 'function'")
        before = self.snapshot()
        self.load()
        self.page.locator("#demoResetBtn").click()
        self.page.locator("#demoExitBtn").click()
        self.page.evaluate("async () => { releaseDraft(delayedDraftText); await new Promise(r => setTimeout(r, 0)); }")
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.page.locator("#importDraftBtn").is_disabled())

    def test_saved_sample_draft_still_restores_through_shared_importer(self):
        self.load()
        self.edit("Saved synthetic review")
        exported = self.export("sample-to-restore.json")
        self.page.locator("#demoResetBtn").click()
        self.page.locator("#handoffFile").set_input_files(str(exported))
        self.page.locator("#importDraftBtn").click()
        self.page.wait_for_function("el.exportStatus.textContent.startsWith('Saved draft restored')")
        self.page.locator('.cell[data-key="ESS|security"]').click()
        self.assertEqual(self.page.locator("#note").input_value(), "Saved synthetic review")
        self.page.locator("#demoResetBtn").click()
        self.assertEqual(self.page.locator("#note").input_value(), "")

    def test_reset_and_leave_work_from_keyboard(self):
        self.page.locator("#demoBtn").focus()
        self.page.keyboard.press("Enter")
        self.edit()
        self.page.locator("#demoResetBtn").focus()
        self.page.keyboard.press("Enter")
        self.assertEqual(self.page.locator(".cell").count(), 12)
        self.assertEqual(self.page.locator("#note").input_value(), "")
        self.page.locator("#demoExitBtn").focus()
        self.page.keyboard.press("Enter")
        self.assertIsNone(self.page.evaluate("state.report"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
