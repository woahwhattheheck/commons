import importlib.util
import pathlib
import unittest

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("oracle", HERE / "locked_land_preposition_oracle.py")
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)

GOOD = r"""
def _apply_unit_action(farm, private, idx, action, board_size, day, turns_per_day, shed_capacity=100):
    op = action[0]
    fx, fy = farm["farmer"]
    if op in FARMER_MOVES:
        nx, ny = fx + 1, fy
        if not (0 <= nx < board_size and 0 <= ny < board_size):
            return
        # Movement onto LOCKED tiles is allowed: test fixture.
        _set_farmer_position(farm, idx, (nx, ny))
        return
    tile = farm["tiles"][fy][fx]
    if tile == "LOCKED":
        return

def _do_buy_land(farm, board_size):
    cost = 1
    if farm["money"] < cost:
        return
    quadrant = "NE"
    farm["unlocked_quadrants"].append(quadrant)
    for y in range(board_size):
        for x in range(board_size):
            if True:
                farm["tiles"][y][x] = None

def _process_market(state, env):
    order_states = []
    for player_id, ostate in enumerate(order_states):
        if ostate is None:
            continue
        op = ostate["type"]
        if op == "HIRE":
            pass
        elif op == "BUY_LAND":
            _do_buy_land({}, 10)
            order_states[player_id] = None

def interpreter(state, env):
    for i, s in enumerate(state):
        _apply_unit_action({}, {}, 0, ["PASS"], 10, 0, 24, 100)
    _process_market(state, env)
"""

class OracleTests(unittest.TestCase):
    def test_valid_source_proves_phase_coupling(self):
        out = oracle.analyze_text(GOOD)
        self.assertTrue(all(out["checks"].values()))
        self.assertEqual(out["theorem"]["phase_order"], ["unit MOVE", "market BUY_LAND", "tile unlock"])
        self.assertEqual(out["scope"], "RESEARCH_ONLY_NO_POLICY_PROMOTION")

    def test_market_before_unit_is_rejected(self):
        bad = GOOD.replace(
            'def interpreter(state, env):\n    for i, s in enumerate(state):\n        _apply_unit_action({}, {}, 0, ["PASS"], 10, 0, 24, 100)\n    _process_market(state, env)',
            'def interpreter(state, env):\n    _process_market(state, env)\n    _apply_unit_action({}, {}, 0, ["PASS"], 10, 0, 24, 100)')
        with self.assertRaisesRegex(ValueError, "unit_phase_precedes_market_phase"):
            oracle.analyze_text(bad)

    def test_tile_guard_before_move_is_rejected(self):
        bad = GOOD.replace(
            '    if op in FARMER_MOVES:\n',
            '    tile = farm["tiles"][fy][fx]\n    if tile == "LOCKED":\n        return\n    if op in FARMER_MOVES:\n',
            1).replace(
            '    tile = farm["tiles"][fy][fx]\n    if tile == "LOCKED":\n        return\n\ndef _do_buy_land',
            '\ndef _do_buy_land',
            1)
        with self.assertRaisesRegex(ValueError, "locked_move_precedes_tile_guard"):
            oracle.analyze_text(bad)

    def test_unlock_before_cash_guard_is_rejected(self):
        bad = GOOD.replace(
            '    if farm["money"] < cost:\n        return\n    quadrant = "NE"\n    farm["unlocked_quadrants"].append(quadrant)',
            '    quadrant = "NE"\n    farm["unlocked_quadrants"].append(quadrant)\n    if farm["money"] < cost:\n        return')
        with self.assertRaisesRegex(ValueError, "buy_land_cash_guard_precedes_unlock"):
            oracle.analyze_text(bad)

    def test_missing_buy_land_dispatch_is_rejected(self):
        bad = GOOD.replace('elif op == "BUY_LAND":', 'elif op == "OTHER":')
        with self.assertRaisesRegex(ValueError, "buy_land_market_dispatch"):
            oracle.analyze_text(bad)

    def test_missing_locked_movement_contract_is_rejected(self):
        bad = GOOD.replace("Movement onto LOCKED tiles is allowed", "ordinary movement")
        with self.assertRaisesRegex(ValueError, "locked_move_is_explicitly_legal"):
            oracle.analyze_text(bad)

    def test_git_blob_helper(self):
        self.assertEqual(oracle.git_blob(b""), "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391")

if __name__ == "__main__":
    unittest.main()
