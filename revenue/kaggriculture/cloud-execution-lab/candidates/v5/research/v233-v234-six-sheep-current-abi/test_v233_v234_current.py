# SPDX-License-Identifier: Apache-2.0
import copy, hashlib, json, types, unittest
from v233_v234_current import V233V234SixSheepCurrentABI, SUBMITTED_V31_ARCHIVE_SHA256, SUBMITTED_R03_GIT_BLOB

def action(hands=0,market=None):return {"farmer":["PASS"],"hands":[["PASS"] for _ in range(hands)],"market":copy.deepcopy(market or [])}
def route(actions=None):return json.dumps(actions or [action() for _ in range(719)],sort_keys=True,separators=(",",":"),ensure_ascii=True)
def snapshot(step=288,raw=None,route_id="r1"):
    raw=raw or route(); parsed=json.loads(raw)
    return types.SimpleNamespace(schema="titan-v5-current-full-route-snapshot-v1",route_source="committed_producer_route.R[route_id]",route_id=route_id,current_step=step,route_sha256=hashlib.sha256(raw.encode("ascii")).hexdigest(),route_length=len(parsed),route_json=raw)
def obs(step=288,money=20000,hands=None,quadrants=None,shed=None,inventories=None,shops=None,prices=None,targets="LOCKED"):
    hands=list(hands or []); tiles=[[{"kind":"EMPTY"} for _ in range(10)] for _ in range(10)]
    for y in (5,6):
        for x in range(5,8):tiles[y][x]=copy.deepcopy(targets)
    return {"step":step,"player":0,"farms":[{"money":money,"hires_today":0,"farmer":[4,4],"hands":[list(p) for p in hands],"tiles":tiles,"unlocked_quadrants":list(quadrants or ["NW","NE","SW"])}],"private":{"shed":dict(shed or {}),"inventories":copy.deepcopy(inventories if inventories is not None else [{} for _ in range(len(hands)+1)])},"town":{"unlocked_shops":list(shops or ["YARN_STORE","YARN_STORE","BAKERY"])},"market":{"prices":dict(prices or {"WOOL":220,"WHEAT":45})}}

class SixSheepTests(unittest.TestCase):
    def test_authority_and_off_identity(self):
        self.assertEqual(SUBMITTED_V31_ARCHIVE_SHA256,"5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361"); self.assertEqual(SUBMITTED_R03_GIT_BLOB,"182e0b7b3f0cc1125967dc092b2c118601b19084")
        selected=action(); out=V233V234SixSheepCurrentABI().transform(obs(),selected,route_snapshot=snapshot()); self.assertEqual(out,selected); self.assertIsNot(out,selected)
    def test_exact_day12_commit_request(self):
        c=V233V234SixSheepCurrentABI(True); out=c.transform(obs(),action(),route_snapshot=snapshot())
        self.assertEqual(out["market"],[["BUY_LAND"],["BUY_ANIMAL","SHEEP",6],["BUY_PRODUCT","WHEAT",6],["HIRE"],["HIRE"]]); self.assertEqual(c.telemetry()["commit_requests"],1)
    def test_future_land_or_sheep_conflict_kills_irreversible_commit(self):
        for changed in (lambda r:r[400].update(market=[["BUY_LAND"]]),lambda r:r[500].update(farmer=["PICKUP","SHEEP",1])):
            rows=[action() for _ in range(719)]; changed(rows); raw=route(rows); c=V233V234SixSheepCurrentABI(True)
            self.assertEqual(c.transform(obs(),action(),route_snapshot=snapshot(raw=raw)),action()); self.assertEqual(c.telemetry()["commit_requests"],0)
    def test_price_shop_land_budget_capacity_gates(self):
        cases=[obs(prices={"WOOL":219,"WHEAT":45}),obs(prices={"WOOL":220,"WHEAT":46}),obs(shops=["YARN_STORE"]),obs(quadrants=["NW","NE","SW","SE"]),obs(targets=None),obs(shed={"SHEEP":1}),obs(money=10000),obs(shed={"WHEAT":90})]
        for case in cases:self.assertEqual(V233V234SixSheepCurrentABI(True).transform(case,action(),route_snapshot=snapshot()),action())
    def test_same_step_retry_and_changed_retry_rollback(self):
        c=V233V234SixSheepCurrentABI(True); first=c.transform(obs(),action(),route_snapshot=snapshot()); second=c.transform(copy.deepcopy(obs()),action(),route_snapshot=snapshot()); self.assertEqual(second,first); self.assertEqual(c.telemetry()["commit_requests"],1)
        changed=c.transform(obs(money=10000),action(),route_snapshot=snapshot()); self.assertEqual(changed,action()); self.assertEqual(c.telemetry()["commit_requests"],0)
        next_obs=obs(step=289,hands=[[4,4],[5,4]],quadrants=["NW","NE","SW","SE"],shed={"SHEEP":6,"WHEAT":6},inventories=[{},{},{}]); c.transform(next_obs,action(2),route_snapshot=snapshot(step=289)); self.assertEqual(c.telemetry()["committed"],0)
    def test_physical_confirmation_owns_exact_two_workers(self):
        c=V233V234SixSheepCurrentABI(True); c.transform(obs(),action(),route_snapshot=snapshot())
        next_obs=obs(step=289,hands=[[4,4],[5,4]],quadrants=["NW","NE","SW","SE"],shed={"SHEEP":6,"WHEAT":6},inventories=[{},{},{}]); out=c.transform(next_obs,action(2),route_snapshot=snapshot(step=289))
        self.assertEqual(c.telemetry()["committed"],1); self.assertEqual(c.telemetry()["workers_confirmed"],2); self.assertEqual(out["hands"],[['PICKUP','SHEEP',3],['PICKUP','SHEEP',3]])
    def test_route_drift_fails_closed_after_commit(self):
        c=V233V234SixSheepCurrentABI(True); c.transform(obs(),action(),route_snapshot=snapshot()); self.assertEqual(c.transform(obs(step=289),action(),route_snapshot=snapshot(step=289,route_id="other")),action()); self.assertEqual(c.telemetry()["route_declines"],1)
    def test_v234_shortage_rescue_is_bounded(self):
        c=V233V234SixSheepCurrentABI(True); w=snapshot(step=313); fresh=V233V234SixSheepCurrentABI(True); fresh.transform(obs(),action(),route_snapshot=snapshot())
        c._states[0]={"last":312,"day":13,"committed":True,"pending":None,"workers":{1:[(5,5),(6,5),(7,5)],2:[(5,6),(6,6),(7,6)]},"work":{},"credit":{"WOOL":0,"FERTILIZER":0},"rescue":0,"route_id":"r1","route_sha256":w.route_sha256,"route":json.loads(route()),"telemetry":{k:0 for k in fresh.telemetry()}}
        o=obs(step=313,hands=[[4,4],[5,4]],quadrants=["NW","NE","SW","SE"],inventories=[{},{},{}]); tiles=[[{"kind":"EMPTY"} for _ in range(10)] for _ in range(10)]
        for x,y in ((5,5),(6,5),(7,5),(5,6),(6,6),(7,6)):tiles[y][x]={"kind":"PASTURE","animal":"SHEEP","fed_today":False,"cared_today":True,"yield_units":0,"fertilizer_available":False}
        o["farms"][0]["tiles"]=tiles; out=c.transform(o,action(2),route_snapshot=w); self.assertIn(["BUY_PRODUCT","WHEAT",6],out["market"]); self.assertEqual(c.telemetry()["rescue_feed_requests"],6)

if __name__=="__main__":unittest.main()
