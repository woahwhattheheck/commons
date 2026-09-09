# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("_mnemosyne_recovery_tested", HERE / "recovery_main.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ForeignDeadline(RuntimeError):
    pass


def seller_public(step, player=0, marker=1):
    farms = [{"tiles": []}, {"tiles": []}]
    farms[1 - int(player)] = {
        "tiles": [[{"kind": "PLANT", "crop": "MILK", "yield_units": marker}]]
    }
    return {"step": int(step), "player": int(player), "farms": farms}


class FakeInstance:
    def __init__(self, *, ready=False):
        self.ready = ready
        self.controller_cur = "MAIN"
        self._completed_route = None
        self._completed_seller_state = None
        self._seller_fallback_observations = []
        self.replayed_fallback_steps = []
        self.remember_calls = 0
        self.partial_finalizer = {"status": "clean"}
        self.history = {"unsafe": "fresh"}
        self.spatial = {"unsafe": "fresh"}
        self.quadrant = {"unsafe": "fresh"}
        self.diagnostics = {"unsafe": "fresh"}

    def _remember_seller_fallback(self, observation):
        self.remember_calls += 1
        step = int(observation.get("step", 0))
        row = seller_public(step, int(observation.get("player", 0)), marker=step + 1)
        if self._seller_fallback_observations:
            prior = int(self._seller_fallback_observations[-1].get("step", -1))
            if step < prior:
                self._seller_fallback_observations = []
            elif step == prior:
                self._seller_fallback_observations[-1] = row
                return
        self._seller_fallback_observations.append(row)

    def rebuild(self):
        self.controller_cur = self._completed_route or "MAIN"
        self.replayed_fallback_steps = [
            int(row["step"]) for row in self._seller_fallback_observations
        ]
        self.ready = True


class DriftedInstance:
    """Factory drift: deliberately lacks the committed seller fields."""
    def __init__(self):
        self.ready = False
        self.controller_cur = "MAIN"

    def rebuild(self):
        self.ready = True


class FakeCanonical:
    def __init__(self, behaviors=(), *, drift_factory=False):
        self._INSTANCE = None
        self.behaviors = list(behaviors)
        self.created = []
        self.drift_factory = drift_factory
        self.foreign = ForeignDeadline("foreign")

    def _new_instance(self, _root, _feature_data):
        instance = DriftedInstance() if self.drift_factory else FakeInstance(ready=False)
        self.created.append(instance)
        return instance

    @staticmethod
    def _step(observation, configuration):
        if observation.get("step") is not None:
            return int(observation["step"])
        return int(observation.get("day", 0)) * int((configuration or {}).get("turnsPerDay", 24)) + int(
            observation.get("hour", 0)
        )

    def agent(self, observation, configuration=None):
        step = self._step(observation, configuration)
        replace = self._INSTANCE is None or step == 0
        if replace:
            self._INSTANCE = self._new_instance(Path("."), {})
        instance = self._INSTANCE
        if not instance.ready:
            instance.rebuild()

        # Model Arlene's exact-turn branch decision and TITAN's pre-finalizer
        # publication of the route checkpoint.
        if step == 360:
            instance.controller_cur = "YARN_CARROT"
            if hasattr(instance, "_completed_route"):
                instance._completed_route = "YARN_CARROT"

        behavior = self.behaviors.pop(0) if self.behaviors else "success"
        output = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["ROUTE", instance.controller_cur, step]],
        }
        if behavior == "foreign":
            raise self.foreign
        if behavior in ("timeout", "timeout_recorded", "timeout_committed"):
            if hasattr(instance, "_completed_seller_state"):
                if behavior == "timeout_committed":
                    # Model a successful inner action whose completed seller
                    # checkpoint was published before the outer timer fired in
                    # the late finalizer.  Replaying this observation again
                    # would double-observe it.
                    instance._completed_seller_state = {
                        "planned": {"MILK": [[step + 1, 2]]},
                        "pending": {"MILK": 2},
                        "previous": seller_public(step, marker=step + 1),
                        "observed_harvests": {"MILK": [[step, 1]]},
                    }
                    instance._seller_fallback_observations = []
                elif instance._completed_seller_state is None:
                    instance._completed_seller_state = {
                        "planned": {"MILK": [[step + 1, 2]]},
                        "pending": {"MILK": 2},
                        "previous": seller_public(step - 1, marker=step),
                        "observed_harvests": {"MILK": [[step - 1, 1]]},
                    }
                if behavior == "timeout_recorded":
                    instance._remember_seller_fallback(observation)
            instance.partial_finalizer = {"status": "corrupt", "step": step}
            instance.history = {"unsafe": "mutated"}
            instance.spatial = {"unsafe": "mutated"}
            instance.quadrant = {"unsafe": "mutated"}
            instance.diagnostics = {"unsafe": "mutated"}
            instance.ready = False
            self._INSTANCE = None
        return output


def observation(step):
    return {"step": step, "player": 0, "farms": [{}, {}], "private": {}}


class RecoveryCarrierTests(unittest.TestCase):
    def test_predecessor_loses_exact_checkpoint_route_and_fallback(self):
        canonical = FakeCanonical(("timeout", "success"))
        original = FakeInstance(ready=True)
        canonical._INSTANCE = original

        first = canonical.agent(observation(360), {})
        second = canonical.agent(observation(361), {})

        self.assertEqual(first["market"][0][1], "YARN_CARROT")
        self.assertEqual(second["market"][0][1], "MAIN")
        self.assertEqual(canonical.created[-1].replayed_fallback_steps, [])
        self.assertEqual(original._seller_fallback_observations, [])

    def test_candidate_restores_route_seller_checkpoint_and_public_fallback(self):
        canonical = FakeCanonical(("timeout", "success"))
        original = FakeInstance(ready=True)
        canonical._INSTANCE = original
        carrier = MODULE.RecoveryCarrier(canonical)

        first = carrier.agent(observation(360), {})
        capsule = carrier.capsule()
        self.assertEqual(first["market"][0][1], "YARN_CARROT")
        self.assertEqual(carrier.last_report["status"], "captured")
        self.assertEqual(capsule["payload"]["route"], "YARN_CARROT")
        self.assertEqual([row["step"] for row in capsule["payload"]["fallbacks"]], [360])

        # The capsule is detached from the discarded, possibly corrupt object.
        original._completed_route = "MUTATED_AFTER_CAPTURE"
        original._completed_seller_state["pending"]["MILK"] = 999
        original._seller_fallback_observations[0]["step"] = 999

        second = carrier.agent(observation(361), {})
        rebuilt = canonical.created[-1]
        self.assertEqual(second["market"][0][1], "YARN_CARROT")
        self.assertEqual(rebuilt._completed_route, "YARN_CARROT")
        self.assertEqual(rebuilt._completed_seller_state["pending"]["MILK"], 2)
        self.assertEqual(rebuilt.replayed_fallback_steps, [360])
        self.assertIsNone(carrier.capsule())
        self.assertEqual(carrier.last_report["status"], "restored")

    def test_completed_current_checkpoint_is_not_requeued(self):
        canonical = FakeCanonical(("timeout_committed", "success"))
        original = FakeInstance(ready=True)
        canonical._INSTANCE = original
        carrier = MODULE.RecoveryCarrier(canonical)

        first = carrier.agent(observation(360), {})
        capsule = carrier.capsule()
        self.assertEqual(first["market"][0][1], "YARN_CARROT")
        self.assertEqual(carrier.last_report["status"], "captured")
        self.assertEqual(carrier.last_report["public_observation"], "checkpointed")
        self.assertFalse(carrier.last_report["recorded_current_step"])
        self.assertEqual(original.remember_calls, 0)
        self.assertEqual(capsule["payload"]["seller"]["previous"]["step"], 360)
        self.assertEqual(capsule["payload"]["fallbacks"], [])

        second = carrier.agent(observation(361), {})
        rebuilt = canonical.created[-1]
        self.assertEqual(second["market"][0][1], "YARN_CARROT")
        self.assertEqual(rebuilt.replayed_fallback_steps, [])
        self.assertEqual(rebuilt._completed_seller_state["previous"]["step"], 360)

    def test_partial_finalizer_objects_are_never_transferred(self):
        canonical = FakeCanonical(("timeout", "success"))
        original = FakeInstance(ready=True)
        canonical._INSTANCE = original
        carrier = MODULE.RecoveryCarrier(canonical)

        carrier.agent(observation(360), {})
        carrier.agent(observation(361), {})
        rebuilt = canonical.created[-1]

        self.assertEqual(rebuilt.partial_finalizer, {"status": "clean"})
        self.assertEqual(rebuilt.history, {"unsafe": "fresh"})
        self.assertEqual(rebuilt.spatial, {"unsafe": "fresh"})
        self.assertEqual(rebuilt.quadrant, {"unsafe": "fresh"})
        self.assertEqual(rebuilt.diagnostics, {"unsafe": "fresh"})

    def test_true_step_zero_clears_cross_episode_capsule(self):
        canonical = FakeCanonical(("timeout", "success"))
        canonical._INSTANCE = FakeInstance(ready=True)
        carrier = MODULE.RecoveryCarrier(canonical)
        carrier.agent(observation(360), {})
        self.assertIsNotNone(carrier.capsule())

        out = carrier.agent({"step": None, "day": 0, "hour": 0}, {"turnsPerDay": 24})
        rebuilt = canonical.created[-1]
        self.assertEqual(out["market"][0][1], "MAIN")
        self.assertIsNone(rebuilt._completed_route)
        self.assertEqual(rebuilt.replayed_fallback_steps, [])
        self.assertIsNone(carrier.capsule())

    def test_repeated_outer_timeouts_accumulate_exact_public_replay(self):
        canonical = FakeCanonical(("timeout", "timeout", "success"))
        canonical._INSTANCE = FakeInstance(ready=True)
        carrier = MODULE.RecoveryCarrier(canonical)

        carrier.agent(observation(360), {})
        carrier.agent(observation(361), {})
        capsule = carrier.capsule()
        self.assertEqual(capsule["payload"]["route"], "YARN_CARROT")
        self.assertEqual([row["step"] for row in capsule["payload"]["fallbacks"]], [360, 361])

        out = carrier.agent(observation(362), {})
        rebuilt = canonical.created[-1]
        self.assertEqual(out["market"][0][1], "YARN_CARROT")
        self.assertEqual(rebuilt.replayed_fallback_steps, [360, 361])

    def test_future_upstream_record_is_same_step_deduplicated(self):
        canonical = FakeCanonical(("timeout_recorded", "success"))
        original = FakeInstance(ready=True)
        canonical._INSTANCE = original
        carrier = MODULE.RecoveryCarrier(canonical)

        carrier.agent(observation(360), {})
        capsule = carrier.capsule()
        self.assertEqual([row["step"] for row in capsule["payload"]["fallbacks"]], [360])
        self.assertEqual(carrier.last_report["public_observation"], "queued")
        self.assertFalse(carrier.last_report["recorded_current_step"])
        self.assertEqual(original.remember_calls, 1)
        self.assertIsNone(canonical._INSTANCE)
        carrier.agent(observation(361), {})
        self.assertEqual(canonical.created[-1].replayed_fallback_steps, [360])

    def test_future_or_reordered_seller_state_fails_closed(self):
        source = FakeInstance(ready=True)
        source._completed_route = "YARN"
        source._completed_seller_state = {
            "planned": {}, "pending": {}, "previous": seller_public(400),
            "observed_harvests": {},
        }
        covered, reason = MODULE.ensure_public_observation(source, observation(360), 360)
        self.assertFalse(covered)
        self.assertEqual(reason, "future_state")
        self.assertEqual(source.remember_calls, 0)

        source._completed_seller_state["previous"] = seller_public(359)
        source._seller_fallback_observations = [seller_public(360), seller_public(360)]
        covered, reason = MODULE.ensure_public_observation(source, observation(360), 360)
        self.assertFalse(covered)
        self.assertEqual(reason, "malformed_fallback_order")
        self.assertEqual(source.remember_calls, 0)

    def test_digest_valid_incomplete_checkpoint_is_rejected_atomically(self):
        payload = {"route": "YARN", "seller": {}, "fallbacks": []}
        capsule = {
            "schema": MODULE.SCHEMA,
            "sha256": MODULE.hashlib.sha256(MODULE._canonical_bytes(payload)).hexdigest(),
            "payload": payload,
        }
        target = FakeInstance(ready=False)
        restored, reason = MODULE.restore_committed(target, capsule)
        self.assertFalse(restored)
        self.assertEqual(reason, "malformed_checkpoint_keys")
        self.assertIsNone(target._completed_route)
        self.assertIsNone(target._completed_seller_state)
        self.assertEqual(target._seller_fallback_observations, [])

    def test_player_board_and_numeric_drift_are_rejected(self):
        source = FakeInstance(ready=True)
        source._completed_route = "YARN"
        source._completed_seller_state = {
            "planned": {}, "pending": {}, "previous": seller_public(359),
            "observed_harvests": {},
        }
        other_player = seller_public(360, player=1)
        source._seller_fallback_observations = [other_player]
        self.assertIsNone(MODULE.capture_committed(source))

        source._seller_fallback_observations = [seller_public(360)]
        source._seller_fallback_observations[0]["farms"][1]["tiles"].append([])
        self.assertIsNone(MODULE.capture_committed(source))

        source._seller_fallback_observations = [seller_public(360)]
        source._completed_seller_state["pending"] = {"MILK": 1.5}
        self.assertIsNone(MODULE.capture_committed(source))

    def test_digest_tamper_is_rejected_without_partial_restore(self):
        canonical = FakeCanonical(("success",))
        carrier = MODULE.RecoveryCarrier(canonical)
        source = FakeInstance(ready=True)
        source._completed_route = "YARN"
        source._completed_seller_state = {"planned": {}, "pending": {}, "previous": None,
                                          "observed_harvests": {}}
        source._seller_fallback_observations = [seller_public(226)]
        capsule = MODULE.capture_committed(source)
        capsule["payload"]["route"] = "MUTATED"
        carrier._capsule = capsule

        out = carrier.agent(observation(227), {})
        rebuilt = canonical.created[-1]
        self.assertEqual(out["market"][0][1], "MAIN")
        self.assertIsNone(rebuilt._completed_route)
        self.assertEqual(rebuilt._seller_fallback_observations, [])
        self.assertEqual(carrier.last_report["status"], "restore_rejected")
        self.assertEqual(carrier.last_report["reason"], "digest")

    def test_factory_drift_degrades_to_canonical_fresh(self):
        canonical = FakeCanonical(("success",), drift_factory=True)
        carrier = MODULE.RecoveryCarrier(canonical)
        source = FakeInstance(ready=True)
        source._completed_route = "YARN"
        source._seller_fallback_observations = [seller_public(226)]
        carrier._capsule = MODULE.capture_committed(source)

        out = carrier.agent(observation(227), {})
        self.assertEqual(out["market"][0][1], "MAIN")
        self.assertEqual(carrier.last_report["status"], "restore_rejected")
        self.assertEqual(carrier.last_report["reason"], "factory_drift")

    def test_normal_success_preserves_exact_output_and_live_instance(self):
        canonical = FakeCanonical(("success",))
        live = FakeInstance(ready=True)
        live._completed_route = "YARN"
        live.controller_cur = "YARN"
        canonical._INSTANCE = live
        carrier = MODULE.RecoveryCarrier(canonical)

        expected = canonical.agent(observation(300), {})
        # Recreate the same state and run through the carrier.
        canonical.behaviors = ["success"]
        canonical._INSTANCE = live
        actual = carrier.agent(observation(300), {})
        self.assertEqual(actual, expected)
        self.assertIs(canonical._INSTANCE, live)
        self.assertIsNone(carrier.capsule())

    def test_foreign_exception_identity_and_live_state_are_untouched(self):
        canonical = FakeCanonical(("foreign",))
        live = FakeInstance(ready=True)
        live._completed_route = "YARN"
        live.controller_cur = "YARN"
        canonical._INSTANCE = live
        carrier = MODULE.RecoveryCarrier(canonical)

        with self.assertRaises(ForeignDeadline) as caught:
            carrier.agent(observation(300), {})
        self.assertIs(caught.exception, canonical.foreign)
        self.assertIs(canonical._INSTANCE, live)
        self.assertIsNone(carrier.capsule())

    def test_capture_rejects_non_json_and_wrong_safe_field_types(self):
        source = FakeInstance(ready=True)
        source._completed_route = 7
        self.assertIsNone(MODULE.capture_committed(source))
        source._completed_route = "YARN"
        source._completed_seller_state = {"bad": object()}
        self.assertIsNone(MODULE.capture_committed(source))
        source._completed_seller_state = {}
        source._seller_fallback_observations = []
        self.assertIsNone(MODULE.capture_committed(source))
        source._seller_fallback_observations = ["not-an-observation"]
        self.assertIsNone(MODULE.capture_committed(source))


if __name__ == "__main__":
    unittest.main()
