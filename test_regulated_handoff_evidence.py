from __future__ import annotations
import copy
import hashlib
import json
import os
from pathlib import Path
import random
import tempfile
import unittest

from revenue.regulated_handoff_evidence.engine import (
    ContractError, canonical_json_bytes, compile_receipt, loads_strict,
    read_json_regular, verify_receipt, write_json_exclusive,
)

FIXTURE = Path(__file__).parent / "revenue" / "regulated_handoff_evidence" / "fixture.json"

class RegulatedHandoffEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.envelope = loads_strict(FIXTURE.read_text())

    def compile(self, events=None, policy=None):
        return compile_receipt(events if events is not None else self.envelope["events"],
                               policy if policy is not None else self.envelope["policy"])

    def test_fixture_pass_is_deterministic_and_verifiable(self):
        a = self.compile()
        b = self.compile(list(reversed(self.envelope["events"])))
        self.assertEqual(a["body"]["state"], "PASS_EVIDENCE")
        self.assertEqual(a, b)
        self.assertEqual(verify_receipt(a), a)
        self.assertEqual(a["body"]["current_custodian"], "receiver-custody")
        self.assertEqual(a["body"]["unique_event_count"], 6)

    def test_exact_replay_is_not_second_transition(self):
        events = self.envelope["events"] + [copy.deepcopy(self.envelope["events"][2])]
        r = self.compile(events)
        self.assertEqual(r["body"]["state"], "PASS_EVIDENCE")
        self.assertEqual(r["body"]["unique_event_count"], 6)
        self.assertEqual(r["body"]["exact_replay_count"], 1)

    def test_changed_payload_same_event_id_holds(self):
        changed = copy.deepcopy(self.envelope["events"][2]); changed["temperature_c"] = 7.7
        r = self.compile(self.envelope["events"] + [changed])
        self.assertEqual(r["body"]["state"], "HOLD")
        self.assertIn("e3", r["body"]["conflicting_event_ids"])
        self.assertIn("EVENT_ID_CHANGED_PAYLOAD", {x["code"] for x in r["body"]["reasons"]})
        self.assertEqual(verify_receipt(r), r)
        reverse = self.compile([changed] + list(reversed(self.envelope["events"])))
        self.assertEqual(r, reverse)

    def test_identity_custody_lineage_and_exception_fail_closed(self):
        cases = []
        fp = copy.deepcopy(self.envelope["events"]); fp[2]["shipment_fingerprint_sha256"] = "0" * 64; cases.append((fp,"SHIPMENT_FINGERPRINT_AMBIGUOUS"))
        custody = copy.deepcopy(self.envelope["events"]); custody[2]["from_custodian"] = "wrong"; cases.append((custody,"CUSTODY_TRANSITION_MISMATCH"))
        lineage = copy.deepcopy(self.envelope["events"]); lineage[1]["source_event_id"] = ""; cases.append((lineage,"MISSING_SOURCE_LINEAGE"))
        exception = copy.deepcopy(self.envelope["events"]); exception.pop(4); cases.append((exception,"UNRESOLVED_EXCEPTION"))
        for events, code in cases:
            with self.subTest(code=code):
                r = self.compile(events)
                self.assertEqual(r["body"]["state"], "HOLD")
                self.assertIn(code, {x["code"] for x in r["body"]["reasons"]})

    def test_temperature_missing_stale_and_range_hold(self):
        missing = copy.deepcopy(self.envelope["events"]); missing[2].pop("temperature_c"); missing.pop(1)
        stale = copy.deepcopy(self.envelope["events"]); stale[2].pop("temperature_c"); stale[1]["event_time_utc"]="2026-09-14T09:00:00Z"
        oor = copy.deepcopy(self.envelope["events"]); oor[2]["temperature_c"] = 9.0
        for events, code in ((missing,"MISSING_TEMPERATURE_EVIDENCE"),(stale,"STALE_TEMPERATURE_EVIDENCE"),(oor,"TEMPERATURE_OUT_OF_RANGE")):
            with self.subTest(code=code):
                r=self.compile(events); self.assertEqual(r["body"]["state"],"HOLD"); self.assertIn(code,{x["code"] for x in r["body"]["reasons"]})

    def test_strict_json_and_schema_rejections_survive_optimized_python(self):
        with self.assertRaisesRegex(ContractError, "duplicate JSON key"):
            loads_strict('{"a":1,"a":2}')
        with self.assertRaises(ContractError): loads_strict('{"x":NaN}')
        e=copy.deepcopy(self.envelope["events"]); e[0]["event_time_utc"]="2026-09-14T10:00Z"
        with self.assertRaisesRegex(ContractError,"canonical UTC-second"): self.compile(e)
        e=copy.deepcopy(self.envelope["events"]); e[0]["unknown"]="x"
        with self.assertRaisesRegex(ContractError,"unknown fields"): self.compile(e)
        e=copy.deepcopy(self.envelope["events"]); e[2]["temperature_c"]=True
        with self.assertRaisesRegex(ContractError,"numeric"): self.compile(e)

    def test_receipt_tamper_and_reseal_are_rejected(self):
        r=self.compile()
        tampered=copy.deepcopy(r); tampered["body"]["state"]="HOLD"
        with self.assertRaisesRegex(ContractError,"SHA-256 mismatch"): verify_receipt(tampered)
        resealed=copy.deepcopy(r); resealed["body"]["state"]="HOLD"; resealed["receipt_sha256"]=hashlib.sha256(canonical_json_bytes(resealed["body"])).hexdigest()
        with self.assertRaisesRegex(ContractError,"semantic verification failed"): verify_receipt(resealed)
        added=copy.deepcopy(r); added["body"]["untrusted_extension"]="ignored?"; added["receipt_sha256"]=hashlib.sha256(canonical_json_bytes(added["body"])).hexdigest()
        with self.assertRaisesRegex(ContractError,"body fields invalid"): verify_receipt(added)

    def test_io_regular_input_exclusive_output_and_symlink_refusal(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); src=td/"in.json"; src.write_bytes(canonical_json_bytes(self.envelope))
            self.assertEqual(read_json_regular(src), self.envelope)
            out=td/"out.json"; write_json_exclusive(out,self.compile()); self.assertTrue(out.is_file())
            with self.assertRaises(FileExistsError): write_json_exclusive(out,self.compile())
            if hasattr(os,"symlink"):
                link=td/"link.json"
                try: os.symlink(src,link)
                except (OSError,NotImplementedError): return
                with self.assertRaises(ContractError): read_json_regular(link)
                outlink=td/"outlink.json"; os.symlink(td/"target.json",outlink)
                with self.assertRaises(OSError): write_json_exclusive(outlink,self.compile())

    def test_order_invariance_many_permutations(self):
        rng=random.Random(13664); baseline=self.compile()
        for _ in range(20):
            events=copy.deepcopy(self.envelope["events"]); rng.shuffle(events)
            self.assertEqual(self.compile(events), baseline)

if __name__ == "__main__": unittest.main()
