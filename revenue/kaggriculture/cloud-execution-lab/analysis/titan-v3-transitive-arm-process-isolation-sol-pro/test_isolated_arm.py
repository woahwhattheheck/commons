# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import unittest
from contextlib import contextmanager
from typing import Iterator

HERE = pathlib.Path(__file__).resolve().parent
MODULE_PATH = HERE / "isolated_arm.py"
SPEC = importlib.util.spec_from_file_location("isolated_arm_under_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
iso = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = iso
SPEC.loader.exec_module(iso)


def write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")


def cell(arm: str = "control", seat: int = 0, seed: int = 7) -> dict[str, object]:
    return {
        "schema": iso.CELL_SCHEMA,
        "arm": arm,
        "opponent": "fixture",
        "seed": seed,
        "candidate_seat": seat,
        "engine_sha256": "1" * 64,
        "evaluator_sha256": "2" * 64,
        "opponent_sha256": "3" * 64,
        "schedule_sha256": "4" * 64,
        "invocation_id": f"fixture-{arm}-{seed}-{seat}",
    }


@contextmanager
def runtime(main: str, **modules: str) -> Iterator[pathlib.Path]:
    with tempfile.TemporaryDirectory(prefix="iso-runtime-") as raw:
        root = pathlib.Path(raw)
        write(root / "main.py", main)
        for name, source in modules.items():
            write(root / name, source)
        yield root


def unsafe_private_main_load(root: pathlib.Path, unique: str):
    """Model the predecessor: private main, shared transitive imports."""
    previous_path = list(sys.path)
    sys.path.insert(0, str(root))
    try:
        spec = importlib.util.spec_from_file_location(unique, root / "main.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path[:] = previous_path


def purge_fixture_modules() -> None:
    for name in ["frozen_selected", "scheduler", "helper", "main"]:
        sys.modules.pop(name, None)


class BindingContracts(unittest.TestCase):
    def test_binding_and_runtime_verify(self) -> None:
        with runtime("def agent(x):\n    return x\n") as root:
            binding = iso.build_binding(root)
            self.assertEqual(binding["schema"], iso.BINDING_SCHEMA)
            self.assertEqual(binding["entrypoint"], "main.py")
            self.assertEqual(binding["files"].keys(), {"main.py"})
            iso.verify_runtime(root, binding)

    def test_binding_rejects_symlink(self) -> None:
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unsupported")
        with runtime("def agent():\n    return 1\n") as root:
            outside = root.parent / f"outside-{root.name}.py"
            outside.write_text("X=1\n", encoding="utf-8")
            try:
                os.symlink(outside, root / "link.py")
                with self.assertRaisesRegex(iso.BindingError, "symlink"):
                    iso.build_binding(root)
            finally:
                outside.unlink(missing_ok=True)

    def test_binding_rejects_hardlink(self) -> None:
        if not hasattr(os, "link"):
            self.skipTest("hardlink unsupported")
        with runtime("def agent():\n    return 1\n") as root:
            os.link(root / "main.py", root / "alias.py")
            with self.assertRaisesRegex(iso.BindingError, "hard-linked"):
                iso.build_binding(root)

    def test_binding_rejects_traversal_entrypoint(self) -> None:
        with runtime("def agent():\n    return 1\n") as root:
            with self.assertRaisesRegex(iso.BindingError, "unsafe entrypoint"):
                iso.build_binding(root, entrypoint="../main.py")

    def test_binding_detects_mutation(self) -> None:
        with runtime("def agent():\n    return 1\n") as root:
            binding = iso.build_binding(root)
            write(root / "main.py", "def agent():\n    return 2\n")
            with self.assertRaisesRegex(iso.BindingError, r"changed=\['main.py'\]"):
                iso.verify_runtime(root, binding)

    def test_binding_separates_same_entry_different_dependency(self) -> None:
        main = "from helper import VALUE\ndef agent():\n    return VALUE\n"
        with runtime(main, **{"helper.py": "VALUE='a'\n"}) as left, runtime(
            main, **{"helper.py": "VALUE='b'\n"}
        ) as right:
            lbind = iso.build_binding(left)
            rbind = iso.build_binding(right)
            self.assertEqual(lbind["files"]["main.py"], rbind["files"]["main.py"])
            self.assertNotEqual(lbind["binding_sha256"], rbind["binding_sha256"])
            self.assertNotEqual(lbind["tree_sha256"], rbind["tree_sha256"])

    def test_duplicate_and_nonfinite_json_fail(self) -> None:
        with self.assertRaisesRegex(iso.ProtocolError, "duplicate JSON key"):
            iso.strict_loads('{"x":1,"x":2}')
        with self.assertRaisesRegex(iso.ProtocolError, "non-finite"):
            iso.strict_loads('{"x":NaN}')

    def test_cell_requires_exact_provenance_hashes(self) -> None:
        bad = cell()
        bad["engine_sha256"] = "ABC"
        with self.assertRaisesRegex(iso.ProtocolError, "lowercase 64-hex"):
            iso.validate_cell(bad)

    def test_boolean_seat_and_seed_fail(self) -> None:
        bad = cell()
        bad["candidate_seat"] = False
        with self.assertRaisesRegex(iso.ProtocolError, "exact integer"):
            iso.validate_cell(bad)
        bad = cell()
        bad["seed"] = True
        with self.assertRaisesRegex(iso.ProtocolError, "exact integer"):
            iso.validate_cell(bad)


class SessionContracts(unittest.TestCase):
    def test_state_persists_within_cell_and_resets_between_cells(self) -> None:
        main = """
            counter = 0
            def agent(_=None):
                global counter
                counter += 1
                return counter
        """
        with runtime(main) as root:
            binding = iso.build_binding(root)
            with iso.IsolatedAgentSession(root, binding, cell(), timeout=5) as first:
                self.assertEqual(first.call({}).value, 1)
                self.assertEqual(first.call({}).value, 2)
                receipt = first.finalize()
                self.assertEqual(receipt["call_count"], 2)
                self.assertEqual(receipt["python"]["isolated"], 1)
                self.assertEqual(receipt["python"]["dont_write_bytecode"], 1)
            with iso.IsolatedAgentSession(root, binding, cell(seed=8), timeout=5) as second:
                self.assertEqual(second.call({}).value, 1)

    def test_as_agent_adapter(self) -> None:
        with runtime("def agent(obs, cfg):\n    return [obs['x'], cfg['y']]\n") as root:
            binding = iso.build_binding(root)
            with iso.IsolatedAgentSession(root, binding, cell(), timeout=5) as session:
                agent = session.as_agent()
                self.assertEqual(agent({"x": 3}, {"y": 4}), [3, 4])

    def test_stdout_and_stderr_are_captured_without_protocol_corruption(self) -> None:
        main = """
            import sys
            print('import-out')
            print('import-err', file=sys.stderr)
            def agent(x):
                print('call-out', x)
                print('call-err', x, file=sys.stderr)
                return {'ok': x}
        """
        with runtime(main) as root:
            binding = iso.build_binding(root)
            with iso.IsolatedAgentSession(root, binding, cell(), timeout=5) as session:
                result = session.call(9)
                self.assertEqual(result.value, {"ok": 9})
                self.assertIn("call-out 9", result.receipt["stdout"]["text"])
                self.assertIn("call-err 9", result.receipt["stderr"]["text"])
                final = session.finalize()
                self.assertIn("import-out", final["import_log"]["stdout"]["text"])
                self.assertIn("import-err", final["import_log"]["stderr"]["text"])

    def test_environment_is_sanitized_and_cwd_is_private(self) -> None:
        old = os.environ.get("TITAN_SHOULD_NOT_LEAK")
        os.environ["TITAN_SHOULD_NOT_LEAK"] = "secret"
        try:
            main = """
                import os
                def agent():
                    return {
                        'leak': os.environ.get('TITAN_SHOULD_NOT_LEAK'),
                        'pythonpath': os.environ.get('PYTHONPATH'),
                        'cwd': os.getcwd(),
                        'home': os.environ.get('HOME'),
                    }
            """
            with runtime(main) as root:
                binding = iso.build_binding(root)
                with iso.IsolatedAgentSession(root, binding, cell(), timeout=5) as session:
                    value = session.call().value
                    self.assertIsNone(value["leak"])
                    self.assertIsNone(value["pythonpath"])
                    self.assertNotEqual(pathlib.Path(value["cwd"]), root)
                    self.assertNotEqual(pathlib.Path(value["home"]), pathlib.Path.home())
        finally:
            if old is None:
                os.environ.pop("TITAN_SHOULD_NOT_LEAK", None)
            else:
                os.environ["TITAN_SHOULD_NOT_LEAK"] = old

    def test_large_log_is_digest_bound_and_memory_capped(self) -> None:
        main = """
            def agent():
                print('z' * 10000)
                return 1
        """
        with runtime(main) as root:
            binding = iso.build_binding(root)
            with iso.IsolatedAgentSession(root, binding, cell(), timeout=5, max_log_bytes=128) as session:
                result = session.call()
                self.assertEqual(result.value, 1)
                self.assertTrue(result.receipt["stdout"]["truncated"])
                self.assertGreater(result.receipt["stdout"]["bytes"], 10000)
                self.assertLessEqual(len(result.receipt["stdout"]["text"].encode()), 128)

    def test_nonfinite_return_fails_closed(self) -> None:
        with runtime("def agent():\n    return float('nan')\n") as root:
            binding = iso.build_binding(root)
            session = iso.IsolatedAgentSession(root, binding, cell(), timeout=5)
            try:
                with self.assertRaisesRegex(iso.WorkerFailure, "non-finite"):
                    session.call()
            finally:
                session.abort()

    def test_timeout_kills_worker(self) -> None:
        with runtime("import time\ndef agent():\n    time.sleep(5)\n    return 1\n") as root:
            binding = iso.build_binding(root)
            session = iso.IsolatedAgentSession(root, binding, cell(), timeout=0.2)
            process = session._process
            assert process is not None
            with self.assertRaises(iso.WorkerTimeout):
                session.call()
            self.assertIsNotNone(process.poll())
            session.abort()

    def test_tree_mutation_during_call_fails_closed(self) -> None:
        main = """
            import os
            import pathlib
            import helper
            def agent():
                path = pathlib.Path(helper.__file__)
                os.chmod(path, 0o644)
                path.write_text('VALUE=99\\n', encoding='utf-8')
                return helper.VALUE
        """
        with runtime(main, **{"helper.py": "VALUE=1\n"}) as root:
            binding = iso.build_binding(root)
            session = iso.IsolatedAgentSession(root, binding, cell(), timeout=5)
            try:
                with self.assertRaisesRegex(iso.WorkerFailure, "runtime (tree|source) drift"):
                    session.call()
            finally:
                session.abort()
            self.assertEqual((root / "helper.py").read_text(encoding="utf-8"), "VALUE=1\n")

    def test_foreign_runtime_module_origin_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="iso-foreign-") as outside_raw:
            outside = pathlib.Path(outside_raw)
            write(outside / "helper.py", "VALUE='foreign'\n")
            main = f"""
                import sys
                sys.path.insert(0, {str(outside)!r})
                import helper
                def agent():
                    return helper.VALUE
            """
            with runtime(main, **{"helper.py": "VALUE='bound'\n"}) as root:
                binding = iso.build_binding(root)
                with self.assertRaisesRegex(iso.WorkerFailure, "escaped root"):
                    iso.IsolatedAgentSession(root, binding, cell(), timeout=5)

    def test_request_message_limit(self) -> None:
        with runtime("def agent(x):\n    return x\n") as root:
            binding = iso.build_binding(root)
            session = iso.IsolatedAgentSession(
                root, binding, cell(), timeout=5, max_message_bytes=2048
            )
            try:
                with self.assertRaisesRegex(iso.ProtocolError, "request exceeds"):
                    session.call("x" * 5000)
            finally:
                session.abort()

    def test_receipt_is_bound_to_cell_and_runtime(self) -> None:
        with runtime("def agent(x):\n    return x + 1\n") as root:
            binding = iso.build_binding(root)
            with iso.IsolatedAgentSession(root, binding, cell("candidate", 1, 99), timeout=5) as session:
                result = session.call(4)
                receipt = session.finalize()
            self.assertEqual(result.value, 5)
            self.assertEqual(receipt["cell"], cell("candidate", 1, 99))
            self.assertEqual(receipt["binding_sha256"], binding["binding_sha256"])
            unsigned = dict(receipt)
            seal = unsigned.pop("receipt_sha256")
            self.assertEqual(seal, iso.sha256_bytes(iso.canonical_bytes(unsigned)))


class PredecessorContracts(unittest.TestCase):
    def tearDown(self) -> None:
        purge_fixture_modules()

    def test_private_main_does_not_isolate_transitive_class_mutation(self) -> None:
        shared = "class FrozenSelected:\n    marker='control'\n"
        control_main = "from frozen_selected import FrozenSelected\ndef agent():\n    return FrozenSelected.marker\n"
        candidate_main = """
            from frozen_selected import FrozenSelected
            FrozenSelected.marker = 'candidate'
            def agent():
                return FrozenSelected.marker
        """
        with runtime(control_main, **{"frozen_selected.py": shared}) as control, runtime(
            candidate_main, **{"frozen_selected.py": shared}
        ) as candidate:
            purge_fixture_modules()
            control_module = unsafe_private_main_load(control, "_control_private")
            candidate_module = unsafe_private_main_load(candidate, "_candidate_private")
            self.assertEqual(candidate_module.agent(), "candidate")
            self.assertEqual(
                control_module.agent(),
                "candidate",
                "predecessor unexpectedly isolated shared transitive class",
            )

            purge_fixture_modules()
            cbind = iso.build_binding(control)
            xbind = iso.build_binding(candidate)
            with iso.IsolatedAgentSession(control, cbind, cell("control", 0, 1), timeout=5) as c1:
                self.assertEqual(c1.call().value, "control")
            with iso.IsolatedAgentSession(candidate, xbind, cell("candidate", 0, 1), timeout=5) as x:
                self.assertEqual(x.call().value, "candidate")
            with iso.IsolatedAgentSession(control, cbind, cell("control", 0, 2), timeout=5) as c2:
                self.assertEqual(c2.call().value, "control")

    def test_both_arm_load_orders_are_order_invariant(self) -> None:
        shared = "STATE=[]\n"
        main = """
            import scheduler
            def agent(label):
                scheduler.STATE.append(label)
                return list(scheduler.STATE)
        """
        with runtime(main, **{"scheduler.py": shared}) as left, runtime(
            main, **{"scheduler.py": shared}
        ) as right:
            lbind = iso.build_binding(left)
            rbind = iso.build_binding(right)
            for first_root, first_bind, second_root, second_bind in (
                (left, lbind, right, rbind),
                (right, rbind, left, lbind),
            ):
                with iso.IsolatedAgentSession(first_root, first_bind, cell("first", 0, 10), timeout=5) as first:
                    self.assertEqual(first.call("first").value, ["first"])
                with iso.IsolatedAgentSession(second_root, second_bind, cell("second", 1, 10), timeout=5) as second:
                    self.assertEqual(second.call("second").value, ["second"])


class CliContracts(unittest.TestCase):
    def test_bind_and_probe_cli(self) -> None:
        with runtime("def agent(x):\n    return {'twice': x * 2}\n") as root, tempfile.TemporaryDirectory(
            prefix="iso-cli-"
        ) as out_raw:
            out = pathlib.Path(out_raw)
            binding_path = out / "binding.json"
            cell_path = out / "cell.json"
            calls_path = out / "calls.json"
            report_path = out / "report.json"
            cell_path.write_text(json.dumps(cell()), encoding="utf-8")
            calls_path.write_text(
                json.dumps([{"args": [6], "kwargs": {}}]), encoding="utf-8"
            )
            subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(MODULE_PATH),
                    "bind",
                    str(root),
                    "--output",
                    str(binding_path),
                ],
                check=True,
                text=True,
                capture_output=True,
            )
            subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(MODULE_PATH),
                    "probe",
                    str(root),
                    "--binding",
                    str(binding_path),
                    "--cell",
                    str(cell_path),
                    "--calls",
                    str(calls_path),
                    "--output",
                    str(report_path),
                ],
                check=True,
                text=True,
                capture_output=True,
            )
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["results"][0]["value"], {"twice": 12})
            self.assertEqual(report["receipt"]["call_count"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
