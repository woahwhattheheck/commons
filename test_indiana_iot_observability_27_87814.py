import copy
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import opportunities.indiana_iot_observability_27_87814.gate as gate
from opportunities.indiana_iot_observability_27_87814.gate import (
    GateError, compile_current, compile_pursuit, loads_strict, verify_pursuit,
)

PKG = Path(__file__).resolve().parent / "opportunities" / "indiana_iot_observability_27_87814"
def load(name): return json.loads((PKG / name).read_text(encoding="utf-8"))
BASE_LEDGER = load("source_ledger.json")
BASE_REQS = load("requirements.json")
BASE_PARTNERS = load("partner_targets.json")
BASE_SCOPE = load("paid_specialist_scope.json")
NOW = "2026-09-17T19:20:00Z"


def write_synthetic_authority(root: Path):
    (root / "retained").mkdir()
    bid = b"official controlling package bytes\n"
    owner = b'{"owner":"synthetic qualification evidence"}\n'
    (root / "retained" / "bid.zip").write_bytes(bid)
    (root / "retained" / "owner.json").write_bytes(owner)
    generation = "SYNTHETIC_AUTH_1"
    bindings = {
        "controlling_package": ("idoa-bid-package", "RFP_CONTROL"),
        "submission_mechanics": ("idoa-bid-package", "RFP_CONTROL"),
        "questions_and_prebid": ("idoa-bid-package", "RFP_CONTROL"),
        "teaming_rules": ("idoa-bid-package", "RFP_CONTROL"),
        "security_compliance": ("idoa-bid-package", "RFP_CONTROL"),
        "pricing_forms": ("idoa-bid-package", "RFP_CONTROL"),
        "prime_platform_qualification": ("owner-capability-evidence", "OWNER_QUALIFICATION"),
        "staffing_capacity": ("owner-capability-evidence", "OWNER_QUALIFICATION"),
        "paid_specialist_workshare": ("owner-capability-evidence", "OWNER_QUALIFICATION"),
    }
    sources = [
        {
            "id": "idoa-bid-package",
            "authority": "OFFICIAL_CONTROLLING_PACKAGE",
            "relpath": "retained/bid.zip",
            "sha256": hashlib.sha256(bid).hexdigest(),
            "subject": gate.OPPORTUNITY_ID,
            "scope": "RFP_CONTROL",
            "generation_id": generation,
        },
        {
            "id": "owner-capability-evidence",
            "authority": "OWNER_RETAINED_EVIDENCE",
            "relpath": "retained/owner.json",
            "sha256": hashlib.sha256(owner).hexdigest(),
            "subject": gate.OPPORTUNITY_ID,
            "scope": "OWNER_QUALIFICATION",
            "generation_id": generation,
        },
    ]
    evidence = [
        {
            "id": f"ev-{rid}", "source_id": sid, "requirement_id": rid,
            "subject": gate.OPPORTUNITY_ID, "scope": scope, "generation_id": generation,
        }
        for rid, (sid, scope) in bindings.items()
    ]
    manifest = {
        "schema": "indiana-iot-observability-authority/v1",
        "opportunity_id": gate.OPPORTUNITY_ID,
        "event_id": gate.EVENT_ID,
        "generation_id": generation,
        "sources": sources,
        "evidence": evidence,
    }
    raw = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode()
    return raw, bindings


def synthetic_inputs():
    ledger = copy.deepcopy(BASE_LEDGER)
    package = next(x for x in ledger["sources"] if x["id"] == "idoa-bid-package")
    package["retained"] = True
    package["controls"] = [
        "submission_mechanics", "question_deadline", "prebid", "teaming_rules",
        "mandatory_requirements", "evaluation_criteria", "security_compliance",
        "pricing_forms", "insurance", "contract_terms",
    ]
    ledger["sources"].append({
        "id": "owner-capability-evidence", "authority": "OWNER_RETAINED_EVIDENCE",
        "retained": True, "url": "internal://retained-owner-capability-evidence",
        "claims": {}, "controls": [],
    })
    reqs = copy.deepcopy(BASE_REQS)
    positive = {
        "controlling_package", "submission_mechanics", "questions_and_prebid", "teaming_rules",
        "prime_platform_qualification", "security_compliance", "staffing_capacity",
        "pricing_forms", "paid_specialist_workshare",
    }
    for row in reqs["requirements"]:
        if row["id"] in positive:
            row["state"] = "PROVEN"
            row["evidence"] = [f"ev-{row['id']}"]
    return ledger, reqs, copy.deepcopy(BASE_PARTNERS), copy.deepcopy(BASE_SCOPE)


class StatefulDict(dict):
    pass


class ObservabilityPursuitTests(unittest.TestCase):
    def hist(self, l=None, r=None, p=None, s=None):
        return compile_pursuit(
            l if l is not None else BASE_LEDGER,
            r if r is not None else BASE_REQS,
            p if p is not None else BASE_PARTNERS,
            s if s is not None else BASE_SCOPE,
            now=NOW,
        )

    def test_current_carrier_holds_and_verifies(self):
        out = compile_current(BASE_LEDGER, BASE_REQS, BASE_PARTNERS, BASE_SCOPE)
        self.assertEqual(out["decision"], "HOLD")
        self.assertIn("CONTROLLING_PACKAGE_NOT_RETAINED", out["reasons"])
        self.assertEqual(out["authenticated_source_ids"], [])
        self.assertFalse(any(out["external_authority"].values()))
        self.assertTrue(verify_pursuit(out, BASE_LEDGER, BASE_REQS, BASE_PARTNERS, BASE_SCOPE))

    def test_historical_replay_is_diagnostic_only(self):
        out = self.hist()
        self.assertEqual(out["evaluation_mode"], "HISTORICAL_CALLER_TIME")
        self.assertEqual(out["decision"], "HOLD")
        self.assertTrue(verify_pursuit(out, BASE_LEDGER, BASE_REQS, BASE_PARTNERS, BASE_SCOPE))

    def test_caller_retained_package_cannot_self_authenticate(self):
        bad = copy.deepcopy(BASE_LEDGER)
        next(x for x in bad["sources"] if x["id"] == "idoa-bid-package")["retained"] = True
        with self.assertRaisesRegex(GateError, "not authenticated"):
            self.hist(l=bad)

    def test_arbitrary_evidence_id_cannot_mint_proven(self):
        bad = copy.deepcopy(BASE_REQS)
        row = next(x for x in bad["requirements"] if x["id"] == "security_compliance")
        row["state"], row["evidence"] = "PROVEN", ["forged"]
        with self.assertRaisesRegex(GateError, "not authenticated"):
            self.hist(r=bad)

    def test_proven_requires_evidence(self):
        bad = copy.deepcopy(BASE_REQS)
        row = next(x for x in bad["requirements"] if x["id"] == "security_compliance")
        row["state"] = "PROVEN"
        with self.assertRaisesRegex(GateError, "requires retained evidence"):
            self.hist(r=bad)

    def test_nonproven_cannot_smuggle_evidence(self):
        bad = copy.deepcopy(BASE_REQS)
        row = next(x for x in bad["requirements"] if x["id"] == "security_compliance")
        row["evidence"] = ["forged"]
        with self.assertRaisesRegex(GateError, "non-PROVEN"):
            self.hist(r=bad)

    def test_mirror_cannot_control(self):
        bad = copy.deepcopy(BASE_LEDGER)
        mirror = next(x for x in bad["sources"] if x["authority"] == "DISCOVERY_MIRROR")
        mirror["retained"], mirror["controls"] = True, ["submission_mechanics"]
        with self.assertRaisesRegex(GateError, "not authenticated"):
            self.hist(l=bad)

    def test_partner_and_scope_never_self_authorize(self):
        p = copy.deepcopy(BASE_PARTNERS)
        p["targets"][0]["contact_authority"] = True
        with self.assertRaisesRegex(GateError, "contact"):
            self.hist(p=p)
        s = copy.deepcopy(BASE_SCOPE)
        s["price_usd"] = 25000
        with self.assertRaisesRegex(GateError, "price"):
            self.hist(s=s)

    def test_strict_json_and_stateful_mapping_fail(self):
        with self.assertRaisesRegex(GateError, "duplicate JSON key"):
            loads_strict('{"x":1,"x":2}')
        with self.assertRaisesRegex(GateError, "non-finite"):
            loads_strict('{"x":NaN}')
        with self.assertRaisesRegex(GateError, "exact built-in JSON"):
            compile_current(StatefulDict(BASE_LEDGER), BASE_REQS, BASE_PARTNERS, BASE_SCOPE)

    def test_manifest_pin_is_out_of_band(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "authority_manifest.json").write_text('{"schema":"tampered"}\n', encoding="utf-8")
            with self.assertRaisesRegex(GateError, "source-literal pinned root"):
                gate._parse_authority((root / "authority_manifest.json").read_bytes(), root, "0" * 64)

    def test_retained_source_digest_is_verified(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw, _ = write_synthetic_authority(root)
            (root / "retained" / "bid.zip").write_bytes(b"tampered\n")
            with self.assertRaisesRegex(GateError, "digest mismatch"):
                gate._parse_authority(raw, root, hashlib.sha256(raw).hexdigest())

    def test_authenticated_positive_path_is_nonvacuous_and_bound(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw, _ = write_synthetic_authority(root)
            authority = gate._parse_authority(raw, root, hashlib.sha256(raw).hexdigest())
            inputs = synthetic_inputs()
            out = gate._compile(
                *inputs, authority=authority,
                evaluation_dt=datetime(2026, 9, 17, 20, 0, tzinfo=timezone.utc), current=True,
            )
            self.assertEqual(out["decision"], "TEAMING_REVIEW_READY")
            self.assertTrue(out["package_retained"])
            self.assertEqual(set(out["authenticated_source_ids"]), {"idoa-bid-package", "owner-capability-evidence"})

            bad = copy.deepcopy(inputs[1])
            security = next(x for x in bad["requirements"] if x["id"] == "security_compliance")
            security["evidence"] = ["ev-prime_platform_qualification"]
            with self.assertRaisesRegex(GateError, "another requirement"):
                gate._compile(
                    inputs[0], bad, inputs[2], inputs[3], authority=authority,
                    evaluation_dt=datetime(2026, 9, 17, 20, 0, tzinfo=timezone.utc), current=True,
                )

    def test_historical_positive_evidence_still_cannot_authorize_current(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw, _ = write_synthetic_authority(root)
            authority = gate._parse_authority(raw, root, hashlib.sha256(raw).hexdigest())
            out = gate._compile(
                *synthetic_inputs(), authority=authority,
                evaluation_dt=datetime(2026, 9, 17, 20, 0, tzinfo=timezone.utc), current=False,
            )
            self.assertEqual(out["decision"], "HOLD")
            self.assertIn("HISTORICAL_EVALUATION_NOT_CURRENT", out["reasons"])

    def test_semantic_receipt_tamper_fails(self):
        out = compile_current(BASE_LEDGER, BASE_REQS, BASE_PARTNERS, BASE_SCOPE)
        bad = copy.deepcopy(out)
        bad["decision"] = "PRIME_REVIEW_READY"
        self.assertFalse(verify_pursuit(bad, BASE_LEDGER, BASE_REQS, BASE_PARTNERS, BASE_SCOPE))

    def test_public_current_functions_capture_authority_and_clock_generation(self):
        old_loader, old_datetime = gate._load_authority, gate.datetime
        try:
            gate._load_authority = lambda: (_ for _ in ()).throw(AssertionError("rebound loader used"))
            gate.datetime = object()
            out = gate.compile_current(BASE_LEDGER, BASE_REQS, BASE_PARTNERS, BASE_SCOPE)
            self.assertEqual(out["decision"], "HOLD")
            self.assertTrue(gate.verify_pursuit(out, BASE_LEDGER, BASE_REQS, BASE_PARTNERS, BASE_SCOPE))
        finally:
            gate._load_authority, gate.datetime = old_loader, old_datetime


if __name__ == "__main__":
    unittest.main(verbosity=2)
