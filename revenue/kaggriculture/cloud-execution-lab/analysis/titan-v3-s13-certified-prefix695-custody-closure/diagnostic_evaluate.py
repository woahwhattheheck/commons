#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Evidence-only evaluator adapter that retains post-game agent diagnostics.

The gameplay loop, engine, timeouts, scoring, and report construction come from
the exact repository evaluator. This adapter changes only the worker protocol:
after a game, the parent asks the already-loaded agent module for diagnostics()
before the worker is closed, and stores that JSON-safe value in the actor report.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import random
import sys
import time

BASE_EVALUATOR_BLOB = "077feb2208b6e0c1727835eb4f8089709bf67f3b"
BASE_EVALUATOR = Path(__file__).resolve().parents[3] / "cloud-eval" / "evaluate.py"


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load_base():
    data = BASE_EVALUATOR.read_bytes()
    actual = git_blob_sha(data)
    if actual != BASE_EVALUATOR_BLOB:
        raise RuntimeError(
            f"base evaluator blob drift: expected={BASE_EVALUATOR_BLOB} actual={actual}"
        )
    name = "titan_s13_certified_base_evaluator"
    spec = importlib.util.spec_from_file_location(name, BASE_EVALUATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load base evaluator: {BASE_EVALUATOR}")
    module = importlib.util.module_from_spec(spec)
    prior = sys.modules.get(name)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        if prior is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = prior
        raise
    return module


base = load_base()


def load_agent(agent_spec, cache, loader):
    if agent_spec == "official_starter":
        engine, _ = base.get_engine(cache, loader)
        return engine.starter_agent, None
    path, sep, name = agent_spec.partition("::")
    sys.path.insert(0, str(Path(path).resolve().parent))
    module = base.import_file(path, "kag_eval_candidate")
    function = getattr(module, name if sep else "agent")
    if not callable(function):
        raise TypeError("Agent entry point is not callable")
    diagnostics = getattr(module, "diagnostics", None)
    if diagnostics is not None and not callable(diagnostics):
        raise TypeError("Agent diagnostics entry point is not callable")
    return function, diagnostics


def diagnostic_worker(agent_spec, cache, loader, rng_seed):
    """Exact action worker plus one explicit post-game diagnostics request."""
    output = sys.stdout

    def send(message):
        payload = base.encoded(message)
        if len(payload) + 1 > base.MAX_PACKET:
            raise ValueError("Worker response exceeds packet limit")
        output.buffer.write(payload + b"\n")
        output.buffer.flush()

    random.seed(rng_seed)
    with open(os.devnull, "w") as quiet, contextlib.redirect_stdout(quiet), contextlib.redirect_stderr(quiet):
        try:
            function, diagnostics = load_agent(agent_spec, cache, loader)
            try:
                inspect.signature(function).bind({}, {})
                takes_config = True
            except TypeError:
                inspect.signature(function).bind({})
                takes_config = False
            send({"kind": "ready", **base.usage()})
        except BaseException as exc:
            send({"kind": "load_error", "error": f"{type(exc).__name__}: {exc}"[:1000], **base.usage()})
            return

        for line in sys.stdin.buffer:
            try:
                request = json.loads(line)
                if request == {"__diagnostics__": True}:
                    value = diagnostics() if diagnostics is not None else None
                    send({"kind": "diagnostics", "diagnostics": value, **base.usage()})
                    continue
                obs = base.structify(request["observation"])
                cfg = base.structify(request["configuration"])
                start, cpu = time.perf_counter(), time.process_time()
                action = function(obs, cfg) if takes_config else function(obs)
                seconds = time.perf_counter() - start
                cpu_seconds = time.process_time() - cpu
            except BaseException as exc:
                send({"kind": "crash", "error": f"{type(exc).__name__}: {exc}"[:1000], **base.usage()})
                return
            try:
                if not isinstance(action, dict):
                    raise TypeError("The official action schema requires an object")
                send(
                    {
                        "kind": "action",
                        "action": action,
                        "call_seconds": seconds,
                        "call_cpu_seconds": cpu_seconds,
                        **base.usage(),
                    }
                )
            except (TypeError, ValueError, OverflowError) as exc:
                send({"kind": "invalid_action", "error": f"{type(exc).__name__}: {exc}"[:1000], **base.usage()})
                return


class DiagnosticActor(base.Actor):
    """Base actor with the same process isolation and one post-game RPC."""

    def __init__(self, spec, cache, loader, rng_seed, startup_timeout=10.0):
        self.spec, self.buffer = spec, bytearray()
        self.stats = {
            "calls": 0,
            "call_seconds": [],
            "rpc_seconds": [],
            "call_cpu_seconds": 0.0,
            "cpu_seconds": 0.0,
            "peak_rss_kib": 0,
            "exit_code": None,
            "resource_sample": "child_rusage",
            "final_resource_sample": "unavailable",
            "procfs_sample_status": "not_attempted",
        }
        self.directory = base.tempfile.TemporaryDirectory(prefix="kag-eval-agent-")
        env = {
            "PATH": os.defpath,
            "HOME": self.directory.name,
            "LANG": "C.UTF-8",
            "PYTHONHASHSEED": str(rng_seed % (2**32)),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        self.proc = base.subprocess.Popen(
            [
                sys.executable,
                "-B",
                "-u",
                str(Path(__file__).resolve()),
                "--worker",
                spec,
                str(Path(cache).resolve()),
                str(Path(loader).resolve()),
                str(rng_seed),
            ],
            stdin=base.subprocess.PIPE,
            stdout=base.subprocess.PIPE,
            stderr=base.subprocess.DEVNULL,
            cwd=self.directory.name,
            env=env,
            start_new_session=True,
        )
        os.set_blocking(self.proc.stdin.fileno(), False)
        os.set_blocking(self.proc.stdout.fileno(), False)
        started = time.perf_counter()
        self.ready = self.exchange(None, startup_timeout)
        self.stats["startup_seconds"] = time.perf_counter() - started
        self._measure(self.ready)
        if self.ready.get("kind") != "ready":
            self.ready = self._retain_rpc_failure(self.ready)
        else:
            self._last_exchange = None

    def close(self):
        if getattr(self, "closed", False):
            return
        try:
            response = self.exchange({"__diagnostics__": True}, 1.0)
            self._measure(response)
            if response.get("kind") == "diagnostics":
                self.stats["agent_diagnostics"] = response.get("diagnostics")
            else:
                self.stats["agent_diagnostics_error"] = {
                    "kind": response.get("kind"),
                    "error": response.get("error"),
                }
        except BaseException as exc:
            self.stats["agent_diagnostics_error"] = {
                "kind": "adapter_exception",
                "error": f"{type(exc).__name__}: {exc}"[:1000],
            }
        super().close()


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--worker":
        diagnostic_worker(sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]))
        return 0
    base.Actor = DiagnosticActor
    # Bind the report fingerprint to this adapter, while all engine/loader constants
    # remain the exact already-imported base evaluator values.
    base.__file__ = str(Path(__file__).resolve())
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
