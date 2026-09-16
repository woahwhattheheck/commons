import json, os, tempfile, unittest
from unittest.mock import patch
from .cli import load_json, write_exclusive, main

class CliTests(unittest.TestCase):
    def test_duplicate_key_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=os.path.join(d,"x.json"); open(p,"w").write('{"a":1,"a":2}')
            with self.assertRaises(ValueError): load_json(p)
    def test_nonfinite_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=os.path.join(d,"x.json"); open(p,"w").write('{"a":NaN}')
            with self.assertRaises(ValueError): load_json(p)
    def test_exclusive_output(self):
        with tempfile.TemporaryDirectory() as d:
            p=os.path.join(d,"out.json"); write_exclusive(p,{"x":1})
            with self.assertRaises(FileExistsError): write_exclusive(p,{"x":2})
    def test_missing_key_is_error(self):
        with patch.dict(os.environ,{},clear=True):
            with tempfile.TemporaryDirectory() as d:
                s=os.path.join(d,"s.json"); o=os.path.join(d,"o.json"); json.dump({"x":1},open(s,"w"))
                with self.assertRaises(ValueError): main(["sign-source",s,o,"--key-id","owner"])
    def test_cli_discovery_holds(self):
        root=os.path.dirname(__file__)
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,{"SCAQMD_SOURCE_AUTHORITY_KEY_HEX":"33"*32},clear=False):
            au=os.path.join(d,"a.json"); out=os.path.join(d,"out.json")
            self.assertEqual(main(["sign-source",os.path.join(root,"source.discovery.json"),au,"--key-id","owner","--issued-at","2026-09-16T13:00:00+00:00"]),0)
            self.assertEqual(main(["compile",os.path.join(root,"example.discovery.json"),au,out,"--key-id","owner","--as-of","2026-09-16T13:00:00+00:00"]),0)
            a=json.load(open(out)); self.assertEqual(a["state"],"HOLD_SOURCE_BYTES_REQUIRED")
            self.assertEqual(main(["verify",os.path.join(root,"example.discovery.json"),au,out,"--key-id","owner"]),0)
if __name__=="__main__": unittest.main()
