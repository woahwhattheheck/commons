#!/usr/bin/env python3
"""Run synthetic record challenges against an explicitly selected local assessor.

This is a test harness, not another recovery assessor. The target module is
trusted test code and executes in a child Python process. No shell or network
operation is implemented. Candidate timeouts, crashes and missing output are
never counted as successful input rejection.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import hashlib
import importlib.util
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

SCHEMA = "tjlabs.recovery-challenges/v1"
REPORT_SCHEMA = "tjlabs.recovery-challenge-report/v1"
MAX_CASES = 200
MAX_INPUT_BYTES = 8_000_000
MAX_OUTPUT_BYTES = 8_000_000


class SuiteError(ValueError):
    pass


def need(condition: bool, message: str) -> None:
    if not condition:
        raise SuiteError(message)


def canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise SuiteError("not finite, acyclic, UTF-8 JSON: " + str(exc)) from exc


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def strict_loads(raw: str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict:
        result = {}
        for key, value in items:
            need(key not in result, "duplicate JSON member: " + key)
            result[key] = value
        return result

    def bad_constant(value: str) -> None:
        raise SuiteError("non-finite JSON constant: " + value)

    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=bad_constant)
    except (ValueError, RecursionError) as exc:
        raise SuiteError(str(exc)) from exc


def fields(item: Any, names: str, where: str) -> None:
    need(type(item) is dict, where + " must be an object")
    need(set(item) == set(names.split()), where + " has missing or extra fields")


def label(value: Any, where: str) -> None:
    need(type(value) is str and bool(value.strip()), where + " must be nonblank text")


def tokens(pointer: Any) -> list[str]:
    need(type(pointer) is str and (pointer == "" or pointer.startswith("/")), "invalid JSON pointer")
    if pointer == "":
        return []
    parts = pointer[1:].split("/")
    for part in parts:
        need(re.search(r"~(?![01])", part) is None, "invalid JSON pointer escape")
    return [p.replace("~1", "/").replace("~0", "~") for p in parts]


def member(value: Any, token: str) -> Any:
    if type(value) is dict:
        need(token in value, "missing object member: " + token)
        return token
    if type(value) is list:
        need(re.fullmatch(r"0|[1-9][0-9]*", token) is not None, "invalid array index: " + token)
        need(len(token) <= 9, "array index too large")
        index = int(token)
        need(index < len(value), "array index out of range")
        return index
    raise SuiteError("pointer traverses a scalar")


def resolve(value: Any, pointer: str) -> Any:
    for token in tokens(pointer):
        value = value[member(value, token)]
    return value


def materialize(suite: dict, case: dict) -> Any:
    value = copy.deepcopy(suite["baselines"][case["baseline"]])
    for edit in case["edits"]:
        parts = tokens(edit["path"])
        if edit["op"] == "append":
            target = resolve(value, edit["path"])
            need(type(target) is list, "append destination must be an array")
            target.append(copy.deepcopy(edit["value"]))
        elif not parts:
            need(edit["op"] == "replace", "cannot remove the root")
            value = copy.deepcopy(edit["value"])
        else:
            parent = value
            for token in parts[:-1]:
                parent = parent[member(parent, token)]
            key = member(parent, parts[-1])
            if edit["op"] == "remove":
                del parent[key]
            else:
                parent[key] = copy.deepcopy(edit["value"])
    return value


def validate_suite(suite: Any) -> dict:
    fields(suite, "schema title classification baselines cases", "suite")
    need(suite["schema"] == SCHEMA, "unsupported suite schema")
    need(suite["classification"] == "synthetic", "this corpus must be labeled synthetic")
    label(suite["title"], "suite title")
    need(type(suite["baselines"]) is dict and bool(suite["baselines"]), "baselines must be a nonempty object")
    need(type(suite["cases"]) is list and 0 < len(suite["cases"]) <= MAX_CASES, "case count must be 1..200")
    ids = set()
    positive = False
    for index, case in enumerate(suite["cases"]):
        fields(case, "id purpose baseline edits expected positive_control", f"case {index}")
        for name in ("id", "purpose", "baseline"):
            label(case[name], "case " + name)
        need(case["id"] not in ids, "duplicate case ID")
        ids.add(case["id"])
        need(case["baseline"] in suite["baselines"], "unknown baseline")
        need(type(case["positive_control"]) is bool, "positive_control must be boolean")
        fields(case["expected"], "kind checks", "expected")
        need(case["expected"]["kind"] in ("return", "reject"), "expected kind must be return or reject")
        need(type(case["expected"]["checks"]) is list, "checks must be an array")
        if case["expected"]["kind"] == "return":
            need(bool(case["expected"]["checks"]), "return case requires non-vacuous assertions")
        else:
            need(not case["expected"]["checks"], "rejection case cannot assert returned fields")
        if case["positive_control"]:
            need(case["expected"]["kind"] == "return", "positive control must return")
            positive = True
        for check in case["expected"]["checks"]:
            fields(check, "path op value", "assertion")
            tokens(check["path"])
            need(check["op"] in ("equals", "not_equals"), "unknown assertion operation")
        need(type(case["edits"]) is list, "edits must be an array")
        for edit in case["edits"]:
            need(type(edit) is dict, "edit must be an object")
            need(edit.get("op") in ("replace", "remove", "append"), "unsupported edit operation")
            fields(edit, "op path" if edit["op"] == "remove" else "op path value", "edit")
            tokens(edit["path"])
        materialize(suite, case)  # A bad test mutation is a suite error, not a candidate result.
    need(positive, "suite requires a successful positive control")
    need(len(canonical(suite)) <= MAX_INPUT_BYTES, "suite exceeds byte bound")
    return suite


def evaluate(case: dict, envelope: dict) -> dict:
    """Judge an observed worker result; a missing output path always fails."""
    result = {"id": case["id"], "purpose": case["purpose"], "positive_control": case["positive_control"],
              "status": "PASS", "observed_kind": envelope.get("kind", "missing"), "assertions": []}
    if envelope.get("kind") in ("crash", "timeout", "protocol_error"):
        return {**result, "status": "ERROR", "diagnostic": envelope.get("message", "candidate execution failed")}
    if envelope.get("kind") != case["expected"]["kind"]:
        return {**result, "status": "FAIL", "diagnostic": "expected " + case["expected"]["kind"] + "; observed " + str(envelope.get("kind"))}
    if case["expected"]["kind"] == "reject":
        return {**result, "rejection": envelope.get("exception", "ValueError")}
    for check in case["expected"]["checks"]:
        observation = {**check, "passed": False}
        try:
            actual = resolve(envelope["output"], check["path"])
            same = canonical(actual) == canonical(check["value"])
            observation.update(actual=actual, passed=same if check["op"] == "equals" else not same)
        except (SuiteError, KeyError) as exc:
            observation["diagnostic"] = "missing or invalid output: " + str(exc)
        result["assertions"].append(observation)
    if not all(c["passed"] for c in result["assertions"]):
        result["status"] = "FAIL"
    return result


def source_manifest(paths: list[Path]) -> list[dict]:
    resolved = sorted(set(p.resolve(strict=True) for p in paths))
    root = Path(os.path.commonpath([str(p.parent) for p in resolved]))
    manifest = []
    for path in resolved:
        need(path.is_file(), "source must be a regular file: " + str(path))
        raw = path.read_bytes()
        manifest.append({"path": path.relative_to(root).as_posix(), "bytes": len(raw),
                         "sha256": hashlib.sha256(raw).hexdigest()})
    return manifest


def worker(target: Path, entry: str) -> int:
    """Isolated process endpoint. Only ValueError is deliberate input rejection."""
    try:
        packet = strict_loads(sys.stdin.read(MAX_INPUT_BYTES + 1))
        name = "_recovery_candidate_" + hashlib.sha256(str(target.resolve()).encode()).hexdigest()[:16]
        spec = importlib.util.spec_from_file_location(name, target)
        need(spec is not None and spec.loader is not None, "cannot load candidate module")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        sys.path.insert(0, str(target.resolve().parent))
        with contextlib.redirect_stdout(sys.stderr):
            spec.loader.exec_module(module)
            function = getattr(module, entry)
            try:
                output = function(packet)
                canonical(output)
                envelope = {"kind": "return", "output": output}
            except ValueError as exc:
                envelope = {"kind": "reject", "exception": type(exc).__name__, "message": str(exc)}
    except BaseException as exc:
        envelope = {"kind": "crash", "exception": type(exc).__name__, "message": str(exc)}
    sys.stdout.buffer.write(canonical(envelope) + b"\n")
    return 0


def run(suite: dict, target: Path, entry: str = "assess", sources: list[Path] | None = None,
        timeout: float = 10) -> dict:
    validate_suite(suite)
    need(type(timeout) in (int, float) and math.isfinite(timeout) and 0 < timeout <= 60, "timeout must be 0..60 seconds, excluding zero")
    need(type(entry) is str and entry.isidentifier(), "entry must be a Python identifier")
    target = target.resolve(strict=True)
    paths = [target, Path(__file__).resolve(), *(sources or [])]
    before = source_manifest(paths)
    results = []
    for case in suite["cases"]:
        packet = materialize(suite, case)
        raw = canonical(packet)
        try:
            proc = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--worker", str(target), entry],
                                  input=raw, capture_output=True, timeout=timeout, check=False)
            if proc.returncode or len(proc.stdout) > MAX_OUTPUT_BYTES:
                envelope = {"kind": "protocol_error", "message": f"worker exit={proc.returncode}; output bytes={len(proc.stdout)}"}
            else:
                try:
                    envelope = strict_loads(proc.stdout.decode("utf-8"))
                    need(type(envelope) is dict, "worker envelope is not an object")
                except (SuiteError, UnicodeError) as exc:
                    envelope = {"kind": "protocol_error", "message": str(exc)}
            stderr = proc.stderr.decode("utf-8", errors="replace")[:4000]
        except subprocess.TimeoutExpired:
            envelope = {"kind": "timeout", "message": "candidate exceeded per-case timeout"}
            stderr = ""
        result = evaluate(case, envelope)
        result.update(input_sha256=hashlib.sha256(raw).hexdigest(), worker_stderr=stderr)
        results.append(result)
    try:
        after = source_manifest(paths)
        unchanged = before == after
    except (OSError, SuiteError):
        after, unchanged = [], False
    counts = {status: sum(c["status"] == status for c in results) for status in ("PASS", "FAIL", "ERROR")}
    overall = "ERROR" if counts["ERROR"] or not unchanged else ("FAIL" if counts["FAIL"] else "PASS")
    report = {"schema": REPORT_SCHEMA, "classification": "synthetic", "suite_title": suite["title"],
              "suite_sha256": digest(suite), "entry": entry, "python_version": sys.version.split()[0],
              "sources_before": before, "sources_after": after, "source_bytes_unchanged": unchanged,
              "status": overall, "counts": counts, "cases": results,
              "boundary": "Local synthetic conformance only. Declared source files, not undeclared transitive dependencies, are hashed. This does not execute recovery or attest University practice, source authenticity, production safety, or merge approval."}
    report["report_sha256"] = digest(report)
    return report


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) == 3 and args[0] == "--worker":
        return worker(Path(args[1]), args[2])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--entry", default="assess")
    parser.add_argument("--source", action="append", default=[], type=Path)
    parser.add_argument("--timeout", type=float, default=10)
    parsed = parser.parse_args(args)
    try:
        raw = parsed.suite.read_bytes()
        need(len(raw) <= MAX_INPUT_BYTES, "suite exceeds byte bound")
        suite = strict_loads(raw.decode("utf-8"))
        report = run(suite, parsed.target, parsed.entry, parsed.source, parsed.timeout)
        print(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False))
        return 0 if report["status"] == "PASS" else 1
    except (OSError, UnicodeError, SuiteError) as exc:
        print("SUITE_ERROR: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
