# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

import activation_eval as target


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


class FakeActor:
    serial = 0

    def __init__(self, *_args, **_kwargs):
        self.serial = FakeActor.serial
        FakeActor.serial += 1

    def act(self, observation, _configuration, _timeout):
        return {"kind": "action", "action": {"actor": self.serial, "step": observation.step}}


class ActivationOverlayTests(unittest.TestCase):
    def setUp(self):
        FakeActor.serial = 0

    def test_tracker_is_seat_specific_and_does_not_mutate_action(self):
        tracker = target.ActionDigestTracker(encoded)
        action0 = {"farmer": ["PASS"]}
        action1 = {"farmer": ["MOVE", 1, 2]}
        before0, before1 = copy.deepcopy(action0), copy.deepcopy(action1)
        tracker.record(0, 0, action0)
        tracker.record(1, 0, action1)
        self.assertEqual(before0, action0)
        self.assertEqual(before1, action1)
        self.assertEqual([1, 1], tracker.counts)
        self.assertNotEqual(*tracker.hexdigests())
        with self.assertRaisesRegex(target.OverlayError, "non-contiguous"):
            tracker.record(0, 2, action0)
        with self.assertRaisesRegex(target.OverlayError, "invalid action seat"):
            tracker.record(True, 1, action0)

    def test_wrapped_play_captures_before_interpreter_and_restores_method(self):
        events = []
        core = SimpleNamespace(Actor=FakeActor, encoded=encoded)
        original_act = FakeActor.act

        def play(*_args, **_kwargs):
            actors = [core.Actor(), core.Actor()]
            for step in range(2):
                actions = []
                for actor in actors:
                    response = actor.act(SimpleNamespace(step=step), {}, 1.0)
                    events.append(("returned", step, copy.deepcopy(response["action"])))
                    actions.append(response["action"])
                events.append(("interpreter", step, copy.deepcopy(actions)))
            return {"candidate_seat": 1, "steps": 2}

        wrapped = target.wrapped_play(core, play, original_act, encoded)
        result = wrapped()
        self.assertIs(core.Actor.act, original_act)
        self.assertEqual([2, 2], result["action_digest_steps_by_seat"])
        self.assertEqual(2, result["candidate_action_digest_steps"])
        self.assertEqual(result["action_sha256_by_seat"][1], result["candidate_action_sha256"])
        self.assertEqual(target.ACTION_DIGEST_SCHEMA, result["action_digest_schema"])
        self.assertEqual(target.ACTION_CAPTURE_BOUNDARY, result["action_digest_capture"])
        self.assertEqual("returned", events[0][0])
        self.assertEqual("interpreter", events[2][0])

    def test_wrapped_play_restores_actor_method_on_error(self):
        core = SimpleNamespace(Actor=FakeActor, encoded=encoded)
        original_act = FakeActor.act

        def explode(*_args, **_kwargs):
            actor = core.Actor()
            actor.act(SimpleNamespace(step=0), {}, 1.0)
            raise RuntimeError("boom")

        with self.assertRaisesRegex(RuntimeError, "boom"):
            target.wrapped_play(core, explode, original_act, encoded)()
        self.assertIs(core.Actor.act, original_act)

    def test_install_marks_every_report_with_overlay_identity(self):
        written = []

        def play(*_args, **_kwargs):
            return {"candidate_seat": 0, "steps": 0}

        def write_report(path, report):
            written.append((path, dict(report)))

        core = SimpleNamespace(Actor=FakeActor, encoded=encoded, play=play, write_report=write_report)
        target.install(core)
        core.write_report(Path("report.json"), {"schema_version": 1})
        identity = written[0][1]["activation_overlay"]
        self.assertEqual(target.CORE_EVALUATOR_GIT_BLOB, identity["core_evaluator_git_blob"])
        self.assertEqual(target.ACTION_DIGEST_SCHEMA, identity["action_digest_schema"])
        self.assertEqual(target.ACTION_CAPTURE_BOUNDARY, identity["action_digest_capture"])
        with self.assertRaisesRegex(target.OverlayError, "already installed"):
            target.install(core)


if __name__ == "__main__":
    unittest.main()
