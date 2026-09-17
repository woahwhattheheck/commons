import copy
import hashlib
import pathlib
import tempfile
import unittest

import opportunities.hamilton_oh_data_integration_hub_065_26_jw.gate as gate

GateError = gate.GateError
compile_pursuit = gate.compile_pursuit
verify_receipt = gate.verify_receipt
digest = gate.digest
loads_strict = gate.loads_strict
canonical_bytes = gate.canonical_bytes

PACKAGE = pathlib.Path(gate.__file__).resolve().parent
RETAINED = PACKAGE / "retained_evidence"
CREATED = []

BASE_LEDGER = {
    "opportunity_id": "065-26/JW",
    "sources": [
        {"id": "portal", "authority": "OFFICIAL_PORTAL_ENTRY", "retrieved": False,
         "url": "https://hamiltoncountyohio.gob2g.com/", "observed_at": "2026-09-17T07:05:00Z",
         "claims": {}, "controls": []},
        {"id": "mirror", "authority": "MIRROR", "retrieved": True,
         "content_sha256": "a" * 64, "url": "https://example.invalid/mirror",
         "observed_at": "2026-09-17T07:05:00Z",
         "claims": {"response_deadline": "2099-10-14T11:00:00-04:00",
                    "teaming_rules": True, "submission_mechanics": "portal"},
         "controls": []},
    ],
}
IDS = (
    "submission_mechanics", "eligibility", "security_compliance",
    "past_performance", "insurance_legal", "pricing",
    "integration_engineering", "validation_evidence", "delivery_capacity",
    "partner_prime",
)
BASE_REQS = {"opportunity_id": "065-26/JW",
             "requirements": [{"id": rid, "state": "UNKNOWN", "evidence": []} for rid in IDS]}
BASE_EVIDENCE = {"opportunity_id": "065-26/JW", "evidence": []}
KIND = {
    "OWNER_QUALIFICATION": "OWNER_QUALIFICATION_RECORD",
    "OWNER_PRICING": "OWNER_PRICING_RECORD",
    "OWNER_CAPABILITY": "OWNER_CAPABILITY_RECORD",
    "OWNER_CAPACITY": "OWNER_CAPACITY_RECORD",
    "PARTNER_DUE_DILIGENCE": "PARTNER_DUE_DILIGENCE_RECORD",
}


def tearDownModule():
    for path in CREATED:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def row(reqs, rid):
    return next(item for item in reqs["requirements"] if item["id"] == rid)


def official(ledger, deadline="2026-10-14T11:00:00-04:00", teaming=True):
    out = copy.deepcopy(ledger)
    claims = {"teaming_rules": teaming, "submission_mechanics": "official portal"}
    controls = ["teaming_rules", "submission_mechanics"]
    if deadline is not None:
        claims["response_deadline"] = deadline
        controls.append("response_deadline")
    out["sources"].append({
        "id": "packet", "authority": "OFFICIAL_CONTROLLING_PACKET",
        "retrieved": True, "content_sha256": "b" * 64,
        "url": "https://hamiltoncountyohio.gob2g.com/packet",
        "observed_at": "2026-09-18T00:00:00Z",
        "claims": claims, "controls": controls,
    })
    return out


def retained(source_id, rid, evidence_class, facts=None, refs=None):
    record = {
        "schema": "hamilton-065-26-jw-evidence/v2",
        "source_id": source_id,
        "opportunity_id": "065-26/JW",
        "binding": {"requirement_id": rid, "evidence_class": evidence_class},
        "evidence": {
            "kind": KIND[evidence_class],
            "facts": facts if facts is not None else [f"source-controlled test evidence for {rid}"],
            "refs": refs if refs is not None else [f"fixture://{rid}"],
        },
    }
    RETAINED.mkdir(exist_ok=True)
    fh = tempfile.NamedTemporaryFile(mode="wb", dir=RETAINED, prefix="test-", suffix=".json", delete=False)
    path = pathlib.Path(fh.name)
    raw = canonical_bytes(record) + b"\n"
    fh.write(raw)
    fh.close()
    CREATED.append(path)
    return path, hashlib.sha256(raw).hexdigest()


def bind(ledger, reqs, manifest, rid, evidence_class, eid=None, source_id=None):
    eid = eid or f"evidence-{rid}"
    if evidence_class == "OFFICIAL_REQUIREMENT":
        source_id = source_id or "packet"
        source = next(item for item in ledger["sources"] if item["id"] == source_id)
        sha = source["content_sha256"]
    else:
        source_id = source_id or f"source-{eid}"
        path, sha = retained(source_id, rid, evidence_class)
        ledger["sources"].append({
            "id": source_id, "authority": "INTERNAL_EVIDENCE", "retrieved": True,
            "content_sha256": sha,
            "retained_artifact": {"path": f"retained_evidence/{path.name}", "sha256": sha},
            "url": f"repo://retained_evidence/{path.name}",
            "observed_at": "2026-09-18T00:00:00Z", "claims": {}, "controls": [],
        })
    manifest["evidence"].append({
        "id": eid, "opportunity_id": "065-26/JW", "requirement_id": rid,
        "evidence_class": evidence_class, "content_sha256": sha, "source_id": source_id,
    })
    row(reqs, rid).update({"state": "PROVEN", "evidence": [eid]})
    return eid


def prime_inputs(deadline="2026-10-14T11:00:00-04:00"):
    ledger, reqs, manifest = official(BASE_LEDGER, deadline), copy.deepcopy(BASE_REQS), copy.deepcopy(BASE_EVIDENCE)
    for rid in ("submission_mechanics", "eligibility", "security_compliance", "insurance_legal", "pricing"):
        bind(ledger, reqs, manifest, rid, "OFFICIAL_REQUIREMENT", f"official-{rid}", "packet")
    bind(ledger, reqs, manifest, "past_performance", "OWNER_QUALIFICATION")
    return ledger, reqs, manifest


def team_inputs(deadline="2026-10-14T11:00:00-04:00", teaming=True):
    ledger, reqs, manifest = official(BASE_LEDGER, deadline, teaming), copy.deepcopy(BASE_REQS), copy.deepcopy(BASE_EVIDENCE)
    for rid, cls in (
        ("integration_engineering", "OWNER_CAPABILITY"),
        ("validation_evidence", "OWNER_CAPABILITY"),
        ("delivery_capacity", "OWNER_CAPACITY"),
        ("partner_prime", "PARTNER_DUE_DILIGENCE"),
    ):
        bind(ledger, reqs, manifest, rid, cls)
    return ledger, reqs, manifest


class HamiltonPursuitGateTests(unittest.TestCase):
    def test_baseline_and_semantic_receipt(self):
        packet = compile_pursuit(BASE_LEDGER, BASE_REQS, BASE_EVIDENCE, now="2026-09-17T07:05:00Z")
        self.assertEqual(packet["decision"], "HOLD")
        self.assertIn("CONTROLLING_PACKET_NOT_ACQUIRED", packet["reasons"])
        self.assertIn("RESPONSE_DEADLINE_UNCONTROLLED", packet["reasons"])
        self.assertFalse(packet["authority"]["mirror_can_control_buyer_terms"])
        self.assertTrue(verify_receipt(packet, BASE_LEDGER, BASE_REQS, BASE_EVIDENCE, now="2026-09-17T07:05:00Z"))

    def test_mirror_cannot_control_buyer_fields(self):
        bad = copy.deepcopy(BASE_LEDGER)
        bad["sources"][1]["controls"] = ["response_deadline"]
        with self.assertRaisesRegex(GateError, "cannot control buyer fields"):
            compile_pursuit(bad, BASE_REQS, BASE_EVIDENCE, now="2026-09-17T07:05:00Z")

    def test_arbitrary_evidence_ref_fails(self):
        reqs = copy.deepcopy(BASE_REQS)
        row(reqs, "integration_engineering").update({"state": "PROVEN", "evidence": ["made-up"]})
        with self.assertRaisesRegex(GateError, "evidence ref not retained"):
            compile_pursuit(BASE_LEDGER, reqs, BASE_EVIDENCE, now="2026-09-17T07:05:00Z")

    def test_repository_retained_internal_positive_path(self):
        ledger, reqs, manifest = official(BASE_LEDGER), copy.deepcopy(BASE_REQS), copy.deepcopy(BASE_EVIDENCE)
        bind(ledger, reqs, manifest, "integration_engineering", "OWNER_CAPABILITY")
        packet = compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")
        self.assertEqual(packet["evidence_bindings"]["integration_engineering"], ["evidence-integration_engineering"])
        self.assertEqual(packet["decision"], "HOLD")

    def test_inline_self_authored_wrappers_fail_for_all_internal_authority_classes(self):
        cases = (
            ("past_performance", "OWNER_QUALIFICATION"),
            ("integration_engineering", "OWNER_CAPABILITY"),
            ("delivery_capacity", "OWNER_CAPACITY"),
            ("partner_prime", "PARTNER_DUE_DILIGENCE"),
        )
        for rid, cls in cases:
            with self.subTest(rid=rid):
                ledger, reqs, manifest = official(BASE_LEDGER), copy.deepcopy(BASE_REQS), copy.deepcopy(BASE_EVIDENCE)
                sid, eid = f"source-{rid}", f"evidence-{rid}"
                wrapper = {"schema": "hamilton-065-26-jw-evidence/v1", "source_id": sid,
                           "opportunity_id": "065-26/JW",
                           "bindings": [{"requirement_id": rid, "evidence_class": cls}]}
                sha = digest(wrapper)
                ledger["sources"].append({
                    "id": sid, "authority": "INTERNAL_EVIDENCE", "retrieved": True,
                    "content_sha256": sha, "retained_artifact": wrapper,
                    "url": f"repo://retained/{rid}", "observed_at": "2026-09-18T00:00:00Z",
                    "claims": {}, "controls": [],
                })
                manifest["evidence"].append({
                    "id": eid, "opportunity_id": "065-26/JW", "requirement_id": rid,
                    "evidence_class": cls, "content_sha256": sha, "source_id": sid,
                })
                row(reqs, rid).update({"state": "PROVEN", "evidence": [eid]})
                with self.assertRaisesRegex(GateError, "exact path and sha256 fields"):
                    compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")

    def test_missing_file_and_path_escape_fail(self):
        for path_text, regex in (
            ("retained_evidence/missing.json", "not retained in source tree"),
            ("../outside.json", "stay under retained_evidence"),
        ):
            with self.subTest(path=path_text):
                ledger, reqs, manifest = official(BASE_LEDGER), copy.deepcopy(BASE_REQS), copy.deepcopy(BASE_EVIDENCE)
                sid, eid, sha = "source-x", "evidence-x", "c" * 64
                ledger["sources"].append({
                    "id": sid, "authority": "INTERNAL_EVIDENCE", "retrieved": True,
                    "content_sha256": sha, "retained_artifact": {"path": path_text, "sha256": sha},
                    "url": "repo://x", "observed_at": "2026-09-18T00:00:00Z", "claims": {}, "controls": [],
                })
                manifest["evidence"].append({
                    "id": eid, "opportunity_id": "065-26/JW",
                    "requirement_id": "integration_engineering", "evidence_class": "OWNER_CAPABILITY",
                    "content_sha256": sha, "source_id": sid,
                })
                row(reqs, "integration_engineering").update({"state": "PROVEN", "evidence": [eid]})
                with self.assertRaisesRegex(GateError, regex):
                    compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")

    def test_retained_byte_drift_fails(self):
        ledger, reqs, manifest = official(BASE_LEDGER), copy.deepcopy(BASE_REQS), copy.deepcopy(BASE_EVIDENCE)
        bind(ledger, reqs, manifest, "integration_engineering", "OWNER_CAPABILITY")
        source = next(x for x in ledger["sources"] if x["id"] == "source-evidence-integration_engineering")
        path = PACKAGE / source["retained_artifact"]["path"]
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaisesRegex(GateError, "does not authenticate retained file bytes"):
            compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")

    def test_empty_generic_retained_record_fails(self):
        ledger, reqs, manifest = official(BASE_LEDGER), copy.deepcopy(BASE_REQS), copy.deepcopy(BASE_EVIDENCE)
        sid, rid = "source-empty", "integration_engineering"
        path, sha = retained(sid, rid, "OWNER_CAPABILITY", facts=[], refs=[])
        ledger["sources"].append({
            "id": sid, "authority": "INTERNAL_EVIDENCE", "retrieved": True,
            "content_sha256": sha, "retained_artifact": {"path": f"retained_evidence/{path.name}", "sha256": sha},
            "url": "repo://empty", "observed_at": "2026-09-18T00:00:00Z", "claims": {}, "controls": [],
        })
        manifest["evidence"].append({
            "id": "evidence-empty", "opportunity_id": "065-26/JW", "requirement_id": rid,
            "evidence_class": "OWNER_CAPABILITY", "content_sha256": sha, "source_id": sid,
        })
        row(reqs, rid).update({"state": "PROVEN", "evidence": ["evidence-empty"]})
        with self.assertRaisesRegex(GateError, "non-empty bounded string array"):
            compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")

    def test_cross_opportunity_wrong_class_and_digest_transplants_fail(self):
        mutators = (
            (lambda m: m["evidence"][0].__setitem__("opportunity_id", "OTHER"), "opportunity_id mismatch"),
            (lambda m: m["evidence"][0].__setitem__("evidence_class", "PARTNER_DUE_DILIGENCE"), "not admissible"),
            (lambda m: m["evidence"][0].__setitem__("content_sha256", "9" * 64), "does not bind source"),
        )
        for mutate, regex in mutators:
            ledger, reqs, manifest = team_inputs()
            mutate(manifest)
            with self.subTest(regex=regex), self.assertRaisesRegex(GateError, regex):
                compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")

    def test_requirement_relabel_fails_against_retained_record(self):
        ledger, reqs, manifest = team_inputs()
        manifest["evidence"][0]["requirement_id"] = "validation_evidence"
        with self.assertRaisesRegex(GateError, "repository-retained evidence binding"):
            compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")

    def test_official_class_cannot_bind_internal_source(self):
        ledger, reqs, manifest = official(BASE_LEDGER), copy.deepcopy(BASE_REQS), copy.deepcopy(BASE_EVIDENCE)
        bind(ledger, reqs, manifest, "eligibility", "OWNER_QUALIFICATION")
        manifest["evidence"][0]["evidence_class"] = "OFFICIAL_REQUIREMENT"
        with self.assertRaisesRegex(GateError, "official evidence must bind official"):
            compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")

    def test_retained_evidence_cannot_disappear(self):
        ledger, reqs, manifest = team_inputs()
        row(reqs, "integration_engineering").update({"state": "UNKNOWN", "evidence": []})
        with self.assertRaisesRegex(GateError, "no matching PROVEN requirement"):
            compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")

    def test_prime_requires_real_bound_internal_evidence_and_future_deadline(self):
        ledger, reqs, manifest = prime_inputs()
        packet = compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")
        self.assertEqual(packet["decision"], "PRIME")
        self.assertEqual(packet["gaps"]["prime"], [])
        self.assertEqual(packet["authority"]["response_deadline_source"], "packet")
        self.assertTrue(packet["evidence_bindings"]["past_performance"])
        self.assertTrue(verify_receipt(packet, ledger, reqs, manifest, now="2026-09-18T01:00:00Z"))

    def test_prime_without_deadline_holds(self):
        ledger, reqs, manifest = prime_inputs(None)
        packet = compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")
        self.assertEqual(packet["decision"], "HOLD")
        self.assertIn("RESPONSE_DEADLINE_UNCONTROLLED", packet["reasons"])

    def test_teaming_requires_permission_evidence_partner_and_deadline(self):
        ledger, reqs, manifest = team_inputs()
        packet = compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")
        self.assertEqual(packet["decision"], "TEAMING")
        self.assertIn("PRIME_GATES_UNPROVEN", packet["reasons"])

    def test_teaming_without_deadline_or_permission_holds(self):
        for deadline, teaming, reason in (
            (None, True, "RESPONSE_DEADLINE_UNCONTROLLED"),
            ("2026-10-14T11:00:00-04:00", False, "TEAMING_NOT_ALLOWED_BY_RETAINED_OFFICIAL_AUTHORITY"),
        ):
            ledger, reqs, manifest = team_inputs(deadline, teaming)
            packet = compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")
            self.assertEqual(packet["decision"], "HOLD")
            self.assertIn(reason, packet["reasons"])

    def test_passed_official_deadline_is_no_bid(self):
        ledger = official(BASE_LEDGER, "2026-09-17T01:00:00-04:00")
        packet = compile_pursuit(ledger, BASE_REQS, BASE_EVIDENCE, now="2026-09-17T07:05:00Z")
        self.assertEqual(packet["decision"], "NO_BID")
        self.assertIn("OFFICIAL_RESPONSE_DEADLINE_PASSED", packet["reasons"])

    def test_rehashed_forged_prime_revenue_fails_semantic_verify(self):
        ledger, reqs, manifest = team_inputs()
        packet = compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")
        forged = copy.deepcopy(packet)
        forged["decision"] = "PRIME"
        forged["external_authority"]["revenue"] = True
        forged.pop("receipt_sha256")
        forged["receipt_sha256"] = digest(forged)
        self.assertFalse(verify_receipt(forged, ledger, reqs, manifest, now="2026-09-18T01:00:00Z"))

    def test_semantic_verify_binds_evaluation_time(self):
        ledger, reqs, manifest = prime_inputs("2026-09-18T02:00:00Z")
        packet = compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")
        self.assertFalse(verify_receipt(packet, ledger, reqs, manifest, now="2026-09-18T03:00:00Z"))

    def test_json_and_type_hostiles(self):
        with self.assertRaisesRegex(GateError, "duplicate JSON key"):
            loads_strict('{"x":1,"x":2}')
        with self.assertRaisesRegex(GateError, "non-finite"):
            loads_strict('{"x":NaN}')
        bad = copy.deepcopy(BASE_LEDGER)
        bad["sources"][0]["retrieved"] = 1
        with self.assertRaisesRegex(GateError, "JSON boolean"):
            compile_pursuit(bad, BASE_REQS, BASE_EVIDENCE, now="2026-09-17T07:05:00Z")

    def test_conflicting_official_authority_fails(self):
        ledger = official(BASE_LEDGER)
        other = copy.deepcopy(ledger["sources"][-1])
        other.update({"id": "addendum", "authority": "OFFICIAL_ADDENDUM", "content_sha256": "d" * 64})
        other["claims"]["response_deadline"] = "2026-10-15T11:00:00-04:00"
        ledger["sources"].append(other)
        with self.assertRaisesRegex(GateError, "conflicting official authority"):
            compile_pursuit(ledger, BASE_REQS, BASE_EVIDENCE, now="2026-09-18T01:00:00Z")

    def test_external_authority_always_false(self):
        ledger, reqs, manifest = prime_inputs()
        packet = compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")
        self.assertTrue(packet["external_authority"])
        self.assertFalse(any(packet["external_authority"].values()))


if __name__ == "__main__":
    unittest.main()
