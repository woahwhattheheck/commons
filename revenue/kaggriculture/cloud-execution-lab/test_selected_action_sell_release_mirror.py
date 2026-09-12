"""Guard the release-mapped selected-action seller against live-source drift."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest

import build_integrated

ROOT = Path(__file__).resolve().parent
MIRROR = ROOT / "reference/titan-current/latest/selected_action_sell.py"
LIVE = ROOT / "selected_action_sell.py"


def _load_mirror():
    spec = importlib.util.spec_from_file_location("release_selected_action_sell", MIRROR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _observation(step, rival_yield, player=0):
    own = {"tiles": [[None]]}
    rival = {"tiles": [[{"kind": "ANIMAL", "animal": "COW", "yield_units": rival_yield}]]}
    farms = [own, rival] if player == 0 else [rival, own]
    return {"step": step, "player": player, "farms": farms}


class SelectedActionSellReleaseMirrorTests(unittest.TestCase):
    def test_builder_maps_release_entry_to_exact_live_postimage(self):
        mapping = build_integrated.source_files()
        self.assertEqual(mapping["selected_action_sell.py"],
                         "reference/titan-current/latest/selected_action_sell.py")
        self.assertEqual(MIRROR.read_bytes(), LIVE.read_bytes())

    def test_packaged_mirror_preserves_same_step_rival_history(self):
        module = _load_mirror()
        seller = module.SelectedActionSell()
        seller._observe(_observation(10, 5), 10)
        at_11 = _observation(11, 2)
        seller._observe(at_11, 11)
        self.assertEqual(seller.observed_harvests, {"MILK": [(11, 3)]})

        seller._observe(copy.deepcopy(at_11), 11)
        self.assertEqual(seller.observed_harvests, {"MILK": [(11, 3)]})

        revised = _observation(11, 1)
        seller._observe(revised, 11)
        self.assertEqual(seller.observed_harvests, {"MILK": [(11, 3)]})
        self.assertEqual(seller.previous[2][0][0]["yield_units"], 1)

        seller._observe(_observation(12, 0), 12)
        self.assertEqual(seller.observed_harvests, {"MILK": [(11, 3), (12, 1)]})


if __name__ == "__main__":
    unittest.main(verbosity=2)
