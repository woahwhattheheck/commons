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
MSP_EVENT_IDS = (
    "lm-gtm-msp-integris-sent-20260830-01",
    "lm-gtm-msp-5k-sent-20260830-01",
    "lm-gtm-msp-transparity-sent-20260830-01",
    "lm-gtm-msp-scout-sent-20260830-01",
    "lm-gtm-msp-courant-sent-20260830-01",
)
FUSE = (
    "fuse-jovie-tim-white",
    "fuse-avantstay-andrei-patseev",
    "fuse-odderon-phi-charles",
    "fuse-immense-de-waal-immelman",
    "fuse-halo-ai-vito-strokov",
)
FUSE_RECS = {
    "fuse-jovie-tim-white": "airtable:recBHZw2VsWWmALcR",
    "fuse-avantstay-andrei-patseev": "airtable:recQL3RMLwizE6kgZ",
    "fuse-odderon-phi-charles": "airtable:recIo5cgbxL96aQSn",
    "fuse-immense-de-waal-immelman": "airtable:rec6SOShVG2fgZQi0",
    "fuse-halo-ai-vito-strokov": "airtable:recIIo5M0lfUlYBXV",
}
HOLD_BUILD = (
    "sara-shannon-tollison",
    "rmb-robert-borash",
    "denton-marcos-diosdado",
    "preinnewhof-steve-bylsma",
    "eagle-ross-caputo",
    "pcl-ryan-ott",
    "canyon-wendy-mach",
    "ace-qat-erick-sharp",
    "sgspsi-kyle-copeland",
    "csanalytical-brandon-zurawlow",
)
HOLD_PRODUCT = {
    "rmb-robert-borash": "rmb-crosssite-courier-accession-lims-01",
    "preinnewhof-steve-bylsma": "preinnewhof-pfas-fieldblank-gate-lims-01",
    "pcl-ryan-ott": "pcl-scope-sla-routing-lims-01",
    "canyon-wendy-mach": "canyon-multisite-regulated-intake-lims-01",
    "ace-qat-erick-sharp": "ace-qat-thermal-rheology-capacity-lims-01",
    "sgspsi-kyle-copeland": "sgspsi-high-throughput-thermal-rheology-lineage-lims-01",
    "csanalytical-brandon-zurawlow": "csanalytical-expansion-crossline-evidence-lims-01",
}
BILLINGS_POINTER = "lm-gtm-billings-material-reply-20260831-01"
BILLINGS_FLOOR_STATUS = "lm-gtm-billings-floor-status-20260831-01"
BILLINGS_RUNNER_STATUS = "lm-gtm-billings-runner-status-20260831-01"
BRIEF_KEYS = {
    "id",
    "lane",
    "organization",
    "person",
    "decision",
    "next_action",
    "dnr",
    "owner",
    "due",
    "route_ref",
    "source",
}
SENT_DNR = MSP + FUSE
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
        self.assertEqual(truth["live_next_actions"], 45)
        self.assertEqual(truth["hot_next_actions"], 12)
        self.assertEqual(truth["hold_build_actions"], 10)
        self.assertEqual(truth["sent_awaiting_dnr_actions"], 10)
        self.assertEqual(truth["external_prospects"], 34)
        self.assertEqual(truth["inbound_contacts"], 11)
        self.assertEqual(truth["seller_context_rows"], 4)
        self.assertEqual(truth["overlay_events"], 35)
        self.assertEqual(truth["index_rows"], 51)
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
        self.assertNotIn("dexmate", ids)
        self.assertNotIn("nextdata", ids)
        self.assertNotIn("ava-example-test", ids)
        self.assertNotIn("marketing-sales-research-universe", ids)
        self.assertNotIn("swarm-mail-public-inboxes", ids)
        for name in FUSE:
            self.assertNotIn(name, ids)
        for name in HOLD_BUILD:
            self.assertNotIn(name, ids)
        ranks = [row["hot_rank"] for row in hot]
        self.assertEqual(ranks, sorted(ranks))

    def test_billings_material_reply_visible_in_hot(self) -> None:
        built = idx.build_index()
        by_id = {row["id"]: row for row in built["rows"]}
        row = by_id["city-of-billings-bid-1421"]
        self.assertEqual(row["decision"], "MATERIAL_REPLY")
        self.assertEqual(row["role"], "inbound_contact")
        self.assertFalse(row["dnr"])
        self.assertEqual(row["due"], "2026-09-28")
        self.assertIn("slack:C0BRGMDQB6G:1788143612.591889", row["source_paths"])
        self.assertIn("gmail:1a055a9913e5f6ec", row["source_paths"])
        self.assertIn("slack:C0BRGMDQB6G:1788146673.583549", row["source_paths"])
        self.assertIn("slack:C0BRGMDQB6G:1788147874.618849", row["source_paths"])
        self.assertIn("p/billings-bid-1421-partner-recon-20260831-01.md", row["source_paths"])
        next_action = row["next_action"].casefold()
        self.assertIn("no bid submitted", next_action)
        self.assertIn("hold / no submission", next_action)
        self.assertIn("addenda", next_action)
        self.assertIn("production runners in flight", next_action)
        self.assertIn("no city contact", next_action)
        self.assertIn("award target 2026-09-28", next_action)
        self.assertIn(BILLINGS_POINTER, row["overlay_event_ids"])
        self.assertIn(BILLINGS_FLOOR_STATUS, row["overlay_event_ids"])
        self.assertIn(BILLINGS_RUNNER_STATUS, row["overlay_event_ids"])
        self.assertNotEqual(BILLINGS_POINTER, BILLINGS_FLOOR_STATUS)
        self.assertNotEqual(BILLINGS_POINTER, BILLINGS_RUNNER_STATUS)
        self.assertNotEqual(BILLINGS_FLOOR_STATUS, BILLINGS_RUNNER_STATUS)
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

    def test_fuse_hands_five_not_in_hot_and_cites_recs(self) -> None:
        built = idx.build_index()
        by_id = {row["id"]: row for row in built["rows"]}
        hot_ids = {row["id"] for row in idx.hot_next_actions()}
        event_ids = {event["id"] for event in built["events"]}
        for name in MSP_EVENT_IDS:
            self.assertIn(name, event_ids)
        self.assertIn(BILLINGS_POINTER, event_ids)
        for name, rec in FUSE_RECS.items():
            row = by_id[name]
            self.assertEqual(row["decision"], "SENT_AWAITING_REPLY")
            self.assertTrue(row["dnr"])
            self.assertEqual(row["route_kind"], "EXISTING_CRM_RECORD")
            self.assertEqual(row["route_ref"], rec)
            self.assertTrue(row["live"])
            self.assertNotIn(name, hot_ids)
            self.assertEqual(row["cash_usd"], 0)
            self.assertTrue(any(path.startswith("gmail:") for path in row["source_paths"]))
            self.assertTrue(any(path.startswith("github:") for path in row["source_paths"]))
            self.assertIn("slack:C0BRGMDQB6G:1788150461.695739", row["source_paths"])
        self.assertEqual(by_id["fuse-jovie-tim-white"]["person"], "Tim White")
        self.assertEqual(by_id["fuse-halo-ai-vito-strokov"]["organization"], "Halo AI")

    def test_hold_build_not_in_hot(self) -> None:
        built = idx.build_index()
        by_id = {row["id"]: row for row in built["rows"]}
        hot_ids = {row["id"] for row in idx.hot_next_actions()}
        hold_ids = [row["id"] for row in idx.hold_build_next_actions()]
        self.assertEqual(sorted(hold_ids), sorted(HOLD_BUILD))
        for name in HOLD_BUILD:
            row = by_id[name]
            self.assertEqual(row["decision"], "HOLD_BUILD_AND_VERIFY")
            self.assertTrue(row["live"])
            self.assertFalse(row["dnr"])
            self.assertNotIn(name, hot_ids)
            self.assertEqual(row["source_ledgers"], ["lm_gtm_overlay"])
            self.assertTrue(any(path.startswith("slack:C0BTURDA3PW:") for path in row["source_paths"]))
            self.assertIn("PRE-SALE TRANSPORT NONE", row["next_action"])
            self.assertNotIn("mailto:", json.dumps(row))
        for name, demand in HOLD_PRODUCT.items():
            row = by_id[name]
            self.assertIn(demand, row["next_action"])
            self.assertTrue(any(path.endswith(".py") for path in row["source_paths"]))
            self.assertTrue(any(path.startswith("p/") and path.endswith(".md") for path in row["source_paths"]))
        self.assertEqual(by_id["sara-shannon-tollison"]["person"], "Shannon Tollison")
        self.assertEqual(by_id["eagle-ross-caputo"]["person"], "Ross A. Caputo")

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
            "halo.live",
            "support@",
            "tim@jov",
            "apatseev@",
        )
        for token in forbidden:
            self.assertNotIn(token, blob)

    def test_show_hydrates_existing_ledgers(self) -> None:
        composio = idx.show_subject("composio", sources=True)
        self.assertEqual(composio["index"]["id"], "composio")
        self.assertEqual(
            composio["sources"]["website_people_email_book"]["prospect_id"], "composio"
        )
        self.assertEqual(composio["sources"]["smart_outreach"]["prospect_id"], "composio")
        self.assertEqual(
            composio["sources"]["website_people_email_book_emails"][0]["transport"],
            "STAGED_NOT_SENT",
        )
        metaforms = idx.show_subject("metaforms", sources=True)
        self.assertEqual(metaforms["index"]["route_ref"], "airtable:recWHbHxQoQfGhS0q")
        self.assertEqual(
            metaforms["sources"]["website_people_email_book"]["route"]["kind"],
            "EXISTING_CRM_RECORD",
        )
        signoz = idx.show_subject("signoz", sources=True)
        self.assertEqual(signoz["index"]["decision"], "RESEARCH_REQUIRED")
        mintplex = idx.show_subject("anythingllm-mintplex", sources=True)
        self.assertTrue(mintplex["index"]["dnr"])
        self.assertTrue(mintplex["sources"]["outreach_receipts"])
        billings = idx.show_subject("city-of-billings-bid-1421", sources=True)
        self.assertEqual(billings["index"]["decision"], "MATERIAL_REPLY")
        self.assertTrue(billings["overlay_events"])
        integris = idx.show_subject("msp-integris", sources=True)
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
            shown = idx.show_subject("composio", paths, sources=True)
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
            shown = idx.show_subject("composio", paths, sources=True)
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
            shown = idx.show_subject("composio", paths, sources=True)
            self.assertEqual(shown["index"]["owner"], "CLAUDE")
            released = idx.release_subject(
                subject_id="composio",
                owner="CLAUDE",
                ts="2026-08-31T03:03:00Z",
                paths=paths,
            )
            self.assertEqual(released["status"], "released")
            shown = idx.show_subject("composio", paths, sources=True)
            self.assertEqual(shown["index"]["owner"], "UNSEATED")
            with self.assertRaises(idx.IndexError_):
                idx.claim_subject(
                    subject_id="ava-example-test",
                    owner="GROK",
                    ts="2026-08-31T03:04:00Z",
                    paths=paths,
                )
        self.assertEqual(LOOP.read_bytes(), loop_before)

    def test_cli_claim_accepts_positional_subject_and_requires_owner(self) -> None:
        parser = idx.build_parser()
        positional = parser.parse_args(["claim", "composio", "--owner", "GROK"])
        self.assertEqual(idx.occupancy_subject(positional), "composio")
        self.assertEqual(positional.owner, "GROK")
        flagged = parser.parse_args(["claim", "--subject", "composio", "--owner", "GROK"])
        self.assertEqual(idx.occupancy_subject(flagged), "composio")
        both = parser.parse_args(["claim", "composio", "--subject", "composio", "--owner", "GROK"])
        self.assertEqual(idx.occupancy_subject(both), "composio")
        with self.assertRaises(idx.IndexError_):
            mixed = parser.parse_args(["claim", "composio", "--subject", "signoz", "--owner", "GROK"])
            idx.occupancy_subject(mixed)
        with self.assertRaises(idx.IndexError_):
            idx.occupancy_subject(parser.parse_args(["claim", "--owner", "GROK"]))
        missing_owner = subprocess.run(
            [sys.executable, str(HOST), "claim", "composio"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(missing_owner.returncode, 0)
        self.assertIn("--owner", (missing_owner.stderr + missing_owner.stdout).casefold())
        missing_subject = subprocess.run(
            [sys.executable, str(HOST), "claim", "--owner", "GROK"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(missing_subject.returncode, 1)
        self.assertIn("subject", missing_subject.stderr.casefold())
        release_pos = parser.parse_args(["release", "composio", "--owner", "GROK"])
        self.assertEqual(idx.occupancy_subject(release_pos), "composio")

    def test_status_cannot_mint_a_contact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = _fork_index(directory)
            events = idx.load_jsonl(paths["events"])
            events.append(
                {
                    "schema_version": idx.SCHEMA_VERSION,
                    "kind": idx.KIND_EVENT,
                    "id": "lm-gtm-status-mint-refuse-20260831-01",
                    "subject_id": "brand-new-status-buyer",
                    "type": "STATUS",
                    "ts": "2026-08-31T05:00:00Z",
                    "from": "UNSEATED",
                    "body": "STATUS cannot mint a contact",
                    "next_action": "should not land",
                    "source_paths": ["slack:C0BRGMDQB6G:1788140000.000001"],
                    "cash_usd": 0,
                    "transport": "NONE",
                }
            )
            idx.write_jsonl(paths["events"], events)
            with self.assertRaises(idx.IndexError_):
                idx.write_index(paths)

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
            shown = idx.show_subject("metaforms", paths, sources=True)
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

    def test_hot_lane_receipt_not_reminted(self) -> None:
        receipt = ROOT / "p" / "lm-gtm-hot-lane-20260831-01.md"
        self.assertTrue(receipt.is_file())
        self.assertIn("id: lm-gtm-hot-lane-20260831-01", receipt.read_text(encoding="utf-8"))
        self.assertNotIn("id: lm-gtm-floor-sync-20260831-01", receipt.read_text(encoding="utf-8"))

    def test_floor_sync_receipt_not_reminted(self) -> None:
        receipt = ROOT / "p" / "lm-gtm-floor-sync-20260831-01.md"
        self.assertTrue(receipt.is_file())
        self.assertIn("id: lm-gtm-floor-sync-20260831-01", receipt.read_text(encoding="utf-8"))

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
        self.assertNotIn("fuse-jovie-tim-white", hot_ids)
        self.assertNotIn("sara-shannon-tollison", hot_ids)
        hold = subprocess.run(
            [sys.executable, str(HOST), "hold"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        hold_ids = [json.loads(line)["id"] for line in hold.splitlines() if line.strip()]
        self.assertEqual(sorted(hold_ids), sorted(HOLD_BUILD))
        show = subprocess.run(
            [sys.executable, str(HOST), "show", "metaforms"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        parsed = json.loads(show)
        self.assertEqual(parsed["route_ref"], "airtable:recWHbHxQoQfGhS0q")
        self.assertNotIn("sources", parsed)
        self.assertNotIn("schema_version", parsed)
        self.assertIsNone(EMAIL_RE.search(show))
        self.assertIsNone(PHONE_RE.search(show))
        hydrated = subprocess.run(
            [sys.executable, str(HOST), "show", "composio", "--sources"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        hydrated_obj = json.loads(hydrated)
        self.assertEqual(
            hydrated_obj["sources"]["website_people_email_book_emails"][0]["transport"],
            "STAGED_NOT_SENT",
        )

    def test_brief_is_compact_hot_without_extra_keys_or_pii(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(HOST), "brief"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        lines = [line for line in proc.stdout.splitlines() if line.strip()]
        header = json.loads(lines[0])
        self.assertEqual(
            set(header),
            {"hot", "hold", "sent_dnr", "cash_usd", "canonical_crm"},
        )
        self.assertEqual(header["hot"], 12)
        self.assertEqual(header["hold"], 10)
        self.assertEqual(header["sent_dnr"], 10)
        self.assertEqual(header["cash_usd"], 0)
        self.assertEqual(header["canonical_crm"], "JOJO Revenue Recovery CRM / Revenue Pipeline")
        rows = [json.loads(line) for line in lines[1:]]
        self.assertEqual(len(rows), 12)
        self.assertEqual(rows[0]["id"], "city-of-billings-bid-1421")
        self.assertEqual(rows[0]["lane"], "material_reply")
        self.assertEqual(rows[0]["decision"], "MATERIAL_REPLY")
        self.assertIn("hold / no submission", rows[0]["next_action"].casefold())
        self.assertIn("production runners in flight", rows[0]["next_action"].casefold())
        for row in rows:
            extra = set(row) - BRIEF_KEYS
            self.assertFalse(extra, extra)
            self.assertNotIn("schema_version", row)
            self.assertNotIn("kind", row)
            self.assertNotIn("overlay_event_ids", row)
            self.assertNotIn("cash_usd", row)
            self.assertNotIn("source_ledgers", row)
            self.assertTrue(all(value is not None for value in row.values()))
            blob = json.dumps(row)
            self.assertIsNone(EMAIL_RE.search(blob))
            self.assertIsNone(PHONE_RE.search(blob))
            self.assertNotIn("mailto:", blob)
        hot_ids = [row["id"] for row in idx.hot_next_actions()]
        self.assertEqual([row["id"] for row in rows], hot_ids)
        for name in SENT_DNR + HOLD_BUILD:
            self.assertNotIn(name, [row["id"] for row in rows])
        self.assertIn("list_brief", idx.build_index()["state"]["contract"])
        self.assertIn("list_sent", idx.build_index()["state"]["contract"])
        self.assertEqual(
            idx.build_index()["state"]["contract"]["list_brief"],
            "python3 host/lm_gtm_index.py brief",
        )
        blob = proc.stdout
        self.assertIsNone(EMAIL_RE.search(blob))
        self.assertIsNone(PHONE_RE.search(blob))
        for token in ("execdir@", "jpereira@", "hbest@", "info@5ktech", "sales@integrisit", "halo.live", "support@", "tim@jov"):
            self.assertNotIn(token, blob)

    def test_sent_lists_all_dnr_and_none_are_hot(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(HOST), "sent"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        rows = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
        ids = [row["id"] for row in rows]
        self.assertEqual(sorted(ids), sorted(SENT_DNR))
        self.assertEqual(len(ids), 10)
        hot_ids = {row["id"] for row in idx.hot_next_actions()}
        for row in rows:
            extra = set(row) - BRIEF_KEYS
            self.assertFalse(extra, extra)
            self.assertEqual(row["lane"], "sent_dnr")
            self.assertEqual(row["decision"], "SENT_AWAITING_REPLY")
            self.assertTrue(row["dnr"])
            self.assertNotIn(row["id"], hot_ids)
            self.assertTrue(str(row.get("route_ref") or "").startswith("airtable:rec"))
            blob = json.dumps(row)
            self.assertIsNone(EMAIL_RE.search(blob))
            self.assertIsNone(PHONE_RE.search(blob))
        self.assertIsNone(EMAIL_RE.search(proc.stdout))
        self.assertIsNone(PHONE_RE.search(proc.stdout))

    def test_hold_product_pointers_cite_demand_ids_without_pii(self) -> None:
        hold = idx.hold_build_next_actions()
        by_id = {row["id"]: row for row in hold}
        for name, demand in HOLD_PRODUCT.items():
            row = by_id[name]
            compact = idx.compact_row(row, lane="hold_build")
            self.assertIn(demand, row["next_action"])
            self.assertIn(demand, compact["next_action"])
            self.assertEqual(compact["lane"], "hold_build")
            self.assertTrue(str(compact["source"]).endswith(".py"))
            blob = json.dumps(row) + json.dumps(compact)
            self.assertIsNone(EMAIL_RE.search(blob))
            self.assertIsNone(PHONE_RE.search(blob))
            self.assertNotIn("mailto:", blob)
            self.assertNotIn("halo.live", blob)
        hold_cli = subprocess.run(
            [sys.executable, str(HOST), "hold", "--brief"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        hold_ids = [json.loads(line)["id"] for line in hold_cli.splitlines() if line.strip()]
        self.assertEqual(sorted(hold_ids), sorted(HOLD_BUILD))
        self.assertIsNone(EMAIL_RE.search(hold_cli))
        self.assertIsNone(PHONE_RE.search(hold_cli))

    def test_show_default_is_compact_without_pii(self) -> None:
        shown = idx.show_subject("composio")
        self.assertEqual(shown["id"], "composio")
        self.assertEqual(shown["lane"], "ready_to_draft")
        self.assertNotIn("sources", shown)
        self.assertNotIn("schema_version", shown)
        self.assertIn("overlay_event_ids", shown)
        self.assertIn("source_paths", shown)
        blob = json.dumps(shown)
        self.assertIsNone(EMAIL_RE.search(blob))
        self.assertIsNone(PHONE_RE.search(blob))
        billings = idx.show_subject("city-of-billings-bid-1421")
        self.assertEqual(billings["decision"], "MATERIAL_REPLY")
        self.assertEqual(billings["lane"], "material_reply")
        self.assertIn(BILLINGS_POINTER, billings["overlay_event_ids"])
        self.assertIn(BILLINGS_RUNNER_STATUS, billings["overlay_event_ids"])
        self.assertNotIn("sources", billings)

    def test_prior_receipts_not_reminted(self) -> None:
        for name, prefix in (
            ("lm-gtm-index-20260831-01", "8845d65a"),
            ("lm-gtm-hot-lane-20260831-01", "8cb3e49a"),
            ("lm-gtm-floor-sync-20260831-01", "ce1482ef"),
        ):
            path = ROOT / "p" / f"{name}.md"
            self.assertTrue(path.is_file(), name)
            text = path.read_text(encoding="utf-8")
            self.assertIn(f"id: {name}", text)
            digest = subprocess.run(
                ["git", "hash-object", str(path)],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertTrue(digest.startswith(prefix), (name, digest))
        agent = ROOT / "p" / "lm-gtm-agent-brief-20260831-01.md"
        self.assertTrue(agent.is_file())
        self.assertIn("id: lm-gtm-agent-brief-20260831-01", agent.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
