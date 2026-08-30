#!/usr/bin/env python3
"""Unbuilt-items surface: claimed_paths vs current main. Slack CLAIMED is not a land."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))
import unbuilt_items as ui  # noqa: E402


SHA = "b" * 40


class UnbuiltItemsContract(unittest.TestCase):
    def test_self_and_seed(self):
        self.assertEqual(ui.self_test(), 0)
        catalog = ui.load_json(ui._read(ROOT, ui.SEED_REL))
        self.assertNotIn("error", catalog)
        self.assertEqual(ui.validate_catalog(catalog), [])
        ids = [item["id"] for item in catalog["items"]]
        self.assertIn(ui.CLAUDE_LEFTOVER_ID, ids)
        for ident in ui.ALIAS_IDS:
            self.assertIn(ident, ids)

    def test_current_tree_keeps_named_leftover_unbuilt(self):
        out = ui.measure_tree(ROOT, SHA)
        self.assertEqual(out.get("problems"), [])
        by_id = {row["id"]: row for row in out["items"]}
        leftover = by_id[ui.CLAUDE_LEFTOVER_ID]
        self.assertEqual(leftover["status"], "UNBUILT")
        self.assertEqual(leftover["claimed_paths"], [])
        self.assertEqual(leftover["receipt_hits"], [])
        for ident in ui.ALIAS_IDS:
            row = by_id[ident]
            self.assertEqual(row["status"], "OPEN_ALIAS", ident)
            self.assertTrue(row["stay_unclosed"], ident)
            self.assertTrue(row["missing"], ident)
            self.assertFalse(os.path.isfile(os.path.join(ROOT, row["claimed_paths"][0])))

    def test_chat_and_slack_never_close(self):
        catalog = ui.load_json(ui._read(ROOT, ui.SEED_REL))
        item = [row for row in catalog["items"] if row["id"] == ui.CLAUDE_LEFTOVER_ID][0]
        snap = {
            "main_sha": SHA,
            "chat_said_done": True,
            "slack_claimed": True,
            "slack_text": "CLAIMED",
            "ntfy_200": True,
            "open_prs": [5529],
            "pages_bake": True,
        }
        row = ui.reconcile_item(item, ROOT, snap)
        self.assertTrue(row["chat_ignored"])
        self.assertEqual(row["status"], "UNBUILT")

    def test_alias_stays_open_even_if_receipt_appears(self):
        tmp = tempfile.mkdtemp(prefix="unbuilt-alias-")
        receipt = os.path.join(tmp, "p", "kimi-settled-facts-20260829-01.md")
        os.makedirs(os.path.dirname(receipt), exist_ok=True)
        with open(receipt, "w", encoding="utf-8") as handle:
            handle.write("from: KIMI\nid: kimi-settled-facts-20260829-01\n\n---\n\nfixture\n")
        item = {
            "id": "kimi-settled-facts-20260829-01",
            "title": "kimi settled facts projector alias",
            "kind": "OPEN_ALIAS",
            "claimed_paths": ["p/kimi-settled-facts-20260829-01.md"],
            "stay_unclosed": True,
        }
        row = ui.reconcile_item(item, tmp, {"main_sha": SHA})
        self.assertEqual(row["status"], "OPEN_ALIAS")
        self.assertEqual(row["present"], ["p/kimi-settled-facts-20260829-01.md"])

    def test_receipt_glob_can_land_only_the_named_leftover(self):
        tmp = tempfile.mkdtemp(prefix="unbuilt-claude-")
        os.makedirs(os.path.join(tmp, "p"), exist_ok=True)
        with open(os.path.join(tmp, "p", "claude-unbuilt-item-named-20260830-01.md"), "w", encoding="utf-8") as handle:
            handle.write("from: CLAUDE\nid: claude-unbuilt-item-named-20260830-01\n\n---\n\nnames\n")
        item = {
            "id": ui.CLAUDE_LEFTOVER_ID,
            "title": "Claude-derived unbuilt-item post is not surfaced",
            "kind": "NAMED_LEFTOVER",
            "claimed_paths": [],
            "receipt_glob": "p/claude*unbuilt*.md",
            "stay_unclosed_until_receipt": True,
        }
        row = ui.reconcile_item(item, tmp, {"main_sha": SHA})
        self.assertEqual(row["status"], "LANDED")
        self.assertEqual(row["receipt_hits"], ["p/claude-unbuilt-item-named-20260830-01.md"])

    def test_page_is_open_and_names_the_leftover(self):
        with open(os.path.join(ROOT, "unbuilt-items.html"), encoding="utf-8") as handle:
            page = handle.read()
        self.assertIn("Claude-derived unbuilt-item post is not surfaced", page)
        self.assertIn("No login", page)
        self.assertIn('src="./session.js?v=20260824a"', page)
        self.assertIn('href="./index.html"', page)
        self.assertIn("OPEN_ALIAS", page)
        self.assertNotIn("login required", page.lower())
        self.assertNotIn("$2.5M", page)
        for ident in ui.ALIAS_IDS:
            self.assertIn(ident, page)

    def test_directory_claimed_path_counts_as_present(self):
        tmp = tempfile.mkdtemp(prefix="unbuilt-dir-")
        os.makedirs(os.path.join(tmp, "builds", "records"), exist_ok=True)
        item = {
            "id": "demo-dir-path-20260830-01",
            "title": "demo directory claimed path",
            "kind": "BUILDABLE",
            "claimed_paths": ["builds/records"],
        }
        row = ui.reconcile_item(item, tmp, {"main_sha": SHA})
        self.assertEqual(row["status"], "LANDED")
        self.assertEqual(row["present"], ["builds/records"])

    def test_write_projection_and_harvest(self):
        tmp = tempfile.mkdtemp(prefix="unbuilt-write-")
        os.makedirs(os.path.join(tmp, "ground"), exist_ok=True)
        os.makedirs(os.path.join(tmp, "features", "registry"), exist_ok=True)
        os.makedirs(os.path.join(tmp, "p"), exist_ok=True)
        seed = json.loads(ui._read(ROOT, ui.SEED_REL))
        with open(os.path.join(tmp, ui.SEED_REL), "w", encoding="utf-8") as handle:
            json.dump(seed, handle)
        with open(os.path.join(tmp, ui.CURRENT_WORK_REL), "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "items": [
                        {
                            "id": "harvest-missing-path-20260830-01",
                            "title": "harvest missing path",
                            "from": "TEST",
                            "claimed_paths": ["no/such/claimed/path.md"],
                        }
                    ]
                },
                handle,
            )
        out = ui.write_projection(tmp, SHA)
        self.assertTrue(os.path.isfile(os.path.join(tmp, ui.JSON_OUT)))
        harvested = [row for row in out["items"] if row["id"] == "harvest-missing-path-20260830-01"]
        self.assertEqual(len(harvested), 1)
        self.assertEqual(harvested[0]["status"], "UNBUILT")
        self.assertEqual(harvested[0]["missing"], ["no/such/claimed/path.md"])

    def test_no_auth_words_in_instrument(self):
        with open(os.path.join(ROOT, "host", "unbuilt_items.py"), encoding="utf-8") as handle:
            src = handle.read()
        with open(os.path.join(ROOT, "unbuilt-items.html"), encoding="utf-8") as handle:
            page = handle.read()
        for blob in (src, page):
            self.assertNotIn("authorization required", blob.lower())
            self.assertNotIn("permission denied", blob.lower())


if __name__ == "__main__":
    unittest.main()
