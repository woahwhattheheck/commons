from __future__ import annotations
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("trace_replay", HERE / "trace_replay.py")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def transition(step, candidate_money, rival_money, candidate_action=None, rival_action=None):
    observation = {
        "step": step,
        "day": step // 24,
        "hour": step % 24,
        "farms": [{"money": candidate_money}, {"money": rival_money}],
    }
    return {
        "game_step": step,
        "after": [observation, observation],
        "applied_actions": [
            candidate_action or {"farmer": ["PASS"], "hands": [], "market": []},
            rival_action or {"farmer": ["PASS"], "hands": [], "market": []},
        ],
    }


class InterventionTests(unittest.TestCase):
    def test_drop_one_market_order_preserves_everything_else(self):
        action = {"farmer": ["NORTH"], "hands": [["PICKUP", "WHEAT"]],
                  "market": [["HIRE"], ["BUY_SEED", "WHEAT", 3], ["SELL", "MILK", 1]]}
        result = module.apply_intervention(action, {"mode": "drop_market_order", "order_index": 1})
        self.assertEqual(result["market"], [["HIRE"], ["SELL", "MILK", 1]])
        self.assertEqual(result["farmer"], ["NORTH"])
        self.assertEqual(len(action["market"]), 3)

    def test_full_pass_preserves_hand_cardinality(self):
        action = {"farmer": ["NORTH"], "hands": [["WEST"], ["CARE"]], "market": [["HIRE"]]}
        result = module.apply_intervention(action, {"mode": "full_pass"})
        self.assertEqual(result, {"farmer": ["PASS"], "hands": [["PASS"], ["PASS"]], "market": []})

    def test_invalid_drop_is_rejected(self):
        with self.assertRaises(ValueError):
            module.apply_intervention({"market": []}, {"mode": "drop_market_order", "order_index": 2})


class AnalysisTests(unittest.TestCase):
    def test_permanent_deficit_and_largest_widening(self):
        rows = [
            transition(0, 100, 100),
            transition(1, 90, 100, {"farmer": ["PASS"], "hands": [], "market": [["HIRE"]]}),
            transition(2, 130, 100),
            transition(3, 80, 100, {"farmer": ["PASS"], "hands": [], "market": [["BUY_SEED", "WHEAT", 4]]}),
            transition(4, 75, 110),
        ]
        analysis = module.analyze_transitions(rows, 0)
        self.assertEqual(analysis["permanent_deficit_onset"]["game_step"], 3)
        self.assertEqual(analysis["largest_one_step_deficit_expansions"][0]["game_step"], 3)
        self.assertEqual(analysis["terminal_money_margin"], -35)

    def test_intervention_selection_is_bounded_and_order_specific(self):
        rows = [
            transition(0, 100, 100),
            transition(1, 10, 100, {"farmer": ["PASS"], "hands": [],
                                    "market": [["HIRE"], ["BUY_SEED", "WHEAT", 5]]}),
        ]
        selected = module.intervention_candidates(module.analyze_transitions(rows, 0), 2)
        self.assertEqual([item["mode"] for item in selected], ["drop_market_order", "drop_market_order"])
        self.assertEqual([item["order_index"] for item in selected], [0, 1])


class ArchiveTests(unittest.TestCase):
    def _pin(self, archive, files):
        return {"release": {"sha256": module.sha256_file(archive), "bytes": archive.stat().st_size,
                            "runtime_files": files, "entrypoint": "main.py::agent", "config": "TITAN-CONFIG.json"}}

    def test_verified_archive_extracts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive = root / "candidate.tar.gz"
            with tarfile.open(archive, "w:gz") as tar:
                for name, data in (("main.py", b"def agent(o,c=None): return {}\n"),
                                   ("TITAN-CONFIG.json", b"{}\n")):
                    info = tarfile.TarInfo(name)
                    info.size = len(data)
                    tar.addfile(info, io.BytesIO(data))
            pin = root / "PIN.json"
            pin.write_text(json.dumps(self._pin(archive, 2)))
            receipt = module.verify_and_extract(archive, pin, root / "out")
            self.assertEqual(receipt["extraction"]["regular_files"], 2)

    def test_parent_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive = root / "candidate.tar.gz"
            with tarfile.open(archive, "w:gz") as tar:
                info = tarfile.TarInfo("../escape")
                info.size = 1
                tar.addfile(info, io.BytesIO(b"x"))
            pin = root / "PIN.json"
            pin.write_text(json.dumps(self._pin(archive, 1)))
            with self.assertRaises(ValueError):
                module.verify_and_extract(archive, pin, root / "out")


if __name__ == "__main__":
    unittest.main()
