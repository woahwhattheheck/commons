import json
import pathlib
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from compose_native_return_bridge import patch_main, patch_runtime, patch_config, replace_once


class ComposerTests(unittest.TestCase):
    def test_runtime_feature_and_contract(self):
        source = """    early_capital: bool = False

    def __post_init__(self):
        if self.redundant_hire and (self.consumer != 'frozen' or self.terminal_route):
            raise ValueError('redundant_hire is the tested nonterminal frozen SELL composition')
        if (self.spatial_pathing or self.spatial_tempo or self.fourth_quadrant or self.idle_fertilizer or self.crop_release) and (self.consumer != 'frozen' or self.terminal_route):
            pass
"""
        out=patch_runtime(source)
        self.assertIn("lockstep_join: bool = False",out)
        self.assertIn("lockstep_join requires nonterminal frozen SELL",out)

    def test_main_hooks_exact_outer_timer_scope(self):
        source = """    features = Features(**feature_data)

    class FinalPressureAgent(TitanAgent):
        pass
    return FinalPressureAgent(features, fourth_quadrant_admission=admission)
            stage = 'entrypoint_runtime'
            output = instance.act(observation, cfg, entry_started=entry_started)
"""
        out=patch_main(source)
        self.assertIn("bridge.observe(observation, cfg)",out)
        self.assertLess(out.index("output = instance.act"),out.index("bridge.commit("))
        self.assertIn("instance._return_bridge = bridge",out)

    def test_config_is_default_off(self):
        out=patch_config(json.dumps({'early_capital':True}))
        self.assertIs(json.loads(out)['lockstep_join'],False)

    def test_config_duplicate_rejected(self):
        with self.assertRaises(ValueError):
            patch_config(json.dumps({'early_capital':True,'lockstep_join':False}))

    def test_anchor_drift_rejected(self):
        with self.assertRaises(ValueError):
            replace_once('abc','zzz','x','drift')

    def test_duplicate_anchor_rejected(self):
        with self.assertRaises(ValueError):
            replace_once('aa','a','x','duplicate')

if __name__=='__main__': unittest.main()
