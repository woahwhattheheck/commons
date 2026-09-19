#!/usr/bin/env python3
"""Chromium regression coverage for receipt-bound draft resumption.

Reports come from the real parent CompilerAdapter and checked-in fixtures. The
browser executes the checked-in UI assets; only fetch timing is controlled, so
these checks also run where browser navigation is restricted. Actual HTTP and
compiler transport coverage lives in test_workbench.py.

Install Playwright and a Chromium browser before running this script. Set
CHROMIUM_EXECUTABLE to use a specific browser, or let Playwright use its download.
"""
from __future__ import annotations

import copy
import json
import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from server import CompilerAdapter


ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent / "uiowa_rfq_18649_workshare"
AUTHORITY_FLAGS = {
    "buyer_approved", "prime_approved", "current_evidence_review_authority",
    "submission_authorized", "signature_authorized",
    "invoice_or_payment_authorized", "recognized_revenue",
}


class DraftResumeBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidate = json.loads((PARENT / "fixtures/synthetic_packet.json").read_text())
        cls.authority = json.loads((PARENT / "fixtures/synthetic_authority.json").read_text())
        # The adapter derives its inspection time from the newest embedded source,
        # making these genuine compiler reports repeatable across test dates.
        cls.report = CompilerAdapter().inspect(cls.candidate, cls.authority)
        alternate = copy.deepcopy(cls.candidate)
        alternate["source_ids"].remove("ESS-SW-01")
        alternate_authority = copy.deepcopy(cls.authority)
        alternate_authority["sources"] = [
            row for row in alternate_authority["sources"] if row["source_id"] != "ESS-SW-01"
        ]
        cls.alternate_report = CompilerAdapter().inspect(alternate, alternate_authority)
        assert cls.report["receipt_sha256"] != cls.alternate_report["receipt_sha256"]
        cls.playwright = sync_playwright().start()
        executable = os.environ.get("CHROMIUM_EXECUTABLE") or shutil.which("chromium")
        options = {"headless": True, "args": ["--no-sandbox"]}
        if executable:
            options["executable_path"] = executable
        try:
            cls.browser = cls.playwright.chromium.launch(**options)
        except Exception:
            cls.playwright.stop()
            raise

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
        self.page.set_default_timeout(5000)
        self.script_errors = []
        self.page.on("pageerror", lambda error: self.script_errors.append(str(error)))
        html = (ROOT / "index.html").read_text()
        html = html.replace('<link rel="stylesheet" href="/style.css">', "")
        html = re.sub(r'<script src="/(?:handoff|handoff_import|app)\.js" defer></script>', "", html)
        self.page.set_content(html, wait_until="load")
        self.page.add_style_tag(content=(ROOT / "style.css").read_text())
        for asset in ("handoff.js", "handoff_import.js", "app.js"):
            self.page.add_script_tag(content=(ROOT / asset).read_text())

    def tearDown(self):
        self.assertEqual(self.script_errors, [], "UI emitted an uncaught JavaScript error")

    def upload(self, selector, value, name="draft.json"):
        raw = value if isinstance(value, (str, bytes)) else json.dumps(value, ensure_ascii=False)
        buffer = raw if isinstance(raw, bytes) else raw.encode("utf-8")
        self.page.locator(selector).set_input_files({
            "name": name, "mimeType": "application/json", "buffer": buffer
        })

    def upload_package(self):
        self.open_import()
        self.upload("#candidateFile", self.candidate, "candidate.json")
        self.upload("#authorityFile", self.authority, "authority.json")

    def open_import(self):
        if self.page.locator("#importPanel").get_attribute("open") is None:
            self.page.locator("#importPanel > summary").click()

    def reset(self):
        self.open_import()
        self.page.locator("#resetBtn").click()

    def inspect(self, report=None):
        report = report or self.report
        self.page.evaluate("""report => {
            window.__inspectionRequests = [];
            window.fetch = async (url, options) => {
                window.__inspectionRequests.push({url, options});
                return {ok: true, status: 200, json: async () => ({report})};
            };
        }""", report)
        self.upload_package()
        self.page.locator("#inspectBtn").click()
        expect(self.page.locator("#matrix")).to_have_attribute("data-rendered-cells", "12")
        expect(self.page.locator("#reportMeta")).to_contain_text(report["receipt_sha256"])
        expect(self.page.locator("#summary-heading")).to_be_focused()
        requests = self.page.evaluate("window.__inspectionRequests")
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]["url"], "/api/inspect")
        self.assertEqual(requests[0]["options"]["method"], "POST")
        self.assertEqual(json.loads(requests[0]["options"]["body"]), {
            "candidate": self.candidate, "authority": self.authority,
        })
        self.assertEqual(requests[0]["options"]["body"],
                         '{"candidate":' + json.dumps(self.candidate, ensure_ascii=False) +
                         ',"authority":' + json.dumps(self.authority, ensure_ascii=False) + '}',
                         "inspection must preserve the uploaded JSON source fragments")

    def annotate(self, index, note, disposition="NEEDS_EVIDENCE"):
        self.page.locator(".cell").nth(index).click()
        self.page.locator("#note").fill(note)
        self.page.locator("#disposition").select_option(disposition)

    def export(self):
        with self.page.expect_download() as pending:
            self.page.locator("#exportBtn").click()
        downloaded = pending.value
        destination = Path(self.temp.name) / downloaded.suggested_filename
        downloaded.save_as(destination)
        return json.loads(destination.read_text())

    def restore(self, draft):
        self.upload("#handoffFile", draft)
        self.page.locator("#importDraftBtn").click()
        expect(self.page.locator("#importDraftBtn")).to_be_enabled()

    def read_cell_notes(self):
        """Read every visible cell through the operator UI, without downloading."""
        notes = []
        for index in range(12):
            self.page.locator(".cell").nth(index).click()
            detail = json.loads(self.page.locator("#detail").text_content())
            notes.append({
                "group": detail["group"],
                "dimension": detail["dimension"],
                "compiler_status": detail["status"],
                "disposition": self.page.locator("#disposition").input_value(),
                "analyst_note": self.page.locator("#note").input_value(),
            })
        return notes

    def begin_delayed_restore(self, draft):
        # Hold the browser's actual File.arrayBuffer await, then resolve it explicitly.
        # No wall-clock sleep is needed to create a deterministic race.
        self.page.evaluate("""() => {
            const original = File.prototype.arrayBuffer;
            File.prototype.arrayBuffer = function () {
                if (this.name !== 'delayed-draft.json') return original.call(this);
                return new Promise(resolve => {
                    window.__releaseDraftRead = () => original.call(this).then(resolve);
                });
            };
        }""")
        self.upload("#handoffFile", draft, "delayed-draft.json")
        self.page.locator("#importDraftBtn").click()
        self.page.wait_for_function("typeof window.__releaseDraftRead === 'function'")

    def release_draft_read(self):
        self.page.evaluate("""async () => {
            await window.__releaseDraftRead();
            await new Promise(resolve => setTimeout(resolve, 0));
        }""")

    def begin_delayed_inspection(self):
        self.upload_package()
        self.page.evaluate("""() => {
            window.fetch = () => new Promise(resolve => {
                window.__releaseInspection = resolve;
            });
        }""")
        self.page.locator("#inspectBtn").click()
        self.page.wait_for_function("typeof window.__releaseInspection === 'function'")

    def release_inspection(self, report=None, error=None):
        self.page.evaluate("""async payload => {
            window.__releaseInspection({
                ok: payload.error === null,
                status: payload.error === null ? 200 : 400,
                json: async () => payload.error === null ? {report: payload.report} : {error: payload.error}
            });
            await new Promise(resolve => setTimeout(resolve, 0));
        }""", {"report": report or self.report, "error": error})

    def assert_no_authority(self, draft):
        self.assertEqual(draft["status"], "DRAFT_NON_AUTHORITATIVE")
        self.assertEqual(draft["report_mode"], "UNTRUSTED_INSPECTION")
        self.assertEqual(set(draft["authority"]), AUTHORITY_FLAGS)
        for value in draft["authority"].values():
            self.assertIs(value, False)

    def test_restore_requires_active_report(self):
        expect(self.page.locator("#importDraftBtn")).to_be_disabled()
        expect(self.page.locator("#exportBtn")).to_be_disabled()
        self.inspect()
        expect(self.page.locator("#importDraftBtn")).to_be_enabled()
        self.reset()
        expect(self.page.locator("#importDraftBtn")).to_be_disabled()
        expect(self.page.locator("#matrix")).to_have_attribute("data-rendered-cells", "0")

    def test_all_twelve_cells_roundtrip_by_identity_without_network(self):
        self.inspect()
        dispositions = ("UNREVIEWED", "NEEDS_EVIDENCE", "DISCUSS_WITH_PRIME", "TECHNICAL_DRAFT_NOTE")
        for index in range(12):
            self.annotate(index, f"Cell {index}: draft café / 観察\nLiteral <b>text</b>", dispositions[index % 4])
        saved = self.export()
        self.assert_no_authority(saved)
        self.assertEqual(len(saved["cell_notes"]), 12)
        self.assertFalse(saved["synthetic_demo"])
        self.reset()
        self.inspect()
        self.assertTrue(all(not row["analyst_note"] for row in self.export()["cell_notes"]))
        # Order is transport detail: restoration is keyed by group/dimension.
        reordered = copy.deepcopy(saved)
        reordered["cell_notes"].reverse()
        self.restore(reordered)
        expect(self.page.locator("#error")).to_be_empty()
        self.assertEqual(self.export(), saved)
        self.assertEqual(len(self.page.evaluate("window.__inspectionRequests")), 1,
                         "restoring a local draft must not call the server")
        for index, cell in enumerate(saved["cell_notes"]):
            self.page.locator(".cell").nth(index).click()
            expect(self.page.locator("#note")).to_have_value(cell["analyst_note"])
            expect(self.page.locator("#disposition")).to_have_value(cell["disposition"])

    def test_invalid_drafts_preserve_existing_notes_and_report(self):
        self.inspect()
        self.annotate(0, "Current work must survive rejected restore.", "DISCUSS_WITH_PRIME")
        baseline = self.export()
        variants = {}
        for label, key, value in (
            ("receipt mismatch", "report_receipt_sha256", "f" * 64),
            ("mode mismatch", "report_mode", "CURRENT"),
            ("synthetic mismatch", "synthetic_demo", True),
            ("aggregate mismatch", "aggregate_state", "READY"),
        ):
            variants[label] = {**copy.deepcopy(baseline), key: value}
        duplicate = copy.deepcopy(baseline)
        duplicate["cell_notes"][-1] = copy.deepcopy(duplicate["cell_notes"][0])
        variants["duplicate cell identity"] = duplicate
        missing = copy.deepcopy(baseline)
        missing["cell_notes"].pop()
        variants["missing cell"] = missing
        status = copy.deepcopy(baseline)
        status["cell_notes"][0]["compiler_status"] = "READY"
        variants["compiler status mismatch"] = status
        authority = copy.deepcopy(baseline)
        authority["authority"]["prime_approved"] = True
        variants["authority claim"] = authority
        long_note = copy.deepcopy(baseline)
        long_note["cell_notes"][0]["analyst_note"] = "x" * 4001
        variants["oversized note"] = long_note
        variants["malformed JSON"] = "{not-json"
        variants["invalid UTF-8 note"] = json.dumps(baseline).encode("utf-8").replace(
            b"Current work must survive rejected restore.", b"Invalid byte: \xff"
        )
        variants["browser intake limit"] = " " * (1024 * 1024 + 1)
        for label, draft in variants.items():
            with self.subTest(label=label):
                self.restore(draft)
                expect(self.page.locator("#error")).not_to_be_empty()
                expect(self.page.locator("#matrix")).to_have_attribute("data-rendered-cells", "12")
                expect(self.page.locator("#reportMeta")).to_contain_text(baseline["report_receipt_sha256"])
                self.assertEqual(self.read_cell_notes(), baseline["cell_notes"])
        # Keep actual file custody coverage without flooding Chromium's automatic
        # download limiter with a dozen immediate downloads in one browser page.
        self.assertEqual(self.export(), baseline)

    def test_draft_from_previous_compiler_generation_cannot_replace_current_work(self):
        self.inspect()
        self.annotate(0, "Saved under original evidence.")
        old_draft = self.export()
        self.inspect(self.alternate_report)
        self.annotate(1, "Notes for the changed evidence only.")
        current = self.export()
        self.page.locator("#search").fill("ESS")
        selected_status = current["cell_notes"][1]["compiler_status"]
        self.page.locator("#statusFilter").select_option(selected_status)
        visible_count = self.page.locator("#matrix").get_attribute("data-rendered-cells")
        selected_detail = self.page.locator("#detail").text_content()
        self.restore(old_draft)
        expect(self.page.locator("#error")).not_to_be_empty()
        expect(self.page.locator("#search")).to_have_value("ESS")
        expect(self.page.locator("#statusFilter")).to_have_value(selected_status)
        expect(self.page.locator("#matrix")).to_have_attribute("data-rendered-cells", visible_count)
        expect(self.page.locator("#detail")).to_have_text(selected_detail)
        self.assertEqual(self.export(), current)

    def test_restored_draft_exports_readable_markdown_with_receipt(self):
        self.inspect()
        note = "Confirm the evidence owner before prospective prime discussion"
        self.annotate(0, note, "DISCUSS_WITH_PRIME")
        saved = self.export()
        self.inspect()
        self.restore(saved)
        with self.page.expect_download() as pending:
            self.page.locator("#markdownBtn").click()
        downloaded = pending.value
        self.assertTrue(downloaded.suggested_filename.endswith(".md"))
        destination = Path(self.temp.name) / downloaded.suggested_filename
        downloaded.save_as(destination)
        markdown = destination.read_text()
        self.assertIn(saved["report_receipt_sha256"], markdown)
        self.assertIn("**DRAFT — NON-AUTHORITATIVE**", markdown)
        self.assertIn(note, markdown)
        self.assertIn("## Open follow-ups", markdown)
        self.assertIn("authority flag is false", markdown)
        self.assertEqual(len(re.findall(r"^### ", markdown, re.MULTILINE)), 12)
        self.assertEqual(self.export(), saved, "Markdown export must not mutate the draft")

    def test_delayed_draft_cannot_overwrite_intervening_note_edit(self):
        self.inspect()
        self.annotate(0, "Old saved note.")
        saved = self.export()
        self.begin_delayed_restore(saved)
        self.annotate(0, "New edit while draft file is being read.", "TECHNICAL_DRAFT_NOTE")
        current = self.export()
        self.release_draft_read()
        expect(self.page.locator("#importDraftBtn")).to_be_enabled()
        self.assertEqual(self.export(), current)

    def test_delayed_draft_cannot_cross_report_replacement(self):
        self.inspect()
        self.annotate(0, "Old real-report note.")
        self.begin_delayed_restore(self.export())
        # Even identical compiler bytes constitute a new operator generation.
        # A receipt-only stale check would incorrectly accept the pending read.
        self.inspect()
        self.annotate(2, "New note after reimporting the same report.")
        current = self.export()
        self.release_draft_read()
        self.assertEqual(self.export(), current)
        self.assertFalse(current["synthetic_demo"])

    def test_delayed_draft_cannot_repopulate_cleared_workbench(self):
        self.inspect()
        self.annotate(0, "Saved before clearing.")
        self.begin_delayed_restore(self.export())
        self.reset()
        self.release_draft_read()
        expect(self.page.locator("#matrix")).to_have_attribute("data-rendered-cells", "0")
        expect(self.page.locator("#exportBtn")).to_be_disabled()
        expect(self.page.locator("#importDraftBtn")).to_be_disabled()
        expect(self.page.locator("#note")).to_have_value("")

    def test_delayed_compiler_success_cannot_replace_newer_report_or_notes(self):
        self.begin_delayed_inspection()
        self.page.locator("#demoBtn").click()
        self.annotate(0, "Keep the newer report's note.")
        current = self.export()
        self.release_inspection(self.report)
        self.assertEqual(self.export(), current)
        expect(self.page.locator("#error")).to_be_empty()

    def test_delayed_compiler_failure_cannot_mark_newer_report_failed(self):
        self.begin_delayed_inspection()
        self.page.locator("#demoBtn").click()
        self.annotate(0, "A stale failure cannot invalidate this report.")
        current = self.export()
        self.release_inspection(error="Old inspection failed after its generation was replaced")
        self.assertEqual(self.export(), current)
        expect(self.page.locator("#error")).to_be_empty()


if __name__ == "__main__":
    unittest.main(verbosity=2)
