#!/usr/bin/env python3
"""Actual-browser acceptance tests for draft continuity within one open tab.

Chromium uploads the checked-in evidence files to the real loopback server and
CompilerAdapter. Changed receipts come from changed evidence, not report mocks.
The late-response case delays delivery of a real HTTP Response; one failure case
injects a local serialization fault. No external service is contacted.

Install Playwright and Chromium, or set CHROMIUM_EXECUTABLE to an existing browser.
"""
from __future__ import annotations

import copy
import json
import os
import shutil
import tempfile
import threading
import unittest
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from server import CompilerAdapter, create_server


ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent / "uiowa_rfq_18649_workshare"
AUTHORITY_FLAGS = {
    "buyer_approved", "prime_approved", "current_evidence_review_authority",
    "submission_authorized", "signature_authorized",
    "invoice_or_payment_authorized", "recognized_revenue",
}


class DraftContinuityBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidate_path = PARENT / "fixtures/synthetic_packet.json"
        cls.authority_path = PARENT / "fixtures/synthetic_authority.json"
        candidate = json.loads(cls.candidate_path.read_text())
        authority = json.loads(cls.authority_path.read_text())
        adapter = CompilerAdapter()
        cls.report = adapter.inspect(candidate, authority)
        alternate = copy.deepcopy(candidate)
        alternate["source_ids"].remove("ESS-SW-01")
        alternate_authority = copy.deepcopy(authority)
        alternate_authority["sources"] = [
            row for row in alternate_authority["sources"] if row["source_id"] != "ESS-SW-01"
        ]
        cls.alternate_report = adapter.inspect(alternate, alternate_authority)
        if cls.report["receipt_sha256"] == cls.alternate_report["receipt_sha256"]:
            raise RuntimeError("changed evidence must produce a different compiler receipt")
        cls.fixtures = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.fixtures.cleanup)
        cls.alternate_candidate_path = Path(cls.fixtures.name) / "changed-candidate.json"
        cls.alternate_authority_path = Path(cls.fixtures.name) / "changed-authority.json"
        cls.alternate_candidate_path.write_text(json.dumps(alternate), encoding="utf-8")
        cls.alternate_authority_path.write_text(json.dumps(alternate_authority), encoding="utf-8")

        cls.http = create_server(port=0, adapter=adapter, static_root=ROOT)
        cls.addClassCleanup(cls.http.server_close)
        cls.http_thread = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.http_thread.start()
        cls.addClassCleanup(cls.stop_http)
        cls.url = f"http://127.0.0.1:{cls.http.server_port}/"
        cls.playwright = sync_playwright().start()
        cls.addClassCleanup(cls.playwright.stop)
        executable = os.environ.get("CHROMIUM_EXECUTABLE") or shutil.which("chromium")
        options = {"headless": True, "args": ["--no-sandbox"]}
        if executable:
            options["executable_path"] = executable
        cls.browser = cls.playwright.chromium.launch(**options)
        cls.addClassCleanup(cls.browser.close)

    @classmethod
    def stop_http(cls):
        cls.http.shutdown()
        cls.http_thread.join(timeout=2)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.context = self.browser.new_context(accept_downloads=True)
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()
        self.page.set_default_timeout(7500)
        self.script_errors = []
        self.inspection_requests = []
        self.page.on("pageerror", lambda error: self.script_errors.append(str(error)))
        self.page.on("request", lambda request: self.inspection_requests.append(request)
                     if request.url == self.url + "api/inspect" else None)
        response = self.page.goto(self.url, wait_until="load")
        self.assertEqual(response.status, 200)
        expect(self.page.locator("#matrix")).to_have_attribute("data-rendered-cells", "0")
        self.download_count = 0

    def tearDown(self):
        self.assertEqual(self.script_errors, [], "UI emitted an uncaught JavaScript error")

    def open_panel(self, selector):
        if self.page.locator(selector).get_attribute("open") is None:
            self.page.locator(selector + " > summary").click()

    def upload_package(self, alternate=False):
        self.open_panel("#importPanel")
        candidate = self.alternate_candidate_path if alternate else self.candidate_path
        authority = self.alternate_authority_path if alternate else self.authority_path
        self.page.locator("#candidateFile").set_input_files(str(candidate))
        self.page.locator("#authorityFile").set_input_files(str(authority))
        return candidate, authority

    def inspect(self, alternate=False):
        candidate, authority = self.upload_package(alternate)
        expected = self.alternate_report if alternate else self.report
        count = len(self.inspection_requests)
        with self.page.expect_response(lambda response: response.url == self.url + "api/inspect") as pending:
            self.page.locator("#inspectBtn").click()
        response = pending.value
        self.assertEqual(response.status, 200)
        self.assertEqual(response.json()["report"], expected)
        expect(self.page.locator("#matrix")).to_have_attribute("data-rendered-cells", "12")
        expect(self.page.locator("#reportMeta")).to_contain_text(expected["receipt_sha256"])
        expect(self.page.locator("#inspectBtn")).to_be_enabled()
        self.assertEqual(len(self.inspection_requests), count + 1)
        request = self.inspection_requests[-1]
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.post_data,
                         '{"candidate":' + candidate.read_text() +
                         ',"authority":' + authority.read_text() + '}',
                         "the real HTTP request must retain original JSON source fragments")
        return expected

    def annotate(self, index, note, disposition="NEEDS_EVIDENCE"):
        self.page.locator(".cell").nth(index).click()
        self.page.locator("#note").fill(note)
        self.page.locator("#disposition").select_option(disposition)

    def read_cell_notes(self):
        notes = []
        for index in range(12):
            self.page.locator(".cell").nth(index).click()
            detail = json.loads(self.page.locator("#detail").text_content())
            notes.append({
                "group": detail["group"], "dimension": detail["dimension"],
                "compiler_status": detail["status"],
                "disposition": self.page.locator("#disposition").input_value(),
                "analyst_note": self.page.locator("#note").input_value(),
            })
        return notes

    def download(self, selector):
        with self.page.expect_download() as pending:
            self.page.locator(selector).click()
        downloaded = pending.value
        self.download_count += 1
        destination = Path(self.temp.name) / f"{self.download_count}-{downloaded.suggested_filename}"
        downloaded.save_as(destination)
        self.last_download_path = destination
        draft = json.loads(destination.read_bytes().decode("utf-8"))
        self.assertEqual(draft["status"], "DRAFT_NON_AUTHORITATIVE")
        self.assertEqual(draft["report_mode"], "UNTRUSTED_INSPECTION")
        self.assertEqual(set(draft["authority"]), AUTHORITY_FLAGS)
        for value in draft["authority"].values():
            self.assertIs(value, False)
        self.assertIn(draft["report_receipt_sha256"][:12], downloaded.suggested_filename)
        return draft

    def select_saved(self, receipt):
        self.open_panel("#savedDraftPanel")
        self.page.locator("#savedDraftSelect").select_option(receipt)
        expect(self.page.locator("#savedDraftStatus")).to_contain_text(receipt)

    def clear(self):
        self.open_panel("#importPanel")
        self.page.locator("#resetBtn").click()

    def assert_inactive(self):
        expect(self.page.locator("#matrix")).to_have_attribute("data-rendered-cells", "0")
        expect(self.page.locator("#exportBtn")).to_be_disabled()
        expect(self.page.locator("#markdownBtn")).to_be_disabled()
        expect(self.page.locator("#importDraftBtn")).to_be_disabled()
        expect(self.page.locator("#restoreTabDraftBtn")).to_be_disabled()
        expect(self.page.locator("#note")).to_have_value("")
        expect(self.page.locator("#note")).to_be_disabled()
        self.assertIsNone(self.page.evaluate("state.report"))

    def test_same_files_reinspect_retains_all_twelve_notes_and_dispositions(self):
        self.inspect()
        dispositions = ("UNREVIEWED", "NEEDS_EVIDENCE", "DISCUSS_WITH_PRIME", "TECHNICAL_DRAFT_NOTE")
        for index in range(12):
            self.annotate(index, f"Draft {index}: café 📝 / 観察\nLiteral <b>text</b>", dispositions[index % 4])
        saved = self.download("#exportBtn")
        self.assertFalse(saved["synthetic_demo"])
        self.inspect()
        self.assertEqual(self.read_cell_notes(), saved["cell_notes"])
        self.select_saved(saved["report_receipt_sha256"])
        expect(self.page.locator("#savedDraftStatus")).to_contain_text("12 notes")
        expect(self.page.locator("#restoreTabDraftBtn")).to_be_enabled()
        count = len(self.inspection_requests)
        self.page.locator("#restoreTabDraftBtn").click()
        expect(self.page.locator("#exportStatus")).to_contain_text("Draft restored from this tab")
        self.assertEqual(self.read_cell_notes(), saved["cell_notes"])
        self.assertEqual(len(self.inspection_requests), count, "local restore must not call the compiler")

    def test_changed_receipt_starts_clean_and_old_draft_downloads_without_cross_restore(self):
        self.inspect()
        self.annotate(0, "Original evidence follow-up.", "DISCUSS_WITH_PRIME")
        self.annotate(11, "Original final area.", "TECHNICAL_DRAFT_NOTE")
        saved = self.download("#exportBtn")
        self.inspect(alternate=True)
        clean = self.read_cell_notes()
        self.assertTrue(all(row["analyst_note"] == "" and row["disposition"] == "UNREVIEWED" for row in clean))
        self.select_saved(saved["report_receipt_sha256"])
        expect(self.page.locator("#restoreTabDraftBtn")).to_be_disabled()
        self.assertEqual(self.download("#downloadTabDraftBtn"), saved)
        expect(self.page.locator("#reportMeta")).to_contain_text(self.alternate_report["receipt_sha256"])
        self.assertEqual(self.read_cell_notes(), clean)
        self.annotate(1, "Different evidence needs its own note.")
        self.inspect()
        self.assertEqual(self.read_cell_notes(), saved["cell_notes"])

    def test_failed_real_compiler_inspection_keeps_saved_work_recoverable(self):
        self.inspect()
        self.annotate(2, "Keep this through a rejected evidence package.", "DISCUSS_WITH_PRIME")
        saved = self.download("#exportBtn")
        self.upload_package()
        self.page.locator("#candidateFile").set_input_files({
            "name": "invalid-candidate.json", "mimeType": "application/json", "buffer": b"{}"
        })
        with self.page.expect_response(lambda response: response.url == self.url + "api/inspect") as pending:
            self.page.locator("#inspectBtn").click()
        response = pending.value
        self.assertEqual(response.status, 400)
        self.assertIn("compiler rejected", response.json()["error"])
        expect(self.page.locator("#error")).not_to_be_empty()
        expect(self.page.locator("#inspectBtn")).to_be_enabled()
        self.assert_inactive()
        self.select_saved(saved["report_receipt_sha256"])
        self.assertEqual(self.download("#downloadTabDraftBtn"), saved)
        self.assert_inactive()
        self.inspect()
        self.assertEqual(self.read_cell_notes(), saved["cell_notes"])

    def test_clear_retains_download_but_late_actual_http_response_cannot_resurrect_report(self):
        self.inspect()
        self.annotate(0, "Saved before the delayed inspection.")
        saved = self.download("#exportBtn")
        self.upload_package()
        self.page.evaluate("""() => {
            const nativeFetch = window.fetch.bind(window);
            window.fetch = async (...args) => {
                const response = await nativeFetch(...args);
                if (args[0] !== '/api/inspect') return response;
                window.__heldInspectionStatus = response.status;
                const nativeJson = response.json.bind(response);
                response.json = async () => {
                    const payload = await nativeJson();
                    window.__lateInspectionJsonParsed = true;
                    return payload;
                };
                return new Promise(resolve => {
                    window.__releaseInspection = () => resolve(response);
                });
            };
        }""")
        self.page.locator("#inspectBtn").click()
        self.page.wait_for_function("typeof window.__releaseInspection === 'function'")
        self.assertEqual(self.page.evaluate("window.__heldInspectionStatus"), 200)
        self.clear()
        self.assert_inactive()
        self.select_saved(saved["report_receipt_sha256"])
        self.assertEqual(self.download("#downloadTabDraftBtn"), saved)
        self.page.evaluate("window.__releaseInspection()")
        self.page.wait_for_function("window.__lateInspectionJsonParsed === true")
        self.page.evaluate("() => new Promise(resolve => setTimeout(resolve, 0))")
        self.assert_inactive()
        expect(self.page.locator("#error")).to_be_empty()
        expect(self.page.locator("#downloadTabDraftBtn")).to_be_enabled()

    def test_demo_and_real_inspection_restore_their_own_separate_drafts(self):
        self.inspect()
        self.annotate(0, "Compiled evidence note.", "DISCUSS_WITH_PRIME")
        real = self.download("#exportBtn")
        self.open_panel("#importPanel")
        self.page.locator("#demoBtn").click()
        self.assertTrue(all(row["analyst_note"] == "" for row in self.read_cell_notes()))
        self.annotate(0, "Illustrative UI sample note.", "TECHNICAL_DRAFT_NOTE")
        demo = self.download("#exportBtn")
        self.assertTrue(demo["synthetic_demo"])
        self.assertNotEqual(demo["report_receipt_sha256"], real["report_receipt_sha256"])
        self.inspect()
        self.assertEqual(self.read_cell_notes(), real["cell_notes"])
        self.select_saved(demo["report_receipt_sha256"])
        expect(self.page.locator("#restoreTabDraftBtn")).to_be_disabled()
        self.open_panel("#importPanel")
        self.page.locator("#demoBtn").click()
        self.assertEqual(self.read_cell_notes(), demo["cell_notes"])
        expect(self.page.locator("#sampleBadge")).to_contain_text("Synthetic sample")

    def test_empty_edits_replace_saved_snapshot_instead_of_resurrecting_old_note(self):
        self.inspect()
        self.annotate(4, "This note will be intentionally cleared.", "DISCUSS_WITH_PRIME")
        self.annotate(4, "", "UNREVIEWED")
        self.select_saved(self.report["receipt_sha256"])
        expect(self.page.locator("#savedDraftStatus")).to_contain_text("0 notes; 0 reviewed dispositions")
        self.inspect()
        self.assertTrue(all(row["analyst_note"] == "" and row["disposition"] == "UNREVIEWED"
                            for row in self.read_cell_notes()))
        self.select_saved(self.report["receipt_sha256"])
        empty = self.download("#downloadTabDraftBtn")
        self.assertTrue(all(row["analyst_note"] == "" and row["disposition"] == "UNREVIEWED"
                            for row in empty["cell_notes"]))

    def test_serialization_failure_preserves_active_edits_and_previous_saved_drafts(self):
        self.inspect()
        self.annotate(0, "Earlier receipt must remain recoverable.")
        prior = self.download("#exportBtn")
        self.inspect(alternate=True)
        self.annotate(6, "Active work must survive serialization failure.", "TECHNICAL_DRAFT_NOTE")
        current = self.read_cell_notes()
        self.select_saved(prior["report_receipt_sha256"])
        self.upload_package()
        requests = len(self.inspection_requests)
        self.page.evaluate("""() => {
            window.__nativeStringify = JSON.stringify;
            JSON.stringify = function (value, ...args) {
                if (value?.schema === 'uiowa-rfq18649-analyst-handoff-draft/v1') {
                    throw new Error('Controlled draft serialization failure');
                }
                return window.__nativeStringify.call(JSON, value, ...args);
            };
        }""")
        self.page.locator("#inspectBtn").click()
        expect(self.page.locator("#error")).to_contain_text("Controlled draft serialization failure")
        expect(self.page.locator("#reportMeta")).to_contain_text(self.alternate_report["receipt_sha256"])
        self.assertEqual(self.read_cell_notes(), current)
        self.assertEqual(len(self.inspection_requests), requests,
                         "failed preservation must stop before replacing the active report")
        self.page.evaluate("JSON.stringify = window.__nativeStringify")
        self.select_saved(prior["report_receipt_sha256"])
        self.assertEqual(self.download("#downloadTabDraftBtn"), prior)
        self.inspect()
        self.assertEqual(self.read_cell_notes(), prior["cell_notes"])

    def test_file_draft_restore_updates_tab_snapshot_before_clear_and_reinspect(self):
        self.inspect()
        self.annotate(3, "Restore this downloaded draft into tab memory.", "DISCUSS_WITH_PRIME")
        saved = self.download("#exportBtn")
        downloaded_path = self.last_download_path
        self.annotate(3, "Temporary edit to replace through file restore.", "TECHNICAL_DRAFT_NOTE")
        requests = len(self.inspection_requests)
        self.page.locator("#handoffFile").set_input_files(str(downloaded_path))
        self.page.locator("#importDraftBtn").click()
        expect(self.page.locator("#exportStatus")).to_contain_text("Saved draft restored for this report")
        self.assertEqual(self.read_cell_notes(), saved["cell_notes"])
        self.assertEqual(len(self.inspection_requests), requests)
        self.clear()
        self.assert_inactive()
        self.select_saved(saved["report_receipt_sha256"])
        self.assertEqual(self.download("#downloadTabDraftBtn"), saved)
        self.inspect()
        self.assertEqual(self.read_cell_notes(), saved["cell_notes"])

    def test_reload_has_no_persisted_drafts_or_automatically_reopened_report(self):
        self.inspect()
        self.annotate(0, "This draft exists in this document's memory only.")
        self.select_saved(self.report["receipt_sha256"])
        expect(self.page.locator("#downloadTabDraftBtn")).to_be_enabled()
        response = self.page.reload(wait_until="load")
        self.assertEqual(response.status, 200)
        self.assert_inactive()
        self.open_panel("#savedDraftPanel")
        expect(self.page.locator("#savedDraftSelect")).to_be_disabled()
        expect(self.page.locator("#downloadTabDraftBtn")).to_be_disabled()
        self.assertEqual(self.page.evaluate("state.savedDrafts.size"), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
