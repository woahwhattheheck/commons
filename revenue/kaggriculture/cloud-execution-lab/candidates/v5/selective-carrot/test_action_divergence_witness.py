#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("witness", HERE / "action_divergence_witness.py")
w = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(w)


def row(step, obs, action):
    return {
        "step": step,
        "observation_sha256": w._digest({"obs": obs}),
        "response_kind": "action",
        "action_sha256": w._digest({"a": action}),
        "action": {"a": action},
    }


class WitnessTests(unittest.TestCase):
    def test_candidate_action_first_then_observation_diverges(self):
        lc = [row(i, 0 if i < 4 else 1, 0 if i < 3 else 7) for i in range(6)]
        rc = [row(i, 0 if i < 4 else 2, 0 if i < 3 else 8) for i in range(6)]
        lo = [row(i, 0 if i < 4 else 1, 4 if i < 4 else 5) for i in range(6)]
        ro = [row(i, 0 if i < 4 else 2, 4 if i < 4 else 6) for i in range(6)]
        got = w.compare_traces(lc, rc, lo, ro, radius=1)
        self.assertEqual(got["first_candidate_action_divergence_step"], 3)
        self.assertEqual(got["first_candidate_observation_divergence_step"], 4)
        self.assertEqual(got["first_opponent_action_divergence_step"], 4)
        self.assertEqual(got["first_any_action_divergence_step"], 3)
        self.assertTrue(got["candidate_action_is_first_observed_divergence"])
        self.assertEqual([r["step"] for r in got["witness_window"]], [2, 3, 4])
        self.assertEqual(got["witness_window"][1]["left_candidate"]["action"], {"a": 7})
        self.assertEqual(got["witness_window"][1]["right_candidate"]["action"], {"a": 8})

    def test_complete_compact_vectors_bind_trace_digest_without_full_actions(self):
        trace = [row(i, i, i + 10) for i in range(5)]
        got = w.compare_traces(trace, trace, trace, trace)
        vectors = got["trace_vectors"]
        self.assertEqual(
            set(vectors),
            {"left_candidate", "right_candidate", "left_opponent", "right_opponent"},
        )
        compact = vectors["left_candidate"]
        self.assertEqual(len(compact), 5)
        self.assertEqual([item["step"] for item in compact], list(range(5)))
        self.assertEqual(
            set(compact[0]),
            {"step", "observation_sha256", "action_sha256"},
        )
        expected_digest = w._digest([
            {key: value for key, value in item.items() if key != "action"}
            for item in trace
        ])
        self.assertEqual(got["left_candidate_trace_sha256"], expected_digest)

    def test_identical_traces_have_no_window(self):
        trace = [row(i, i, i + 10) for i in range(5)]
        got = w.compare_traces(trace, trace, trace, trace)
        self.assertTrue(got["all_actions_identical"])
        self.assertIsNone(got["first_any_action_divergence_step"])
        self.assertEqual(got["witness_window"], [])

    def test_opponent_divergence_first_blocks_candidate_causal_label(self):
        lc = [row(i, i, 1 if i < 3 else 2) for i in range(5)]
        rc = [row(i, i, 1 if i < 3 else 3) for i in range(5)]
        lo = [row(i, i, 9 if i < 2 else 8) for i in range(5)]
        ro = [row(i, i, 9 if i < 2 else 7) for i in range(5)]
        got = w.compare_traces(lc, rc, lo, ro)
        self.assertEqual(got["first_opponent_action_divergence_step"], 2)
        self.assertEqual(got["first_candidate_action_divergence_step"], 3)
        self.assertFalse(got["candidate_action_is_first_observed_divergence"])

    def test_same_step_observation_divergence_blocks_causal_label(self):
        lc = [row(i, 0, 0 if i < 2 else 1) for i in range(4)]
        rc = [row(i, 0 if i < 2 else 1, 0 if i < 2 else 2) for i in range(4)]
        opp = [row(i, 0, 5) for i in range(4)]
        got = w.compare_traces(lc, rc, opp, opp)
        self.assertEqual(got["first_candidate_action_divergence_step"], 2)
        self.assertEqual(got["first_candidate_observation_divergence_step"], 2)
        self.assertFalse(got["candidate_action_is_first_observed_divergence"])

    def test_noncontiguous_trace_rejects(self):
        bad = [row(0, 0, 0), row(2, 0, 0)]
        good = [row(0, 0, 0), row(1, 0, 0)]
        with self.assertRaises(w.WitnessError):
            w.compare_traces(bad, good, good, good)

    def test_trace_length_mismatch_rejects(self):
        a = [row(0, 0, 0)]
        b = [row(0, 0, 0), row(1, 0, 0)]
        with self.assertRaises(w.WitnessError):
            w.compare_traces(a, b, b, b)

    def test_window_radius_bounds(self):
        trace = [row(i, i, i) for i in range(2)]
        with self.assertRaises(w.WitnessError):
            w.compare_traces(trace, trace, trace, trace, radius=13)

    def test_seat_parser(self):
        self.assertEqual(w._parse_seats("0,1"), [0, 1])
        self.assertEqual(w._parse_seats("1"), [1])
        for bad in ("", "2", "0,0", "x"):
            with self.assertRaises(w.WitnessError):
                w._parse_seats(bad)

    def test_sha_validation(self):
        good = "a" * 64
        self.assertEqual(w._expected_sha(good, "x"), good)
        for bad in ("A" * 64, "a" * 63, "nope"):
            with self.assertRaises(w.WitnessError):
                w._expected_sha(bad, "x")


class MockEvaluator:
    class Actor:
        def __init__(self, spec, cache, loader, rng_seed, startup_timeout=10.0):
            self.spec = spec

        def act(self, observation, configuration, timeout):
            return {
                "kind": "action",
                "action": {"type": "farm"},
            }

        def close(self):
            pass

    @classmethod
    def play(
        cls,
        engine,
        specs,
        engine_dir,
        loader,
        seed,
        candidate_seat,
        rng_seed=0,
        action_timeout=1.0,
        startup_timeout=10.0,
        game_timeout=60.0,
    ):
        actors = [
            cls.Actor(s, engine_dir, loader, rng_seed + i, startup_timeout)
            for i, s in enumerate(specs)
        ]
        try:
            obs = {"step": 0}
            for actor in actors:
                actor.act(obs, {}, action_timeout)
        finally:
            for actor in actors:
                actor.close()
        return {
            "status": "complete",
            "scores": [100, 100],
            "steps": 1,
        }


class CustodyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="test_witness_custody_")
        self.tmp_path = Path(self.tmp.name)
        self.left_spec_file = self.tmp_path / "left.py"
        self.right_spec_file = self.tmp_path / "right.py"
        self.opponent_spec_file = self.tmp_path / "opponent.py"

        self.left_spec_file.write_text("def agent(obs, cfg):\n    return {}\n", encoding="utf-8")
        self.right_spec_file.write_text("def agent(obs, cfg):\n    return {}\n", encoding="utf-8")
        self.opponent_spec_file.write_text("def agent(obs, cfg):\n    return {}\n", encoding="utf-8")

        self.left_spec = f"{self.left_spec_file}::agent"
        self.right_spec = f"{self.right_spec_file}::agent"
        self.opponent_spec = f"{self.opponent_spec_file}::agent"

        self.expected_deps = {
            self.left_spec: w._inspect_spec_dependencies(self.left_spec),
            self.right_spec: w._inspect_spec_dependencies(self.right_spec),
            self.opponent_spec: w._inspect_spec_dependencies(self.opponent_spec),
        }

    def tearDown(self):
        self.tmp.cleanup()

    def test_clean_execution_passes_custody(self):
        res, rec = w._run_arm(
            MockEvaluator,
            None,
            candidate_spec=self.left_spec,
            opponent_spec=self.opponent_spec,
            engine_dir=self.tmp_path,
            loader=self.tmp_path,
            seed=42,
            candidate_seat=0,
            rng_seed=0,
            action_timeout=1.0,
            startup_timeout=1.0,
            game_timeout=5.0,
            expected_deps=self.expected_deps,
        )
        self.assertEqual(res["status"], "complete")

    def test_hostile_mutation_between_arms_fails(self):
        # Arm 1 runs clean
        res1, rec1 = w._run_arm(
            MockEvaluator,
            None,
            candidate_spec=self.left_spec,
            opponent_spec=self.opponent_spec,
            engine_dir=self.tmp_path,
            loader=self.tmp_path,
            seed=42,
            candidate_seat=0,
            rng_seed=0,
            action_timeout=1.0,
            startup_timeout=1.0,
            game_timeout=5.0,
            expected_deps=self.expected_deps,
        )
        self.assertEqual(res1["status"], "complete")

        # Adversary mutates right candidate spec file before Arm 2
        self.right_spec_file.write_text(
            "def agent(obs, cfg):\n    return {'tampered': True}\n", encoding="utf-8"
        )

        # Arm 2 must fail immediately at actor startup boundary
        with self.assertRaises(w.WitnessError) as ctx:
            w._run_arm(
                MockEvaluator,
                None,
                candidate_spec=self.right_spec,
                opponent_spec=self.opponent_spec,
                engine_dir=self.tmp_path,
                loader=self.tmp_path,
                seed=42,
                candidate_seat=0,
                rng_seed=0,
                action_timeout=1.0,
                startup_timeout=1.0,
                game_timeout=5.0,
                expected_deps=self.expected_deps,
            )
        self.assertIn("drifted", str(ctx.exception))

    def test_hostile_mutation_and_restore_fails_at_startup_boundary(self):
        # Adversary mutates spec, starts arm (expecting to restore before final hash)
        original_content = self.left_spec_file.read_text(encoding="utf-8")
        self.left_spec_file.write_text("# tampered bytes\n" + original_content, encoding="utf-8")

        # Startup boundary verification prevents execution of mutated code
        with self.assertRaises(w.WitnessError) as ctx:
            w._run_arm(
                MockEvaluator,
                None,
                candidate_spec=self.left_spec,
                opponent_spec=self.opponent_spec,
                engine_dir=self.tmp_path,
                loader=self.tmp_path,
                seed=42,
                candidate_seat=0,
                rng_seed=0,
                action_timeout=1.0,
                startup_timeout=1.0,
                game_timeout=5.0,
                expected_deps=self.expected_deps,
            )
        self.assertIn("drifted", str(ctx.exception))

        # Even if restored, the startup boundary already aborted execution
        self.left_spec_file.write_text(original_content, encoding="utf-8")

    def test_hostile_underlying_dependency_mutation_fails(self):
        # Create an adapter referencing an underlying main.py member
        member_file = self.tmp_path / "underlying_main.py"
        member_file.write_text("# initial policy member\n", encoding="utf-8")
        adapter_file = self.tmp_path / "adapter.py"
        adapter_file.write_text(
            f'TARGET = "{member_file.as_posix()}"\ndef agent(obs, cfg):\n    return {{}}\n',
            encoding="utf-8",
        )
        adapter_spec = f"{adapter_file}::agent"

        expected = {
            adapter_spec: w._inspect_spec_dependencies(adapter_spec),
            self.opponent_spec: w._inspect_spec_dependencies(self.opponent_spec),
        }
        self.assertIn(str(member_file.resolve()), expected[adapter_spec])

        # Mutate the underlying member between arms
        member_file.write_text("# modified policy member\n", encoding="utf-8")

        # Startup boundary checks discovered dependencies and fails closed
        with self.assertRaises(w.WitnessError) as ctx:
            w._run_arm(
                MockEvaluator,
                None,
                candidate_spec=adapter_spec,
                opponent_spec=self.opponent_spec,
                engine_dir=self.tmp_path,
                loader=self.tmp_path,
                seed=42,
                candidate_seat=0,
                rng_seed=0,
                action_timeout=1.0,
                startup_timeout=1.0,
                game_timeout=5.0,
                expected_deps=expected,
            )
        self.assertIn("drifted", str(ctx.exception))

    def test_hostile_mutation_during_game_fails_at_close(self):
        spec_file = self.left_spec_file

        class TamperingEvaluator:
            class Actor:
                def __init__(self, spec, cache, loader, rng_seed, startup_timeout=10.0):
                    self.spec = spec

                def act(self, obs, cfg, to):
                    # Hostile tamper during execution
                    spec_file.write_text("# tampered during game\n", encoding="utf-8")
                    return {"kind": "action", "action": {}}

                def close(self):
                    pass

            @classmethod
            def play(cls, engine, specs, engine_dir, loader, seed, candidate_seat, **kwargs):
                actors = [cls.Actor(s, engine_dir, loader, 0) for s in specs]
                try:
                    for a in actors:
                        a.act({"step": 0}, {}, 1.0)
                finally:
                    for a in actors:
                        a.close()
                return {"status": "complete", "scores": [0, 0]}

        with self.assertRaises(w.WitnessError) as ctx:
            w._run_arm(
                TamperingEvaluator,
                None,
                candidate_spec=self.left_spec,
                opponent_spec=self.opponent_spec,
                engine_dir=self.tmp_path,
                loader=self.tmp_path,
                seed=42,
                candidate_seat=0,
                rng_seed=0,
                action_timeout=1.0,
                startup_timeout=1.0,
                game_timeout=5.0,
                expected_deps=self.expected_deps,
            )
        self.assertIn("drifted", str(ctx.exception))

    def test_run_witness_hostile_mutation_between_arms_fails(self):
        evaluator_file = self.tmp_path / "mock_evaluator.py"
        evaluator_code = """
class Actor:
    def __init__(self, spec, cache, loader, rng_seed, startup_timeout=10.0):
        self.spec = spec
    def act(self, obs, cfg, to):
        return {"kind": "action", "action": {"a": 1}}
    def close(self):
        pass

def get_engine(engine_dir, loader):
    return None, {"engine": "0" * 64}

def play(engine, specs, engine_dir, loader, seed, candidate_seat, **kwargs):
    actors = [Actor(s, engine_dir, loader, 0) for s in specs]
    try:
        obs = {"step": 0}
        for a in actors:
            a.act(obs, {}, 1.0)
    finally:
        for a in actors:
            a.close()
    return {"status": "complete", "scores": [0, 0], "candidate_seat": candidate_seat}
"""
        evaluator_file.write_text(evaluator_code, encoding="utf-8")
        loader_file = self.tmp_path / "loader.py"
        loader_file.write_text("# loader\n", encoding="utf-8")
        left_archive = self.tmp_path / "left.tar.gz"
        left_archive.write_text("# archive\n", encoding="utf-8")
        right_archive = self.tmp_path / "right.tar.gz"
        right_archive.write_text("# archive\n", encoding="utf-8")

        import argparse

        args = argparse.Namespace(
            evaluator=str(evaluator_file),
            expected_evaluator_sha256=w._sha_file(evaluator_file),
            loader=str(loader_file),
            expected_loader_sha256=w._sha_file(loader_file),
            engine_dir=str(self.tmp_path),
            left_archive=str(left_archive),
            left_archive_sha256=w._sha_file(left_archive),
            right_archive=str(right_archive),
            right_archive_sha256=w._sha_file(right_archive),
            left_candidate=self.left_spec,
            right_candidate=self.right_spec,
            opponent=self.opponent_spec,
            left_label="left",
            right_label="right",
            opponent_label="opp",
            seats="0",
            action_timeout=1.0,
            startup_timeout=1.0,
            game_timeout=5.0,
            seed=42,
            rng_seed=0,
            window_radius=2,
            output=self.tmp_path / "out.json",
        )

        rep = w.run_witness(args)
        self.assertEqual(rep["authority"]["left_entry_sha256"], w._sha_file(self.left_spec_file))

        tamper_evaluator = self.tmp_path / "tamper_evaluator.py"
        opp_file = self.opponent_spec_file
        tamper_code = f"""
class Actor:
    def __init__(self, spec, cache, loader, rng_seed, startup_timeout=10.0):
        self.spec = spec
    def act(self, obs, cfg, to):
        return {{"kind": "action", "action": {{"a": 1}}}}
    def close(self):
        pass

def get_engine(engine_dir, loader):
    return None, {{"engine": "0" * 64}}

call_count = 0
def play(engine, specs, engine_dir, loader, seed, candidate_seat, **kwargs):
    global call_count
    call_count += 1
    if call_count == 2:
        from pathlib import Path
        Path({repr(str(opp_file))}).write_text("# adversary tamper\\n", encoding="utf-8")
    actors = [Actor(s, engine_dir, loader, 0) for s in specs]
    try:
        obs = {{"step": 0}}
        for a in actors:
            a.act(obs, {{}}, 1.0)
    finally:
        for a in actors:
            a.close()
    return {{"status": "complete", "scores": [0, 0], "candidate_seat": candidate_seat}}
"""
        tamper_evaluator.write_text(tamper_code, encoding="utf-8")
        args.evaluator = str(tamper_evaluator)
        args.expected_evaluator_sha256 = w._sha_file(tamper_evaluator)

        with self.assertRaises(w.WitnessError) as ctx:
            w.run_witness(args)
        self.assertIn("drifted", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
