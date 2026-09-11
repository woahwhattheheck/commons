import hashlib
import unittest
from types import SimpleNamespace

import v31_externality_replay_sidecar as sidecar


def board(signal=None):
    tiles = [[None for _ in range(10)] for _ in range(10)]
    if signal:
        product, units = signal
        if product in {"WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"}:
            tiles[0][0] = {"kind": "PLANT", "crop": product, "yield_units": units}
        elif product == "WOOL":
            tiles[0][0] = {"kind": "PASTURE", "animal": "SHEEP", "yield_units": units}
        elif product == "MILK":
            tiles[0][0] = {"kind": "PASTURE", "animal": "COW", "yield_units": units}
        elif product == "EGG":
            tiles[0][0] = {"kind": "COOP", "animal": "GOOSE", "yield_units": units}
    return tiles


def farms(signal0=None, signal1=None):
    return [{"tiles": board(signal0)}, {"tiles": board(signal1)}]


class FakeEngine:
    def __init__(self, schedule, malformed_step=None, raise_step=None):
        self.schedule = schedule
        self.malformed_step = malformed_step
        self.raise_step = raise_step
        self.interpreter = self._interpreter

    def _interpreter(self, state, env):
        # Initial call intentionally has no step.
        if not hasattr(state[0].observation, "step"):
            return None
        step = state[0].observation.step
        if self.raise_step == step:
            raise RuntimeError("engine boom")
        payload = self.schedule[step]
        for seat in (0, 1):
            state[seat].observation.farms = payload["farms"]
            state[seat].observation.market = {"prices": dict(payload["prices"])}
            state[seat].observation.player = seat
        if self.malformed_step == step:
            state[0].observation.market["prices"]["WOOL"] = True
        return None


class FakeEvaluator:
    @staticmethod
    def play(engine, specs, cache, loader, seed, candidate_seat, **kwargs):
        state = [SimpleNamespace(observation=SimpleNamespace()), SimpleNamespace(observation=SimpleNamespace())]
        env = SimpleNamespace()
        engine.interpreter(state, env)
        steps = len(engine.schedule)
        trace = hashlib.sha256()
        for step in range(steps):
            for seat in (0, 1):
                state[seat].observation.step = step
            engine.interpreter(state, env)
            trace.update(str(step).encode())
        return {
            "status": "complete",
            "scores": [100.0, 90.0],
            "steps": steps,
            "trace_sha256": trace.hexdigest(),
        }


def prices(**patch):
    base = {product: 100 for product in sidecar._PRODUCTS}
    base.update(patch)
    return base


class SidecarTests(unittest.TestCase):
    def capture(self, schedule, seat=0, **engine_kwargs):
        engine = FakeEngine(schedule, **engine_kwargs)
        original = engine.interpreter
        result = sidecar.capture_official_play(
            FakeEvaluator, engine, ["a", "b"], None, None, 123, seat
        )
        self.assertIs(engine.interpreter, original)
        return result

    def test_complete_capture_preserves_result_and_steps(self):
        schedule = [
            {"farms": farms(None, ("WOOL", 4)), "prices": prices()},
            {"farms": farms(None, ("WOOL", 5)), "prices": prices(WOOL=99)},
        ]
        got = self.capture(schedule)
        self.assertTrue(got["capture_complete"])
        self.assertEqual([s["step"] for s in got["snapshots"]], [0, 1])
        self.assertEqual(got["result"]["scores"], [100.0, 90.0])

    def test_price_divergence_emits_conservative_public_supply_event(self):
        baseline = self.capture([
            {"farms": farms(None, ("WOOL", 4)), "prices": prices(WOOL=100)}
        ])
        candidate = self.capture([
            {"farms": farms(None, ("WOOL", 7)), "prices": prices(WOOL=103)}
        ])
        receipt = sidecar.compare_cell("v1", 123, 0, baseline, candidate)
        self.assertTrue(receipt["externality_complete"])
        self.assertEqual(receipt["coverage"]["events_observed"], 1)
        event = receipt["events"][0]
        self.assertEqual(event["price_delta"], 3)
        self.assertEqual(event["rival_long_units"], 7)
        self.assertEqual(event["product"], "WOOL")

    def test_equal_prices_can_prove_complete_zero_event_coverage(self):
        arm = self.capture([
            {"farms": farms(None, ("WOOL", 4)), "prices": prices(WOOL=100)}
        ])
        receipt = sidecar.compare_cell("v1", 123, 0, arm, arm)
        doc = sidecar.assemble_d3_document([receipt])
        self.assertTrue(doc["externality_complete"])
        self.assertEqual(doc["externality_events"], [])
        self.assertEqual(doc["externality_coverage"][0]["events_observed"], 0)

    def test_malformed_public_state_marks_capture_incomplete_without_changing_scores(self):
        schedule = [{"farms": farms(None, ("WOOL", 4)), "prices": prices()}]
        got = self.capture(schedule, malformed_step=0)
        self.assertFalse(got["capture_complete"])
        self.assertEqual(got["result"]["scores"], [100.0, 90.0])
        self.assertTrue(got["capture_errors"])

    def test_bool_yield_units_fail_closed(self):
        schedule = [{"farms": farms(None, ("WOOL", True)), "prices": prices()}]
        got = self.capture(schedule)
        self.assertFalse(got["capture_complete"])

    def test_mismatched_trace_domains_produce_hold_receipt(self):
        baseline = self.capture([
            {"farms": farms(None, ("WOOL", 1)), "prices": prices()},
            {"farms": farms(None, ("WOOL", 1)), "prices": prices()},
        ])
        candidate = self.capture([
            {"farms": farms(None, ("WOOL", 1)), "prices": prices()}
        ])
        receipt = sidecar.compare_cell("v1", 123, 0, baseline, candidate)
        self.assertFalse(receipt["externality_complete"])
        doc = sidecar.assemble_d3_document([receipt])
        self.assertFalse(doc["externality_complete"])
        self.assertNotIn("externality_coverage", doc)

    def test_candidate_seat_one_measures_seat_zero_public_supply(self):
        baseline = self.capture([
            {"farms": farms(("MILK", 6), None), "prices": prices(MILK=100)}
        ], seat=1)
        candidate = self.capture([
            {"farms": farms(("MILK", 8), None), "prices": prices(MILK=102)}
        ], seat=1)
        receipt = sidecar.compare_cell("v1", 123, 1, baseline, candidate)
        self.assertEqual(receipt["events"][0]["rival_long_units"], 8)

    def test_interpreter_exception_propagates_and_wrapper_restores(self):
        schedule = [{"farms": farms(), "prices": prices()}]
        engine = FakeEngine(schedule, raise_step=0)
        original = engine.interpreter
        with self.assertRaises(RuntimeError):
            sidecar.capture_official_play(FakeEvaluator, engine, ["a", "b"], None, None, 1, 0)
        self.assertIs(engine.interpreter, original)

    def test_multiple_products_and_steps_have_unique_event_ids(self):
        baseline = self.capture([
            {"farms": farms(None, ("WOOL", 2)), "prices": prices(WOOL=100, MILK=100)},
            {"farms": farms(None, ("MILK", 3)), "prices": prices(WOOL=100, MILK=100)},
        ])
        candidate = self.capture([
            {"farms": farms(None, ("WOOL", 2)), "prices": prices(WOOL=101, MILK=99)},
            {"farms": farms(None, ("MILK", 3)), "prices": prices(WOOL=100, MILK=102)},
        ])
        receipt = sidecar.compare_cell("v1", 123, 0, baseline, candidate)
        ids = [e["event_id"] for e in receipt["events"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 3)

    def test_assemble_rejects_duplicate_cells(self):
        arm = self.capture([{ "farms": farms(), "prices": prices()}])
        receipt = sidecar.compare_cell("v1", 123, 0, arm, arm)
        with self.assertRaises(sidecar.ProducerError):
            sidecar.assemble_d3_document([receipt, receipt])


if __name__ == "__main__":
    unittest.main()
