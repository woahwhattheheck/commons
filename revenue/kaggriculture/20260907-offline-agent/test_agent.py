"""Offline contract regressions: no dependencies or external accounts."""
import copy
import importlib.util
import unittest
from pathlib import Path
from evaluate import Struct, get_engine, load_agent, play
import tempfile

class AgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix="kaggriculture-tests-")
        cls.engine,_=get_engine(cls.temp.name)
        cls.path=Path(__file__).with_name("main.py")
    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()
    def initial(self):
        cfg=Struct(episodeSteps=720,seed=17)
        env=Struct(configuration=cfg,done=False,info={})
        states=[Struct(observation=Struct(),action={},status="ACTIVE",reward=0) for _ in range(2)]
        self.engine.interpreter(states,env)
        return states[0].observation
    def test_input_is_not_mutated(self):
        obs=self.initial()
        before=copy.deepcopy(obs)
        load_agent(self.path)(obs)
        self.assertEqual(obs,before)
    def test_agent_is_deterministic_and_json_serializable(self):
        import json
        obs=self.initial()
        f=load_agent(self.path)
        self.assertEqual(f(obs),f(copy.deepcopy(obs)))
        self.assertEqual(json.loads(json.dumps(f(obs))),f(obs))
    def test_no_observation_fallback(self):
        self.assertEqual(load_agent(self.path)({})["farmer"],["PASS"])
    def test_last_turn_liquidates_at_depot(self):
        obs=self.initial()
        obs.step=718
        obs.day=29
        obs.hour=22
        obs.private["inventories"][0]={"EGG":4,"FERTILIZER":2}
        action=load_agent(self.path)(obs)
        self.assertEqual(action["farmer"],["DROP"])
        self.assertIn(["SELL","EGG",4],action["market"])
        self.assertIn(["SELL","FERTILIZER",2],action["market"])
    def test_no_market_orders_exceed_cap(self):
        obs=self.initial()
        obs.private["shed"].update({p:1 for p in self.engine.PRODUCTS})
        self.assertLessEqual(len(load_agent(self.path)(obs)["market"]),10)
    def test_pending_animal_is_installed_at_capacity(self):
        obs=self.initial()
        obs.private["shed"]["GOOSE"]=1
        f=load_agent(self.path,{"animal_cap":1})
        action=f(obs)
        self.assertEqual(action["farmer"],["PICKUP","GOOSE",1])
    def test_official_full_game_and_early_stop(self):
        result=play(self.engine,[load_agent(self.path),
            lambda obs,cfg:self.engine.starter_agent(obs)],5)
        self.assertEqual(result["status"],["DONE","DONE"])
        self.assertEqual(result["steps"],719)
        self.assertGreater(result["bank"][0],result["bank"][1])
    def test_plant_and_water_are_separate_actions(self):
        obs=self.initial()
        obs.private["seeds"]["WHEAT"]=1
        x,y=obs.farms[0]["farmer"]
        obs.farms[0]["tiles"][y][x]=self.engine._new_plant("WHEAT",0,24)
        action=load_agent(self.path)(obs)
        self.assertEqual(action["farmer"],["WATER"])

if __name__=="__main__":
    unittest.main()
