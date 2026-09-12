import importlib.util
import pathlib
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("route_motion_census", HERE / "route_motion_census.py")
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def action(farmer=None, market=None):
    return {
        "farmer": farmer or ["PASS"],
        "hands": [],
        "market": market or [],
    }


class MotionCensusTests(unittest.TestCase):
    def test_two_step_loop_is_admitted(self):
        report = mod.census_route(
            [action(["EAST"]), action(["WEST"])],
            plan=0,
        )
        self.assertEqual(report["closed_loop_count"], 1)
        self.assertEqual(report["individually_pass_equivalent_movement_rows"], [])
        self.assertEqual(report["jointly_pass_equivalent_loop_movement_rows"], [0, 1])
        self.assertEqual(
            report["closed_hire_free_motion_loops"][0]["movement_rows"], [0, 1]
        )

    def test_closed_loop_rows_are_not_individual_authorizations(self):
        report = mod.census_route(
            [action(["EAST"]), action(["WEST"])],
            plan=0,
        )
        self.assertEqual(report["individually_pass_equivalent_movement_rows"], [])
        self.assertEqual(
            report["closed_hire_free_motion_loops"][0]["movement_rows"], [0, 1]
        )
        # Replacing only one member would leave the other executed move and
        # therefore cannot inherit the closed-loop equivalence theorem.
        start = mod._default_spawn()
        after_east, _ = mod._move(start, "EAST", mod.BOARD_SIZE)
        after_west_only, _ = mod._move(start, "WEST", mod.BOARD_SIZE)
        self.assertNotEqual(after_east, start)
        self.assertNotEqual(after_west_only, start)

    def test_hire_is_a_position_semantics_barrier(self):
        report = mod.census_route(
            [
                action(["EAST"], [["HIRE"]]),
                action(["WEST"]),
            ],
            plan=0,
        )
        self.assertEqual(report["closed_loop_count"], 0)
        self.assertEqual(report["individually_pass_equivalent_movement_rows"], [])
        self.assertEqual(report["jointly_pass_equivalent_loop_movement_rows"], [])

    def test_substantive_unit_action_is_a_barrier(self):
        report = mod.census_route(
            [
                action(["EAST"]),
                action(["WATER"]),
                action(["WEST"]),
            ],
            plan=0,
        )
        self.assertEqual(report["closed_loop_count"], 0)

    def test_pass_inside_loop_does_not_break_proof(self):
        report = mod.census_route(
            [
                action(["EAST"]),
                action(["PASS"]),
                action(["WEST"]),
            ],
            plan=0,
        )
        self.assertEqual(report["closed_loop_count"], 1)
        self.assertEqual(report["individually_pass_equivalent_movement_rows"], [])
        self.assertEqual(report["jointly_pass_equivalent_loop_movement_rows"], [0, 2])

    def test_boundary_move_is_already_pass_equivalent(self):
        report = mod.census_route(
            [action(["EAST"])],
            plan=0,
            board_size=1,
        )
        self.assertEqual(report["boundary_noop_rows"], [0])
        self.assertEqual(report["individually_pass_equivalent_movement_rows"], [0])
        self.assertEqual(report["jointly_pass_equivalent_loop_movement_rows"], [])

    def test_day_boundary_resets_loop_state(self):
        route = [action(["PASS"]) for _ in range(25)]
        route[23] = action(["EAST"])
        route[24] = action(["WEST"])
        report = mod.census_route(route, plan=0)
        self.assertEqual(report["closed_loop_count"], 0)

    def test_disjoint_loops_are_not_nested_spam(self):
        report = mod.census_route(
            [
                action(["EAST"]),
                action(["WEST"]),
                action(["NORTH"]),
                action(["SOUTH"]),
            ],
            plan=0,
        )
        self.assertEqual(report["closed_loop_count"], 2)
        self.assertEqual(report["individually_pass_equivalent_movement_rows"], [])
        self.assertEqual(
            report["jointly_pass_equivalent_loop_movement_rows"], [0, 1, 2, 3]
        )
        self.assertEqual(
            [g["movement_rows"] for g in report["closed_hire_free_motion_loops"]],
            [[0, 1], [2, 3]],
        )

    def test_effective_route_uses_canonical_splice(self):
        tapes = []
        for plan in range(mod.TAPE_COUNT):
            tapes.append([
                {"farmer": ["PASS", plan, step], "hands": [], "market": []}
                for step in range(mod.TAPE_STEPS)
            ])
        route = mod.effective_route(tapes, 7)
        self.assertEqual(len(route), mod.TAPE_STEPS)
        self.assertEqual(route[143]["farmer"][1], 0)
        self.assertEqual(route[144]["farmer"][1], 7)
        self.assertEqual(route[647]["farmer"][1], 7)
        self.assertEqual(route[648]["farmer"][1], 2)

    def test_source_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            engine = root / "engine.py"
            tapes = root / "tapes.py"
            router = root / "router.py"
            engine.write_text("x = 1\n", encoding="utf-8")
            tapes.write_text("x = 1\n", encoding="utf-8")
            router.write_text("x = 1\n", encoding="utf-8")
            with self.assertRaises(mod.MotionCensusError):
                mod.verify_sources(
                    engine_path=engine,
                    tapes_path=tapes,
                    router_path=router,
                )

    def test_checkout_sources_and_full_bank(self):
        if not (mod.ENGINE_PATH.exists() and mod.TAPES_PATH.exists() and mod.ROUTER_PATH.exists()):
            self.skipTest("repository checkout not mounted")
        sources = mod.verify_sources()
        tapes = mod.load_tapes()
        report = mod.build_report(tapes, sources)
        self.assertEqual(report["schema"], "titan.v4.route-motion-census.v2")
        self.assertEqual(len(report["routes"]), 13)
        self.assertEqual(
            report["totals"]["individually_pass_equivalent_count"],
            sum(
                route["individually_pass_equivalent_count"]
                for route in report["routes"]
            ),
        )
        self.assertEqual(
            report["totals"]["jointly_pass_equivalent_loop_movement_count"],
            sum(
                route["jointly_pass_equivalent_loop_movement_count"]
                for route in report["routes"]
            ),
        )


if __name__ == "__main__":
    unittest.main()
