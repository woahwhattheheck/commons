# SPDX-License-Identifier: Apache-2.0
"""Replay/reset contracts for the candidate and naive scheduler entrypoints."""
import unittest
from unittest.mock import patch

import scheduler


class _StubScheduler:
    def __init__(self, mode="candidate", token="stub"):
        self.mode = mode
        self.token = token
        self.calls = []

    def act(self, observation, configuration=None):
        self.calls.append((dict(observation), dict(configuration or {})))
        return {
            "token": self.token,
            "mode": self.mode,
            "calls": len(self.calls),
        }


class _FailingScheduler(_StubScheduler):
    def act(self, observation, configuration=None):
        self.calls.append((dict(observation), dict(configuration or {})))
        raise RuntimeError("injected reset failure")


class SchedulerEntrypointReplayTests(unittest.TestCase):
    def setUp(self):
        scheduler._INSTANCE = None
        scheduler._LAST_STEP = None
        scheduler._NAIVE = None
        scheduler._NAIVE_LAST_STEP = None

    def tearDown(self):
        scheduler._INSTANCE = None
        scheduler._LAST_STEP = None
        scheduler._NAIVE = None
        scheduler._NAIVE_LAST_STEP = None

    def test_candidate_and_naive_reuse_equal_steps_and_reset_only_on_rewind(self):
        created = []

        def make_stub(mode="candidate"):
            stub = _StubScheduler(mode, f"{mode}-{len(created)}")
            created.append(stub)
            return stub

        with patch.object(scheduler, "SellScheduler", side_effect=make_stub) as factory:
            first = scheduler.agent({"step": 0}, {})
            replay = scheduler.agent({"step": 0}, {})
            forward = scheduler.agent({"step": 4}, {})
            same = scheduler.agent({"step": 4}, {})
            rewind = scheduler.agent({"step": 3}, {})

            naive_first = scheduler.naive_agent({"step": 0}, {})
            naive_replay = scheduler.naive_agent({"step": 0}, {})
            naive_forward = scheduler.naive_agent({"step": 4}, {})
            naive_same = scheduler.naive_agent({"step": 4}, {})
            naive_rewind = scheduler.naive_agent({"step": 3}, {})

        self.assertEqual(factory.call_count, 4)
        self.assertEqual(
            [first["token"], replay["token"], forward["token"], same["token"]],
            ["candidate-0"] * 4,
        )
        self.assertEqual(rewind["token"], "candidate-1")
        self.assertEqual(
            [naive_first["token"], naive_replay["token"], naive_forward["token"], naive_same["token"]],
            ["naive-2"] * 4,
        )
        self.assertEqual(naive_rewind["token"], "naive-3")
        self.assertEqual([len(instance.calls) for instance in created], [4, 1, 4, 1])
        self.assertEqual(scheduler._LAST_STEP, 3)
        self.assertEqual(scheduler._NAIVE_LAST_STEP, 3)

    def test_failed_rewind_does_not_consume_reset_boundary(self):
        cases = (
            ("candidate", "agent", "_INSTANCE", "_LAST_STEP"),
            ("naive", "naive_agent", "_NAIVE", "_NAIVE_LAST_STEP"),
        )
        for mode, entrypoint_name, instance_name, last_step_name in cases:
            with self.subTest(mode=mode):
                old = _StubScheduler(mode, "old")
                failed = _FailingScheduler(mode, "failed-reset")
                retry = _StubScheduler(mode, "retry-reset")
                setattr(scheduler, instance_name, old)
                setattr(scheduler, last_step_name, 5)

                created = []

                def make_reset(requested_mode="candidate"):
                    self.assertEqual(requested_mode, mode)
                    instance = failed if not created else retry
                    created.append(instance)
                    return instance

                with patch.object(scheduler, "SellScheduler", side_effect=make_reset) as factory:
                    entrypoint = getattr(scheduler, entrypoint_name)
                    with self.assertRaisesRegex(RuntimeError, "injected reset failure"):
                        entrypoint({"step": 0}, {})
                    self.assertIs(getattr(scheduler, instance_name), failed)
                    self.assertEqual(getattr(scheduler, last_step_name), 5)

                    recovered = entrypoint({"step": 0}, {})

                self.assertEqual(factory.call_count, 2)
                self.assertIs(getattr(scheduler, instance_name), retry)
                self.assertEqual(getattr(scheduler, last_step_name), 0)
                self.assertEqual(recovered["token"], "retry-reset")
                self.assertEqual(len(failed.calls), 1)
                self.assertEqual(len(retry.calls), 1)

                setattr(scheduler, instance_name, None)
                setattr(scheduler, last_step_name, None)


if __name__ == "__main__":
    unittest.main()
