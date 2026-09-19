#!/usr/bin/env python3
"""Find tests that cannot fail, across every landed lane.

The sibling defect to a self-sealing digest (see audit_self_sealing.py). That
one is a check whose expected value is written by the run that verifies it.
This one is simpler and more common: a test that passes because it never
asserted anything, or asserted something that is true by construction, or
caught the failure it was supposed to report.

All four detections are facts about the parsed syntax tree, not guesses:

  NO_ASSERTION   a test method with no assertion of any kind on any path
  TAUTOLOGY      an assertion that is true by construction -- assertTrue(True),
                 assertEqual(x, x), assertIsNotNone("literal")
  SWALLOWED      a try/except in a test whose handler neither asserts, raises,
                 nor calls fail() -- the failure is caught and discarded
  ASSERT_IS_THE_CHECK       a module whose verification IS bare asserts; run
                 it under `python -O` and it passes having checked nothing
  ASSERT_INTERNAL_INVARIANT an internal guard that disappears under -O
                 (advisory -- this is what assert is for)

A test that cannot fail is worse than a missing test, because a missing test is
visible in the count and this one is not. It reports PASS forever and it is
counted in "704 tests across 33 lanes".

Python 3 standard library only. Reads source; executes nothing.
"""
import argparse
import ast
import json
import os
import sys

SKIP_DIRS = {"__pycache__", ".git", ".pytest_cache", "node_modules"}
ASSERT_CALLS = ("assert", "fail", "raises", "warns")
# Context managers that make a block's body an assertion in its own right.
ASSERTING_CM = ("assertRaises", "assertWarns", "assertLogs", "assertRaisesRegex",
                "assertWarnsRegex", "assertNoLogs")


def _is_assert_call(node):
    if not isinstance(node, ast.Call):
        return False
    fn = node.func
    name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
    return any(name.startswith(p) for p in ASSERT_CALLS)


def _called_helpers(node):
    """Names of same-file helpers this function delegates to.

    Why this exists: the first run flagged twelve tests in
    uiowa_rfq_18649_report_visuals as having no assertion. Every one of them
    delegates to a `_expect_error` helper that does `assertRaises` + `assertIn`.
    The tests were fine; the analyzer was looking only inside the test body. An
    analyzer that accuses a correct suite is the defect it was written to find.
    """
    out = set()
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Call):
            continue
        fn = sub.func
        if isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name) \
                and fn.value.id in ("self", "cls"):
            out.add(fn.attr)
        elif isinstance(fn, ast.Name):
            out.add(fn.id)
    return out


def _asserts_directly(node):
    for sub in ast.walk(node):
        if isinstance(sub, ast.Assert) or isinstance(sub, ast.Raise):
            return True
        if _is_assert_call(sub):
            return True
        if isinstance(sub, ast.With):
            for item in sub.items:
                if _is_assert_call(item.context_expr):
                    return True
    return False


def _asserts_anywhere(node, helpers, seen=None):
    """True if this function asserts, or delegates to something that does."""
    if _asserts_directly(node):
        return True
    seen = seen if seen is not None else set()
    for name in _called_helpers(node):
        if name in seen or name not in helpers:
            continue
        seen.add(name)
        if _asserts_anywhere(helpers[name], helpers, seen):
            return True
    return False


def _literal(node):
    """The node's constant value, or a sentinel when it is not a constant."""
    try:
        return ast.literal_eval(node), True
    except (ValueError, SyntaxError, TypeError):
        return None, False


def _same_expr(a, b):
    try:
        return ast.dump(a) == ast.dump(b)
    except Exception:
        return False


def _tautologies(fn):
    out = []
    for node in ast.walk(fn):
        if isinstance(node, ast.Assert):
            val, ok = _literal(node.test)
            if ok and val:
                out.append((node.lineno, "assert on a constant truthy value"))
            continue
        if not _is_assert_call(node):
            continue
        name = node.func.attr if isinstance(node.func, ast.Attribute) else \
            getattr(node.func, "id", "")
        args = node.args
        if name in ("assertTrue", "assertFalse") and len(args) >= 1:
            val, ok = _literal(args[0])
            if ok and ((name == "assertTrue" and val) or (name == "assertFalse" and not val)):
                out.append((node.lineno, "%s on a constant" % name))
        elif name in ("assertEqual", "assertIs", "assertNotEqual") and len(args) >= 2:
            # assertEqual(f(x), f(x)) EVALUATES f TWICE -- that is a
            # determinism check, not a tautology, and flagging it was the
            # analyzer's own false positive on its first run. Only a
            # call-free expression compared with itself is vacuous.
            if name != "assertNotEqual" and _same_expr(args[0], args[1]) \
                    and not any(isinstance(s, ast.Call)
                                for a in args[:2] for s in ast.walk(a)):
                out.append((node.lineno, "%s compares an expression with itself" % name))
            else:
                l, lok = _literal(args[0])
                r, rok = _literal(args[1])
                if lok and rok and ((name == "assertNotEqual" and l != r) or
                                    (name != "assertNotEqual" and l == r)):
                    out.append((node.lineno, "%s compares two constants" % name))
        elif name in ("assertIsNotNone", "assertIsNone") and len(args) >= 1:
            val, ok = _literal(args[0])
            if ok and ((name == "assertIsNotNone" and val is not None) or
                       (name == "assertIsNone" and val is None)):
                out.append((node.lineno, "%s on a literal" % name))
    return out


def _swallowed(fn):
    """A handler that discards the failure entirely.

    Narrowed after a false positive: uiowa_rfq_18649_ai_integration catches
    ValueError and RECORDS it (`scores[wid] = "REJECTED"`), then asserts on
    that record three lines later. That is a correct way to test a rejection
    path. Only a handler that keeps nothing and says nothing is swallowing --
    if it assigns, appends, logs or calls anything, the failure survived in
    some form and a reader can follow it.
    """
    out = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.Try):
            continue
        for handler in node.handlers:
            keeps = False
            for s in ast.walk(handler):
                if isinstance(s, (ast.Assert, ast.Raise, ast.Assign, ast.AugAssign,
                                  ast.AnnAssign, ast.Call, ast.Expr)):
                    keeps = True
                    break
            if not keeps:
                out.append((handler.lineno,
                            "handler discards the failure entirely"))
    return out


def scan_test_file(path, rel):
    try:
        with open(path, encoding="utf-8") as f:
            src = f.read()
        tree = ast.parse(src, filename=path)
    except (OSError, SyntaxError) as exc:
        return [{"rule": "UNPARSEABLE", "file": rel, "line": 0, "test": "-",
                 "detail": str(exc)[:120]}]
    # Every function in the file, so a test that delegates to a helper is
    # judged on what the helper actually does.
    helpers = {n.name: n for n in ast.walk(tree)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("test"):
            continue
        if not _asserts_anywhere(node, helpers):
            out.append({"rule": "NO_ASSERTION", "file": rel, "line": node.lineno,
                        "test": node.name, "detail": "no assertion on any path"})
        for line, why in _tautologies(node):
            out.append({"rule": "TAUTOLOGY", "file": rel, "line": line,
                        "test": node.name, "detail": why})
        for line, why in _swallowed(node):
            out.append({"rule": "SWALLOWED", "file": rel, "line": line,
                        "test": node.name, "detail": why})
    return out


def scan_source_file(path, rel):
    """A bare `assert` in shipped source is removed by `python -O`.

    Two very different situations wear the same syntax, so they are reported
    separately rather than as eighteen undifferentiated lines:

      ASSERT_IS_THE_CHECK       a module whose asserts ARE its verification --
                                a standalone acceptance script with no
                                unittest and no raise. Run it under -O and it
                                passes having checked nothing. This is the
                                same family as a self-sealing digest: a green
                                result with nothing behind it.
      ASSERT_INTERNAL_INVARIANT a guard on an internal code path, e.g.
                                `assert code in VALIDATION_CODES`. That is the
                                textbook use of assert. Advisory only.

    The split is mechanical: a module with no `unittest` import, at least 3
    bare asserts, and more asserts than `raise` statements, is verifying with
    asserts.
    """
    try:
        with open(path, encoding="utf-8") as f:
            src = f.read()
        tree = ast.parse(src, filename=path)
    except (OSError, SyntaxError):
        return []
    asserts = [n for n in ast.walk(tree) if isinstance(n, ast.Assert)]
    if not asserts:
        return []
    has_unittest = any(
        isinstance(n, (ast.Import, ast.ImportFrom)) and
        any("unittest" in (a.name or "") for a in n.names)
        for n in ast.walk(tree))
    # Count, do not merely detect: a single `raise` for an unmet precondition
    # does not make fifteen bare asserts into something else. The first cut
    # used "has any raise" and let a Chromium smoke script whose 15 of 16
    # checks are bare asserts fall into the advisory bucket.
    raises = sum(1 for n in ast.walk(tree) if isinstance(n, ast.Raise))
    is_the_check = (len(asserts) >= 3 and not has_unittest
                    and len(asserts) > raises)
    rule = "ASSERT_IS_THE_CHECK" if is_the_check else "ASSERT_INTERNAL_INVARIANT"
    detail = ("this module's verification is bare asserts; python -O removes "
              "all of them" if is_the_check else
              "internal invariant; absent under python -O")
    return [{"rule": rule, "file": rel, "line": n.lineno, "test": "-",
             "detail": detail} for n in asserts]


def audit_lane(lane):
    name = os.path.basename(lane)
    findings, tests_seen = [], 0
    for dirpath, dirnames, files in os.walk(lane):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in sorted(files):
            if not fn.endswith(".py"):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, os.path.dirname(lane))
            if fn.startswith("test_") or fn.endswith("_test.py"):
                tests_seen += 1
                findings += scan_test_file(full, rel)
            else:
                findings += scan_source_file(full, rel)
    return {"lane": name, "test_files": tests_seen, "findings": findings}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root")
    ap.add_argument("--prefix", default="uiowa_rfq_18649_")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("--only")
    args = ap.parse_args(argv)

    names = sorted(d for d in os.listdir(args.root)
                   if d.startswith(args.prefix)
                   and os.path.isdir(os.path.join(args.root, d)))
    if args.only:
        names = [n for n in names if n == args.only]
    results = [audit_lane(os.path.join(args.root, n)) for n in names]

    if args.format == "json":
        print(json.dumps(results, indent=2, sort_keys=True))
        return 1 if any(r["findings"] for r in results) else 0

    counts, total_tests = {}, 0
    print("scanned %d lane(s) under %s\n" % (len(results), args.root))
    for r in sorted(results, key=lambda r: r["lane"]):
        total_tests += r["test_files"]
        if not r["findings"]:
            continue
        print(r["lane"])
        for f in sorted(r["findings"], key=lambda f: (f["rule"], f["file"], f["line"])):
            counts[f["rule"]] = counts.get(f["rule"], 0) + 1
            print("    %-16s %s:%s  %s  -- %s"
                  % (f["rule"], f["file"], f["line"], f["test"], f["detail"]))
        print()
    print("test files scanned: %d" % total_tests)
    print("summary: " + ("  ".join("%s=%d" % (k, counts[k]) for k in sorted(counts))
                         or "no findings"))
    return 1 if counts else 0


if __name__ == "__main__":
    raise SystemExit(main())
