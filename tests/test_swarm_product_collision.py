import copy
import hashlib
import json
import unittest

from tools.swarm_product_collision.engine import CollisionError, compile_preflight, load_json_strict, verify_bundle


def canon(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()

def root(search):
    payload = {k: search[k] for k in ("provider", "family_id", "query", "observed_at", "state", "hits")}
    return hashlib.sha256(canon(payload)).hexdigest()

def hit(hid="gh:1", created="2026-09-15T04:00:00Z", kind="GITHUB_ISSUE", claim="TAKE", op="OLD-OP", owner="Z-OLD", sig=None):
    sig = sig or {"actors":["franchisee"], "objects":["royalty"], "actions":["reconciliation"]}
    return {"hit_id":hid,"url":"https://github.com/acme/repo/issues/1","created_at":created,"kind":kind,"claim_state":claim,"operation_id":op,"owner":owner,"signature":sig,"evidence_sha256":"a"*64}

def base():
    families = [{"family_id":"royalty","terms":["royalty","franchise"]},{"family_id":"adfund","terms":["advertising","fund"]}]
    searches=[]
    for fam in families:
        for provider in ("GITHUB_ISSUES","SLACK"):
            s={"provider":provider,"family_id":fam["family_id"],"query":f"{fam['family_id']} query","observed_at":"2026-09-15T05:15:00Z","state":"COMPLETE","hits":[]}
            s["retained_root"]=root(s); searches.append(s)
    return {"schema":"swarm-product-collision-preflight/v1","evaluation_time":"2026-09-15T05:15:30Z","max_age_seconds":300,"required_providers":["GITHUB_ISSUES","SLACK"],"candidate":{"operation_id":"NEW-OP","seat_id":"Z-NEW","project":"commons","title":"New lane","created_at":"2026-09-15T05:15:16Z","signature":{"actors":["franchisee"],"objects":["royalty"],"actions":["reconciliation"]}},"families":families,"searches":searches}

def packet(raw):
    return json.loads(compile_preflight(raw)["packet.json"])

class Tests(unittest.TestCase):
    def test_clear(self):
        self.assertEqual(packet(base())["status"], "CLEAR_ON_SUPPLIED_EVIDENCE")

    def test_earlier_synonym_collision(self):
        d=base(); d["searches"][0]["hits"]=[hit()]; d["searches"][0]["retained_root"]=root(d["searches"][0])
        p=packet(d); self.assertEqual(p["status"],"COLLISION"); self.assertEqual(p["canonicalPriorCarrier"]["owner"],"Z-OLD")

    def test_later_duplicate_does_not_displace(self):
        d=base(); d["searches"][0]["hits"]=[hit(created="2026-09-15T05:15:20Z")]; d["searches"][0]["retained_root"]=root(d["searches"][0])
        p=packet(d); self.assertEqual(p["status"],"CLEAR_ON_SUPPLIED_EVIDENCE"); self.assertEqual(len(p["laterDuplicates"]),1)

    def test_chatter_not_ownership(self):
        d=base(); d["searches"][0]["hits"]=[hit(kind="SLACK_CHATTER",claim="MENTION")]; d["searches"][0]["retained_root"]=root(d["searches"][0])
        self.assertEqual(packet(d)["status"],"CLEAR_ON_SUPPLIED_EVIDENCE")

    def test_missing_provider_holds(self):
        d=base(); d["searches"]=[s for s in d["searches"] if not (s["provider"]=="SLACK" and s["family_id"]=="royalty")]
        p=packet(d); self.assertEqual(p["status"],"UNKNOWN_HOLD"); self.assertIn("MISSING_SEARCH:SLACK:royalty",p["reasons"])

    def test_rate_limit_holds(self):
        d=base(); d["searches"][0]["state"]="RATE_LIMITED"; d["searches"][0]["retained_root"]=root(d["searches"][0])
        self.assertEqual(packet(d)["status"],"UNKNOWN_HOLD")

    def test_stale_holds(self):
        d=base(); d["searches"][0]["observed_at"]="2026-09-15T05:00:00Z"; d["searches"][0]["retained_root"]=root(d["searches"][0])
        self.assertEqual(packet(d)["status"],"UNKNOWN_HOLD")

    def test_root_mismatch_rejected(self):
        d=base(); d["searches"][0]["retained_root"]="0"*64
        with self.assertRaises(CollisionError): compile_preflight(d)

    def test_semantically_unrelated_does_not_collide(self):
        d=base(); d["searches"][0]["hits"]=[hit(sig={"actors":["carrier"],"objects":["freight"],"actions":["audit"]})]; d["searches"][0]["retained_root"]=root(d["searches"][0])
        self.assertEqual(packet(d)["status"],"CLEAR_ON_SUPPLIED_EVIDENCE")

    def test_input_order_invariance(self):
        a=base(); b=copy.deepcopy(a); b["families"].reverse(); b["searches"].reverse(); b["required_providers"].reverse()
        self.assertEqual(compile_preflight(a),compile_preflight(b))

    def test_bundle_tamper_rejected(self):
        d=base(); bundle=compile_preflight(d); self.assertTrue(verify_bundle(d,bundle)); bundle=dict(bundle); bundle["review.md"]+=b"tamper"; self.assertFalse(verify_bundle(d,bundle))

    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(CollisionError): load_json_strict('{"a":1,"a":2}')

    def test_bool_integer_rejected(self):
        d=base(); d["max_age_seconds"]=True
        with self.assertRaises(CollisionError): compile_preflight(d)

    def test_control_character_rejected(self):
        d=base(); d["candidate"]["title"]="bad\nline"
        with self.assertRaises(CollisionError): compile_preflight(d)

if __name__ == "__main__": unittest.main()
