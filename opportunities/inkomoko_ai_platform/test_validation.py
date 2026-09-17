from __future__ import annotations
import copy,tempfile,unittest
from pathlib import Path
from opportunities.inkomoko_ai_platform.core import CarrierError,load_json_file,loads_strict,validate_reference
from opportunities.inkomoko_ai_platform.engine import _compile_at
from test_support import NOW,all_evidence,buyer,fixture,proof

class ValidationTests(unittest.TestCase):
    def setUp(self):self.ref=fixture("reference_rfp.json");self.c=fixture("synthetic_candidate.json")
    def test_reference_valid(self):self.assertEqual(validate_reference(copy.deepcopy(self.ref))["schema_version"],1)
    def test_duplicate_json_key(self):
        with self.assertRaisesRegex(CarrierError,"duplicate JSON key"):loads_strict('{"a":1,"a":2}')
    def test_nonfinite_json(self):
        with self.assertRaisesRegex(CarrierError,"non-finite"):loads_strict('{"x":NaN}')
    def test_bool_generation(self):
        c=copy.deepcopy(self.c);c["generation"]=True
        with self.assertRaisesRegex(CarrierError,"integer"):_compile_at(self.ref,c,NOW)
    def test_unknown_candidate_key(self):
        c=copy.deepcopy(self.c);c["surprise"]="unsafe"
        with self.assertRaisesRegex(CarrierError,"keys mismatch"):_compile_at(self.ref,c,NOW)
    def test_duplicate_evidence(self):
        c=copy.deepcopy(self.c);c["evidence"]=[proof("TECH-RBAC"),proof("TECH-RBAC")]
        with self.assertRaisesRegex(CarrierError,"duplicate evidence"):_compile_at(self.ref,c,NOW)
    def test_future_evidence(self):
        c=copy.deepcopy(self.c);row=proof("TECH-RBAC");row["observed_at"]="2026-09-18T00:00:00Z";c["evidence"]=[row]
        with self.assertRaisesRegex(CarrierError,"future evidence"):_compile_at(self.ref,c,NOW)
    def test_stale_evidence(self):
        c=copy.deepcopy(self.c);row=proof("TECH-RBAC");row["observed_at"]="2026-01-01T00:00:00Z";c["evidence"]=[row]
        with self.assertRaisesRegex(CarrierError,"stale evidence"):_compile_at(self.ref,c,NOW)
    def test_partner_authority(self):
        r=buyer(self.ref);c=all_evidence(r,self.c);c["evidence"][0]["state"]="PARTNER_PROVEN"
        with self.assertRaisesRegex(CarrierError,"PARTNER_FIRST_PARTY"):_compile_at(r,c,NOW)
    def test_synthetic_cannot_prove(self):
        r=buyer(self.ref);c=all_evidence(r,self.c);c["evidence"][0]["authority"]="SYNTHETIC_TEST_ONLY"
        with self.assertRaisesRegex(CarrierError,"synthetic evidence cannot prove"):_compile_at(r,c,NOW)
    def test_future_source(self):
        r=copy.deepcopy(self.ref);r["opportunity"]["observed_at"]="2026-09-18T00:00:00Z"
        with self.assertRaisesRegex(CarrierError,"future opportunity source"):_compile_at(r,self.c,NOW)
    def test_stale_source(self):
        r=copy.deepcopy(self.ref);r["opportunity"]["observed_at"]="2026-01-01T00:00:00Z"
        with self.assertRaisesRegex(CarrierError,"stale opportunity source"):_compile_at(r,self.c,NOW)
    def test_symlink_input(self):
        with tempfile.TemporaryDirectory() as td:
            real=Path(td)/"real.json";link=Path(td)/"link.json";real.write_text("{}")
            try:link.symlink_to(real)
            except (OSError,NotImplementedError):self.skipTest("symlink unavailable")
            with self.assertRaisesRegex(CarrierError,"symlink"):load_json_file(link)

if __name__=="__main__":unittest.main()
