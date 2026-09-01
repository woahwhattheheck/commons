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
    "mga-marshall-houston",
    "mvmtc-craig-riviello",
    "luvak-dean-gaskill",
    "sharp-james-hamilton",
    "pace-amanda-yoakum",
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
BILLINGS_OWNER_HOLD = "lm-gtm-billings-owner-hold-status-20260831-02"
HALO_BOUNCE_STATUS = "lm-gtm-fuse-halo-bounce-status-20260831-02"
HOLD_TRUTH_SYNC = (
    "lm-gtm-hold-mga-20260831-02",
    "lm-gtm-hold-mvmtc-20260831-02",
    "lm-gtm-hold-luvak-20260831-02",
    "lm-gtm-hold-sharp-20260831-02",
    "lm-gtm-hold-pace-20260831-02",
)
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
        self.assertEqual(truth["live_next_actions"], 50)
        self.assertEqual(truth["hot_next_actions"], 11)
        self.assertEqual(truth["hold_build_actions"], 15)
        self.assertEqual(truth["sent_awaiting_dnr_actions"], 10)
        self.assertEqual(truth["external_prospects"], 39)
        self.assertEqual(truth["inbound_contacts"], 11)
        self.assertEqual(truth["seller_context_rows"], 4)
        self.assertEqual(truth["overlay_events"], 42)
        self.assertEqual(truth["index_rows"], 56)
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
        self.assertEqual(ids[0], "composio")
        self.assertEqual(classes[0], "ready_to_draft")
        self.assertNotIn("city-of-billings-bid-1421", ids)
        self.assertIn("composio", ids)
        self.assertEqual(hot[ids.index("composio")]["hot_class"], "ready_to_draft")
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

    def test_billings_owner_hold_not_hot_and_not_dead_nobid(self) -> None:
        built = idx.build_index()
        by_id = {row["id"]: row for row in built["rows"]}
        row = by_id["city-of-billings-bid-1421"]
        self.assertEqual(row["decision"], "OWNER_HOLD")
        self.assertEqual(row["role"], "inbound_contact")
        self.assertTrue(row["dnr"])
        self.assertTrue(row["live"])
        self.assertEqual(row["due"], "2026-09-04")
        self.assertEqual(row["route_kind"], "EXISTING_CRM_RECORD")
        self.assertEqual(row["route_ref"], "airtable:rec2mCS4ETa8FOvqN")
        self.assertEqual(idx.compact_lane(row), "owner_hold")
        self.assertIn("slack:C0BRGMDQB6G:1788143612.591889", row["source_paths"])
        self.assertIn("gmail:1a055a9913e5f6ec", row["source_paths"])
        self.assertIn("slack:C0BRGMDQB6G:1788146673.583549", row["source_paths"])
        self.assertIn("slack:C0BRGMDQB6G:1788147874.618849", row["source_paths"])
        self.assertIn("p/billings-bid-1421-partner-recon-20260831-01.md", row["source_paths"])
        self.assertIn("slack:C0BU4PSNWG4:1788230699.113579", row["source_paths"])
        self.assertIn("slack:C0BRGMDQB6G:1788230715.431379", row["source_paths"])
        self.assertIn("slack:C0BTURDA3PW:1788170925.499889", row["source_paths"])
        next_action = row["next_action"].casefold()
        self.assertIn("owner_hold", next_action)
        self.assertIn("dnr_outreach", next_action)
        self.assertIn("not_hot", next_action)
        self.assertIn("billings-1421-compliance", next_action)
        self.assertIn("attachment e complete", next_action)
        self.assertIn("no agent send", next_action)
        self.assertIn("no bid submission by agents", next_action)
        self.assertIn("do not contact cheri", next_action)
        self.assertIn("live owner path remains", next_action)
        self.assertIn("pointer only", next_action)
        self.assertNotIn("dead no_bid", next_action)
        self.assertNotEqual(row["decision"], "NO_BID")
        self.assertNotEqual(row["decision"], "MATERIAL_REPLY")
        self.assertIn(BILLINGS_POINTER, row["overlay_event_ids"])
        self.assertIn(BILLINGS_FLOOR_STATUS, row["overlay_event_ids"])
        self.assertIn(BILLINGS_RUNNER_STATUS, row["overlay_event_ids"])
        self.assertIn(BILLINGS_OWNER_HOLD, row["overlay_event_ids"])
        self.assertNotEqual(BILLINGS_POINTER, BILLINGS_OWNER_HOLD)
        self.assertNotEqual(BILLINGS_FLOOR_STATUS, BILLINGS_OWNER_HOLD)
        self.assertNotEqual(BILLINGS_RUNNER_STATUS, BILLINGS_OWNER_HOLD)
        event_ids = {event["id"] for event in built["events"]}
        self.assertIn(BILLINGS_POINTER, event_ids)
        self.assertIn(BILLINGS_FLOOR_STATUS, event_ids)
        self.assertIn(BILLINGS_RUNNER_STATUS, event_ids)
        self.assertIn(BILLINGS_OWNER_HOLD, event_ids)
        hot_ids = [item["id"] for item in idx.hot_next_actions()]
        self.assertNotIn("city-of-billings-bid-1421", hot_ids)
        self.assertEqual(hot_ids[0], "composio")

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
            self.assertTrue(row["dnr"])
            self.assertEqual(row["route_kind"], "EXISTING_CRM_RECORD")
            self.assertEqual(row["route_ref"], rec)
            self.assertTrue(row["live"])
            self.assertNotIn(name, hot_ids)
            self.assertEqual(row["cash_usd"], 0)
            self.assertTrue(any(path.startswith("gmail:") for path in row["source_paths"]))
            self.assertTrue(any(path.startswith("github:") for path in row["source_paths"]))
            self.assertIn("slack:C0BRGMDQB6G:1788150461.695739", row["source_paths"])
            if name == "fuse-halo-ai-vito-strokov":
                self.assertEqual(row["decision"], "BOUNCED")
                self.assertEqual(idx.compact_lane(row), "bounced")
                self.assertIn(HALO_BOUNCE_STATUS, row["overlay_event_ids"])
                self.assertIn("slack:C0BTURDA3PW:1788159251.530269", row["source_paths"])
                self.assertIn("gmail:1a056118151078d4", row["source_paths"])
                bounce = row["next_action"].casefold()
                self.assertIn("bounced", bounce)
                self.assertIn("hard_do_not_resend", bounce)
                self.assertNotIn("awaiting_reply", bounce)
            else:
                self.assertEqual(row["decision"], "SENT_AWAITING_REPLY")
        self.assertEqual(by_id["fuse-jovie-tim-white"]["person"], "Tim White")
        self.assertEqual(by_id["fuse-halo-ai-vito-strokov"]["organization"], "Halo AI")
        self.assertIn(HALO_BOUNCE_STATUS, event_ids)

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
        self.assertEqual(by_id["mga-marshall-houston"]["person"], "Marshall Houston")
        self.assertEqual(by_id["mga-marshall-houston"]["organization"], "MGA Research")
        self.assertIn("mga-alabama-materials-program-lims-01", by_id["mga-marshall-houston"]["next_action"])
        self.assertEqual(by_id["mvmtc-craig-riviello"]["person"], "Craig A. Riviello")
        self.assertEqual(by_id["luvak-dean-gaskill"]["person"], "Dean Gaskill")
        self.assertEqual(by_id["sharp-james-hamilton"]["person"], "James Hamilton")
        self.assertEqual(by_id["pace-amanda-yoakum"]["person"], "Amanda Yoakum")
        event_ids = {event["id"] for event in built["events"]}
        for event_id in HOLD_TRUTH_SYNC:
            self.assertIn(event_id, event_ids)

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
        self.assertEqual(billings["index"]["decision"], "OWNER_HOLD")
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
            compact = idx.compact_row(shown["index"])
            self.assertEqual(compact["owner"], "GROK")
            self.assertNotIn("dnr", compact)
            self.assertEqual(idx.brief_header(paths=paths)["occupied"], 1)
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
            compact = idx.compact_row(shown["index"])
            self.assertNotIn("owner", compact)
            self.assertEqual(idx.brief_header(paths=paths)["occupied"], 0)
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
            self.assertEqual(hot_ids[0], "metaforms")
            self.assertNotIn("city-of-billings-bid-1421", hot_ids)
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
        self.assertIn("11 hot", first)
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
        self.assertEqual(hot_ids[0], "composio")
        self.assertNotIn("city-of-billings-bid-1421", hot_ids)
        self.assertNotIn("fuse-halo-ai-vito-strokov", hot_ids)
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
        extra_header = set(header) - idx.BRIEF_HEADER_KEYS
        self.assertFalse(extra_header, extra_header)
        self.assertIn("composed_at", header)
        self.assertEqual(header["composed_at"], idx.build_index()["state"]["composed_at"])
        self.assertEqual(header["hot"], 11)
        self.assertEqual(header["hold"], 15)
        self.assertEqual(header["sent_dnr"], 10)
        self.assertEqual(header["occupied"], 0)
        self.assertEqual(header["cash_usd"], 0)
        self.assertEqual(header["canonical_crm"], "JOJO Revenue Recovery CRM / Revenue Pipeline")
        self.assertEqual(header["mailbox"], "NEEDS_OWNER_MAILBOX")
        rows = [json.loads(line) for line in lines[1:]]
        self.assertEqual(len(rows), 11)
        self.assertEqual(rows[0]["id"], "composio")
        self.assertEqual(rows[0]["lane"], "ready_to_draft")
        self.assertEqual(rows[0]["decision"], "READY_TO_DRAFT")
        self.assertNotIn("city-of-billings-bid-1421", [row["id"] for row in rows])
        self.assertNotIn("fuse-halo-ai-vito-strokov", [row["id"] for row in rows])
        for row in rows:
            extra = set(row) - BRIEF_KEYS
            self.assertFalse(extra, extra)
            self.assertNotIn("schema_version", row)
            self.assertNotIn("kind", row)
            self.assertNotIn("overlay_event_ids", row)
            self.assertNotIn("cash_usd", row)
            self.assertNotIn("source_ledgers", row)
            self.assertNotIn("owner", row)
            self.assertNotIn("dnr", row)
            self.assertTrue(all(value is not None for value in row.values()))
            blob = json.dumps(row)
            self.assertIsNone(EMAIL_RE.search(blob))
            self.assertIsNone(PHONE_RE.search(blob))
            self.assertNotIn("mailto:", blob)
        hot_ids = [row["id"] for row in idx.hot_next_actions()]
        self.assertEqual([row["id"] for row in rows], hot_ids)
        for name in SENT_DNR + HOLD_BUILD:
            self.assertNotIn(name, [row["id"] for row in rows])
        contract = idx.build_index()["state"]["contract"]
        self.assertIn("list_brief", contract)
        self.assertIn("list_sent", contract)
        self.assertEqual(contract["list_brief"], "python3 host/lm_gtm_index.py brief")
        self.assertEqual(
            contract["claim"],
            "python3 host/lm_gtm_index.py claim <subject> --owner <you>",
        )
        self.assertEqual(
            contract["release"],
            "python3 host/lm_gtm_index.py release <subject> --owner <you>",
        )
        self.assertEqual(
            contract["append_event"],
            'python3 host/lm_gtm_index.py append-event --subject <id> --id <event> --body "<note>"',
        )
        self.assertIn("claim <subject>", contract["claim"])
        self.assertNotEqual(
            contract["claim"],
            "python3 host/lm_gtm_index.py claim --owner ",
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
            self.assertEqual(row["lane"] in {"sent_dnr", "bounced"}, True)
            self.assertTrue(row["dnr"])
            self.assertNotIn("owner", row)
            self.assertNotIn(row["id"], hot_ids)
            self.assertTrue(str(row.get("route_ref") or "").startswith("airtable:rec"))
            blob = json.dumps(row)
            self.assertIsNone(EMAIL_RE.search(blob))
            self.assertIsNone(PHONE_RE.search(blob))
            if row["id"] == "fuse-halo-ai-vito-strokov":
                self.assertEqual(row["lane"], "bounced")
                self.assertEqual(row["decision"], "BOUNCED")
                self.assertIn("HARD_DO_NOT_RESEND", row["next_action"])
                self.assertIn("BOUNCED", row["next_action"])
            else:
                self.assertEqual(row["lane"], "sent_dnr")
                self.assertEqual(row["decision"], "SENT_AWAITING_REPLY")
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
        self.assertEqual(billings["decision"], "OWNER_HOLD")
        self.assertEqual(billings["lane"], "owner_hold")
        self.assertIn(BILLINGS_POINTER, billings["overlay_event_ids"])
        self.assertIn(BILLINGS_RUNNER_STATUS, billings["overlay_event_ids"])
        self.assertIn(BILLINGS_OWNER_HOLD, billings["overlay_event_ids"])
        self.assertNotIn("sources", billings)

    def test_prior_receipts_not_reminted(self) -> None:
        for name, prefix in (
            ("lm-gtm-index-20260831-01", "8845d65a"),
            ("lm-gtm-hot-lane-20260831-01", "8cb3e49a"),
            ("lm-gtm-floor-sync-20260831-01", "ce1482ef"),
            ("lm-gtm-agent-brief-20260831-01", "5727847f"),
            ("lm-gtm-truth-sync-20260831-02", "4edb7d70"),
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
        truth = ROOT / "p" / "lm-gtm-truth-sync-20260831-02.md"
        self.assertTrue(truth.is_file())
        self.assertIn("id: lm-gtm-truth-sync-20260831-02", truth.read_text(encoding="utf-8"))
        self.assertNotIn("id: lm-gtm-truth-sync-20260831-02", (ROOT / "p" / "lm-gtm-agent-brief-20260831-01.md").read_text(encoding="utf-8"))
        contract_receipt = ROOT / "p" / "lm-gtm-contract-brief-20260901-01.md"
        self.assertTrue(contract_receipt.is_file())
        self.assertIn("id: lm-gtm-contract-brief-20260901-01", contract_receipt.read_text(encoding="utf-8"))
        door = (ROOT / "lm-gtm-index.html").read_text(encoding="utf-8")
        self.assertIn("Contract claim is positional", door)
        self.assertIn("claim &lt;subject&gt; --owner &lt;you&gt;", door)

    def test_brief_stale_warning_after_twelve_hours(self) -> None:
        import datetime as dt

        built = idx.build_index()
        fresh = idx.brief_header(built=built, now=idx.parse_time(built["state"]["composed_at"]))
        self.assertNotIn("stale_warning", fresh)
        self.assertEqual(fresh["composed_at"], built["state"]["composed_at"])
        extra = set(fresh) - idx.BRIEF_HEADER_KEYS
        self.assertFalse(extra, extra)
        self.assertEqual(fresh["occupied"], 0)
        self.assertEqual(fresh["mailbox"], "NEEDS_OWNER_MAILBOX")
        stale = idx.brief_header(
            built=built,
            now=idx.parse_time(built["state"]["composed_at"]) + dt.timedelta(hours=12, seconds=1),
        )
        self.assertEqual(stale["stale_warning"], idx.STALE_WARNING)
        self.assertIn("composed_at", stale)
        extra = set(stale) - idx.BRIEF_HEADER_KEYS
        self.assertFalse(extra, extra)
        self.assertEqual(stale["occupied"], 0)
        self.assertEqual(stale["mailbox"], "NEEDS_OWNER_MAILBOX")

    def test_compact_row_omits_unseated_owner_and_false_dnr(self) -> None:
        built = idx.build_index()
        by_id = {row["id"]: row for row in built["rows"]}
        composio = idx.compact_row(by_id["composio"])
        self.assertNotIn("owner", composio)
        self.assertNotIn("dnr", composio)
        self.assertEqual(composio["lane"], "ready_to_draft")
        halo = idx.compact_row(by_id["fuse-halo-ai-vito-strokov"])
        self.assertTrue(halo["dnr"])
        self.assertNotIn("owner", halo)
        self.assertEqual(halo["lane"], "bounced")
        hold = idx.compact_row(by_id["pcl-ryan-ott"], lane="hold_build")
        self.assertNotIn("dnr", hold)
        self.assertNotIn("owner", hold)


if __name__ == "__main__":
    unittest.main()
