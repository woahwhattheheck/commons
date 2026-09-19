import csv,json,tempfile,unittest
from pathlib import Path
from revenue.opportunities.tn_31701_03850_cashiering.response_lab.validator import *
ROOT=Path(__file__).resolve().parents[1]/'revenue/opportunities/tn_31701_03850_cashiering/response_lab';MAN=ROOT/'response_manifest.json'
class T(unittest.TestCase):
 def test_complete(self):
  r=validate(MAN);self.assertEqual((r['requirements'],r['required'],r['optional']),(120,112,8));self.assertEqual(r['authority'],FALSE_AUTH)
 def test_ids_and_optional(self):
  rows=load_rows(ROOT/'requirement_crosswalk.csv');self.assertEqual([int(r['id']) for r in rows],list(range(1,121)));self.assertEqual({int(r['id']) for r in rows if r['required']=='N'},OPTIONAL)
 def mutate_manifest(self,fn):
  with tempfile.TemporaryDirectory() as td:
   b=Path(td);m=json.loads(MAN.read_text());fn(m);(b/'m.json').write_text(json.dumps(m));(b/'requirement_crosswalk.csv').write_bytes((ROOT/'requirement_crosswalk.csv').read_bytes());self.assertRaises(ResponseLabError,validate,b/'m.json')
 def test_deadline_drift(self):self.mutate_manifest(lambda d:d.__setitem__('questions_due_ct','2026-09-26T14:00:00-05:00'))
 def test_commercial_self_accept(self):self.mutate_manifest(lambda d:d['commercial'].__setitem__('state','ACCEPTED'))
 def test_authority_self_promote(self):self.mutate_manifest(lambda d:d['authority'].__setitem__('buyer_contact',True))
 def test_source_drift(self):self.mutate_manifest(lambda d:d.__setitem__('source_url','https://example.com/rfi.pdf'))
 def test_crosswalk_tamper(self):
  with tempfile.TemporaryDirectory() as td:
   b=Path(td);(b/'response_manifest.json').write_bytes(MAN.read_bytes());(b/'requirement_crosswalk.csv').write_bytes((ROOT/'requirement_crosswalk.csv').read_bytes()+b'121,X,Y,x,PRIME_PRODUCT_EVIDENCE\n');self.assertRaises(ResponseLabError,validate,b/'response_manifest.json')
 def test_strict_duplicate_json_key(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'x';p.write_text('{"a":1,"a":2}');self.assertRaises(ResponseLabError,load_json,p)
if __name__=='__main__':unittest.main()
