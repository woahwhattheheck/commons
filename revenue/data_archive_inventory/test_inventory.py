from __future__ import annotations
import copy,tempfile,unittest
from pathlib import Path
from revenue.data_archive_inventory.cli import main
from revenue.data_archive_inventory.inventory import *
NOW="2026-09-13T10:00:00Z"
def doc():
 return {"schema":SCHEMA,"assets":[{"asset_id":"receipt-corpus","repo_path":"data/public/receipts.jsonl","version":"2026.09.13","asset_sha256":"1"*64,"provenance_sha256":"2"*64,"source_kind":"REGULAR_FILE","provenance":{"source":"commons","scrubbed":True},"rights":{"basis":"OWNED","license_id":"TJL-Data-1.0","license_evidence_sha256":"3"*64,"permitted_grants":["EVALUATION","INTERNAL_USE"],"transfer_allowed":True,"publication_allowed":True},"sensitive_class":"REDACTED","redaction":{"status":"VERIFIED","policy_sha256":"4"*64,"review_evidence_sha256":"5"*64,"reviewed_at":"2026-09-13T09:00:00Z"},"evidence_valid_until":"2026-10-13T10:00:00Z"}]}
class T(unittest.TestCase):
 def test_ready_deterministic_and_seed(self):
  r,c=compile_inventory(doc(),NOW); r2,c2=compile_inventory(copy.deepcopy(doc()),NOW); self.assertEqual(ELIGIBLE,r["decision"]); self.assertEqual(c,c2); self.assertEqual(canonical_json(r),canonical_json(r2)); self.assertTrue(verify_inventory(doc(),r,c,NOW)); self.assertEqual(["schema_fields","sample_rows","offer"],r["assets"][0]["license_desk_seed"]["remaining_requirements"])
 def test_unknown_rights_hold(self):
  d=doc(); d["assets"][0]["rights"]["basis"]="UNKNOWN"; self.assertIn("RIGHTS_UNKNOWN_OR_NOT_REDISTRIBUTABLE",compile_inventory(d,NOW)[0]["assets"][0]["reasons"])
 def test_unhashable_grant_fails_closed(self):
  d=doc(); d["assets"][0]["rights"]["permitted_grants"]=[{"bad":"grant"}]; row=compile_inventory(d,NOW)[0]["assets"][0]; self.assertTrue(row["reasons"][0].startswith("MALFORMED:"))
 def test_transfer_hold(self):
  d=doc(); d["assets"][0]["rights"]["transfer_allowed"]=False; self.assertIn("TRANSFER_NOT_RECORDED_ALLOWED",compile_inventory(d,NOW)[0]["assets"][0]["reasons"])
 def test_publish_hold(self):
  d=doc(); d["assets"][0]["rights"]["publication_allowed"]=False; self.assertIn("PUBLICATION_NOT_RECORDED_ALLOWED",compile_inventory(d,NOW)[0]["assets"][0]["reasons"])
 def test_symlink_shape_hold(self):
  d=doc(); d["assets"][0]["source_kind"]="SYMLINK"; self.assertIn("SOURCE_NOT_RECORDED_REGULAR_FILE",compile_inventory(d,NOW)[0]["assets"][0]["reasons"])
 def test_public_not_required(self):
  d=doc(); a=d["assets"][0]; a["sensitive_class"]="PUBLIC"; a["redaction"]={"status":"NOT_REQUIRED"}; self.assertEqual(ELIGIBLE,compile_inventory(d,NOW)[0]["decision"])
 def test_public_verified_is_hold(self):
  d=doc(); d["assets"][0]["sensitive_class"]="PUBLIC"; self.assertIn("PUBLIC_REDACTION_STATE_INVALID",compile_inventory(d,NOW)[0]["assets"][0]["reasons"])
 def test_redaction_pending_hold(self):
  d=doc(); d["assets"][0]["redaction"]["status"]="PENDING"; self.assertIn("REDACTION_NOT_VERIFIED",compile_inventory(d,NOW)[0]["assets"][0]["reasons"])
 def test_redaction_future_hold(self):
  d=doc(); d["assets"][0]["redaction"]["reviewed_at"]="2026-09-14T10:00:00Z"; self.assertIn("REDACTION_REVIEW_IN_FUTURE",compile_inventory(d,NOW)[0]["assets"][0]["reasons"])
 def test_evidence_stale_hold(self):
  d=doc(); d["assets"][0]["evidence_valid_until"]=NOW; self.assertIn("EVIDENCE_STALE",compile_inventory(d,NOW)[0]["assets"][0]["reasons"])
 def test_unsafe_path_malformed(self):
  d=doc(); d["assets"][0]["repo_path"]="../secret"; self.assertTrue(compile_inventory(d,NOW)[0]["assets"][0]["reasons"][0].startswith("MALFORMED:"))
 def test_windows_path_malformed(self):
  d=doc(); d["assets"][0]["repo_path"]="data\\x"; self.assertTrue(compile_inventory(d,NOW)[0]["assets"][0]["reasons"][0].startswith("MALFORMED:"))
 def test_unhashable_identity_fails_closed(self):
  d=doc(); d["assets"][0]["asset_id"]=["bad"]; row=compile_inventory(d,NOW)[0]["assets"][0]; self.assertTrue(row["reasons"][0].startswith("MALFORMED:"))
 def test_duplicate_id_rejected(self):
  d=doc(); d["assets"].append(copy.deepcopy(d["assets"][0])); d["assets"][1]["repo_path"]="data/other"; self.assertRaises(InventoryError,compile_inventory,d,NOW)
 def test_duplicate_path_rejected(self):
  d=doc(); d["assets"].append(copy.deepcopy(d["assets"][0])); d["assets"][1]["asset_id"]="other"; self.assertRaises(InventoryError,compile_inventory,d,NOW)
 def test_receipt_mutation_rejects(self):
  r,c=compile_inventory(doc(),NOW); r=copy.deepcopy(r); r["counts"]["eligible"]=0; self.assertFalse(verify_inventory(doc(),r,c,NOW))
 def test_csv_mutation_rejects(self):
  r,c=compile_inventory(doc(),NOW); self.assertFalse(verify_inventory(doc(),r,c+b"x",NOW))
 def test_later_trusted_time_invalidates(self):
  r,c=compile_inventory(doc(),NOW); self.assertFalse(verify_inventory(doc(),r,c,"2026-10-14T10:00:00Z"))
 def test_cli_roundtrip_and_hold_exit(self):
  with tempfile.TemporaryDirectory() as td:
   td=Path(td); inp=td/"in.json"; inp.write_bytes(canonical_json(doc())); rec=td/"r.json"; csv=td/"r.csv"; self.assertEqual(0,main(["build",str(inp),"--receipt",str(rec),"--csv",str(csv),"--at",NOW])); self.assertEqual(0,main(["verify",str(inp),"--receipt",str(rec),"--csv",str(csv),"--at",NOW])); d=doc(); d["assets"][0]["rights"]["basis"]="UNKNOWN"; inp.write_bytes(canonical_json(d)); self.assertEqual(3,main(["build",str(inp),"--receipt",str(rec),"--csv",str(csv),"--at",NOW]))
 def test_cli_symlink_input_refusal(self):
  with tempfile.TemporaryDirectory() as td:
   td=Path(td); p=td/"in.json"; p.write_bytes(canonical_json(doc())); l=td/"l.json"
   try: l.symlink_to(p)
   except OSError: self.skipTest("symlink unavailable")
   self.assertEqual(2,main(["build",str(l),"--receipt",str(td/"r"),"--csv",str(td/"c"),"--at",NOW]))
if __name__=="__main__": unittest.main()
