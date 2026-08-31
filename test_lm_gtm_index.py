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
MSP = (
    "msp-integris",
    "msp-5k-technical-services",
    "msp-transparity",
    "msp-scout-technology-guides",
    "msp-courant",
)
MSP_RECS = {
    "msp-integris": "airtable:recyxAWjUjrUY1Xln",
    "msp-5k-technical-services": "airtable:recsn64MYUCoASZfO",
    "msp-transparity": "airtable:recw9LCqVCI8wlzPE",
    "msp-scout-technology-guides": "airtable:recZYe6YoV5V8H0K7",
    "msp-courant": "airtable:recnC5TSQhiFB2trp",
}
LEADS = (
    "communitycare-katherine-reyes",
    "pitt-mark-henderson",
    "nutanix-thomas-cornely",
    "mrhd-david-gleiser",
    "sixty-vines-jeff-carcara",
    "ohio-university-rfp",
    "rhode-island-foundation",
    "golden-corral-lance-trenary",
    "pepsico-athina-kanioura",
    "cracker-barrel-david-deno",
)
PHONE_RE = idx.PHONE_RE
EMAIL_RE = idx.EMAIL_AT_RE


def _fork_index(directory: str) -> dict:
    dest = Path(directory)
    shutil.copytree(ROOT / "revenue" / "lm_gtm_index", dest / "revenue" / "lm_gtm_index")
    paths = dict(idx.default_paths(ROOT))
    paths["index"] = dest / "revenue" / "lm_gtm_index" / "INDEX.jsonl"
    paths["state"] = dest / "revenue" / "lm_gtm_index" / "state.json"
    paths["events"] = dest / "revenue" / "lm_gtm_index" / "events.jsonl"
    return paths


class LmGtmIndexTests(unittest.TestCase):
    def test_validate_matches_committed_projection(self) -> None:
        built = idx.validate_index()
        truth = built["state"]["truth"]
        self.assertEqual(truth["cash_usd"], 0)
        self.assertEqual(truth["transport_actions"], 0)
        self.assertEqual(truth["calls_booked"], 0)
        self.assertEqual(truth["mailbox"], "NEEDS_OWNER_MAILBOX")
        self.assertEqual(truth["live_next_actions"], 30)
        self.assertEqual(truth["hot_next_actions"], 12)
        self.assertEqual(truth["external_prospects"], 19)
        self.assertEqual(truth["inbound_contacts"], 11)
        self.assertEqual(truth["seller_context_rows"], 4)
        self.assertEqual(truth["overlay_events"], 16)
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
        self.assertIsNone(EMAIL_RE.search(blob))
        self.assertIsNone(PHONE_RE.search(blob))

    def test_seller_contacts_are_not_live_buyers(self) -> None:
        live_ids = {row["id"] for row in idx.live_next_actions()}
        hot_ids = {row["id"] for row in idx.hot_next_actions()}
        for name in SELLERS:
            self.assertNotIn(name, live_ids)
            self.assertNotIn(name, hot_ids)
        built = idx.build_index()
        by_id = {row["id"]: row for row in built["rows"]}
        for name in SELLERS:
            self.assertEqual(by_id[name]["role"], "seller_context")
            self.assertFalse(by_id[name]["live"])

    def test_research_universe_is_not_live_sales(self) -> None:
        live_ids = {row["id"] for row in idx.live_next_actions()}
        hot_ids = {row["id"] for row in idx.hot_next_actions()}
        self.assertNotIn("marketing-sales-research-universe", live_ids)
        self.assertNotIn("marketing-sales-research-universe", hot_ids)
        row = next(
            item
            for item in idx.build_index()["rows"]
            if item["id"] == "marketing-sales-research-universe"
        )
        self.assertEqual(row["decision"], "RESEARCH_UNIVERSE_NOT_LIVE_SALES")
        self.assertFalse(row["live"])

    def test_hot_ranking_and_exclusions(self) -> None:
        hot = idx.hot_next_actions()
        ids = [row["id"] for row in hot]
        classes = [row["hot_class"] for row in hot]
        self.assertEqual(ids[0], "city-of-billings-bid-1421")
        self.assertEqual(classes[0], "material_reply")
        self.assertIn("composio", ids)
        self.assertEqual(hot[ids.index("composio")]["hot_class"], "ready_to_draft")
        self.assertLess(ids.index("city-of-billings-bid-1421"), ids.index("composio"))
        self.assertLess(ids.index("composio"), ids.index("communitycare-katherine-reyes"))
        for lead in LEADS:
            self.assertIn(lead, ids)
            self.assertEqual(hot[ids.index(lead)]["hot_class"], "verified_lead_unsent")
        for name in MSP:
            self.assertNotIn(name, ids)
        self.assertNotIn("anythingllm-mintplex", ids)
        self.assertNotIn("metaforms", ids)
        self.assertNotIn("signoz", ids)
        self.assertNotIn("ava-example-test", ids)
        self.assertNotIn("marketing-sales-research-universe", ids)
        self.assertNotIn("swarm-mail-public-inboxes", ids)
        ranks = [row["hot_rank"] for row in hot]
        self.assertEqual(ranks, sorted(ranks))

    def test_billings_material_reply_visible_in_hot(self) -> None:
        built = idx.build_index()
        by_id = {row["id"]: row for row in built["rows"]}
        row = by_id["city-of-billings-bid-1421"]
        self.assertEqual(row["decision"], "MATERIAL_REPLY")
        self.assertEqual(row["role"], "inbound_contact")
        self.assertFalse(row["dnr"])
        self.assertIn("slack:C0BRGMDQB6G:1788143612.591889", row["source_paths"])
        self.assertIn("gmail:1a055a9913e5f6ec", row["source_paths"])
        self.assertIn("no bid submitted", row["next_action"].casefold())
        hot_ids = [item["id"] for item in idx.hot_next_actions()]
        self.assertEqual(hot_ids[0], "city-of-billings-bid-1421")

    def test_dnr_msp_sent_not_in_hot_and_cites_existing_crm(self) -> None:
        built = idx.build_index()
        by_id = {row["id"]: row for row in built["rows"]}
        hot_ids = {row["id"] for row in idx.hot_next_actions()}
        for name, rec in MSP_RECS.items():
            row = by_id[name]
            self.assertEqual(row["decision"], "SENT_AWAITING_REPLY")
            self.assertTrue(row["dnr"])
            self.assertEqual(row["route_kind"], "EXISTING_CRM_RECORD")
            self.assertEqual(row["route_ref"], rec)
            self.assertTrue(row["live"])
            self.assertNotIn(name, hot_ids)
            self.assertEqual(row["cash_usd"], 0)

    def test_leads_are_pointers_without_contact_book(self) -> None:
        built = idx.build_index()
        by_id = {row["id"]: row for row in built["rows"]}
        self.assertEqual(by_id["communitycare-katherine-reyes"]["person"], "Katherine T. Reyes")
        self.assertEqual(by_id["pitt-mark-henderson"]["person"], "Mark D. Henderson")
        self.assertEqual(by_id["ohio-university-rfp"]["person"], "Halie Best")
        for name in LEADS:
            row = by_id[name]
            self.assertEqual(row["decision"], "VERIFIED_LEAD_UNSENT")
            self.assertEqual(row["role"], "external_prospect")
            self.assertTrue(any(path.startswith("slack:C0BTURDA3PW:") for path in row["source_paths"]))
            self.assertEqual(row["source_ledgers"], ["lm_gtm_overlay"])

    def test_no_email_or_phone_in_index_blob(self) -> None:
        blob = idx.build_index()["blob"]
        self.assertIsNone(EMAIL_RE.search(blob))
        self.assertIsNone(PHONE_RE.search(blob))
        forbidden = (
            "execdir@",
            "jpereira@",
            "hbest@",
            "info@5ktech",
            "sales@integrisit",
            "(712)",
            "899-6631",
            "427-4052",
        )
        for token in forbidden:
            self.assertNotIn(token, blob)

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
        billings = idx.show_subject("city-of-billings-bid-1421")
        self.assertEqual(billings["index"]["decision"], "MATERIAL_REPLY")
        self.assertTrue(billings["overlay_events"])
        integris = idx.show_subject("msp-integris")
        self.assertEqual(integris["index"]["route_ref"], "airtable:recyxAWjUjrUY1Xln")

    def test_append_event_on_existing_id_without_minting_contacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = _fork_index(directory)
            dest = Path(directory)
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
            self.assertEqual(shown["overlay_events"][-1]["id"], "lm-gtm-index-note-20260831-99")
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

    def test_claim_fail_closed_without_steal_and_does_not_rewrite_loop(self) -> None:
        loop_before = LOOP.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            paths = _fork_index(directory)
            first = idx.claim_subject(
                subject_id="composio",
                owner="GROK",
                ts="2026-08-31T03:00:00Z",
                paths=paths,
            )
            self.assertEqual(first["status"], "occupied")
            shown = idx.show_subject("composio", paths)
            self.assertEqual(shown["index"]["owner"], "GROK")
            with self.assertRaises(idx.IndexError_):
                idx.claim_subject(
                    subject_id="composio",
                    owner="CLAUDE",
                    ts="2026-08-31T03:01:00Z",
                    paths=paths,
                )
            stolen = idx.claim_subject(
                subject_id="composio",
                owner="CLAUDE",
                steal=True,
                ts="2026-08-31T03:02:00Z",
                paths=paths,
            )
            self.assertEqual(stolen["event"]["type"], "STEAL")
            shown = idx.show_subject("composio", paths)
            self.assertEqual(shown["index"]["owner"], "CLAUDE")
            released = idx.release_subject(
                subject_id="composio",
                owner="CLAUDE",
                ts="2026-08-31T03:03:00Z",
                paths=paths,
            )
            self.assertEqual(released["status"], "released")
            shown = idx.show_subject("composio", paths)
            self.assertEqual(shown["index"]["owner"], "UNSEATED")
            with self.assertRaises(idx.IndexError_):
                idx.claim_subject(
                    subject_id="ava-example-test",
                    owner="GROK",
                    ts="2026-08-31T03:04:00Z",
                    paths=paths,
                )
        self.assertEqual(LOOP.read_bytes(), loop_before)

    def test_material_reply_reopens_dnr_into_hot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = _fork_index(directory)
            events = idx.load_jsonl(paths["events"])
            events.append(
                {
                    "schema_version": idx.SCHEMA_VERSION,
                    "kind": idx.KIND_EVENT,
                    "id": "lm-gtm-metaforms-reopen-20260831-01",
                    "subject_id": "metaforms",
                    "type": "MATERIAL_REPLY",
                    "ts": "2026-08-31T04:00:00Z",
                    "from": "UNSEATED",
                    "body": "synthetic reopen for ranking proof; no cash",
                    "organization": "Metaforms",
                    "role": "external_prospect",
                    "next_action": "material reply reopened this DNR into hot",
                    "source_paths": ["slack:C0BRGMDQB6G:1788140000.000000"],
                    "cash_usd": 0,
                    "transport": "NONE",
                }
            )
            idx.write_jsonl(paths["events"], events)
            idx.write_index(paths)
            hot_ids = [row["id"] for row in idx.hot_next_actions(paths)]
            self.assertEqual(hot_ids[0], "city-of-billings-bid-1421")
            self.assertIn("metaforms", hot_ids)
            self.assertLess(hot_ids.index("metaforms"), hot_ids.index("composio"))
            shown = idx.show_subject("metaforms", paths)
            self.assertEqual(shown["index"]["decision"], "MATERIAL_REPLY")
            self.assertFalse(shown["index"]["dnr"])

    def test_does_not_rewrite_loop_schema_v2(self) -> None:
        loop = json.loads(LOOP.read_text(encoding="utf-8"))
        self.assertEqual(loop["schema_version"], "commons-website-people-email-book/v2")
        self.assertEqual({row["prospect_id"] for row in loop["prospects"]}, set(NAMED))

    def test_no_second_crm_roots_on_repo(self) -> None:
        for name in ("crm", "people", "contacts", "sales"):
            self.assertFalse((ROOT / name).exists(), name)

    def test_v1_receipt_not_reminted(self) -> None:
        receipt = ROOT / "p" / "lm-gtm-index-20260831-01.md"
        self.assertTrue(receipt.is_file())
        self.assertIn("id: lm-gtm-index-20260831-01", receipt.read_text(encoding="utf-8"))

    def test_send_exits_3(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(HOST), "hot", "--send"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 3)
        self.assertIn("never transports mail", proc.stderr.casefold())
        self.assertEqual(proc.stdout.strip(), "")

    def test_cli_validate_hot_and_next_are_deterministic(self) -> None:
        command = [sys.executable, str(HOST), "validate"]
        first = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True).stdout
        second = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True).stdout
        self.assertEqual(first, second)
        self.assertIn("USD 0 cash", first)
        self.assertIn("12 hot", first)
        nxt = subprocess.run(
            [sys.executable, str(HOST), "next"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        ids = [json.loads(line)["id"] for line in nxt.splitlines() if line.strip()]
        self.assertIn("anythingllm-mintplex", ids)
        self.assertIn("composio", ids)
        self.assertIn("msp-integris", ids)
        self.assertNotIn("ava-example-test", ids)
        hot = subprocess.run(
            [sys.executable, str(HOST), "hot"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        hot_ids = [json.loads(line)["id"] for line in hot.splitlines() if line.strip()]
        self.assertEqual(hot_ids[0], "city-of-billings-bid-1421")
        self.assertNotIn("msp-integris", hot_ids)
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
