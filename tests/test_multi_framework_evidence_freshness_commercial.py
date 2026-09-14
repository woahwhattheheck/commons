import copy, importlib.util, json, pathlib, tempfile, unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
MOD=ROOT/"revenue/multi_framework_evidence_freshness/commercial/verify_commercial.py"
spec=importlib.util.spec_from_file_location("verify_commercial", MOD)
vc=importlib.util.module_from_spec(spec); spec.loader.exec_module(vc)
OFFER=ROOT/"revenue/multi_framework_evidence_freshness/commercial/offer.json"
SAMPLE=ROOT/"revenue/multi_framework_evidence_freshness/commercial/sample_report.json"

class CommercialPacketTests(unittest.TestCase):
    def setUp(self):
        self.offer=json.loads(OFFER.read_text())
        self.sample=json.loads(SAMPLE.read_text())
    def write(self, td, offer=None, sample=None):
        op=pathlib.Path(td)/"o.json"; sp=pathlib.Path(td)/"s.json"
        op.write_text(json.dumps(self.offer if offer is None else offer))
        sp.write_text(json.dumps(self.sample if sample is None else sample))
        return op,sp
    def test_canonical_packet_verifies(self):
        od,sd=vc.verify(OFFER,SAMPLE); self.assertEqual(od,self.offer["offer_sha256"]); self.assertEqual(sd,self.sample["sample_sha256"])
    def test_price_reseal_rejected(self):
        x=copy.deepcopy(self.offer); x["offer"]["price"]["amount_cents"]=1; x["offer_sha256"]=vc._sha(x["offer"])
        with tempfile.TemporaryDirectory() as td:
            op,sp=self.write(td,offer=x)
            with self.assertRaisesRegex(vc.CommercialPacketError,"diagnostic_price"): vc.verify(op,sp)
    def test_authority_reseal_rejected(self):
        x=copy.deepcopy(self.offer); x["offer"]["authority"]["audit_opinion"]=True; x["offer_sha256"]=vc._sha(x["offer"])
        y=copy.deepcopy(self.sample); y["sample"]["offer_sha256"]=x["offer_sha256"]; y["sample_sha256"]=vc._sha(y["sample"])
        with tempfile.TemporaryDirectory() as td:
            op,sp=self.write(td,offer=x,sample=y)
            with self.assertRaisesRegex(vc.CommercialPacketError,"authority_escalation"): vc.verify(op,sp)
    def test_sample_must_bind_offer(self):
        x=copy.deepcopy(self.sample); x["sample"]["offer_sha256"]="0"*64; x["sample_sha256"]=vc._sha(x["sample"])
        with tempfile.TemporaryDirectory() as td:
            op,sp=self.write(td,sample=x)
            with self.assertRaisesRegex(vc.CommercialPacketError,"sample_offer_binding"): vc.verify(op,sp)
    def test_sample_cannot_claim_buyer_data(self):
        x=copy.deepcopy(self.sample); x["sample"]["contains_buyer_data"]=True; x["sample_sha256"]=vc._sha(x["sample"])
        with tempfile.TemporaryDirectory() as td:
            op,sp=self.write(td,sample=x)
            with self.assertRaisesRegex(vc.CommercialPacketError,"sample_data_posture"): vc.verify(op,sp)
    def test_engine_provenance_reseal_rejected(self):
        x=copy.deepcopy(self.offer); x["offer"]["acceptance"]["engine_provenance"]["merge_commit"]="f"*40; x["offer_sha256"]=vc._sha(x["offer"])
        with tempfile.TemporaryDirectory() as td:
            op,sp=self.write(td,offer=x)
            with self.assertRaisesRegex(vc.CommercialPacketError,"engine_merge"): vc.verify(op,sp)
    def test_duplicate_key_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            op=pathlib.Path(td)/"o.json"; sp=pathlib.Path(td)/"s.json"
            op.write_text('{"offer":{},"offer":{},"offer_sha256":"x"}'); sp.write_text(SAMPLE.read_text())
            with self.assertRaisesRegex(vc.CommercialPacketError,"duplicate_json_key"): vc.verify(op,sp)

if __name__=="__main__": unittest.main()
