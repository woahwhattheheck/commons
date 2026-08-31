from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
HOST = ROOT / "host" / "lm_gtm_index.py"
SPEC = importlib.util.spec_from_file_location("lm_gtm_index", HOST)
assert SPEC and SPEC.loader
idx = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(idx)

LOOP = ROOT / "revenue" / "website_people_email_book" / "loop.json"
NAMED = ("composio", "signoz", "metaforms", "anythingllm-mintplex")
SELLERS = ("ava-example-test", "noah-example-test", "riley-quiet", "sam-example-test")


class LmGtmIndexTests(unittest.TestCase):
    def test_validate_matches_committed_projection(self) -> None:
        built = idx.validate_index()
        truth = built["state"]["truth"]
        self.assertEqual(truth["cash_usd"], 0)
        self.assertEqual(truth["transport_actions"], 0)
        self.assertEqual(truth["calls_booked"], 0)
        self.assertEqual(truth["mailbox"], "NEEDS_OWNER_MAILBOX")
        self.assertEqual(truth["live_next_actions"], 14)
        self.assertEqual(truth["external_prospects"], 4)
        self.assertEqual(truth["seller_context_rows"], 4)
        self.assertEqual(truth["research_entities_not_live"], 1000)
        self.assertTrue(built["state"]["public_projection_is_not_crm"])
        self.assertEqual(
            built["state"]["canonical_crm"],
            "JOJO Revenue Recovery CRM / Revenue Pipeline",
        )

    def test_named_prospects_are_references_not_a_new_book(self) -> None:
        built = idx.build_index()
        by_id = {row["id"]: row for row in built["rows"]}
        for name in NAMED:
            self.assertIn(name, by_id)
            self.assertTrue(by_id[name]["live"])
            self.assertEqual(by_id[name]["role"], "external_prospect")
            self.assertEqual(by_id[name]["cash_usd"], 0)
        self.assertEqual(by_id["composio"]["decision"], "READY_TO_DRAFT")
        self.assertEqual(by_id["signoz"]["decision"], "RESEARCH_REQUIRED")
        self.assertEqual(by_id["metaforms"]["route_kind"], "EXISTING_CRM_RECORD")
        self.assertEqual(by_id["metaforms"]["route_ref"], "airtable:recWHbHxQoQfGhS0q")
        self.assertTrue(by_id["metaforms"]["dnr"])
        self.assertTrue(by_id["anythingllm-mintplex"]["dnr"])
        self.assertNotIn("github:bytedance", by_id)
        blob = built["blob"]
        self.assertNotRegex(blob, r"[^@\s]+@[^@\s]+\.[^@\s]+")

    def test_seller_contacts_are_not_live_buyers(self) -> None:
        live_ids = {row["id"] for row in idx.live_next_actions()}
        for name in SELLERS:
            self.assertNotIn(name, live_ids)
        built = idx.build_index()
        by_id = {row["id"]: row for row in built["rows"]}
        for name in SELLERS:
            self.assertEqual(by_id[name]["role"], "seller_context")
            self.assertFalse(by_id[name]["live"])

    def test_research_universe_is_not_live_sales(self) -> None:
        live_ids = {row["id"] for row in idx.live_next_actions()}
        self.assertNotIn("marketing-sales-research-universe", live_ids)
        row = next(
            item
            for item in idx.build_index()["rows"]
            if item["id"] == "marketing-sales-research-universe"
        )
        self.assertEqual(row["decision"], "RESEARCH_UNIVERSE_NOT_LIVE_SALES")
        self.assertFalse(row["live"])

    def test_show_hydrates_existing_ledgers(self) -> None:
        composio = idx.show_subject("composio")
        self.assertEqual(composio["index"]["id"], "composio")
        self.assertEqual(
            composio["sources"]["website_people_email_book"]["prospect_id"], "composio"
        )
        self.assertEqual(composio["sources"]["smart_outreach"]["prospect_id"], "composio")
        self.assertEqual(
            composio["sources"]["website_people_email_book_emails"][0]["transport"],
            "STAGED_NOT_SENT",
        )
        metaforms = idx.show_subject("metaforms")
        self.assertEqual(metaforms["index"]["route_ref"], "airtable:recWHbHxQoQfGhS0q")
        self.assertEqual(
            metaforms["sources"]["website_people_email_book"]["route"]["kind"],
            "EXISTING_CRM_RECORD",
        )
        signoz = idx.show_subject("signoz")
        self.assertEqual(signoz["index"]["decision"], "RESEARCH_REQUIRED")
        mintplex = idx.show_subject("anythingllm-mintplex")
        self.assertTrue(mintplex["index"]["dnr"])
        self.assertTrue(mintplex["sources"]["outreach_receipts"])

    def test_append_event_on_existing_id_without_minting_contacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory)
            shutil.copytree(ROOT / "revenue" / "lm_gtm_index", dest / "revenue" / "lm_gtm_index")
            paths = idx.default_paths(ROOT)
            paths = dict(paths)
            paths["index"] = dest / "revenue" / "lm_gtm_index" / "INDEX.jsonl"
            paths["state"] = dest / "revenue" / "lm_gtm_index" / "state.json"
            paths["events"] = dest / "revenue" / "lm_gtm_index" / "events.jsonl"
            result = idx.append_event(
                subject_id="composio",
                event_id="lm-gtm-index-note-20260831-99",
                body="draft remains STAGED_NOT_SENT; overlay only",
                ts="2026-08-31T01:20:00Z",
                paths=paths,
            )
            self.assertEqual(result["event"]["subject_id"], "composio")
            self.assertEqual(result["event"]["cash_usd"], 0)
            self.assertEqual(result["event"]["transport"], "NONE")
            shown = idx.show_subject("composio", paths)
            self.assertEqual(
                shown["overlay_events"][0]["id"], "lm-gtm-index-note-20260831-99"
            )
            self.assertFalse((dest / "crm").exists())
            self.assertFalse((dest / "people").exists())
            self.assertFalse((dest / "contacts").exists())
            self.assertFalse((dest / "sales").exists())
            with self.assertRaises(idx.IndexError_):
                idx.append_event(
                    subject_id="composio",
                    event_id="lm-gtm-index-note-20260831-99",
                    body="remint",
                    paths=paths,
                )
            with self.assertRaises(idx.IndexError_):
                idx.append_event(
                    subject_id="brand-new-buyer",
                    event_id="lm-gtm-index-note-20260831-98",
                    body="would mint a book",
                    paths=paths,
                )
            with self.assertRaises(idx.IndexError_):
                idx.append_event(
                    subject_id="ava-example-test",
                    event_id="lm-gtm-index-note-20260831-97",
                    body="seller is not a prospect",
                    paths=paths,
                )

    def test_does_not_rewrite_loop_schema_v2(self) -> None:
        loop = json.loads(LOOP.read_text(encoding="utf-8"))
        self.assertEqual(loop["schema_version"], "commons-website-people-email-book/v2")
        self.assertEqual({row["prospect_id"] for row in loop["prospects"]}, set(NAMED))

    def test_no_second_crm_roots_on_repo(self) -> None:
        for name in ("crm", "people", "contacts", "sales"):
            self.assertFalse((ROOT / name).exists(), name)

    def test_send_exits_3(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(HOST), "next", "--send"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 3)
        self.assertIn("never transports mail", proc.stderr.casefold())
        self.assertEqual(proc.stdout.strip(), "")

    def test_cli_validate_and_next_are_deterministic(self) -> None:
        command = [sys.executable, str(HOST), "validate"]
        first = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True).stdout
        second = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True).stdout
        self.assertEqual(first, second)
        self.assertIn("USD 0 cash", first)
        nxt = subprocess.run(
            [sys.executable, str(HOST), "next"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        ids = [json.loads(line)["id"] for line in nxt.splitlines() if line.strip()]
        self.assertEqual(
            ids[:4],
            ["anythingllm-mintplex", "composio", "metaforms", "signoz"],
        )
        self.assertNotIn("ava-example-test", ids)
        show = subprocess.run(
            [sys.executable, str(HOST), "show", "metaforms"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        parsed = json.loads(show)
        self.assertEqual(parsed["index"]["route_ref"], "airtable:recWHbHxQoQfGhS0q")


if __name__ == "__main__":
    unittest.main()
