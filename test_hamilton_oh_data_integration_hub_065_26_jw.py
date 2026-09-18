from __future__ import annotations

import copy
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import MappingProxyType

import opportunities.hamilton_oh_data_integration_hub_065_26_jw.gate as gate

GateError = gate.GateError
compile_pursuit = gate.compile_pursuit
verify_receipt = gate.verify_receipt

PACKAGE = Path(gate.__file__).resolve().parent
RETAINED = PACKAGE / "retained_evidence"
_OFFICIAL_CREATED: list[Path] = []
IDS = (
    "submission_mechanics", "eligibility", "security_compliance", "past_performance",
    "insurance_legal", "pricing", "integration_engineering", "validation_evidence",
    "delivery_capacity", "partner_prime",
)
KIND = {
    "OWNER_QUALIFICATION": "OWNER_QUALIFICATION_RECORD",
    "OWNER_PRICING": "OWNER_PRICING_RECORD",
    "OWNER_CAPABILITY": "OWNER_CAPABILITY_RECORD",
    "OWNER_CAPACITY": "OWNER_CAPACITY_RECORD",
    "PARTNER_DUE_DILIGENCE": "PARTNER_DUE_DILIGENCE_RECORD",
}
BASE_LEDGER = {
    "opportunity_id": "065-26/JW",
    "sources": [
        {
            "id": "portal", "authority": "OFFICIAL_PORTAL_ENTRY", "retrieved": False,
            "url": "https://hamiltoncountyohio.gob2g.com/",
            "observed_at": "2026-09-17T07:05:00Z", "claims": {}, "controls": [],
        },
        {
            "id": "mirror", "authority": "MIRROR", "retrieved": True,
            "content_sha256": "a" * 64, "url": "https://example.invalid/mirror",
            "observed_at": "2026-09-17T07:05:00Z",
            "claims": {
                "response_deadline": "2099-10-14T11:00:00-04:00",
                "teaming_rules": True, "submission_mechanics": "portal",
            },
            "controls": [],
        },
    ],
}
BASE_REQS = {
    "opportunity_id": "065-26/JW",
    "requirements": [{"id": rid, "state": "UNKNOWN", "evidence": []} for rid in IDS],
}
BASE_EVIDENCE = {"opportunity_id": "065-26/JW", "evidence": []}


def row(reqs, rid):
    return next(item for item in reqs["requirements"] if item["id"] == rid)


def _admit_test_leaf(path: Path, sha: str) -> None:
    current = dict(gate.SOURCE_OWNED_RETAINED_EVIDENCE)
    current[path.name] = sha
    gate.SOURCE_OWNED_RETAINED_EVIDENCE = MappingProxyType(current)


def official(
    ledger,
    deadline="2026-10-14T11:00:00-04:00",
    teaming=True,
    *,
    source_id="packet",
    authority="OFFICIAL_CONTROLLING_PACKET",
):
    """Create a genuinely retained/pinned official fixture for positive tests.

    This is trusted-process test setup that simulates the source-code admission a
    real official artifact would require. Production's source-owned map is empty.
    """
    out = copy.deepcopy(ledger)
    claims = {"teaming_rules": teaming, "submission_mechanics": "official portal"}
    controls = ["teaming_rules", "submission_mechanics"]
    if deadline is not None:
        claims["response_deadline"] = deadline
        controls.append("response_deadline")
    url = f"https://hamiltoncountyohio.gob2g.com/{source_id}"
    observed_at = "2026-09-18T00:00:00Z"
    record = {
        "schema": gate.OFFICIAL_ARTIFACT_SCHEMA,
        "source_id": source_id,
        "opportunity_id": gate.OPPORTUNITY_ID,
        "authority": authority,
        "url": url,
        "observed_at": observed_at,
        "claims": claims,
        "controls": controls,
    }
    RETAINED.mkdir(exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb", dir=RETAINED, prefix=f"test-{source_id}-", suffix=".json", delete=False
    ) as fh:
        path = Path(fh.name)
        raw = gate.canonical_bytes(record) + b"\n"
        fh.write(raw)
    _OFFICIAL_CREATED.append(path)
    sha = hashlib.sha256(raw).hexdigest()
    _admit_test_leaf(path, sha)
    out["sources"].append({
        "id": source_id,
        "authority": authority,
        "retrieved": True,
        "content_sha256": sha,
        "retained_artifact": {
            "path": f"retained_evidence/{path.name}",
            "sha256": sha,
        },
        "url": url,
        "observed_at": observed_at,
        "claims": claims,
        "controls": controls,
    })
    return out


class HamiltonPursuitGateTests(unittest.TestCase):
    def setUp(self):
        self._original_index = gate.SOURCE_OWNED_RETAINED_EVIDENCE
        self.created: list[Path] = []
        self.pins: dict[str, str] = {}
        _OFFICIAL_CREATED.clear()

    def tearDown(self):
        gate.SOURCE_OWNED_RETAINED_EVIDENCE = self._original_index
        for path in self.created + list(_OFFICIAL_CREATED):
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        _OFFICIAL_CREATED.clear()

    def _retained(self, source_id, rid, evidence_class, *, facts=None, refs=None, pin=True):
        record = {
            "schema": gate.EVIDENCE_ARTIFACT_SCHEMA,
            "source_id": source_id,
            "opportunity_id": gate.OPPORTUNITY_ID,
            "binding": {"requirement_id": rid, "evidence_class": evidence_class},
            "evidence": {
                "kind": KIND[evidence_class],
                "facts": facts if facts is not None else [f"reviewed test evidence for {rid}"],
                "refs": refs if refs is not None else [f"fixture://{rid}"],
            },
        }
        RETAINED.mkdir(exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=RETAINED, prefix="test-", suffix=".json", delete=False
        ) as fh:
            path = Path(fh.name)
            raw = gate.canonical_bytes(record) + b"\n"
            fh.write(raw)
        self.created.append(path)
        sha = hashlib.sha256(raw).hexdigest()
        if pin:
            self.pins[path.name] = sha
            _admit_test_leaf(path, sha)
        return path, sha

    def _bind(
        self, ledger, reqs, manifest, rid, evidence_class,
        *, eid=None, source_id=None, pin=True,
    ):
        eid = eid or f"evidence-{rid}"
        if evidence_class == "OFFICIAL_REQUIREMENT":
            source_id = source_id or "packet"
            source = next(item for item in ledger["sources"] if item["id"] == source_id)
            sha = source["content_sha256"]
        else:
            source_id = source_id or f"source-{eid}"
            path, sha = self._retained(source_id, rid, evidence_class, pin=pin)
            ledger["sources"].append({
                "id": source_id, "authority": "INTERNAL_EVIDENCE", "retrieved": True,
                "content_sha256": sha,
                "retained_artifact": {
                    "path": f"retained_evidence/{path.name}", "sha256": sha,
                },
                "url": f"repo://retained_evidence/{path.name}",
                "observed_at": "2026-09-18T00:00:00Z", "claims": {}, "controls": [],
            })
        manifest["evidence"].append({
            "id": eid, "opportunity_id": gate.OPPORTUNITY_ID,
            "requirement_id": rid, "evidence_class": evidence_class,
            "content_sha256": sha, "source_id": source_id,
        })
        row(reqs, rid).update({"state": "PROVEN", "evidence": [eid]})
        return eid

    def _prime_inputs(self, deadline="2026-10-14T11:00:00-04:00"):
        ledger = official(BASE_LEDGER, deadline)
        reqs = copy.deepcopy(BASE_REQS)
        manifest = copy.deepcopy(BASE_EVIDENCE)
        self._bind(
            ledger, reqs, manifest, "submission_mechanics", "OFFICIAL_REQUIREMENT",
            eid="official-submission", source_id="packet",
        )
        for rid in ("eligibility", "security_compliance", "past_performance", "insurance_legal"):
            self._bind(ledger, reqs, manifest, rid, "OWNER_QUALIFICATION")
        self._bind(ledger, reqs, manifest, "pricing", "OWNER_PRICING")
        return ledger, reqs, manifest

    def _team_inputs(self, deadline="2026-10-14T11:00:00-04:00", teaming=True):
        ledger = official(BASE_LEDGER, deadline, teaming)
        reqs = copy.deepcopy(BASE_REQS)
        manifest = copy.deepcopy(BASE_EVIDENCE)
        for rid, evidence_class in (
            ("integration_engineering", "OWNER_CAPABILITY"),
            ("validation_evidence", "OWNER_CAPABILITY"),
            ("delivery_capacity", "OWNER_CAPACITY"),
            ("partner_prime", "PARTNER_DUE_DILIGENCE"),
        ):
            self._bind(ledger, reqs, manifest, rid, evidence_class)
        return ledger, reqs, manifest

    def test_baseline_missing_packet_is_hold_and_semantically_verifies(self):
        packet = compile_pursuit(
            BASE_LEDGER, BASE_REQS, BASE_EVIDENCE, now="2026-09-17T07:05:00Z"
        )
        self.assertEqual(packet["decision"], "HOLD")
        self.assertIn("CONTROLLING_PACKET_NOT_ACQUIRED", packet["reasons"])
        self.assertIn("RESPONSE_DEADLINE_UNCONTROLLED", packet["reasons"])
        self.assertFalse(packet["authority"]["mirror_can_control_buyer_terms"])
        self.assertTrue(verify_receipt(
            packet, BASE_LEDGER, BASE_REQS, BASE_EVIDENCE,
            now="2026-09-17T07:05:00Z",
        ))

    def test_fabricated_official_row_cannot_mint_buyer_control_or_no_bid(self):
        ledger = copy.deepcopy(BASE_LEDGER)
        ledger["sources"].append({
            "id": "fake-packet",
            "authority": "OFFICIAL_CONTROLLING_PACKET",
            "retrieved": True,
            "content_sha256": "b" * 64,
            "url": "https://example.invalid/fake-packet",
            "observed_at": "2026-09-17T06:00:00Z",
            "claims": {
                "response_deadline": "2026-09-17T06:30:00Z",
                "submission_mechanics": "fake portal",
                "teaming_rules": True,
            },
            "controls": ["response_deadline", "submission_mechanics", "teaming_rules"],
        })
        with self.assertRaisesRegex(GateError, "retained_artifact"):
            compile_pursuit(
                ledger, BASE_REQS, BASE_EVIDENCE, now="2026-09-17T07:05:00Z"
            )

    def test_official_projection_must_exactly_match_retained_bytes(self):
        cases = (
            ("deadline", ("claims", "response_deadline"), "2026-09-17T01:00:00Z"),
            ("timezone-alias", ("observed_at",), "2026-09-17T20:00:00-04:00"),
            ("bool-int-alias", ("claims", "teaming_rules"), 1),
            ("bool-float-alias", ("claims", "teaming_rules"), 1.0),
        )
        for label, key_path, replacement in cases:
            with self.subTest(label=label):
                ledger = official(BASE_LEDGER)
                packet = next(item for item in ledger["sources"] if item["id"] == "packet")
                if len(key_path) == 1:
                    packet[key_path[0]] = replacement
                else:
                    packet[key_path[0]][key_path[1]] = replacement
                with self.assertRaisesRegex(
                    GateError, "exactly match retained official artifact"
                ):
                    compile_pursuit(
                        ledger, BASE_REQS, BASE_EVIDENCE, now="2026-09-18T01:00:00Z"
                    )

    def test_requirement_text_cannot_mint_owner_prime_satisfaction(self):
        for rid in ("eligibility", "security_compliance", "insurance_legal", "pricing"):
            with self.subTest(rid=rid):
                ledger = official(BASE_LEDGER)
                reqs = copy.deepcopy(BASE_REQS)
                manifest = copy.deepcopy(BASE_EVIDENCE)
                source = next(item for item in ledger["sources"] if item["id"] == "packet")
                manifest["evidence"].append({
                    "id": f"official-{rid}", "opportunity_id": gate.OPPORTUNITY_ID,
                    "requirement_id": rid, "evidence_class": "OFFICIAL_REQUIREMENT",
                    "content_sha256": source["content_sha256"], "source_id": "packet",
                })
                row(reqs, rid).update({"state": "PROVEN", "evidence": [f"official-{rid}"]})
                with self.assertRaisesRegex(GateError, "evidence_class not admissible"):
                    compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")

    def test_submission_mechanics_may_use_official_requirement_evidence(self):
        ledger = official(BASE_LEDGER)
        reqs = copy.deepcopy(BASE_REQS)
        manifest = copy.deepcopy(BASE_EVIDENCE)
        self._bind(
            ledger, reqs, manifest, "submission_mechanics", "OFFICIAL_REQUIREMENT",
            source_id="packet",
        )
        packet = compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")
        self.assertEqual(packet["decision"], "HOLD")
        self.assertIn("submission_mechanics", packet["evidence_bindings"])

    def test_runtime_planted_single_link_file_is_not_source_owned(self):
        ledger = official(BASE_LEDGER)
        reqs = copy.deepcopy(BASE_REQS)
        manifest = copy.deepcopy(BASE_EVIDENCE)
        self._bind(
            ledger, reqs, manifest, "integration_engineering", "OWNER_CAPABILITY", pin=False
        )
        with self.assertRaisesRegex(GateError, "source-owned evidence index"):
            compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")

    def test_source_pinned_internal_positive_path(self):
        ledger = official(BASE_LEDGER)
        reqs = copy.deepcopy(BASE_REQS)
        manifest = copy.deepcopy(BASE_EVIDENCE)
        self._bind(ledger, reqs, manifest, "integration_engineering", "OWNER_CAPABILITY")
        packet = compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")
        self.assertEqual(packet["decision"], "HOLD")
        self.assertTrue(packet["evidence_bindings"]["integration_engineering"])

    def test_source_index_digest_must_equal_locator_and_source(self):
        ledger = official(BASE_LEDGER)
        reqs = copy.deepcopy(BASE_REQS)
        manifest = copy.deepcopy(BASE_EVIDENCE)
        self._bind(ledger, reqs, manifest, "integration_engineering", "OWNER_CAPABILITY")
        ledger["sources"][-1]["retained_artifact"]["sha256"] = "f" * 64
        with self.assertRaisesRegex(GateError, "digest does not match source-owned"):
            compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")

    def test_pinned_hardlink_alias_is_rejected(self):
        sid = "source-hardlink"
        rid = "integration_engineering"
        evidence_class = "OWNER_CAPABILITY"
        record = {
            "schema": gate.EVIDENCE_ARTIFACT_SCHEMA, "source_id": sid,
            "opportunity_id": gate.OPPORTUNITY_ID,
            "binding": {"requirement_id": rid, "evidence_class": evidence_class},
            "evidence": {
                "kind": KIND[evidence_class],
                "facts": ["outside-owned bytes cannot mint qualification"],
                "refs": ["fixture://hardlink"],
            },
        }
        raw = gate.canonical_bytes(record) + b"\n"
        sha = hashlib.sha256(raw).hexdigest()
        RETAINED.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory() as td:
            outside = Path(td) / "outside.json"
            outside.write_bytes(raw)
            alias = RETAINED / f"test-hardlink-{os.getpid()}.json"
            try:
                os.link(outside, alias)
                self.pins[alias.name] = sha
                _admit_test_leaf(alias, sha)
                ledger = official(BASE_LEDGER)
                reqs = copy.deepcopy(BASE_REQS)
                manifest = copy.deepcopy(BASE_EVIDENCE)
                ledger["sources"].append({
                    "id": sid, "authority": "INTERNAL_EVIDENCE", "retrieved": True,
                    "content_sha256": sha,
                    "retained_artifact": {
                        "path": f"retained_evidence/{alias.name}", "sha256": sha,
                    },
                    "url": f"repo://retained_evidence/{alias.name}",
                    "observed_at": "2026-09-18T00:00:00Z", "claims": {}, "controls": [],
                })
                manifest["evidence"].append({
                    "id": "evidence-hardlink", "opportunity_id": gate.OPPORTUNITY_ID,
                    "requirement_id": rid, "evidence_class": evidence_class,
                    "content_sha256": sha, "source_id": sid,
                })
                row(reqs, rid).update({"state": "PROVEN", "evidence": ["evidence-hardlink"]})
                with self.assertRaisesRegex(GateError, "exactly one filesystem link"):
                    compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")
            finally:
                try:
                    alias.unlink()
                except FileNotFoundError:
                    pass

    def test_retained_byte_drift_fails(self):
        ledger = official(BASE_LEDGER)
        reqs = copy.deepcopy(BASE_REQS)
        manifest = copy.deepcopy(BASE_EVIDENCE)
        self._bind(ledger, reqs, manifest, "integration_engineering", "OWNER_CAPABILITY")
        source = ledger["sources"][-1]
        path = PACKAGE / source["retained_artifact"]["path"]
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaisesRegex(GateError, "does not authenticate retained file bytes"):
            compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")

    def test_path_escape_fails_before_open(self):
        ledger = official(BASE_LEDGER)
        reqs = copy.deepcopy(BASE_REQS)
        manifest = copy.deepcopy(BASE_EVIDENCE)
        sid = "source-escape"
        sha = "c" * 64
        ledger["sources"].append({
            "id": sid, "authority": "INTERNAL_EVIDENCE", "retrieved": True,
            "content_sha256": sha,
            "retained_artifact": {"path": "../outside.json", "sha256": sha},
            "url": "repo://outside", "observed_at": "2026-09-18T00:00:00Z",
            "claims": {}, "controls": [],
        })
        manifest["evidence"].append({
            "id": "escape", "opportunity_id": gate.OPPORTUNITY_ID,
            "requirement_id": "integration_engineering",
            "evidence_class": "OWNER_CAPABILITY", "content_sha256": sha,
            "source_id": sid,
        })
        row(reqs, "integration_engineering").update({"state": "PROVEN", "evidence": ["escape"]})
        with self.assertRaisesRegex(GateError, "stay under retained_evidence"):
            compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")

    def test_prime_requires_owner_specific_bound_evidence(self):
        ledger, reqs, manifest = self._prime_inputs()
        packet = compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")
        self.assertEqual(packet["decision"], "PRIME")
        self.assertEqual(packet["gaps"]["prime"], [])
        self.assertTrue(verify_receipt(
            packet, ledger, reqs, manifest, now="2026-09-18T01:00:00Z"
        ))

    def test_team_requires_bound_specialist_partner_and_permission(self):
        ledger, reqs, manifest = self._team_inputs()
        packet = compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")
        self.assertEqual(packet["decision"], "TEAMING")
        self.assertIn("PRIME_GATES_UNPROVEN", packet["reasons"])

    def test_team_not_allowed_holds(self):
        ledger, reqs, manifest = self._team_inputs(teaming=False)
        packet = compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")
        self.assertEqual(packet["decision"], "HOLD")
        self.assertIn("TEAMING_NOT_ALLOWED_BY_RETAINED_OFFICIAL_AUTHORITY", packet["reasons"])

    def test_missing_or_passed_deadline_blocks_positive_decision(self):
        ledger, reqs, manifest = self._team_inputs(deadline=None)
        packet = compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")
        self.assertEqual(packet["decision"], "HOLD")
        self.assertIn("RESPONSE_DEADLINE_UNCONTROLLED", packet["reasons"])
        ledger = official(BASE_LEDGER, "2026-09-17T01:00:00-04:00")
        packet = compile_pursuit(
            ledger, BASE_REQS, BASE_EVIDENCE, now="2026-09-17T07:05:00Z"
        )
        self.assertEqual(packet["decision"], "NO_BID")
        self.assertIn("OFFICIAL_RESPONSE_DEADLINE_PASSED", packet["reasons"])

    def test_rehashed_forged_prime_and_revenue_fail_semantic_verify(self):
        ledger, reqs, manifest = self._team_inputs()
        packet = compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")
        forged = copy.deepcopy(packet)
        forged["decision"] = "PRIME"
        forged["external_authority"]["revenue"] = True
        forged.pop("receipt_sha256")
        forged["receipt_sha256"] = gate.digest(forged)
        self.assertFalse(verify_receipt(
            forged, ledger, reqs, manifest, now="2026-09-18T01:00:00Z"
        ))

    def test_semantic_verify_binds_evaluation_time(self):
        ledger, reqs, manifest = self._prime_inputs("2026-09-18T02:00:00Z")
        packet = compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")
        self.assertFalse(verify_receipt(
            packet, ledger, reqs, manifest, now="2026-09-18T03:00:00Z"
        ))

    def test_unbound_evidence_and_arbitrary_refs_fail(self):
        reqs = copy.deepcopy(BASE_REQS)
        row(reqs, "integration_engineering").update({"state": "PROVEN", "evidence": ["made-up"]})
        with self.assertRaisesRegex(GateError, "evidence ref not retained"):
            compile_pursuit(BASE_LEDGER, reqs, BASE_EVIDENCE, now="2026-09-17T07:05:00Z")
        ledger = official(BASE_LEDGER)
        reqs = copy.deepcopy(BASE_REQS)
        manifest = copy.deepcopy(BASE_EVIDENCE)
        self._bind(ledger, reqs, manifest, "integration_engineering", "OWNER_CAPABILITY")
        row(reqs, "integration_engineering").update({"state": "UNKNOWN", "evidence": []})
        with self.assertRaisesRegex(GateError, "no matching PROVEN requirement"):
            compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")

    def test_duplicate_keys_nonfinite_and_bool_int_alias_fail(self):
        with self.assertRaisesRegex(GateError, "duplicate JSON key"):
            gate.loads_strict('{"x":1,"x":2}')
        with self.assertRaisesRegex(GateError, "non-finite"):
            gate.loads_strict('{"x":NaN}')
        with self.assertRaisesRegex(GateError, "floating-point"):
            gate.loads_strict('{"x":1.5}')
        bad = copy.deepcopy(BASE_LEDGER)
        bad["sources"][0]["retrieved"] = 1
        with self.assertRaisesRegex(GateError, "JSON boolean"):
            compile_pursuit(bad, BASE_REQS, BASE_EVIDENCE, now="2026-09-17T07:05:00Z")

    def test_raw_json_resource_failures_are_typed_gate_errors(self):
        cases = (
            '{"x":' + ("9" * 5000) + "}",
            ("[" * 1200) + "0" + ("]" * 1200),
            '{"x":"' + ("a" * (gate.MAX_JSON_TEXT_BYTES + 1)) + '"}',
        )
        for raw in cases:
            with self.subTest(prefix=raw[:24]):
                with self.assertRaises(GateError):
                    gate.loads_strict(raw)

    def test_mirror_cannot_control_buyer_fields(self):
        bad = copy.deepcopy(BASE_LEDGER)
        bad["sources"][1]["controls"] = ["response_deadline"]
        with self.assertRaisesRegex(GateError, "cannot control buyer fields"):
            compile_pursuit(bad, BASE_REQS, BASE_EVIDENCE, now="2026-09-17T07:05:00Z")

    def test_conflicting_official_authority_fails(self):
        ledger = official(BASE_LEDGER)
        ledger = official(
            ledger,
            deadline="2026-10-15T11:00:00-04:00",
            source_id="addendum",
            authority="OFFICIAL_ADDENDUM",
        )
        with self.assertRaisesRegex(GateError, "conflicting official authority"):
            compile_pursuit(ledger, BASE_REQS, BASE_EVIDENCE, now="2026-09-18T01:00:00Z")

    def test_external_authority_is_hard_false(self):
        ledger, reqs, manifest = self._prime_inputs()
        packet = compile_pursuit(ledger, reqs, manifest, now="2026-09-18T01:00:00Z")
        self.assertTrue(packet["external_authority"])
        self.assertFalse(any(packet["external_authority"].values()))

    def test_predecessor_suite_runs_under_real_python_optimized_mode(self):
        if os.environ.get("HAMILTON_OPT_CHILD") == "1":
            return
        env = dict(os.environ)
        env["HAMILTON_OPT_CHILD"] = "1"
        run = subprocess.run(
            [sys.executable, "-O", "-m", "unittest", "-v", Path(__file__).stem],
            cwd=Path(__file__).resolve().parent,
            env=env, text=True, capture_output=True, check=False,
        )
        self.assertEqual(run.returncode, 0, msg=run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
