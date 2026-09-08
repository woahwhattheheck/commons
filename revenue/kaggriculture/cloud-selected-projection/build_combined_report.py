#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Summarize all selected-projection suites from saved, source-bound output.

This reads existing files, never imports policy code or reruns a test/game.
Missing or inconsistent evidence produces an explicit unsuccessful report.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = "revenue/kaggriculture/"
LAB = ROOT + "cloud-execution-lab/"
MARKET = ROOT + "cloud-selected-market-checks/"
PROJECTION = ROOT + "cloud-selected-projection/"
# key, log, test source, optional JSON report, JSON count field
SUITES = (
    ("original", "original-seller-tests.log", LAB + "test_selected_action_sell.py", None, None),
    ("projection", "projection-tests.log", PROJECTION + "test_projection.py", "projection-results.json", "tests_run"),
    ("market", "market-tests.log", MARKET + "check_market_contracts.py", "market-results.json", "test_methods"),
    ("loader", "loader-tests.log", MARKET + "test_engine_binding.py", "loader-results.json", "test_methods"),
    ("empty_lot", "empty-lot-tests.log", MARKET + "test_empty_lot.py", None, None),
    ("joined_wrapper", "joined-wrapper-tests.log", LAB + "test_ordered_selected_sell.py", None, None),
)
FUNDED_JOIN = ("funded_join", "funded-join-tests.log", ROOT + "cloud-composition-cases/cypress/test_funded_join.py", "funded-join-results.json", "test_methods")
CANCELLATION = ("deadline_cancellation", "deadline-cancellation-tests.log", ROOT + "cloud-economic-stress/cancellation/test_deadline_cancellation.py", "deadline-cancellation.json", "tests_run")
RUNTIME_REGRESSIONS = (
    ("capture_binding", "capture-binding-tests.log", ROOT + "cloud-market-game-theory/adaptive/test_capture_binding.py", "capture-binding-results.json", "run"),
    ("score_schedule", "score-schedule-tests.log", LAB + "test_score_schedule.py", None, None),
    ("workflow_bindings", "workflow-bindings-tests.log", ROOT + "cloud-composition-cases/cover/test_regression_bindings.py", None, None),
)
REPORTER = ("reporter", "reporter-tests.log", PROJECTION + "test_combined_report.py", None, None)
SUMMARY = re.compile(r"^Ran ([0-9]+) tests? in .+\n\s*\n(OK(?: \([^\n]*\))?|FAILED(?: \([^\n]*\))?)\s*$", re.M)
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def parse_unittest(text: str) -> dict:
    """Accept one complete unittest summary, including trailing JSON output."""
    summaries = list(SUMMARY.finditer(text))
    runs = re.findall(r"^Ran [0-9]+ tests? in ", text, re.M)
    if len(summaries) != 1 or len(runs) != 1:
        raise ValueError("expected exactly one completed unittest summary")
    match = summaries[0]
    trailer = text[match.end():].strip()
    if trailer:
        try:
            trailing_report = json.loads(trailer)
        except ValueError as exc:
            raise ValueError("unexpected output after unittest completion") from exc
        if not isinstance(trailing_report, dict):
            raise ValueError("expected optional trailing JSON object")
    count = int(match.group(1))
    status = match.group(2)
    flags = dict((k, int(v)) for k, v in re.findall(r"([a-zA-Z ]+)=([0-9]+)", status))
    # Expected failures and skips are not counted as passing methods.
    successful = status == "OK" and count > 0
    return {"tests": count, "successful": successful, "summary": status,
            "failures": flags.get("failures", 0), "errors": flags.get("errors", 0),
            "skipped": flags.get("skipped", 0)}


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def build_report(directory: Path, *, include_reporter: bool = False, include_funded_join: bool = False, include_runtime_regressions: bool = False, include_cancellation: bool = False) -> dict:
    """Bind all named suite results to their one declared source snapshot."""
    directory = Path(directory)
    problems, digests = [], {}

    def read(name, *, as_json=False):
        try:
            data = (directory / name).read_bytes()
            digests[name] = hashlib.sha256(data).hexdigest()
            text = data.decode("utf-8")
            if not as_json:
                return text
            value = json.loads(text, object_pairs_hook=_pairs)
            if not isinstance(value, dict):
                raise ValueError("expected a JSON object")
            return value
        except (OSError, UnicodeError, ValueError) as exc:
            problems.append(f"{name}: {type(exc).__name__}: {exc}")
            return None

    snapshot = read("SOURCE-SNAPSHOT.json", as_json=True) or {}
    files = snapshot.get("files")
    if not isinstance(files, dict):
        problems.append("source snapshot: missing files mapping")
        files = {}
    for field, pattern in (("checkout", r"[0-9a-f]{40}"), ("run_id", r"[1-9][0-9]*"), ("attempt", r"[1-9][0-9]*")):
        if not re.fullmatch(pattern, str(snapshot.get(field, ""))):
            problems.append("source snapshot: invalid " + field)

    def source(path):
        row = files.get(path)
        value = row.get("sha256") if isinstance(row, dict) else None
        if not isinstance(value, str) or SHA256.fullmatch(value) is None:
            problems.append("source snapshot: missing/invalid SHA256 for " + path)
            return None
        return value

    def bind(label, observed, expected):
        if expected is None or not isinstance(observed, str) or observed != expected:
            problems.append("source mismatch: " + label)

    suites, reports = {}, {}
    declarations = (SUITES + ((FUNDED_JOIN,) if include_funded_join else ())
                    + (RUNTIME_REGRESSIONS if include_runtime_regressions else ())
                    + ((CANCELLATION,) if include_cancellation else ())
                    + ((REPORTER,) if include_reporter else ()))
    for key, log, test_path, report_file, count_key in declarations:
        entry = {"tests": None, "successful": False, "test_source_sha256": source(test_path), "log": log}
        text = read(log)
        if text is not None:
            try:
                entry.update(parse_unittest(text))
            except ValueError as exc:
                problems.append(f"{log}: {exc}")
        if not entry["successful"]:
            problems.append(key + ": no complete unskipped passing suite")
        if report_file:
            report = read(report_file, as_json=True)
            reports[key] = report or {}
            if report is not None:
                summary = report.get("tests", {}) if key == "capture_binding" else report
                if not isinstance(summary, dict):
                    summary = {}
                value = summary.get(count_key)
                if type(value) is not int or value != entry["tests"]:
                    problems.append(key + ": JSON/log test counts differ")
                if key == "deadline_cancellation":
                    for field in ("failures", "errors", "skipped"):
                        if not isinstance(summary.get(field), list) or summary[field]:
                            problems.append(key + ": nonempty or missing JSON " + field + " array")
                else:
                    if any(type(summary.get(k)) is not int or summary[k] != 0 for k in ("failures", "errors")):
                        problems.append(key + ": nonzero or missing JSON failures/errors")
                    if key != "projection" and summary.get("success" if key == "capture_binding" else "successful") is not True:
                        problems.append(key + ": JSON result is not successful")
        suites[key] = entry

    seller = source(LAB + "selected_action_sell.py")
    projected, market, loader = (reports.get(k, {}) for k in ("projection", "market", "loader"))
    bind("projection seller", projected.get("seller_sha256"), seller)
    bind("projection implementation", projected.get("projection_sha256"), source(PROJECTION + "projection.py"))
    market_sources = market.get("sources") or {}
    if not isinstance(market_sources, dict):
        market_sources = {}
    for name in ("selected_action_sell.py", "selected_sell_core.py", "mechanics.py", "reference/decision/decision.py"):
        bind("market " + name, market_sources.get(name), source(LAB + name))
    engine = {name: source(LAB + "reference/engine/" + name)
              for name in ("kaggriculture.py", "kaggriculture.json", "utils.py")}
    same_engine = all(engine.values()) and projected.get("engine_sha256") == engine and market.get("engine_sha256") == engine
    if not same_engine:
        problems.append("engine hashes do not match both JSON reports and source snapshot")
    loader_sources = loader.get("source_sha256") or {}
    if not isinstance(loader_sources, dict):
        loader_sources = {}
    for name, path in (("checker", MARKET + "check_market_contracts.py"),
                       ("evaluator", LAB + "reference/evaluator/evaluate.py"),
                       ("loader", LAB + "reference/evaluator/loader.py")):
        bind("loader " + name, loader_sources.get(name), source(path))
    joined = source(LAB + "ordered_selected_sell.py")
    funded = reports.get("funded_join", {})
    if include_funded_join:
        funded_sources = funded.get("sources")
        if not isinstance(funded_sources, dict) or not funded_sources:
            problems.append("funded join: missing source bindings")
            funded_sources = {}
        for name, row in funded_sources.items():
            digest = row.get("sha256") if isinstance(row, dict) else None
            bind("funded join " + name, digest, source(ROOT + name))
        required = (FUNDED_JOIN[2], LAB + "integrated_selected.py",
                    LAB + "selected_action_sell.py", LAB + "reference/engine/kaggriculture.py")
        for path in required:
            if path[len(ROOT):] not in funded_sources:
                problems.append("funded join: missing binding for " + path)
        for field, origin in (("workflow_run", "run_id"), ("workflow_attempt", "attempt")):
            if str(funded.get(field)) != str(snapshot.get(origin)):
                problems.append("funded join: mismatched " + field)

    if include_runtime_regressions:
        capture = reports.get("capture_binding", {})
        bind("capture runtime", capture.get("runtime_sha256"),
             source(ROOT + "cloud-market-game-theory/adaptive/runtime.py"))
        bind("capture optimizer", capture.get("optimizer_sha256"),
             source(LAB + "selected_sell_core.py"))
        source(".github/workflows/titan-selected-projection.yml")

    cancelled = reports.get("deadline_cancellation", {})
    if include_cancellation:
        bind("cancellation adapter", cancelled.get("adapter_sha256"),
             source(ROOT + "cloud-economic-stress/deadline_adapter.py"))
        partition = [cancelled.get(field) for field in
                     ("new_regression_methods", "unchanged_upstream_guard_methods")]
        if (any(type(n) is not int or n < 0 for n in partition)
                or sum(partition) != cancelled.get("tests_run")):
            problems.append("cancellation: method partition does not match tests_run")

    observed_total = sum(s["tests"] for s in suites.values() if s["tests"] is not None)
    counts_complete = all(s["tests"] is not None for s in suites.values())
    result = {"schema": "titan.selected-projection.combined.v2",
              "checkout": snapshot.get("checkout"), "run_id": snapshot.get("run_id"),
              "attempt": snapshot.get("attempt"), "python": snapshot.get("python"),
              "seller_sha256": seller, "joined_wrapper_sha256": joined,
              "engine_sha256": engine, "same_engine": bool(same_engine),
              "suites": suites, "suite_count": len(suites),
              "observed_tests": observed_total,
              "total_tests": observed_total if counts_complete else None,
              "complete": counts_complete and not problems,
              "successful": not problems,
              "projection_cases": projected.get("differential_cases"),
              "projection_transitions": projected.get("interpreter_transitions"),
              "market_cases": market.get("official_market_cases"),
              "loader_market_cases": loader.get("official_market_cases"),
              "input_sha256": digests, "problems": problems, "full_games": 0,
              "scope": "saved focused-suite outputs; source alignment is not independent execution attestation"}
    for key, entry in suites.items():
        result[key + "_tests"] = entry["tests"]
    first_three = [result[k + "_tests"] for k in ("original", "projection", "market")]
    result["legacy_three_suite_tests"] = sum(first_three) if all(v is not None for v in first_three) else None
    if include_funded_join:
        result["funded_join_transitions"] = funded.get("official_transitions")
        result["funded_join_full_games"] = funded.get("full_games")
    if include_cancellation:
        result["cancellation_new_regression_methods"] = cancelled.get("new_regression_methods")
        result["cancellation_retained_guard_methods"] = cancelled.get("unchanged_upstream_guard_methods")
        result["cancellation_adapter_sha256"] = cancelled.get("adapter_sha256")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--include-reporter-tests", action="store_true")
    parser.add_argument("--include-funded-join", action="store_true")
    parser.add_argument("--include-runtime-regressions", action="store_true")
    parser.add_argument("--include-cancellation", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(args.directory, include_reporter=args.include_reporter_tests,
                          include_funded_join=args.include_funded_join,
                          include_runtime_regressions=args.include_runtime_regressions,
                          include_cancellation=args.include_cancellation)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0 if report["successful"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
