#!/usr/bin/env python3
"""OPS-PERF-SCAN -- read-only hotspot scanner for the delivered assessment kit.

UIOWA-095 measured two real performance defects in shipped lane tools. This
looks for the same shapes everywhere else in the kit, so a defect found once
does not get shipped everywhere else unnoticed.

WHY AST AND NOT GREP
--------------------
A regex over source produces confident nonsense: it cannot tell
``path.read_text()[:500]`` (the real defect -- whole file materialised to look
at a slice) from ``header[:500]`` (fine), and it cannot see whether an ``in``
test is against a set or a list. This walks the parsed tree instead, so a hit
means a structural match rather than a lexical coincidence. That matters extra
here because these findings are about other seats' files, and a false
accusation is worse than no scan.

WHAT A HIT MEANS, AND WHAT IT DOES NOT
--------------------------------------
Every finding carries a ``confidence``:

  CONFIRMED_SHAPE  the AST match is unambiguous -- the code really does do the
                   thing described. Whether it MATTERS here depends on inputs
                   this scanner cannot see.
  CANDIDATE        the shape is suggestive but the scanner cannot prove intent
                   from source alone. Needs a human look.

And every finding carries a ``measured_cost``. It is a real figure ONLY for the
two patterns measured on this machine under UIOWA-095. For everything else it
is the string ``UNKNOWN`` -- because a pattern match is not a measurement, and
turning one into the other is exactly the move this kit is not allowed to make.

WHAT THIS IS NOT
----------------
Not a score. Findings are listed by file so the owner can act. This does not
rank seats, lanes, or people, does not compute a quality metric, and does not
assert that any lane is deficient. Files are read; nothing outside the output
directory is written.

Python 3 standard library only. No network.
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

# Cost evidence carried over from the UIOWA-095 benchmark, which measured these
# two shapes end to end on synthetic workloads. Cited by pattern id so a reader
# can go check the run rather than take this file's word for it.
MEASURED_EVIDENCE = {
    "P1_substring_scan_in_loop": {
        "measured_in": "revenue/uiowa_rfq_18649_capacity_benchmark/results/BENCHMARK_REPORT.md",
        "workload": "3,000 statements against a 631,500-character report (synthetic)",
        "result": "22.55x elapsed-time reduction after repair; baseline stage grew ~13,000x "
                  "across a 128x workload increase (quadratic)",
    },
    "P2_read_all_then_slice": {
        "measured_in": "revenue/uiowa_rfq_18649_capacity_benchmark/results/BENCHMARK_REPORT.md",
        "workload": "600 documents / 55 MB of synthetic evidence, largest 1.4 MB",
        "result": "4.15x elapsed-time reduction after repair; peak memory stops tracking the "
                  "largest document in the collection",
    },
}

# Names of calls that yield a string read off disk. Membership against one of
# these is a substring scan -- the shape UIOWA-095 measured as quadratic.
READ_CALLS = {"read_text", "read"}
# Calls that yield a list. Membership against one of these is the classic O(n^2).
LIST_CALLS = {"list", "sorted", "split", "splitlines", "readlines"}
# Deliberately NARROW. An earlier version treated any str-producing expression
# as a substring-scan target; calibrated against the delivered kit that produced
# eight matches against short bounded strings (a filename, a CSV token, one
# joined row) and only one real instance. The measured defect needs a LARGE
# string, and the only strings a source-only scanner can be confident are large
# are the ones that came off disk.
STR_CALLS = {"read_text", "read"}


class Finding:
    __slots__ = ("path", "line", "col", "pattern", "confidence", "detail", "snippet")

    def __init__(self, path, line, col, pattern, confidence, detail, snippet):
        self.path, self.line, self.col = path, line, col
        self.pattern, self.confidence = pattern, confidence
        self.detail, self.snippet = detail, snippet

    def to_dict(self, root: Path) -> dict:
        return {
            "file": str(Path(self.path).relative_to(root)) if str(self.path).startswith(str(root)) else str(self.path),
            "line": self.line,
            "column": self.col,
            "pattern": self.pattern,
            "confidence": self.confidence,
            "detail": self.detail,
            "source": self.snippet,
            "measured_cost": MEASURED_EVIDENCE.get(self.pattern, "UNKNOWN -- shape matched, cost not measured"),
        }


def _name_of(node) -> str:
    """Best-effort attribute/function name for a call target, or '' if absent."""
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def _is_read_call(node) -> bool:
    return isinstance(node, ast.Call) and _name_of(node.func) in READ_CALLS


def _annotation_name(node) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Subscript):
        return _annotation_name(node.value)
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return ""


class HotspotVisitor(ast.NodeVisitor):
    """Walks one module collecting structural matches.

    PRECISION NOTE -- this is the second version of this visitor, and the reason
    is worth recording. The first version flagged any in-loop membership test
    whose container was not visibly a set. Run against the delivered kit it
    produced 131 hits, nearly all of them ordinary ``if key in some_dict``
    lookups that are already O(1) and perfectly correct. A detector that is
    92% noise is worse than no detector: it buries the real findings and it
    reads as an accusation against three dozen lanes that did nothing wrong.

    So the rule was narrowed to the shapes UIOWA-095 actually MEASURED:

      * membership against a string that came off disk -- a substring scan,
        quadratic when the loop count grows with the string
      * membership against a list -- the classic O(n*m)

    Membership against a dict or set is not reported at all, because it is the
    correct way to write it.
    """

    def __init__(self, path: Path, source_lines):
        self.path = path
        self.lines = source_lines
        self.findings = []
        self.loop_targets = []          # stack of names bound by enclosing loops
        self.string_names = set()       # names known to hold text READ FROM A FILE
        self.annotated_str_params = set()  # params declared str -- size unknown here
        self.list_names = set()         # names known to hold list

    # -- helpers ---------------------------------------------------------
    def _snippet(self, node) -> str:
        idx = getattr(node, "lineno", 1) - 1
        return self.lines[idx].strip()[:200] if 0 <= idx < len(self.lines) else ""

    def _add(self, node, pattern, confidence, detail):
        self.findings.append(Finding(
            self.path, getattr(node, "lineno", 0), getattr(node, "col_offset", 0),
            pattern, confidence, detail, self._snippet(node)))

    def _classify(self, value):
        """Return 'str', 'list' or '' for an expression, conservatively."""
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            return "str"
        if isinstance(value, ast.JoinedStr):
            return "str"
        if isinstance(value, (ast.List, ast.ListComp)):
            return "list"
        if isinstance(value, ast.Call):
            fn = _name_of(value.func)
            if fn in LIST_CALLS:
                return "list"
            if fn in STR_CALLS:
                return "str"
        if isinstance(value, ast.Name):
            if value.id in self.string_names:
                return "str"
            if value.id in self.list_names:
                return "list"
        if isinstance(value, ast.BinOp) and isinstance(value.op, ast.Add):
            for side in (value.left, value.right):
                kind = self._classify(side)
                if kind:
                    return kind
        return ""

    def _bind(self, name, kind):
        self.string_names.discard(name)
        self.list_names.discard(name)
        if kind == "str":
            self.string_names.add(name)
        elif kind == "list":
            self.list_names.add(name)

    # -- tracking --------------------------------------------------------
    def visit_Assign(self, node):
        kind = self._classify(node.value)
        for target in node.targets:
            if isinstance(target, ast.Name):
                self._bind(target.id, kind)
                self._mark_iteration_dependent(target.id)
        self.generic_visit(node)

    def visit_With(self, node):
        """``with open(path) as fh:`` inside a loop binds a NEW handle each pass.

        Without this, every `fh.read()` in the kit looked like a re-read of one
        file, which is what made the first version of this check 95% noise.
        """
        for item in node.items:
            var = item.optional_vars
            if isinstance(var, ast.Name):
                self._mark_iteration_dependent(var.id)
        self.generic_visit(node)

    visit_AsyncWith = visit_With

    def _mark_iteration_dependent(self, name):
        if self.loop_targets:
            self.loop_targets[-1].add(name)

    def visit_AnnAssign(self, node):
        kind = _annotation_name(node.annotation)
        if isinstance(node.target, ast.Name):
            self._bind(node.target.id, "str" if kind == "str" else "list" if kind in ("list", "List") else "")
        self.generic_visit(node)

    def visit_AugAssign(self, node):
        # ``report += f.read_text()`` keeps report a string.
        if isinstance(node.target, ast.Name) and isinstance(node.op, ast.Add):
            kind = self._classify(node.value)
            if kind:
                self._bind(node.target.id, kind)
        self.generic_visit(node)

    def _visit_function(self, node):
        """Annotated parameters tell us the type without guessing."""
        for arg in list(node.args.args) + list(node.args.kwonlyargs):
            ann = _annotation_name(arg.annotation) if arg.annotation else ""
            if ann == "str":
                # A str parameter's SIZE is invisible here, so it is tracked
                # separately and reported at CANDIDATE, never CONFIRMED.
                self.annotated_str_params.add(arg.arg)
            elif ann in ("list", "List"):
                self._bind(arg.arg, "list")
        self.generic_visit(node)

    visit_FunctionDef = _visit_function
    visit_AsyncFunctionDef = _visit_function

    def _visit_loop(self, node):
        # The iterable is evaluated ONCE, before the body runs, so it is visited
        # OUTSIDE the loop frame. Getting this wrong made
        # `for line in Path(p).read_text().splitlines()` -- a single read --
        # look like a read on every iteration.
        self.visit(node.iter)
        targets = set()
        target = getattr(node, "target", None)
        if isinstance(target, ast.Name):
            targets.add(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            targets.update(e.id for e in target.elts if isinstance(e, ast.Name))
        self.loop_targets.append(targets)
        for stmt in node.body + node.orelse:
            self.visit(stmt)
        self.loop_targets.pop()

    visit_For = _visit_loop
    visit_AsyncFor = _visit_loop

    def visit_While(self, node):
        self.loop_targets.append(set())
        self.generic_visit(node)
        self.loop_targets.pop()

    # -- P2: whole file read, then sliced --------------------------------
    def visit_Subscript(self, node):
        if _is_read_call(node.value) and isinstance(node.slice, ast.Slice):
            sl = node.slice
            simple_prefix = sl.lower is None and sl.upper is not None
            self._add(node, "P2_read_all_then_slice", "CONFIRMED_SHAPE",
                      "A whole file is read and decoded, then sliced. Elapsed time and peak "
                      "memory track total file size rather than the slice; a bounded read "
                      "returns the same characters." + ("" if simple_prefix else
                      " This slice is not a simple prefix, so a bounded read is not "
                      "automatically a drop-in substitute."))
        self.generic_visit(node)

    # -- P1: the two measured membership shapes --------------------------
    def visit_Compare(self, node):
        if self.loop_targets and len(node.ops) == 1 and isinstance(node.ops[0], (ast.In, ast.NotIn)):
            container = node.comparators[0]
            if _is_read_call(container):
                self._add(node, "P1_substring_scan_in_loop", "CONFIRMED_SHAPE",
                          "A file is read INSIDE a loop and then searched. Both the read and "
                          "the scan repeat on every iteration.")
            elif isinstance(container, ast.Name) and container.id in self.string_names:
                self._add(node, "P1_substring_scan_in_loop", "CONFIRMED_SHAPE",
                          f"Substring scan of {container.id!r} once per iteration, where that "
                          "name holds text read from a file. When the loop count grows with the "
                          "text -- as it does when the text is generated from the very items "
                          "being looked up -- this is quadratic in characters scanned. This is "
                          "the exact shape UIOWA-095 measured at 22.55x.")
            elif isinstance(container, ast.Name) and container.id in self.annotated_str_params:
                self._add(node, "P1_substring_scan_in_loop", "CANDIDATE",
                          f"Substring scan of the str parameter {container.id!r} once per "
                          "iteration. Whether this is the quadratic depends on how large the "
                          "caller's string is, which a source-only scanner cannot see: the "
                          "value arrives across a function boundary. Needs a human look.")
            elif isinstance(container, ast.Name) and container.id in self.list_names:
                self._add(node, "P1_list_membership_in_loop", "CONFIRMED_SHAPE",
                          f"Membership test against the list {container.id!r} inside a loop: "
                          "O(len(list)) per iteration. A set gives the same answer in O(1).")
            elif isinstance(container, (ast.List, ast.Tuple)) and len(getattr(container, "elts", [])) > 12:
                self._add(node, "P1_list_membership_in_loop", "CONFIRMED_SHAPE",
                          f"Membership test against a {len(container.elts)}-item literal inside "
                          "a loop. A set literal is O(1) here.")
        self.generic_visit(node)

    # -- P3: re-reading the SAME file every iteration ---------------------
    def visit_Call(self, node):
        if self.loop_targets and _is_read_call(node):
            # Reading a different file each iteration is the normal, correct
            # thing. Only flag it when the path expression does not mention any
            # enclosing loop variable, which means the same bytes are being
            # re-read every time.
            live = set().union(*self.loop_targets) if self.loop_targets else set()
            mentioned = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
            if not (mentioned & live):
                self._add(node, "P3_same_file_reread_in_loop", "CANDIDATE",
                          "A file read inside a loop whose path expression does not reference "
                          "any loop variable, so the same file may be re-read on every "
                          "iteration. Hoisting it out of the loop would read it once.")
        self.generic_visit(node)


def scan_source(path: Path, source: str) -> list:
    """Parse and walk one file. Raises SyntaxError on unparseable input."""
    tree = ast.parse(source, filename=str(path))
    visitor = HotspotVisitor(path, source.splitlines())
    visitor.visit(tree)
    return visitor.findings


def scan_tree(root: Path, include_glob: str = "*.py", skip_dirs=("__pycache__", ".git")) -> dict:
    """Scan every Python file under root.

    A file that cannot be read or parsed is reported as ``unscannable`` with the
    reason. It is never counted as clean -- "we could not look" and "we looked
    and it was fine" are different claims, and collapsing them is how a scan
    starts lying.
    """
    root = Path(root).resolve()
    findings, unscannable, scanned = [], [], []
    for path in sorted(root.rglob(include_glob)):
        if any(part in skip_dirs for part in path.parts):
            continue
        if not path.is_file():
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as exc:
            unscannable.append({"file": str(path.relative_to(root)),
                                "reason": f"{type(exc).__name__}: {exc}"})
            continue
        try:
            findings.extend(scan_source(path, source))
        except SyntaxError as exc:
            unscannable.append({"file": str(path.relative_to(root)),
                                "reason": f"SyntaxError: {exc.msg} (line {exc.lineno})"})
            continue
        scanned.append(str(path.relative_to(root)))

    by_pattern = {}
    for f in findings:
        by_pattern.setdefault(f.pattern, 0)
        by_pattern[f.pattern] += 1

    return {
        "schema": "uiowa-ops-perf-scan-v1",
        "root": str(root),
        "files_scanned": len(scanned),
        "files_unscannable": len(unscannable),
        "unscannable": unscannable,
        "finding_count": len(findings),
        "findings_by_pattern": by_pattern,
        "findings": [f.to_dict(root) for f in findings],
        "disclaimer": (
            "Structural matches, not proven defects. CONFIRMED_SHAPE means the code really "
            "does have the shape described; whether it costs anything depends on inputs this "
            "scanner cannot see. CANDIDATE needs a human look. measured_cost is a real figure "
            "ONLY where UIOWA-095 measured that pattern; everywhere else it is UNKNOWN. "
            "This is not a score of any lane, seat, or person, and no ranking is implied."
        ),
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Delivery-kit performance hotspot scan (OPS-PERF-SCAN)",
        "",
        "Read-only AST scan for the two performance shapes measured under UIOWA-095, plus a",
        "closely related third. Generated by `scan_hotspots.py`.",
        "",
        "**These are structural matches, not proven defects, and this is not a score.**",
        "Findings are listed by file so an owner can act on their own code. No lane, seat or",
        "person is ranked, and no quality metric is computed. `measured_cost` is a real figure",
        "only where UIOWA-095 actually measured that pattern; everywhere else it is UNKNOWN.",
        "",
        f"- Root scanned: `{report['root']}`",
        f"- Files scanned: **{report['files_scanned']}**",
        f"- Files that could NOT be scanned: **{report['files_unscannable']}** "
        "(reported, never counted as clean)",
        f"- Structural matches: **{report['finding_count']}**",
        "",
        "## Matches by pattern",
        "",
        "| Pattern | Count | Cost evidence |",
        "| --- | ---: | --- |",
    ]
    if report["findings_by_pattern"]:
        for pattern, count in sorted(report["findings_by_pattern"].items()):
            ev = MEASURED_EVIDENCE.get(pattern)
            cost = f"measured under UIOWA-095: {ev['result']}" if ev else "UNKNOWN -- not measured"
            lines.append(f"| `{pattern}` | {count} | {cost} |")
    else:
        lines.append("| _none_ | 0 | — |")

    lines += ["", "## Findings", ""]
    if not report["findings"]:
        lines += ["No structural matches found. That is a real result: the two shapes measured",
                  "under UIOWA-095 were not detected elsewhere in the scanned tree.", ""]
    else:
        lines += ["| File | Line | Pattern | Confidence | Source |",
                  "| --- | ---: | --- | --- | --- |"]
        for f in report["findings"]:
            src = f["source"].replace("|", "\\|")
            lines.append(f"| `{f['file']}` | {f['line']} | `{f['pattern']}` | {f['confidence']} | `{src}` |")
        lines += ["", "### Detail", ""]
        for f in report["findings"]:
            lines += [f"**`{f['file']}:{f['line']}`** — `{f['pattern']}` ({f['confidence']})", "",
                      f"> {f['detail']}", ""]

    if report["unscannable"]:
        lines += ["## Could not be scanned", "",
                  "Reported rather than silently skipped — an unreadable file is not a clean file.",
                  "", "| File | Reason |", "| --- | --- |"]
        for u in report["unscannable"]:
            lines.append(f"| `{u['file']}` | {u['reason']} |")
        lines.append("")

    lines += ["## Limits", "",
              "- Source-only. A structural match says nothing about the inputs the code actually",
              "  sees in production, so a CONFIRMED_SHAPE hit is not automatically a problem.",
              "- `P3_file_read_in_loop` is expected to match a lot of correct code (reading many",
              "  different files in a loop is the normal way to do that). It is reported at",
              "  CANDIDATE and is not evidence of anything on its own.",
              "- Scope is whatever tree is passed on the command line. Nothing outside it was",
              "  examined, and nothing outside the output directory was written.", ""]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Read-only performance hotspot scan of a source tree.")
    p.add_argument("root", type=Path, help="Directory to scan (read-only).")
    p.add_argument("--out", type=Path, default=None, help="Directory for the report files.")
    a = p.parse_args(argv)

    if not a.root.is_dir():
        print(f"not a directory: {a.root}", file=sys.stderr)
        return 2

    report = scan_tree(a.root)
    if a.out:
        a.out.mkdir(parents=True, exist_ok=True)
        (a.out / "scan_results.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (a.out / "SCAN_REPORT.md").write_text(render_markdown(report), encoding="utf-8")
        print(f"wrote {a.out / 'scan_results.json'}")
        print(f"wrote {a.out / 'SCAN_REPORT.md'}")

    print(f"scanned={report['files_scanned']} unscannable={report['files_unscannable']} "
          f"matches={report['finding_count']}")
    for pattern, count in sorted(report["findings_by_pattern"].items()):
        print(f"  {pattern}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
