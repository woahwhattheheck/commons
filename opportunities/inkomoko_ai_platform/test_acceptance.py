from __future__ import annotations
import copy,unittest
from opportunities.inkomoko_ai_platform.acceptance import evaluate_scenario
from opportunities.inkomoko_ai_platform.engine import CarrierError

def ev(seq,typ,channel="WEB",ctx="b"*64,req=None,system=None,stage=None,subject=None,result="OK"):
    return {"seq":seq,"type":typ,"channel":channel,"conversation_id":"SYN-CONV-1","context_sha256":ctx,"request_id":req,"system":system,"stage":stage,"subject_id":subject,"result":result}
def good_scenario():
    events=[ev(1,"TRAINING_STAGE",stage="IDEATION"),ev(2,"TRAINING_STAGE",stage="INVESTMENT_READINESS"),ev(3,"CHANNEL_SWITCH",channel="WHATSAPP"),ev(4,"TRAINING_STAGE",channel="WHATSAPP",stage="BUSINESS_PLANNING"),ev(5,"ESCALATION_REQUEST",channel="WHATSAPP"),ev(6,"HUMAN_HANDOFF",channel="WHATSAPP"),ev(7,"LOAN_ENQUIRY",channel="WHATSAPP",subject="SYN-CLIENT-1"),ev(8,"INTEGRATION_CALL",channel="WHATSAPP",req="SYN-REQ-1",system="CBS"),ev(9,"INTEGRATION_RESULT",channel="WHATSAPP",req="SYN-REQ-1",system="CBS"),ev(10,"AUDIT",channel="WHATSAPP",req="SYN-REQ-1",system="CBS"),ev(11,"TRAINING_STAGE",channel="WHATSAPP",stage="MARKET_ENTRY")]
    return {"schema_version":1,"scenario_id":"SYN-SCENARIO-GOOD","language":"rw","initial_channel":"WEB","role":"ENTREPRENEUR","events":events}

class AcceptanceTests(unittest.TestCase):
    def test_good_trace_passes(self):
        r=evaluate_scenario(good_scenario());self.assertEqual(r["status"],"PASS");self.assertEqual(r["findings"],[]);self.assertTrue(all(v is False for v in r["authority"].values()))
    def test_channel_jump_fails(self):
        s=good_scenario();s["events"][1]["channel"]="WHATSAPP";self.assertIn("CHANNEL_WITHOUT_SWITCH",{f["code"] for f in evaluate_scenario(s)["findings"]})
    def test_escalation_context_loss_fails(self):
        s=good_scenario();s["events"][5]["context_sha256"]="c"*64;self.assertIn("ESCALATION_CONTEXT_LOST",{f["code"] for f in evaluate_scenario(s)["findings"]})
    def test_orphan_integration_result_fails(self):
        s=good_scenario();s["events"][8]["request_id"]="SYN-REQ-OTHER";self.assertIn("ORPHAN_INTEGRATION_RESULT",{f["code"] for f in evaluate_scenario(s)["findings"]})
    def test_missing_audit_fails(self):
        s=good_scenario();s["events"]=[e for e in s["events"] if e["type"]!="AUDIT"];self.assertIn("INTEGRATION_AUDIT_MISSING",{f["code"] for f in evaluate_scenario(s)["findings"]})
    def test_incomplete_training_sequence_fails(self):
        s=good_scenario();s["events"]=[e for e in s["events"] if e.get("stage")!="BUSINESS_PLANNING"];self.assertIn("TRAINING_SEQUENCE_INCOMPLETE",{f["code"] for f in evaluate_scenario(s)["findings"]})
    def test_non_synthetic_identity_refused(self):
        s=good_scenario();s["scenario_id"]="REAL-CUSTOMER"
        with self.assertRaisesRegex(CarrierError,"SYN"):evaluate_scenario(s)
    def test_duplicate_integration_request_fails(self):
        s=good_scenario();d=copy.deepcopy(s["events"][7]);s["events"].insert(8,d)
        for i,e in enumerate(s["events"],1):e["seq"]=i
        self.assertIn("DUPLICATE_INTEGRATION_REQUEST",{f["code"] for f in evaluate_scenario(s)["findings"]})

if __name__=="__main__":unittest.main()
