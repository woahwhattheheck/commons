from __future__ import annotations

import copy
import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("swarm_mail", ROOT / "host" / "swarm_mail.py")
assert SPEC and SPEC.loader
mail = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mail)

NOW = "2026-08-27T00:30:00Z"
LATER = "2026-08-27T00:31:00Z"
PROOF_BUNDLE = b"measured mx/spf/dkim/dmarc proof bundle\n"
MTA_EVIDENCE = b"trusted local MTA envelope receipt\n"
BASE_SKU = "same-day-agent-survival-proof"
SECOND_SKU = "production-survival-sprint"
BUYER = "buyer@example.com"
SUBJECT = "Bounded production proof"
BODY = "A truthful, targeted message. Reply to opt out or unsubscribe."


def canonical_dnc_addresses() -> set[str]:
    addresses: set[str] = set()
    for path in sorted(mail.OUTREACH_RECEIPTS.glob("*.json")):
        receipt = json.loads(path.read_text(encoding="utf-8"))
        if receipt.get("dedupe", {}).get("do_not_resend") is True:
            addresses.add(mail.normalize_address(receipt["recipient_email"]))
    return addresses


def measured_manifest(
    connection: sqlite3.Connection,
    *,
    measured_inboxes: tuple[str, ...] = ("codex-sales",),
    proof_bundle: bytes = PROOF_BUNDLE,
) -> dict:
    value = copy.deepcopy(mail.load_manifest())
    value["domain"] = {
        "state": "MEASURED",
        "public_name": "example.test",
        "proofs": {"mx": "MEASURED", "spf": "MEASURED", "dkim": "MEASURED", "dmarc": "MEASURED"},
        "proof_bundle_commitment": mail.commitment(connection, "domain-proof", proof_bundle),
    }
    for inbox in value["inboxes"]:
        if inbox["inbox_id"] in measured_inboxes:
            inbox["address_state"] = "MEASURED"
            inbox["public_address"] = f"{inbox['local_part']}@example.test"
            inbox["send_mode"] = "INBOUND_AND_OUTBOUND"
    return value


class SwarmMailManifestTests(unittest.TestCase):
    def test_manifest_v2_validates_and_routes_every_commerce_sku_once(self) -> None:
        manifest = mail.validate_manifest()
        self.assertEqual(manifest["schema_version"], "commons-swarm-mail/v2")
        routed = [sku for inbox in manifest["inboxes"] for sku in inbox["sku_ids"]]
        self.assertEqual(set(routed), mail.commerce_skus())
        self.assertEqual(len(routed), len(set(routed)))
        grok = next(item for item in manifest["inboxes"] if item["inbox_id"] == "grok-sales")
        for sku in (
            "sku-muhlnickel-titan-20260826",
            "sku-muhlnickel-attested-inference",
            "sku-muhlnickel-generated-token-capacity",
        ):
            self.assertIn(sku, grok["sku_ids"])
            self.assertEqual(mail.route_sku(sku)["inbox_id"], "grok-sales")
        for sku in routed:
            route = mail.route_sku(sku)
            self.assertEqual(route["sku_id"], sku)
            inbox = next(item for item in manifest["inboxes"] if item["inbox_id"] == route["inbox_id"])
            self.assertIn(sku, inbox["sku_ids"])

    def test_public_truth_starts_at_zero_and_addresses_are_unprovisioned(self) -> None:
        manifest = mail.validate_manifest()
        self.assertEqual(
            manifest["truth"],
            {
                "measured_inboxes": 0,
                "drafted_messages": 0,
                "queued_messages": 0,
                "unknown_effect_dispatches": 0,
                "mta_accepted_messages": 0,
                "provider_reported_deliveries": 0,
                "verified_positive_replies": 0,
                "paid_deliveries": 0,
                "bank_available_usd": 0.0,
            },
        )
        self.assertEqual(manifest["domain"]["state"], "UNPROVISIONED")
        self.assertIsNone(manifest["domain"]["proof_bundle_commitment"])
        for inbox in manifest["inboxes"]:
            self.assertEqual(inbox["address_state"], "UNPROVISIONED")
            self.assertEqual(inbox["send_mode"], "DRAFT_ONLY")
            self.assertIsNone(inbox["public_address"])

    def test_manifest_rejects_bool_nonfinite_and_negative_truth(self) -> None:
        base = mail.load_manifest()
        count_fields = set(base["truth"]) - {"bank_available_usd"}
        for field in count_fields:
            value = copy.deepcopy(base)
            value["truth"][field] = True
            with self.subTest(field=field, value=True), self.assertRaises(mail.SwarmMailError):
                mail.validate_manifest(value)
            value = copy.deepcopy(base)
            value["truth"][field] = -1
            with self.subTest(field=field, value=-1), self.assertRaises(mail.SwarmMailError):
                mail.validate_manifest(value)
        for cash in (True, float("nan"), float("inf"), -0.01):
            value = copy.deepcopy(base)
            value["truth"]["bank_available_usd"] = cash
            with self.subTest(cash=repr(cash)), self.assertRaises(mail.SwarmMailError):
                mail.validate_manifest(value)

    def test_duplicate_sku_or_local_part_fails_closed(self) -> None:
        value = copy.deepcopy(mail.load_manifest())
        value["inboxes"][1]["local_part"] = value["inboxes"][0]["local_part"]
        with self.assertRaises(mail.SwarmMailError):
            mail.validate_manifest(value)
        value = copy.deepcopy(mail.load_manifest())
        value["inboxes"][1]["sku_ids"].append(value["inboxes"][0]["sku_ids"][0])
        with self.assertRaises(mail.SwarmMailError):
            mail.validate_manifest(value)

    def test_event_schema_has_exact_public_safe_surface(self) -> None:
        schema = json.loads((ROOT / "revenue" / "swarm_mail" / "event.schema.json").read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            set(schema["properties"]),
            {
                "schema_version", "kind", "event_id", "event_type", "occurred_at", "inbox_id",
                "thread_ref", "message_ref", "sku_id", "prospect_ref", "payload_commitment",
                "send_ref", "classification", "transport_state", "evidence_ref", "readiness", "limits",
            },
        )
        forbidden = {
            "address", "email", "from", "to", "header", "subject", "body", "attachment",
            "secret", "payload_sha256", "evidence_sha256", "prospect_key", "send_key",
        }
        self.assertTrue(forbidden.isdisjoint(schema["properties"]))
        self.assertEqual(set(schema["properties"]["event_type"]["enum"]), set(mail.EVENT_STATES))
        self.assertIn("SUPPRESSED_AT_DISPATCH", schema["properties"]["readiness"]["enum"])
        self.assertIn("OUTBOUND_THREAD_AND_TRUSTED_MTA_AUTH_PASS", schema["properties"]["readiness"]["enum"])

    def test_public_page_uses_canonical_v2_files_and_no_client_telemetry(self) -> None:
        page = (ROOT / "swarm-mail.html").read_text(encoding="utf-8")
        script = (ROOT / "swarm-mail.js").read_text(encoding="utf-8")
        self.assertIn('id="routes"', page)
        self.assertIn('id="truth"', page)
        self.assertIn("UNPROVISIONED", page)
        self.assertIn("commons-swarm-mail/v2", script)
        self.assertIn("./revenue/swarm_mail/inboxes.json", script)
        self.assertIn("./revenue/outcome_commerce/catalog.json", script)
        self.assertIn("FAIL CLOSED", script)
        for telemetry in ("sendBeacon", "localStorage", "sessionStorage", "document.cookie"):
            self.assertNotIn(telemetry, script)
        self.assertIn("/commons/swarm-mail.html", (ROOT / "sitemap.xml").read_text(encoding="utf-8"))

    def test_ingest_cli_requires_a_trusted_mta_auth_verdict(self) -> None:
        args = mail.build_parser().parse_args(
            [
                "ingest", "--db", "/tmp/mail.sqlite3", "--inbox-id", "codex-sales",
                "--eml", "/tmp/reply.eml", "--classification", "QUESTION",
                "--mta-envelope-ref", "opaque:mta:inbound-0001",
                "--mta-evidence-file", "/tmp/mta-proof.bin", "--mta-auth-verdict", "PASS",
            ]
        )
        self.assertEqual(args.mta_auth_verdict, "PASS")


class SwarmMailRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="commons-swarm-mail-")
        self.root = Path(self.temp.name)
        self.db_path = self.root / "private" / "mail.sqlite3"
        self.connection = mail.open_db(self.db_path)
        self.manifest: dict | None = None

    def tearDown(self) -> None:
        self.connection.close()
        self.temp.cleanup()

    def provision(self, *inbox_ids: str) -> dict:
        inbox_ids = inbox_ids or ("codex-sales",)
        self.manifest = measured_manifest(self.connection, measured_inboxes=tuple(inbox_ids))
        results = {}
        with mock.patch.object(mail, "load_manifest", return_value=self.manifest):
            mail.validate_manifest()
            for inbox_id in inbox_ids:
                spec = next(item for item in self.manifest["inboxes"] if item["inbox_id"] == inbox_id)
                results[inbox_id] = mail.provision_inbox(
                    self.connection,
                    inbox_id,
                    spec["public_address"],
                    PROOF_BUNDLE,
                    NOW,
                )
        return results

    def queue(
        self,
        *,
        recipient: str = BUYER,
        sku_id: str = BASE_SKU,
        prospect_key: str = "buyer-example",
        subject: str = SUBJECT,
        body: str = BODY,
        send_key: str = "send-first-001",
        occurred_at: str = NOW,
        manifest: dict | None = None,
    ) -> dict:
        selected = manifest or self.manifest
        context = (
            mock.patch.object(mail, "load_manifest", return_value=selected)
            if selected
            else mock.patch.object(mail, "load_manifest", wraps=mail.load_manifest)
        )
        with context:
            return mail.queue_message(
                self.connection,
                recipient=recipient,
                sku_id=sku_id,
                prospect_key=prospect_key,
                subject=subject,
                body=body,
                send_key=send_key,
                occurred_at=occurred_at,
            )

    def executable(self, name: str, source: str = "#!/bin/sh\ncat >/dev/null\n") -> Path:
        path = self.root / name
        path.write_text(source, encoding="utf-8")
        path.chmod(0o700)
        return path.resolve()

    def accept(self, send_key: str = "send-first-001", *, occurred_at: str = NOW) -> dict:
        return mail.dispatch_message(self.connection, send_key, self.executable(f"sendmail-{send_key}"), occurred_at)

    def outbound_message_id(self, send_key: str = "send-first-001") -> str:
        row = self.connection.execute("SELECT * FROM drafts WHERE send_key=?", (send_key,)).fetchone()
        return BytesParser(policy=policy.default).parsebytes(mail._wire_message(self.connection, row))["Message-ID"]

    def reply_bytes(
        self,
        *,
        sender: str = BUYER,
        message_id: str = "<reply-001@example.com>",
        in_reply_to: str | None = None,
        authentication_results: str | None = None,
        body: str = "Please remove me from future outreach.",
    ) -> bytes:
        message = EmailMessage()
        message["From"] = sender
        message["To"] = "codex@example.test"
        message["Subject"] = f"Re: {SUBJECT}"
        message["Message-ID"] = message_id
        if in_reply_to:
            message["In-Reply-To"] = in_reply_to
        if authentication_results:
            message["Authentication-Results"] = authentication_results
        message.set_content(body)
        return message.as_bytes(policy=policy.SMTP)

    def ingest(
        self,
        raw: bytes,
        *,
        classification: str = "OPT_OUT",
        mta_auth_verdict: str = "PASS",
        evidence: bytes = MTA_EVIDENCE,
        occurred_at: str = NOW,
    ) -> dict:
        return mail.ingest_message(
            self.connection,
            inbox_id="codex-sales",
            raw=raw,
            requested_classification=classification,
            mta_envelope_ref="opaque:mta:inbound-0001",
            mta_auth_verdict=mta_auth_verdict,
            mta_evidence=evidence,
            occurred_at=occurred_at,
        )

    def test_database_inside_repository_is_rejected(self) -> None:
        with self.assertRaises(mail.SwarmMailError):
            mail.open_db(ROOT / "private-mail.sqlite3")

    def test_database_permissions_and_redacted_status(self) -> None:
        self.assertEqual(oct(os.stat(self.db_path).st_mode & 0o777), "0o600")
        status = mail.redacted_status(self.connection)
        self.assertEqual(status["counts"]["measured_inboxes"], 0)
        self.assertNotIn("@", json.dumps(status))
        self.assertNotIn(BUYER, json.dumps(status))

    def test_canonical_crm_dnc_is_seeded_and_wins_before_provisioning(self) -> None:
        known = canonical_dnc_addresses()
        self.assertTrue(known)
        rows = self.connection.execute("SELECT reason FROM suppressions").fetchall()
        self.assertEqual(len(rows), len(known))
        self.assertEqual({row["reason"] for row in rows}, {"CANONICAL_DO_NOT_RESEND"})
        recipient = sorted(known)[0]
        event = self.queue(recipient=recipient, prospect_key="canonical-dnc", send_key="send-canonical-dnc")
        self.assertEqual(event["event_type"], "DRAFT_RECORDED")
        self.assertEqual(event["readiness"], "SUPPRESSED")
        self.assertNotIn(recipient, json.dumps(event))
        with self.assertRaisesRegex(mail.SwarmMailError, "cannot dispatch from state DRAFTED"):
            mail.dispatch_message(self.connection, "send-canonical-dnc", self.executable("unused-sendmail"), NOW)

    def test_unprovisioned_routes_can_record_redacted_drafts(self) -> None:
        event = self.queue()
        self.assertEqual(event["event_type"], "DRAFT_RECORDED")
        self.assertEqual(event["transport_state"], "NOT_SENT")
        self.assertEqual(event["readiness"], "ADDRESS_UNMEASURED")
        row = self.connection.execute("SELECT state,readiness FROM drafts WHERE send_key='send-first-001'").fetchone()
        self.assertEqual((row["state"], row["readiness"]), ("DRAFTED", "ADDRESS_UNMEASURED"))
        self.assert_public_receipt_is_redacted(event)

    def test_measured_provision_requires_keyed_proof_commitment(self) -> None:
        commitment_receipt = mail.proof_bundle_commitment(self.connection, PROOF_BUNDLE)
        self.assertEqual(
            commitment_receipt["proof_bundle_commitment"],
            mail.commitment(self.connection, "domain-proof", PROOF_BUNDLE),
        )
        self.assertNotIn(mail.sha256_bytes(PROOF_BUNDLE), json.dumps(commitment_receipt))
        self.assertNotIn(PROOF_BUNDLE.decode().strip(), json.dumps(commitment_receipt))
        manifest = measured_manifest(self.connection)
        with mock.patch.object(mail, "load_manifest", return_value=manifest):
            event = mail.provision_inbox(self.connection, "codex-sales", "codex@example.test", PROOF_BUNDLE, NOW)
            replay = mail.provision_inbox(self.connection, "codex-sales", "CODEX@example.test", PROOF_BUNDLE, NOW)
            self.assertEqual(event, replay)
            self.assertEqual(event["event_type"], "INBOX_MEASURED")
            self.assert_public_receipt_is_redacted(event)
            with self.assertRaises(mail.SwarmMailError):
                mail.provision_inbox(self.connection, "codex-sales", "codex@example.test", b"different proof", NOW)

    def test_provision_rejects_wrong_local_part_and_domain(self) -> None:
        manifest = measured_manifest(self.connection)
        with mock.patch.object(mail, "load_manifest", return_value=manifest):
            for address in ("grok@example.test", "codex@other.test"):
                with self.subTest(address=address), self.assertRaises(mail.SwarmMailError):
                    mail.provision_inbox(self.connection, "codex-sales", address, PROOF_BUNDLE, NOW)

    def test_queue_is_idempotent_but_canonical_dedupe_blocks_new_send_key(self) -> None:
        self.provision("codex-sales")
        first = self.queue(recipient="Buyer@Example.com")
        second = self.queue(recipient=BUYER)
        self.assertEqual(first, second)
        with self.assertRaisesRegex(mail.CollisionError, "canonical recipient/SKU/channel dedupe"):
            self.queue(recipient=BUYER, send_key="send-second-002")
        with self.assertRaises(mail.CollisionError):
            self.queue(body="Different bytes; unsubscribe here.")

    def test_outreach_requires_visible_opt_out(self) -> None:
        self.provision("codex-sales")
        with self.assertRaisesRegex(mail.SwarmMailError, "visible unsubscribe or opt-out"):
            self.queue(body="No removal route is present.")

    def test_suppression_added_after_queue_blocks_mta_dispatch(self) -> None:
        self.provision("codex-sales")
        queued = self.queue()
        self.assertEqual(queued["readiness"], "SEND_READY")
        mail.suppress_recipient(
            self.connection,
            BUYER,
            "MANUAL_DNC",
            "opaque:operator:late-dnc-0001",
            LATER,
        )
        adapter = self.executable("must-not-run")
        with mock.patch.object(mail.subprocess, "run") as run:
            with self.assertRaisesRegex(mail.SwarmMailError, "suppressed"):
                mail.dispatch_message(self.connection, "send-first-001", adapter, LATER)
            run.assert_not_called()
        row = self.connection.execute("SELECT state,readiness FROM drafts WHERE send_key='send-first-001'").fetchone()
        self.assertEqual((row["state"], row["readiness"]), ("SUPPRESSED", "SUPPRESSED_AT_DISPATCH"))

    def test_daily_budget_records_draft_instead_of_sending(self) -> None:
        self.provision("codex-sales")
        limited = copy.deepcopy(self.manifest)
        next(item for item in limited["inboxes"] if item["inbox_id"] == "codex-sales")["daily_new_thread_limit"] = 1
        first = self.queue(recipient="one@example.com", prospect_key="buyer-one", send_key="send-budget-one", manifest=limited)
        second = self.queue(
            recipient="two@example.com",
            prospect_key="buyer-two",
            send_key="send-budget-two",
            sku_id=SECOND_SKU,
            manifest=limited,
        )
        self.assertEqual(first["event_type"], "QUEUE_PLANNED")
        self.assertEqual(second["event_type"], "DRAFT_RECORDED")
        self.assertEqual(second["readiness"], "DAILY_BUDGET_REACHED")

    def test_concurrent_dispatch_invokes_mta_exactly_once(self) -> None:
        self.provision("codex-sales")
        self.queue()
        adapter = self.executable("concurrent-sendmail")
        entered = threading.Event()
        release = threading.Event()
        calls: list[tuple[list[str], bytes]] = []
        outcome: list[object] = []

        def fake_run(args, *, input, stdout, stderr, check, timeout):
            calls.append((list(args), input))
            entered.set()
            if not release.wait(5):
                raise subprocess.TimeoutExpired(args, timeout)
            return subprocess.CompletedProcess(args, 0, b"accepted", b"")

        def first_dispatch() -> None:
            connection = mail.open_db(self.db_path)
            try:
                outcome.append(mail.dispatch_message(connection, "send-first-001", adapter, NOW))
            except BaseException as error:  # captured for assertion in the parent test thread
                outcome.append(error)
            finally:
                connection.close()

        with mock.patch.object(mail.subprocess, "run", side_effect=fake_run):
            worker = threading.Thread(target=first_dispatch, daemon=True)
            worker.start()
            self.assertTrue(entered.wait(5), "first dispatch never reached the MTA adapter")
            with self.assertRaises(mail.UnknownEffectError):
                mail.dispatch_message(self.connection, "send-first-001", adapter, NOW)
            release.set()
            worker.join(5)
            self.assertFalse(worker.is_alive())

        self.assertEqual(len(calls), 1)
        self.assertEqual(len(outcome), 1)
        self.assertIsInstance(outcome[0], dict)
        self.assertEqual(outcome[0]["event_type"], "MTA_ACCEPTED")
        replay = mail.dispatch_message(self.connection, "send-first-001", adapter, NOW)
        self.assertEqual(replay, outcome[0])
        self.assertEqual(len(calls), 1)

    def test_sendmail_envelope_sender_and_unsubscribe_header_are_emitted(self) -> None:
        self.provision("codex-sales")
        self.queue()
        args_path = self.root / "sendmail-args.json"
        wire_path = self.root / "sendmail-wire.eml"
        script = self.executable(
            "capture-sendmail",
            f"#!{sys.executable}\n"
            "import json, pathlib, sys\n"
            f"pathlib.Path({str(args_path)!r}).write_text(json.dumps(sys.argv[1:]), encoding='utf-8')\n"
            f"pathlib.Path({str(wire_path)!r}).write_bytes(sys.stdin.buffer.read())\n",
        )
        event = mail.dispatch_message(self.connection, "send-first-001", script, NOW)
        self.assertEqual(json.loads(args_path.read_text(encoding="utf-8")), ["-i", "-f", "codex@example.test", "-t"])
        message = BytesParser(policy=policy.default).parsebytes(wire_path.read_bytes())
        self.assertEqual(message["From"], "codex@example.test")
        self.assertIn("mailto:codex@example.test?subject=unsubscribe", message["List-Unsubscribe"])
        self.assertIn("opt out", message.get_body(preferencelist=("plain",)).get_content().lower())
        self.assertEqual(event["transport_state"], "MTA_ACCEPTED")
        self.assertNotEqual(event["transport_state"], "PROVIDER_REPORTED")

    def test_failed_dispatch_becomes_unknown_and_requires_explicit_reconciliation(self) -> None:
        self.provision("codex-sales")
        self.queue()
        adapter = self.executable("failing-sendmail")
        failed = subprocess.CompletedProcess([str(adapter)], 75, b"", b"temporary failure")
        with mock.patch.object(mail.subprocess, "run", return_value=failed) as run:
            with self.assertRaises(mail.UnknownEffectError):
                mail.dispatch_message(self.connection, "send-first-001", adapter, NOW)
            with self.assertRaises(mail.UnknownEffectError):
                mail.dispatch_message(self.connection, "send-first-001", adapter, NOW)
            self.assertEqual(run.call_count, 1)
        row = self.connection.execute("SELECT state,readiness FROM drafts WHERE send_key='send-first-001'").fetchone()
        self.assertEqual((row["state"], row["readiness"]), ("UNKNOWN_EFFECT", "RECONCILE_REQUIRED"))
        not_accepted = mail.reconcile_dispatch(
            self.connection,
            send_key="send-first-001",
            resolution="NOT_ACCEPTED",
            evidence_ref="opaque:operator:not-accepted-0001",
            evidence=b"MTA log proves no handoff",
            occurred_at=LATER,
        )
        self.assertEqual(not_accepted["readiness"], "NOT_ACCEPTED_FINAL")
        state = self.connection.execute("SELECT state FROM drafts WHERE send_key='send-first-001'").fetchone()[0]
        self.assertEqual(state, "NOT_ACCEPTED")
        with self.assertRaises(mail.SwarmMailError):
            mail.dispatch_message(self.connection, "send-first-001", adapter, LATER)

        self.queue(
            recipient="other@example.com",
            prospect_key="other-buyer",
            sku_id=SECOND_SKU,
            send_key="send-unknown-two",
        )
        with mock.patch.object(mail.subprocess, "run", return_value=failed):
            with self.assertRaises(mail.UnknownEffectError):
                mail.dispatch_message(self.connection, "send-unknown-two", adapter, NOW)
        accepted = mail.reconcile_dispatch(
            self.connection,
            send_key="send-unknown-two",
            resolution="MTA_ACCEPTED",
            evidence_ref="opaque:operator:mta-accepted-0002",
            evidence=b"MTA queue log proves acceptance",
            occurred_at=LATER,
        )
        self.assertEqual(accepted["event_type"], "MTA_ACCEPTED")
        row = self.connection.execute(
            "SELECT state,mta_accepted_at FROM drafts WHERE send_key='send-unknown-two'"
        ).fetchone()
        self.assertEqual((row["state"], row["mta_accepted_at"]), ("MTA_ACCEPTED", LATER))

    def test_transport_event_idempotency_and_adverse_finality(self) -> None:
        self.provision("codex-sales")
        self.queue()
        queued = self.connection.execute(
            "SELECT queued_at,mta_accepted_at,provider_reported_at FROM drafts WHERE send_key='send-first-001'"
        ).fetchone()
        self.assertEqual((queued["queued_at"], queued["mta_accepted_at"], queued["provider_reported_at"]), (NOW, None, None))
        self.accept()
        accepted = self.connection.execute(
            "SELECT queued_at,mta_accepted_at,provider_reported_at FROM drafts WHERE send_key='send-first-001'"
        ).fetchone()
        self.assertEqual((accepted["queued_at"], accepted["mta_accepted_at"], accepted["provider_reported_at"]), (NOW, NOW, None))
        kwargs = {
            "send_key": "send-first-001",
            "transport_event_key": "provider-delivery-001",
            "event_type": "PROVIDER_DELIVERY_REPORTED",
            "evidence_ref": "opaque:provider:delivery-0001",
            "evidence": b"provider webhook payload",
            "occurred_at": NOW,
        }
        delivered = mail.record_transport_event(self.connection, **kwargs)
        self.assertEqual(delivered["transport_state"], "PROVIDER_REPORTED")
        provider_at = self.connection.execute(
            "SELECT provider_reported_at FROM drafts WHERE send_key='send-first-001'"
        ).fetchone()[0]
        self.assertEqual(provider_at, NOW)
        self.assertEqual(mail.record_transport_event(self.connection, **kwargs), delivered)
        with self.assertRaises(mail.CollisionError):
            mail.record_transport_event(self.connection, **dict(kwargs, occurred_at=LATER))
        hard = mail.record_transport_event(
            self.connection,
            send_key="send-first-001",
            transport_event_key="provider-hard-bounce-001",
            event_type="HARD_BOUNCE_REPORTED",
            evidence_ref="opaque:provider:hard-bounce-0001",
            evidence=b"provider permanent failure payload",
            occurred_at=LATER,
        )
        self.assertEqual(hard["transport_state"], "FAILED")
        with self.assertRaises(mail.SwarmMailError):
            mail.record_transport_event(self.connection, **dict(kwargs, transport_event_key="provider-delivery-002"))
        suppressed = self.queue(sku_id=SECOND_SKU, send_key="send-after-hard-bounce")
        self.assertEqual(suppressed["readiness"], "SUPPRESSED")

    def test_soft_bounce_does_not_globally_suppress_recipient(self) -> None:
        self.provision("codex-sales")
        self.queue()
        self.accept()
        event = mail.record_transport_event(
            self.connection,
            send_key="send-first-001",
            transport_event_key="provider-soft-bounce-001",
            event_type="SOFT_BOUNCE_REPORTED",
            evidence_ref="opaque:provider:soft-bounce-0001",
            evidence=b"provider temporary failure payload",
            occurred_at=NOW,
        )
        self.assertEqual(event["transport_state"], "PROVIDER_REPORTED")
        recipient_ref = mail._recipient_commitment(self.connection, BUYER)
        row = self.connection.execute("SELECT 1 FROM suppressions WHERE recipient_commitment=?", (recipient_ref,)).fetchone()
        self.assertIsNone(row)
        next_event = self.queue(sku_id=SECOND_SKU, send_key="send-after-soft-bounce")
        self.assertEqual(next_event["readiness"], "SEND_READY")

    def test_unattributed_opt_out_is_forced_to_human_without_suppression(self) -> None:
        self.provision("codex-sales")
        raw = self.reply_bytes(authentication_results="attacker.invalid; spf=pass smtp.mailfrom=buyer@example.com")
        event = self.ingest(raw, classification="OPT_OUT", mta_auth_verdict="FAIL")
        self.assertEqual(event["classification"], "NEEDS_HUMAN")
        self.assertIsNone(event["sku_id"])
        self.assertIsNone(event["prospect_ref"])
        self.assertIsNone(event["send_ref"])
        recipient_ref = mail._recipient_commitment(self.connection, BUYER)
        row = self.connection.execute("SELECT 1 FROM suppressions WHERE recipient_commitment=?", (recipient_ref,)).fetchone()
        self.assertIsNone(row)

    def test_different_sender_cannot_hijack_thread_with_pass_header(self) -> None:
        self.provision("codex-sales")
        self.queue()
        self.accept()
        raw = self.reply_bytes(
            sender="attacker@evil.test",
            message_id="<spoof-001@evil.test>",
            in_reply_to=self.outbound_message_id(),
            authentication_results="mx.example.test; spf=pass smtp.mailfrom=attacker@evil.test",
        )
        event = self.ingest(raw, classification="OPT_OUT")
        self.assertEqual(event["classification"], "NEEDS_HUMAN")
        self.assertIsNone(event["sku_id"])
        self.assertIsNone(event["send_ref"])
        attacker_ref = mail._recipient_commitment(self.connection, "attacker@evil.test")
        row = self.connection.execute("SELECT 1 FROM suppressions WHERE recipient_commitment=?", (attacker_ref,)).fetchone()
        self.assertIsNone(row)

    def test_authenticated_reply_derives_attribution_and_opt_out_atomically(self) -> None:
        self.provision("codex-sales")
        self.queue()
        self.accept()
        raw = self.reply_bytes(
            in_reply_to=self.outbound_message_id(),
            authentication_results="mx.example.test; spf=pass smtp.mailfrom=buyer@example.com",
        )
        event = self.ingest(raw, classification="OPT_OUT")
        self.assertEqual(event["classification"], "OPT_OUT")
        self.assertEqual(event["sku_id"], BASE_SKU)
        self.assertEqual(event["readiness"], "OUTBOUND_THREAD_AND_TRUSTED_MTA_AUTH_PASS")
        self.assertIsNotNone(event["prospect_ref"])
        self.assertIsNotNone(event["send_ref"])
        row = self.connection.execute("SELECT * FROM inbound_messages").fetchone()
        recipient_ref = mail._recipient_commitment(self.connection, BUYER)
        suppression = self.connection.execute(
            "SELECT reason FROM suppressions WHERE recipient_commitment=?", (recipient_ref,)
        ).fetchone()
        self.assertEqual(row["linked_send_key"], "send-first-001")
        self.assertEqual(row["sku_id"], BASE_SKU)
        self.assertEqual(row["prospect_key"], "buyer-example")
        self.assertEqual(json.loads(row["canonical_reply_json"])["classification"], "OPT_OUT")
        self.assertEqual(suppression["reason"], "OPT_OUT")
        self.assert_public_receipt_is_redacted(event)

    def test_inbound_replay_collision_and_missing_suppression_repair(self) -> None:
        self.provision("codex-sales")
        self.queue()
        self.accept()
        raw = self.reply_bytes(
            message_id="<reply-replay@example.com>",
            in_reply_to=self.outbound_message_id(),
            authentication_results="mx.example.test; dkim=pass header.d=example.com",
        )
        first = self.ingest(raw, classification="OPT_OUT")
        recipient_ref = mail._recipient_commitment(self.connection, BUYER)
        self.connection.execute("DELETE FROM suppressions WHERE recipient_commitment=?", (recipient_ref,))
        self.connection.commit()
        row = self.connection.execute("SELECT 1 FROM suppressions WHERE recipient_commitment=?", (recipient_ref,)).fetchone()
        self.assertIsNone(row)
        replay = self.ingest(raw, classification="OPT_OUT")
        self.assertEqual(first, replay)
        reason = self.connection.execute(
            "SELECT reason FROM suppressions WHERE recipient_commitment=?", (recipient_ref,)
        ).fetchone()[0]
        self.assertEqual(reason, "OPT_OUT")
        with self.assertRaises(mail.CollisionError):
            self.ingest(raw, classification="QUESTION")

    def test_public_events_and_status_never_expose_private_mail_or_raw_hashes(self) -> None:
        self.provision("codex-sales")
        event = self.queue(
            recipient="private-buyer@secret.example",
            prospect_key="private-prospect-key",
            subject="Private commercial subject",
            body="Secret offer bytes; unsubscribe here.",
            send_key="private-send-key",
        )
        blob = json.dumps(event)
        private_values = {
            "private-buyer@secret.example",
            "private-prospect-key",
            "Private commercial subject",
            "Secret offer bytes",
            "private-send-key",
        }
        for value in private_values:
            self.assertNotIn(value, blob)
        row = self.connection.execute("SELECT payload_sha256 FROM drafts WHERE send_key='private-send-key'").fetchone()
        self.assertNotIn(row["payload_sha256"], blob)
        self.assertRegex(event["payload_commitment"], r"^hmac-sha256:[0-9a-f]{64}$")
        self.assertNotIn("@", json.dumps(mail.redacted_status(self.connection)))

    def assert_public_receipt_is_redacted(self, event: dict) -> None:
        mail.validate_public_event(event)
        blob = json.dumps(event)
        for private in (BUYER, SUBJECT, BODY, "buyer-example", "send-first-001", PROOF_BUNDLE.decode().strip()):
            self.assertNotIn(private, blob)
        self.assertNotIn("payload_sha256", event)
        self.assertNotIn("evidence_sha256", event)


if __name__ == "__main__":
    unittest.main()
