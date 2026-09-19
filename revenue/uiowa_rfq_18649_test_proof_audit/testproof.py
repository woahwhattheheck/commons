#!/usr/bin/env python3
"""Distinguish a test suite that PASSED from one that PROVED something.

Every correctness claim in this engagement rests on a `Ran N tests / OK`
line. That line is weaker evidence than it looks: a file with no test methods
reports `Ran 0 tests ... OK`, a test method with no assertion passes
unconditionally, and `assertTrue(True)` passes no matter what the code under
it does. A guard tested only on input it accepts is decoration.

This tool reads the source and reports where that has happened. It **parses,
it does not execute** -- pure `ast`, read-only. It never imports, runs, or
writes to the code it audits. Every finding is a path and a line number
somebody can check in a few seconds.

Run:
    python3 testproof.py --root ../..                 # audit every lane
    python3 testproof.py --root ../.. --lane uiowa_rfq_18649_ai_use_inventory
    python3 testproof.py --root fixtures --include-fixtures --print

Severity is split on purpose:

  DEFECT  -- mechanically certain from the syntax. A test with no assertion
             cannot fail on behaviour. There is no judgement in it.
  REVIEW  -- a signal to go look, not a verdict. These use heuristics that
             can be wrong, and a tool that states a heuristic as a fact is
             the same failure it is trying to catch.

It produces counts, not a score, and no per-author ranking of any kind. It
rates test files.
"""

import argparse
import ast
import csv
import json
import os
import sys

LANE_PREFIX = "uiowa_rfq_18649_"
DEFAULT_TEST_GLOB = "test_"

FINDING_KINDS = {
    "NO_TESTS_COLLECTED": (
        "DEFECT",
        "a test file with no test methods; a discovery runner reports 'Ran 0 tests ... OK'",
    ),
    "TEST_WITHOUT_ASSERTION": (
        "DEFECT",
        "a test method with no assertion and no call; nothing it does can fail",
    ),
    "SMOKE_TEST_NO_ASSERTION": (
        "REVIEW",
        "a test method with no assertion that does call the code; it proves only that nothing raised",
    ),
    "TAUTOLOGICAL_ASSERTION": (
        "DEFECT",
        "an assertion over literals only; it passes whatever the code under it does",
    ),
    "NO_REFERENCE_TO_LANE": (
        "REVIEW",
        "a test file that never imports or names any module in its own lane",
    ),
    "GUARD_WITHOUT_NEGATIVE_CASE": (
        "REVIEW",
        "the lane defines a guard, and no test asserts it can refuse anything",
    ),
    "UNPARSEABLE": (
        "REVIEW",
        "the file could not be parsed, so nothing about it can be established",
    ),
}

# Names that mark a call as carrying an assertion.
_FAIL_CALLS = ("fail", "raises")

# Words that, appearing inside an assertion, suggest a failure path is being
# exercised. Heuristic -- which is why it only ever produces REVIEW.
_NEGATIVE_WORDS = (
    "error", "issue", "fail", "invalid", "reject", "refus", "unsafe",
    "violation", "defect", "conflict", "missing", "unknown", "raises",
    "dangling", "duplicate", "malformed", "broken", "stale", "unsupported",
)


class Finding(object):
    __slots__ = ("lane", "path", "line", "kind", "detail", "name")

    def __init__(self, lane, path, line, kind, detail, name=""):
        assert kind in FINDING_KINDS, kind
        self.lane = lane
        self.path = path
        self.line = line
        self.kind = kind
        self.detail = detail
        self.name = name

    @property
    def severity(self):
        return FINDING_KINDS[self.kind][0]

    def as_dict(self):
        return {
            "lane": self.lane,
            "path": self.path,
            "line": self.line,
            "kind": self.kind,
            "severity": self.severity,
            "name": self.name,
            "detail": self.detail,
        }

    def __repr__(self):  # pragma: no cover - debugging aid
        return "Finding(%s:%s %s)" % (self.path, self.line, self.kind)


def _call_name(node):
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _is_assertion_call(name):
    return bool(name) and (name.startswith("assert") or name in _FAIL_CALLS)


def _is_literal(node):
    """A constant, or a container built only from constants."""
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return all(_is_literal(e) for e in node.elts)
    if isinstance(node, ast.Dict):
        return all(_is_literal(k) for k in node.keys if k is not None) and \
               all(_is_literal(v) for v in node.values)
    return False


def _tautology_reason(name, node):
    """Why this assertion proves nothing. None when it is fine."""
    args = [a for a in node.args]
    if name in ("assertTrue", "assertFalse", "assertIsNone", "assertIsNotNone"):
        if args and _is_literal(args[0]):
            return "%s over a literal" % name
    if name in ("assertEqual", "assertNotEqual", "assertIs", "assertIsNot"):
        if len(args) >= 2 and _is_literal(args[0]) and _is_literal(args[1]):
            return "%s comparing two literals" % name
    if name in ("assertIn", "assertNotIn"):
        if len(args) >= 2 and _is_literal(args[0]) and _is_literal(args[1]):
            return "%s over literals only" % name
    return None


class FileReport(object):
    """What one parsed file contains."""

    def __init__(self, path, source, tree):
        self.path = path
        self.source = source
        self.tree = tree
        self.test_functions = []     # (name, node, lineno)
        self.asserting_names = set()  # functions in this file that do assert
        self.imported_modules = set()
        self.string_constants = []
        self.assertion_count = 0
        self.negative_evidence = False
        self._scan()

    def _scan(self):
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.imported_modules.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self.imported_modules.add(node.module.split(".")[0])
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                self.string_constants.append(node.value)

        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                direct = self._direct_assertions(node)
                if direct:
                    self.asserting_names.add(node.name)
                if node.name.startswith("test"):
                    self.test_functions.append((node.name, node, node.lineno))

    def _direct_assertions(self, node):
        """Assertion evidence inside this function, not counting calls out."""
        found = []
        for n in ast.walk(node):
            if isinstance(n, ast.Assert):
                found.append(("assert", n))
            elif isinstance(n, ast.Call):
                name = _call_name(n)
                if _is_assertion_call(name):
                    found.append((name, n))
        return found

    def has_assertion(self, node):
        """Assertion evidence, allowing one level of helper indirection.

        A suite that factors its checks into a helper is not a hollow suite,
        and flagging it would be exactly the over-fire that gets a linter
        switched off.
        """
        if self._direct_assertions(node):
            return True
        for n in ast.walk(node):
            if isinstance(n, ast.Call):
                name = _call_name(n)
                if name and name in self.asserting_names:
                    return True
        return False

    def tautologies(self, node):
        out = []
        for n in ast.walk(node):
            if isinstance(n, ast.Assert) and _is_literal(n.test):
                out.append((n.lineno, "assert over a literal"))
            elif isinstance(n, ast.Call):
                name = _call_name(n)
                if _is_assertion_call(name):
                    reason = _tautology_reason(name, n)
                    if reason:
                        out.append((n.lineno, reason))
        return out

    def count_assertions_and_negatives(self):
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Assert):
                self.assertion_count += 1
            elif isinstance(node, ast.Call):
                name = _call_name(node)
                if _is_assertion_call(name):
                    self.assertion_count += 1
                    if name in ("assertRaises", "assertRaisesRegex", "assertFalse", "raises"):
                        self.negative_evidence = True
                    else:
                        segment = ast.get_source_segment(self.source, node) or ""
                        low = segment.lower()
                        if any(w in low for w in _NEGATIVE_WORDS):
                            self.negative_evidence = True


def parse_file(path):
    with open(path, "r", encoding="utf-8") as fh:
        source = fh.read()
    tree = ast.parse(source, filename=path)
    return FileReport(path, source, tree)


def _lane_guards(module_reports):
    """Functions and classes that can refuse something.

    Either they raise, or they are named like a check. Both are weak signals
    on their own, which is why the finding they feed is REVIEW.
    """
    guards = []
    for report in module_reports:
        for node in ast.walk(report.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                raises = any(isinstance(n, ast.Raise) for n in ast.walk(node))
                named = any(node.name.lower().startswith(p) for p in
                            ("validate", "check", "verify", "guard", "refuse", "reject", "ensure"))
                if raises or named:
                    guards.append((report.path, node.name, node.lineno))
    return guards


def audit_lane(lane_dir, lane_name, test_prefix=DEFAULT_TEST_GLOB):
    findings = []
    test_reports = []
    module_reports = []
    module_basenames = set()
    by_basename = {}
    aggregators = []

    for dirpath, dirnames, filenames in os.walk(lane_dir):
        # Fixture data and generated samples are not lane code. Auditing a
        # lane's own deliberately-hollow fixtures as if they were its suite
        # would be a false report -- this tool ships exactly such fixtures.
        dirnames[:] = [d for d in dirnames
                       if d not in ("__pycache__", ".git", "fixtures", "sample_output")]
        for fn in sorted(filenames):
            if not fn.endswith(".py"):
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, lane_dir)
            try:
                report = parse_file(path)
            except (SyntaxError, UnicodeDecodeError) as exc:
                findings.append(Finding(lane_name, rel, getattr(exc, "lineno", 0) or 0,
                                        "UNPARSEABLE", str(exc)))
                continue
            by_basename[fn[:-3]] = report
            if fn.startswith(test_prefix):
                test_reports.append((rel, report))
            else:
                module_reports.append(report)
                module_basenames.add(fn[:-3])

    for rel, report in test_reports:
        report.count_assertions_and_negatives()

        if not report.test_functions:
            # A suite aggregator -- a file that imports TestCase classes from
            # siblings so one entry point runs them all -- has no test methods
            # of its own and is entirely legitimate. Reporting it as hollow
            # would be a false accusation, and a linter that makes one gets
            # switched off. Found on this tool's first live run.
            imported_with_tests = sorted(
                name for name in report.imported_modules
                if name in by_basename and by_basename[name].test_functions
            )
            if imported_with_tests:
                aggregators.append({"path": rel, "runs": imported_with_tests})
            else:
                findings.append(Finding(
                    lane_name, rel, 1, "NO_TESTS_COLLECTED",
                    "no test methods found and no sibling suite imported; a discovery "
                    "runner collects this file and reports OK",
                ))

        for name, node, lineno in report.test_functions:
            if not report.has_assertion(node):
                # No assertion, but did it call anything? A call into
                # production code can still raise, so the test fails on a
                # regression -- weak, not vacuous. Calling that a defect
                # overstates what the syntax shows.
                calls = [n for n in ast.walk(node) if isinstance(n, ast.Call)]
                if calls:
                    findings.append(Finding(
                        lane_name, rel, lineno, "SMOKE_TEST_NO_ASSERTION",
                        "%s() asserts nothing; it passes unless one of its calls raises" % name,
                        name,
                    ))
                else:
                    findings.append(Finding(
                        lane_name, rel, lineno, "TEST_WITHOUT_ASSERTION",
                        "%s() contains no assertion and no call; nothing it does can fail" % name,
                        name,
                    ))
            for taut_line, reason in report.tautologies(node):
                findings.append(Finding(
                    lane_name, rel, taut_line, "TAUTOLOGICAL_ASSERTION",
                    "%s in %s() -- passes whatever the code under it does" % (reason, name),
                    name,
                ))

        if module_basenames:
            # A lane can legitimately be exercised through its CLI, by file
            # name in a subprocess call, rather than by import. Counting only
            # imports would flag those suites falsely.
            named_in_strings = any(
                base in s or (base + ".py") in s
                for s in report.string_constants for base in module_basenames
            )
            if not (report.imported_modules & module_basenames) and not named_in_strings:
                findings.append(Finding(
                    lane_name, rel, 1, "NO_REFERENCE_TO_LANE",
                    "imports or names none of this lane's modules (%s)"
                    % ", ".join(sorted(module_basenames)),
                ))

    guards = _lane_guards(module_reports)
    if guards and test_reports:
        if not any(r.negative_evidence for _rel, r in test_reports):
            path, gname, gline = guards[0]
            findings.append(Finding(
                lane_name, os.path.relpath(path, lane_dir), gline,
                "GUARD_WITHOUT_NEGATIVE_CASE",
                "%d guard(s) here, e.g. %s(); no test asserts any of them can refuse input. "
                "A green checker that cannot fail is worth nothing."
                % (len(guards), gname),
                gname,
            ))

    metrics = {
        "lane": lane_name,
        "test_files": len(test_reports),
        "test_methods": sum(len(r.test_functions) for _rel, r in test_reports),
        "assertions": sum(r.assertion_count for _rel, r in test_reports),
        "modules": len(module_reports),
        "guards": len(guards),
        "has_negative_case": any(r.negative_evidence for _rel, r in test_reports),
        "suite_aggregators": aggregators,
    }
    return findings, metrics


def audit_tree(root, only_lane=None, include_fixtures=False, test_prefix=DEFAULT_TEST_GLOB):
    findings = []
    metrics = []
    root = os.path.abspath(root)
    if not os.path.isdir(root):
        raise ValueError("not a directory: %s" % root)

    candidates = []
    for dirpath, dirnames, _files in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ("__pycache__", ".git")]
        for d in list(dirnames):
            if d.startswith(LANE_PREFIX) or (include_fixtures and dirpath == root):
                candidates.append(os.path.join(dirpath, d))
        if not include_fixtures:
            dirnames[:] = [d for d in dirnames if not d.startswith(LANE_PREFIX)]

    seen = set()
    for lane_dir in sorted(candidates):
        lane_name = os.path.basename(lane_dir)
        if lane_name in seen:
            continue
        seen.add(lane_name)
        if only_lane and lane_name != only_lane:
            continue
        if not include_fixtures and os.sep + "fixtures" + os.sep in lane_dir + os.sep:
            continue
        f, m = audit_lane(lane_dir, lane_name, test_prefix)
        findings.extend(f)
        metrics.append(m)
    return findings, metrics


def summarise(findings, metrics):
    by_kind = {}
    for f in findings:
        by_kind[f.kind] = by_kind.get(f.kind, 0) + 1
    return {
        "lanes_audited": len(metrics),
        "test_files": sum(m["test_files"] for m in metrics),
        "test_methods": sum(m["test_methods"] for m in metrics),
        "assertions": sum(m["assertions"] for m in metrics),
        "findings_total": len(findings),
        "defects": len([f for f in findings if f.severity == "DEFECT"]),
        "review_items": len([f for f in findings if f.severity == "REVIEW"]),
        "by_kind": by_kind,
        "lanes_with_findings": len(set(f.lane for f in findings)),
        "lanes_clean": len([m for m in metrics if m["lane"] not in set(f.lane for f in findings)]),
    }


def render_markdown(findings, metrics, root_label):
    s = summarise(findings, metrics)
    lines = []
    lines.append("# Test-proof audit")
    lines.append("")
    lines.append("Does a `Ran N tests / OK` line mean the suite proved something?")
    lines.append("This reads the source and reports where it does not. It **parses, it")
    lines.append("does not execute** — nothing here imports, runs, or writes to the code")
    lines.append("it audits.")
    lines.append("")
    lines.append("Audited: `%s`" % root_label)
    lines.append("")
    lines.append("| | |")
    lines.append("| --- | ---: |")
    lines.append("| Lanes audited | %d |" % s["lanes_audited"])
    lines.append("| Test files | %d |" % s["test_files"])
    lines.append("| Test methods | %d |" % s["test_methods"])
    lines.append("| Assertions | %d |" % s["assertions"])
    lines.append("| **Defects** (mechanically certain) | **%d** |" % s["defects"])
    lines.append("| **Review items** (heuristic; go look) | **%d** |" % s["review_items"])
    lines.append("| Lanes with no findings | %d |" % s["lanes_clean"])
    lines.append("")
    lines.append("## What each finding means")
    lines.append("")
    lines.append("| Kind | Severity | Meaning |")
    lines.append("| --- | --- | --- |")
    for kind in sorted(FINDING_KINDS):
        sev, meaning = FINDING_KINDS[kind]
        lines.append("| `%s` | %s | %s |" % (kind, sev, meaning))
    lines.append("")
    lines.append("`DEFECT` is read off the syntax and carries no judgement: a test method")
    lines.append("with no assertion cannot fail on behaviour. `REVIEW` uses heuristics")
    lines.append("that can be wrong — it is a signal to go look, never a verdict. A tool")
    lines.append("that stated a heuristic as a fact would be committing the error it")
    lines.append("exists to catch.")
    lines.append("")
    if findings:
        lines.append("## Findings")
        lines.append("")
        for severity in ("DEFECT", "REVIEW"):
            rows = [f for f in findings if f.severity == severity]
            if not rows:
                continue
            lines.append("### %s (%d)" % (severity, len(rows)))
            lines.append("")
            lines.append("| Lane | File | Line | Kind | Detail |")
            lines.append("| --- | --- | ---: | --- | --- |")
            for f in sorted(rows, key=lambda x: (x.lane, x.path, x.line)):
                lines.append("| `%s` | `%s` | %d | `%s` | %s |"
                             % (f.lane, f.path, f.line, f.kind, f.detail))
            lines.append("")
    else:
        lines.append("## Findings")
        lines.append("")
        lines.append("None.")
        lines.append("")
    lines.append("## What this does not do")
    lines.append("")
    lines.append("- It does not score or rank lanes, and it does not rank the people or")
    lines.append("  agents who wrote them. It rates test files.")
    lines.append("- It does not repair anything. Every finding is a path and a line the")
    lines.append("  owning author can check; the decision is theirs.")
    lines.append("- A lane with zero findings is not certified correct. This checks that")
    lines.append("  assertions exist and are not vacuous — not that they are the right")
    lines.append("  assertions. Absence of a finding is not evidence of correctness.")
    lines.append("")
    return "\n".join(lines)


def write_csv(findings, path):
    cols = ("lane", "path", "line", "kind", "severity", "name", "detail")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for f in sorted(findings, key=lambda x: (x.severity, x.lane, x.path, x.line)):
            d = f.as_dict()
            w.writerow([d[c] for c in cols])


def main(argv=None):
    p = argparse.ArgumentParser(description="Audit whether test suites assert anything.")
    p.add_argument("--root", required=True, help="directory containing lanes")
    p.add_argument("--lane", help="audit only this lane")
    p.add_argument("--include-fixtures", action="store_true",
                   help="treat immediate subdirectories of --root as lanes (used by the tests)")
    p.add_argument("--outdir")
    p.add_argument("--print", dest="do_print", action="store_true")
    args = p.parse_args(argv)

    try:
        findings, metrics = audit_tree(args.root, args.lane, args.include_fixtures)
    except ValueError as exc:
        sys.stderr.write("error: %s\n" % exc)
        return 2

    if args.outdir:
        os.makedirs(args.outdir, exist_ok=True)
        write_csv(findings, os.path.join(args.outdir, "findings.csv"))
        with open(os.path.join(args.outdir, "audit.json"), "w", encoding="utf-8") as fh:
            json.dump({"summary": summarise(findings, metrics),
                       "findings": [f.as_dict() for f in findings],
                       "metrics": metrics}, fh, indent=2, sort_keys=True)
        with open(os.path.join(args.outdir, "audit.md"), "w", encoding="utf-8") as fh:
            fh.write(render_markdown(findings, metrics, args.root))
        sys.stdout.write("wrote 3 files to %s\n" % args.outdir)

    if args.do_print or not args.outdir:
        sys.stdout.write(render_markdown(findings, metrics, args.root))

    s = summarise(findings, metrics)
    sys.stderr.write(
        "lanes=%d test_files=%d test_methods=%d assertions=%d defects=%d review=%d\n"
        % (s["lanes_audited"], s["test_files"], s["test_methods"], s["assertions"],
           s["defects"], s["review_items"])
    )
    return 1 if s["defects"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
