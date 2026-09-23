#!/usr/bin/env python3
"""Replay UIOWA-064 staging failures on explicitly selected calculator bytes.

All fault injection and filesystem writes use disposable synthetic files. This
is a regression replay, not a new calculator, metrics interpretation or runtime
publication component. It does not fetch code or contact a provider.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
import unittest
from unittest import mock

TARGETS = ("new", "existing", "other_hardlink")
PAYLOADS = {
    "ascii": json.dumps({"synthetic": True, "result": "sample"}) + "\n",
    "unicode": json.dumps({"synthetic": True, "result": "café 東京\r\n\u0000"}, ensure_ascii=False) + "\n",
    "buffered": json.dumps({"synthetic": True, "result": "x" * 65536}) + "\n",
}
FAULTS = (
    "success", "create", "partial_write", "flush", "fsync", "close",
    "source_missing", "source_replaced", "replace",
)
OLD_SOURCE = b"SYNTHETIC source evidence: do not replace\r\n\x00\x1a"
NEW_SOURCE = b"SYNTHETIC replacement injected by the test\n"
OLD_REPORT = b"SYNTHETIC previous complete report\r\n\x00\x1a"


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def load_calculator(path: Path, expected_blob: str):
    """Bind execution to explicit local source bytes before importing them."""
    data = path.read_bytes()
    observed = git_blob(data)
    if observed != expected_blob:
        raise ValueError(f"calculator blob mismatch: expected {expected_blob}, observed {observed}")
    name = "uiowa64_staging_replay_target"
    # Compile the same captured bytes that were hashed; do not re-open the path.
    spec = importlib.util.spec_from_loader(name, loader=None, origin=str(path))
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(path)
    sys.modules[name] = module
    exec(compile(data, str(path), "exec"), module.__dict__)
    if not callable(getattr(module, "_write_report", None)):
        raise ValueError("selected calculator has no callable _write_report")
    return module


class FailingStream:
    """Inject write/flush/close errors at the real temporary stream boundary."""
    def __init__(self, wrapped, fault: str, injected: list[str]):
        self.wrapped = wrapped
        self.fault = fault
        self.injected = injected

    def __getattr__(self, name):
        return getattr(self.wrapped, name)

    def __enter__(self):
        self.wrapped.__enter__()
        return self

    def write(self, value):
        if self.fault == "partial_write":
            self.wrapped.write(value[:max(1, len(value) // 2)])
            self.wrapped.flush()
            self.injected.append(self.fault)
            raise OSError("synthetic partial-write failure")
        return self.wrapped.write(value)

    def flush(self):
        self.wrapped.flush()
        if self.fault == "flush":
            self.injected.append(self.fault)
            raise OSError("synthetic stream-flush failure")

    def __exit__(self, exc_type, exc_value, traceback):
        result = self.wrapped.__exit__(exc_type, exc_value, traceback)
        if self.fault == "close" and exc_type is None:
            self.injected.append(self.fault)
            raise OSError("synthetic stream-close failure")
        return result


def exercise(case: unittest.TestCase, calculator, target: str, payload_name: str, fault: str):
    """Exercise one declared case; there are no external or shared file writes."""
    with tempfile.TemporaryDirectory(prefix="uiowa64-r9-staging-") as temporary:
        root = Path(temporary)
        source, retained = root / "source.csv", root / "retained-source.csv"
        output, archive = root / "report.json", root / "archived-report.json"
        source.write_bytes(OLD_SOURCE)
        if target == "existing":
            output.write_bytes(OLD_REPORT)
        elif target == "other_hardlink":
            archive.write_bytes(OLD_REPORT)
            os.link(archive, output)
        payload = PAYLOADS[payload_name]
        real_factory = calculator.tempfile.NamedTemporaryFile
        real_fsync = calculator.os.fsync
        visited = []
        injected = []

        def factory(*args, **kwargs):
            visited.append("create")
            if fault == "create":
                injected.append(fault)
                raise OSError("synthetic temporary-create failure")
            return FailingStream(real_factory(*args, **kwargs), fault, injected)

        def sync(fd):
            visited.append("fsync")
            if fault == "fsync":
                injected.append(fault)
                raise OSError("synthetic file-sync failure")
            real_fsync(fd)
            if fault in {"source_missing", "source_replaced"}:
                # Single-process fault simulation, not concurrent path probing.
                injected.append(fault)
                source.rename(retained)
                if fault == "source_replaced":
                    source.write_bytes(NEW_SOURCE)

        def fail_replace(*args, **kwargs):
            injected.append(fault)
            raise OSError("synthetic replace failure")

        with ExitStack() as patches:
            patches.enter_context(mock.patch.object(calculator.tempfile, "NamedTemporaryFile", side_effect=factory))
            patches.enter_context(mock.patch.object(calculator.os, "fsync", side_effect=sync))
            if fault == "replace":
                patches.enter_context(mock.patch.object(calculator.os, "replace", side_effect=fail_replace))
            if fault == "success":
                calculator._write_report(payload, output, source)
            else:
                with case.assertRaises((OSError, calculator.DataError)):
                    calculator._write_report(payload, output, source)

        case.assertEqual(injected, [] if fault == "success" else [fault], "intended fault was not exercised")
        if fault in {"source_missing", "source_replaced"}:
            case.assertIn("fsync", visited)
            case.assertEqual(retained.read_bytes(), OLD_SOURCE)
            if fault == "source_missing":
                case.assertFalse(source.exists())
            else:
                case.assertEqual(source.read_bytes(), NEW_SOURCE)
        else:
            case.assertEqual(source.read_bytes(), OLD_SOURCE)
            case.assertFalse(retained.exists())

        if fault == "success":
            case.assertEqual(output.read_bytes(), payload.encode("utf-8"))
        elif target == "new":
            case.assertFalse(output.exists(), "failed publication created a visible report")
        else:
            case.assertEqual(output.read_bytes(), OLD_REPORT, "failed publication changed a prior report")

        if target == "other_hardlink":
            case.assertEqual(archive.read_bytes(), OLD_REPORT)
            case.assertEqual(os.path.samefile(archive, output), fault != "success")
        case.assertEqual(sorted(root.glob(".uiowa64-report-*.tmp")), [], "staging file leaked")
        case.assertIn("create", visited)


def suite_for(calculator):
    methods = {}
    for target in TARGETS:
        for payload in PAYLOADS:
            for fault in FAULTS:
                def method(self, target=target, payload=payload, fault=fault):
                    exercise(self, calculator, target, payload, fault)
                name = f"test_{target}_{payload}_{fault}"
                method.__name__ = name
                methods[name] = method
    matrix = type("StagingMatrix", (unittest.TestCase,), methods)
    return unittest.defaultTestLoader.loadTestsFromTestCase(matrix)


def replay(calculator):
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite_for(calculator))
    return {
        "tests": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skips": len(result.skipped),
        "success": result.wasSuccessful(),
        "failed_cases": [test.id() for test, _ in result.failures + result.errors],
        "log": stream.getvalue(),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calculator", type=Path, required=True)
    parser.add_argument("--expected-blob", required=True)
    parser.add_argument("--report", type=Path, help="optional NEW JSON report path; existing paths are refused")
    args = parser.parse_args(argv)
    try:
        module = load_calculator(args.calculator, args.expected_blob)
        result = replay(module)
        report = {
            "schema": "uiowa64.staging-replay.v1",
            "synthetic": True,
            "calculator_blob": args.expected_blob,
            "replay_blob": git_blob(Path(__file__).read_bytes()),
            "environment": {"python": platform.python_version(), "platform": platform.platform(), "optimize": sys.flags.optimize},
            "dimensions": {"targets": list(TARGETS), "payloads": list(PAYLOADS), "faults": list(FAULTS)},
            "execution": result,
        }
        rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.report:
            with args.report.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(rendered)
        else:
            sys.stdout.write(rendered)
        return 0 if result["success"] else 1
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
