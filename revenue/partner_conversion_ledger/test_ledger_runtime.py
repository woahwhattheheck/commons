from __future__ import annotations

from . import engine
from .test_support import (
    AT, D, PartnerLedgerTestCase, Path, base_packet, copy, handoff, hashlib,
    ledger, mock, os, reply, sent, subprocess, sys, tempfile, unittest,
)

class LedgerRuntimeTests(PartnerLedgerTestCase):
    def test_input_order_invariance(self):
        p = base_packet(2)
        c1, c2 = p["opportunities"][0]["candidates"]
        c1["events"] = [reply(), sent()]
        # Same semantic events but shuffled; analyzer sorts by time.
        p2 = copy.deepcopy(p)
        p2["opportunities"][0]["candidates"] = list(reversed(p2["opportunities"][0]["candidates"]))
        p2["opportunities"][0]["qualification"]["source_refs"].reverse()
        self.assertEqual(ledger.canonical_bytes(self.compile(p)), ledger.canonical_bytes(self.compile(p2)))

    def test_receipt_tamper_and_source_drift_fail_verification(self):
        p = base_packet()
        report = self.compile(p)
        self.assertTrue(ledger.verify_historical(p, report))
        tampered = copy.deepcopy(report)
        tampered["summary"]["candidate_count"] = 999
        self.assertFalse(ledger.verify_historical(p, tampered))
        p2 = copy.deepcopy(p)
        p2["opportunities"][0]["qualification"]["digest"] = D("0")
        self.assertFalse(ledger.verify_historical(p2, report))

    def test_current_verifier_detects_expiry_drift(self):
        p = base_packet()
        report = ledger._compile_at(p, "2026-09-15T20:30:00Z")
        with mock.patch.object(engine, "_utc_now_string", return_value="2026-09-15T20:30:00Z"):
            self.assertTrue(ledger.verify_current(p, report))
        with mock.patch.object(engine, "_utc_now_string", return_value="2027-01-01T00:00:00Z"):
            self.assertFalse(ledger.verify_current(p, report))

    def test_markdown_is_bound(self):
        report = self.compile(base_packet())
        md = ledger.render_markdown(report)
        self.assertEqual(report["markdown_sha256"], hashlib.sha256(md.encode()).hexdigest())
        self.assertIn("no** send", md.replace(" **", "**"))

    def test_bool_int_and_wrong_posture_rejected(self):
        p = base_packet()
        p["opportunities"][0]["qualification"]["posture"] = "PRIME"
        with self.assertRaises(ledger.LedgerError):
            self.compile(p)
        p2 = base_packet()
        p2["opportunities"][0]["candidates"][0]["route_digest"] = True
        with self.assertRaises(ledger.LedgerError):
            self.compile(p2)

    def test_cli_compile_verify_and_no_overwrite(self):
        p = base_packet()
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            inp = td / "input.json"
            out = td / "report.json"
            md = td / "report.md"
            inp.write_bytes(ledger.canonical_bytes(p))
            env = dict(os.environ)
            repo_root = str(Path(__file__).resolve().parents[2])
            env["PYTHONPATH"] = repo_root + os.pathsep + env.get("PYTHONPATH", "")
            cmd = [sys.executable, "-m", "revenue.partner_conversion_ledger.cli", "compile", str(inp), str(out), str(md)]
            first = subprocess.run(cmd, env=env, text=True, capture_output=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            second = subprocess.run(cmd, env=env, text=True, capture_output=True)
            self.assertNotEqual(second.returncode, 0)
            verify = subprocess.run([sys.executable, "-m", "revenue.partner_conversion_ledger.cli", "verify", str(inp), str(out)], env=env, text=True, capture_output=True)
            self.assertEqual(verify.returncode, 0, verify.stderr)
            self.assertIn("CURRENT_VERIFIED", verify.stdout)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink unavailable")
    def test_cli_rejects_symlink_input_and_output(self):
        p = base_packet()
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            real = td / "real.json"
            real.write_bytes(ledger.canonical_bytes(p))
            link = td / "link.json"
            os.symlink(real, link)
            with self.assertRaises(ledger.LedgerError):
                from revenue.partner_conversion_ledger.cli import _read_bounded_regular
                _read_bounded_regular(str(link))

            out_target = td / "target.json"
            out_target.write_text("x")
            out_link = td / "out.json"
            os.symlink(out_target, out_link)
            from revenue.partner_conversion_ledger.cli import _write_exclusive
            with self.assertRaises(ledger.LedgerError):
                _write_exclusive(str(out_link), b"no")

    def test_send_before_qualification_holds(self):
        p = base_packet()
        p["opportunities"][0]["qualification"]["captured_at"] = "2026-09-10T12:30:00Z"
        p["opportunities"][0]["candidates"][0]["events"] = [sent(at="2026-09-10T12:00:00Z")]
        r = self.compile(p)
        self.assertEqual(self.state(r), "HOLD")
        self.assertIn("SEND_BEFORE_QUALIFICATION", self.reasons(r))

    def test_event_after_terminal_holds(self):
        p = base_packet()
        c = p["opportunities"][0]["candidates"][0]
        c["events"] = [
            {"event_id": "term-1", "type": "TERMINAL", "at": "2026-09-10T11:00:00Z", "evidence_digest": D("1"), "terminal_class": "NO_FIT"},
            sent(at="2026-09-10T12:00:00Z"),
        ]
        r = self.compile(p)
        self.assertEqual(self.state(r), "HOLD")
        self.assertIn("EVENT_AFTER_TERMINAL", self.reasons(r))

    def test_audit_projection_binds_fit_events_exceptions_and_sources(self):
        p = base_packet()
        r = self.compile(p)
        opp = r["opportunities"][0]
        cand = opp["candidates"][0]
        self.assertEqual(opp["qualification_source_set_sha256"], ledger.sha256_bytes(ledger.canonical_bytes(p["opportunities"][0]["qualification"]["source_refs"])))
        self.assertEqual(cand["fit_evidence_sha256"], ledger.sha256_bytes(ledger.canonical_bytes(p["opportunities"][0]["candidates"][0]["fit_evidence"])))
        self.assertEqual(cand["event_log_sha256"], ledger.sha256_bytes(ledger.canonical_bytes([])))
        self.assertEqual(cand["exception_set_sha256"], ledger.sha256_bytes(ledger.canonical_bytes([])))

    def test_checked_in_sample_compiles_and_contains_no_contact_material(self):
        fixture = Path(__file__).resolve().parent / "fixtures" / "sample_input.json"
        raw = fixture.read_bytes()
        self.assertNotIn(b"@", raw)
        self.assertNotIn(b"mailto", raw.lower())
        packet = ledger.loads_strict(raw)
        report = ledger._compile_at(packet, AT)
        self.assertEqual(report["summary"]["candidate_count"], 2)
        self.assertEqual(report["summary"]["AWAITING_REPLY"], 1)
        self.assertEqual(report["summary"]["READY_FOR_OWNER_REVIEW"], 1)
        self.assertTrue(all(v is False for v in report["authority"].values()))

    def test_followup_exception_transplant_and_evidence_replay_rejected(self):
        p = base_packet(2)
        c1, c2 = p["opportunities"][0]["candidates"]
        exception = {
            "exception_id": "exc-shared", "opportunity_id": "opp-1", "candidate_id": "cand-1",
            "prior_send_event_id": "send-1", "approved_at": "2026-09-11T11:00:00Z",
            "expires_at": "2026-09-12T00:00:00Z", "evidence_digest": D("9")
        }
        c1["exceptions"] = [exception]
        transplanted = copy.deepcopy(exception)
        transplanted["candidate_id"] = "cand-2"
        transplanted["exception_id"] = "exc-other"
        c2["exceptions"] = [transplanted]
        with self.assertRaisesRegex(ledger.LedgerError, "evidence must not be replayed"):
            self.compile(p)

        p2 = base_packet(2)
        c1, c2 = p2["opportunities"][0]["candidates"]
        c1["exceptions"] = [exception]
        dup_id = copy.deepcopy(exception)
        dup_id["candidate_id"] = "cand-2"
        dup_id["evidence_digest"] = D("8")
        c2["exceptions"] = [dup_id]
        with self.assertRaisesRegex(ledger.LedgerError, "id must be globally unique"):
            self.compile(p2)

    def test_duplicate_opportunity_and_candidate_alias_rejected(self):
        p = base_packet()
        p["opportunities"].append(copy.deepcopy(p["opportunities"][0]))
        with self.assertRaisesRegex(ledger.LedgerError, "duplicate opportunity"):
            self.compile(p)
        p2 = base_packet(2)
        p2["opportunities"][0]["candidates"][1]["candidate_id"] = "cand-1"
        with self.assertRaisesRegex(ledger.LedgerError, "globally unique"):
            self.compile(p2)

    @unittest.skipUnless(hasattr(os, "mkfifo") and hasattr(os, "O_NONBLOCK"), "FIFO/nonblocking unavailable")
    def test_cli_rejects_fifo_without_blocking(self):
        with tempfile.TemporaryDirectory() as td:
            fifo = Path(td) / "input.fifo"
            os.mkfifo(fifo)
            from revenue.partner_conversion_ledger.cli import _read_bounded_regular
            with self.assertRaisesRegex(ledger.LedgerError, "regular file"):
                _read_bounded_regular(str(fifo))

    def test_cli_rejects_oversized_regular_input(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "too-large.json"
            path.write_bytes(b"x" * (ledger.MAX_JSON_BYTES + 1))
            from revenue.partner_conversion_ledger.cli import _read_bounded_regular
            with self.assertRaisesRegex(ledger.LedgerError, "size limit"):
                _read_bounded_regular(str(path))
