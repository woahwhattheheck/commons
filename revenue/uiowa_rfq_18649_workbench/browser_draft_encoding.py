#!/usr/bin/env python3
"""Saved analyst-draft fidelity checks in actual Chromium, fully offline.

WORKBENCH_SOURCE must name the composed workbench asset directory. Native File
uploads, decoding, controls, restores and downloads run; report data is the
explicit UI demo, not parent-compiler output. No HTTP/CI/layout claim is made.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import unittest

from playwright.sync_api import expect, sync_playwright

ROOT = Path(os.environ.get("WORKBENCH_SOURCE", Path(__file__).parent)).resolve()


class SavedDraftEncodingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = sync_playwright().start()
        executable = os.environ.get("CHROMIUM_EXECUTABLE") or shutil.which("chromium")
        options = {"headless": True, "args": ["--no-sandbox"]}
        if executable:
            options["executable_path"] = executable
        try:
            cls.browser = cls.runtime.chromium.launch(**options)
        except Exception:
            cls.runtime.stop()
            raise
        print(f"CHROMIUM_VERSION={cls.browser.version}; SOURCE={ROOT}", flush=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.runtime.stop()

    def setUp(self):
        self.context = self.browser.new_context(accept_downloads=True)
        self.addCleanup(self.context.close)
        self.context.route("**/*", lambda route: route.abort())
        self.page = self.context.new_page()
        self.page.set_default_timeout(3000)
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        html = re.sub(r'<link[^>]+href="/style.css"[^>]*>', "", html)
        html = re.sub(r'<script src="/(?:handoff|handoff_import|app)\.js" defer></script>', "", html)
        self.page.set_content(html, wait_until="load")
        for asset in ("handoff.js", "handoff_import.js", "app.js"):
            self.page.add_script_tag(content=(ROOT / asset).read_text(encoding="utf-8"))
        self.page.evaluate("""() => {
            window.__fetchCalls = 0;
            window.fetch = async () => { window.__fetchCalls++; throw new Error('network forbidden'); };
        }""")
        self.page.locator("#demoBtn").click()
        self.page.locator(".cell").first.click()
        self.page.locator("#note").fill("Current analyst work must survive rejection.")
        self.page.locator("#disposition").select_option("DISCUSS_WITH_PRIME")
        self.baseline = self.snapshot()

    def tearDown(self):
        self.assertEqual(self.errors, [], "uncaught browser exception")
        self.assertEqual(self.page.evaluate("window.__fetchCalls"), 0,
                         "saved draft operations must remain browser-local")

    def snapshot(self):
        return self.page.evaluate("""() => ({
            draft: state.report ? WorkbenchHandoff.buildDraft(state.report, state.notes, state.dispositions) : null,
            selected: state.selectedKey,
            note: document.getElementById('note').value,
            disposition: document.getElementById('disposition').value,
            search: document.getElementById('search').value,
            status: document.getElementById('statusFilter').value
        })""")

    def draft(self, note="SAVED_SENTINEL"):
        draft = json.loads(json.dumps(self.baseline["draft"]))
        draft["cell_notes"][0]["analyst_note"] = note
        draft["cell_notes"][0]["disposition"] = "NEEDS_EVIDENCE"
        return draft

    def raw(self, note="SAVED_SENTINEL"):
        return json.dumps(self.draft(note), ensure_ascii=False).encode("utf-8")

    def upload(self, raw, name="saved-draft.json"):
        self.page.locator("#handoffFile").set_input_files({
            "name": name, "mimeType": "application/json", "buffer": raw,
        })

    def restore(self, raw):
        self.upload(raw)
        self.page.locator("#importDraftBtn").click()
        expect(self.page.locator("#importDraftBtn")).to_be_enabled()

    def assert_rejected(self, raw, diagnostic):
        before = self.snapshot()
        self.restore(raw)
        self.assertIn(diagnostic, self.page.locator("#error").inner_text())
        self.assertEqual(self.snapshot(), before)
        expect(self.page.locator("#exportBtn")).to_be_enabled()
        expect(self.page.locator("#markdownBtn")).to_be_enabled()

    def download(self, selector):
        with self.page.expect_download() as pending:
            self.page.locator(selector).click()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / pending.value.suggested_filename
            pending.value.save_as(path)
            return path.read_text(encoding="utf-8")

    def begin_delayed(self, raw, failure=False):
        self.page.evaluate("""failure => {
            for (const method of ['text', 'arrayBuffer']) {
                const original = File.prototype[method];
                File.prototype[method] = function () {
                    if (this.name !== 'delayed-draft.json') return original.call(this);
                    return new Promise((resolve, reject) => {
                        window.__releaseRead = async () => {
                            if (failure) { reject(new Error('Synthetic file read failure')); return; }
                            resolve(await original.call(this));
                        };
                    });
                };
            }
        }""", failure)
        self.upload(raw, "delayed-draft.json")
        self.page.locator("#importDraftBtn").click()
        self.page.wait_for_function("typeof window.__releaseRead === 'function'")

    def release(self):
        self.page.evaluate("""async () => {
            await window.__releaseRead();
            await new Promise(resolve => setTimeout(resolve, 0));
        }""")

    def test_valid_unicode_and_bom_roundtrip(self):
        note = "Composed café; decomposed cafe\u0301; emoji 🧪; CJK 観察; literal �\nLine two."
        self.restore(b"\xef\xbb\xbf" + self.raw(note))
        expect(self.page.locator("#error")).to_be_empty()
        expect(self.page.locator("#note")).to_have_value(note)
        exported = json.loads(self.download("#exportBtn"))
        self.assertEqual(exported, self.draft(note))
        self.assertTrue(all(value is False for value in exported["authority"].values()))
        markdown = self.download("#markdownBtn")
        self.assertIn("Composed café", markdown)
        self.assertIn("decomposed cafe\u0301", markdown)
        self.assertIn("literal �", markdown)

    def test_all_twelve_notes_and_dispositions_survive_reordering(self):
        draft = self.draft()
        for i, row in enumerate(draft["cell_notes"]):
            row["analyst_note"] = f"Fictional cell {i}: café 📝 / 観察"
            row["disposition"] = ("UNREVIEWED", "NEEDS_EVIDENCE", "DISCUSS_WITH_PRIME", "TECHNICAL_DRAFT_NOTE")[i % 4]
        original = json.loads(json.dumps(draft))
        draft["cell_notes"].reverse()
        self.restore(json.dumps(draft, ensure_ascii=False).encode("utf-8"))
        expect(self.page.locator("#error")).to_be_empty()
        self.assertEqual(json.loads(self.download("#exportBtn")), original)

    def test_rejected_restore_preserves_filter_and_selected_cell(self):
        self.page.locator("#search").fill("ESS")
        self.page.locator("#statusFilter").select_option("UNTRUSTED_EVIDENCE_CONSISTENT")
        self.assert_rejected(self.raw().replace(b"SAVED_SENTINEL", b"bad\xffnote"), "UTF-8")

    def test_rejected_then_valid_restore_recovers(self):
        self.assert_rejected(self.raw().replace(b"SAVED_SENTINEL", b"\xff"), "UTF-8")
        self.restore(self.raw("Valid repair of file encoding"))
        expect(self.page.locator("#error")).to_be_empty()
        expect(self.page.locator("#note")).to_have_value("Valid repair of file encoding")

    def test_valid_utf8_malformed_json_preserves_current_work(self):
        self.assert_rejected(b"{not-json", "JSON")

    def test_duplicate_members_preserve_current_work(self):
        raw = self.raw().replace(b'"analyst_note": "SAVED_SENTINEL"',
                                b'"analyst_note": "first", "analyst_note": "second"')
        self.assert_rejected(raw, "duplicate")

    def test_oversize_preserves_current_work(self):
        self.assert_rejected(b" " * (1024 * 1024 + 1), "1 MiB")

    def test_read_failure_preserves_current_work(self):
        self.begin_delayed(self.raw(), failure=True)
        self.release()
        expect(self.page.locator("#importDraftBtn")).to_be_enabled()
        expect(self.page.locator("#error")).not_to_be_empty()
        self.assertEqual(self.snapshot(), self.baseline)

    def test_delayed_read_cannot_overwrite_new_note(self):
        self.begin_delayed(self.raw())
        self.page.locator("#note").fill("New work while file loads")
        before = self.snapshot()
        self.release()
        expect(self.page.locator("#importDraftBtn")).to_be_enabled()
        self.assertEqual(self.snapshot(), before)

    def test_delayed_read_cannot_repopulate_reset(self):
        self.begin_delayed(self.raw())
        self.page.locator("#resetBtn").click()
        before = self.snapshot()
        self.release()
        self.assertEqual(self.snapshot(), before)
        expect(self.page.locator("#importDraftBtn")).to_be_disabled()
        expect(self.page.locator("#exportBtn")).to_be_disabled()

    def test_delayed_invalid_read_cannot_mark_new_generation_failed(self):
        self.begin_delayed(self.raw().replace(b"SAVED_SENTINEL", b"\xff"))
        self.page.locator("#demoBtn").click()
        self.page.locator(".cell").first.click()
        self.page.locator("#note").fill("New generation wins")
        before = self.snapshot()
        self.release()
        self.assertEqual(self.snapshot(), before)
        expect(self.page.locator("#error")).to_be_empty()

    def test_delayed_success_cannot_cross_same_receipt_generation(self):
        self.begin_delayed(self.raw())
        self.page.locator("#demoBtn").click()
        self.page.locator(".cell").first.click()
        self.page.locator("#note").fill("Same receipt, newer generation")
        before = self.snapshot()
        self.release()
        self.assertEqual(self.snapshot(), before)


for name, invalid in (
    ("invalid_leading_byte", b"\xff"),
    ("isolated_continuation", b"\x80"),
    ("truncated_multibyte", b"\xe2\x82"),
    ("overlong_sequence", b"\xc0\xaf"),
    ("encoded_surrogate", b"\xed\xa0\x80"),
    ("above_unicode_maximum", b"\xf4\x90\x80\x80"),
):
    def run(self, invalid=invalid):
        self.assert_rejected(self.raw().replace(b"SAVED_SENTINEL", invalid), "UTF-8")
    setattr(SavedDraftEncodingTests, "test_" + name, run)


if __name__ == "__main__":
    unittest.main(verbosity=2)
