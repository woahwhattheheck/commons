import copy
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from qualification import QualificationError, evaluate, load_json_bytes, verify

SHA_A = "a" * 64
SHA_C = "c" * 64


def evidence(eid, state="PROVEN", sha=SHA_C):
    return {
        "id": eid,
        "state": state,
        "observed_at": "2026-09-13T11:00:00Z",
        "sha256": sha if state == "PROVEN" else None,
        "ref": f"owner-evidence:{eid}" if state == "PROVEN" else None,
    }


def source(sid, cls, state="ACQUIRED", sha=SHA_A):
    return {
        "id": sid,
        "class": cls,
        "state": state,
        "url": f"https://example.invalid/{sid}",
        "captured_at": "2026-09-13T10:00:00Z",
        "sha256": sha if state == "ACQUIRED" and cls in {"OFFICIAL_PACKET", "OFFICIAL_ADDENDUM"} else None,
        "label": sid,
    }


def gate(gid, route="BOTH", state="PROVEN", cure="NONE", src="packet"):
    return {
        "id": gid,
        "title": gid.replace("-", " "),
        "route": route,
        "mandatory": True,
        "cure": cure,
        "requirement_source_id": src,
        "evidence": evidence(f"ev-{gid}", state),
    }


def base_payload(with_packet=True):
    sources = [source("notice", "OFFICIAL_NOTICE", state="OBSERVED")]
    if with_packet:
        sources.append(source("packet", "OFFICIAL_PACKET", sha=SHA_A))
    else:
        sources.append(source("discovery", "SECONDARY", state="OBSERVED"))
    req_src = "packet" if with_packet else "discovery"
    return {
        "schema": "denver-water-10575-qualification/v1",
        "opportunity": {
            "id": "denver-water-10575",
            "solicitation_id": "10575",
            "title": "Customer Experience AI Chatbot",
            "as_of": "2026-09-13T11:03:12Z",
            "proposal_deadline": "2026-09-30T20:00:00Z",
        },
        "sources": sources,
        "gates": [
            gate("agent-runtime", "BOTH", src=req_src),
            gate("references", "PRIME", src=req_src),
            gate("integration-partner", "TEAMING", src=req_src),
        ],
    }


class QualificationTests(unittest.TestCase):
    def test_missing_controlling_packet_holds_even_if_secondary_claims_proven(self):
        r = evaluate(base_payload(False))
        self.assertEqual(r["disposition"], "HOLD")
        self.assertEqual(r["reasons"], ["CONTROLLING_PACKET_NOT_ACQUIRED"])

    def test_prime_ready_requires_official_packet_and_all_prime_gates(self):
        r = evaluate(base_payload(True))
        self.assertEqual(r["disposition"], "PRIME_READY")
        self.assertEqual(r["route_detail"]["PRIME"]["status"], "PASS")

    def test_partner_curable_prime_failure_can_yield_teaming_ready(self):
        p = base_payload(True)
        p["gates"][1]["evidence"] = evidence("ev-references", "FAILED")
        p["gates"][1]["cure"] = "PARTNER_CURABLE"
        r = evaluate(p)
        self.assertEqual(r["disposition"], "TEAMING_READY")
        self.assertEqual(r["route_detail"]["PRIME"]["status"], "PARTNER_GAP")

    def test_unknown_prime_gate_holds_when_teaming_is_incomplete(self):
        p = base_payload(True)
        p["gates"][1]["evidence"] = evidence("ev-references", "UNKNOWN")
        p["gates"][2]["evidence"] = evidence("ev-integration-partner", "UNKNOWN")
        r = evaluate(p)
        self.assertEqual(r["disposition"], "HOLD")

    def test_both_routes_noncurable_fail_no_bid(self):
        p = base_payload(True)
        p["gates"][0]["evidence"] = evidence("ev-agent-runtime", "FAILED")
        r = evaluate(p)
        self.assertEqual(r["disposition"], "NO_BID")

    def test_expired_deadline_no_bid(self):
        p = base_payload(True)
        p["opportunity"]["as_of"] = "2026-10-01T00:00:00Z"
        for s in p["sources"]:
            s["captured_at"] = "2026-09-13T10:00:00Z"
        for g in p["gates"]:
            g["evidence"]["observed_at"] = "2026-09-13T11:00:00Z"
        r = evaluate(p)
        self.assertEqual(r["disposition"], "NO_BID")
        self.assertIn("PROPOSAL_DEADLINE_EXPIRED", r["reasons"])

    def test_secondary_source_cannot_authorize_gate_after_packet_exists(self):
        p = base_payload(True)
        p["sources"].append(source("mirror", "SECONDARY", state="OBSERVED"))
        p["gates"][1]["requirement_source_id"] = "mirror"
        r = evaluate(p)
        self.assertEqual(r["route_detail"]["PRIME"]["status"], "HOLD")
        self.assertTrue(any("REQUIREMENT_NOT_OFFICIAL" in x for x in r["route_detail"]["PRIME"]["hold_reasons"]))

    def test_acquired_packet_requires_sha(self):
        p = base_payload(True)
        p["sources"][1]["sha256"] = None
        with self.assertRaises(QualificationError):
            evaluate(p)

    def test_future_source_rejected(self):
        p = base_payload(True)
        p["sources"][1]["captured_at"] = "2026-09-13T12:00:00Z"
        with self.assertRaises(QualificationError):
            evaluate(p)

    def test_future_evidence_rejected(self):
        p = base_payload(True)
        p["gates"][0]["evidence"]["observed_at"] = "2026-09-13T12:00:00Z"
        with self.assertRaises(QualificationError):
            evaluate(p)

    def test_duplicate_source_id_rejected(self):
        p = base_payload(True)
        p["sources"].append(copy.deepcopy(p["sources"][0]))
        with self.assertRaises(QualificationError):
            evaluate(p)

    def test_duplicate_gate_id_rejected(self):
        p = base_payload(True)
        p["gates"].append(copy.deepcopy(p["gates"][0]))
        with self.assertRaises(QualificationError):
            evaluate(p)

    def test_changed_reuse_of_evidence_id_rejected(self):
        p = base_payload(True)
        p["gates"][1]["evidence"]["id"] = p["gates"][0]["evidence"]["id"]
        with self.assertRaises(QualificationError):
            evaluate(p)

    def test_exact_evidence_replay_allowed_across_gates(self):
        p = base_payload(True)
        p["gates"][1]["evidence"] = copy.deepcopy(p["gates"][0]["evidence"])
        r = evaluate(p)
        self.assertIn(r["disposition"], {"PRIME_READY", "TEAMING_READY"})

    def test_bool_does_not_alias_scalar_types(self):
        p = base_payload(True)
        p["gates"][0]["mandatory"] = 1
        with self.assertRaises(QualificationError):
            evaluate(p)

    def test_noncanonical_time_rejected(self):
        p = base_payload(True)
        p["opportunity"]["as_of"] = "2026-09-13T11:03:12+00:00"
        with self.assertRaises(QualificationError):
            evaluate(p)

    def test_http_url_rejected(self):
        p = base_payload(True)
        p["sources"][0]["url"] = "http://example.invalid"
        with self.assertRaises(QualificationError):
            evaluate(p)

    def test_unknown_key_rejected(self):
        p = base_payload(True)
        p["gates"][0]["surprise"] = True
        with self.assertRaises(QualificationError):
            evaluate(p)

    def test_nonproven_evidence_cannot_carry_digest(self):
        p = base_payload(True)
        p["gates"][1]["evidence"] = evidence("ev-references", "UNKNOWN")
        p["gates"][1]["evidence"]["sha256"] = SHA_A
        with self.assertRaises(QualificationError):
            evaluate(p)

    def test_order_invariance(self):
        p = base_payload(True)
        r1 = evaluate(p)
        p["sources"] = list(reversed(p["sources"]))
        p["gates"] = list(reversed(p["gates"]))
        r2 = evaluate(p)
        self.assertEqual(r1, r2)

    def test_receipt_tamper_rejected(self):
        p = base_payload(True)
        r = evaluate(p)
        bad = copy.deepcopy(r)
        bad["disposition"] = "TEAMING_READY"
        with self.assertRaises(QualificationError):
            verify(p, bad)

    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(QualificationError):
            load_json_bytes(b'{"schema":"a","schema":"b"}')

    def test_nonfinite_json_rejected(self):
        with self.assertRaises(QualificationError):
            load_json_bytes(b'{"x":NaN}')

    def test_current_fixture_is_hold(self):
        here = Path(__file__).parent
        payload = load_json_bytes((here / "current_qualification.json").read_bytes())
        r = evaluate(payload)
        self.assertEqual(r["disposition"], "HOLD")
        self.assertIn("CONTROLLING_PACKET_NOT_ACQUIRED", r["reasons"])

    def test_cli_compile_verify_and_no_overwrite(self):
        here = Path(__file__).parent
        src = here / "current_qualification.json"
        tool = here / "qualification.py"
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "receipt.json"
            subprocess.run([sys.executable, str(tool), "compile", "--input", str(src), "--output", str(out)], check=True)
            subprocess.run([sys.executable, str(tool), "verify", "--input", str(src), "--receipt", str(out)], check=True)
            second = subprocess.run([sys.executable, str(tool), "compile", "--input", str(src), "--output", str(out)], capture_output=True)
            self.assertNotEqual(second.returncode, 0)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unsupported")
    def test_cli_refuses_symlink_output(self):
        here = Path(__file__).parent
        src = here / "current_qualification.json"
        tool = here / "qualification.py"
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.write_text("sentinel")
            out = Path(td) / "receipt.json"
            os.symlink(target, out)
            proc = subprocess.run([sys.executable, str(tool), "compile", "--input", str(src), "--output", str(out)], capture_output=True)
            self.assertNotEqual(proc.returncode, 0)
            self.assertEqual(target.read_text(), "sentinel")


if __name__ == "__main__":
    unittest.main()
