"""Read-only static screen: which tools in a delivery kit can destroy a file?

Why this exists. The operator handoff kit hands a new operator a menu of
commands spanning the whole engagement tree, and those commands get pointed at
a directory of real client evidence. Several of them call `shutil.rmtree` and
`subprocess.run` from non-test code. Most of that is certainly legitimate -- a
verifier cleaning up its own temp copy is exactly right -- but nobody had
checked which `rmtree` targets a scratch directory and which targets a path that
arrived from `argv`. This screen answers that one question and nothing else.

What it is NOT. It is a screen, not a proof. A CLEAN result means the screen
found nothing it could see; it does NOT mean the module is safe. `getattr`,
dynamic dispatch, C extensions, and anything that happens inside a `subprocess`
are all outside what an AST can observe. There is no safety score, no
percentage, and no lane is ever marked compliant. Where the trace runs out the
finding is UNDETERMINED, which is its own class precisely so that a screen which
cannot tell does not get to say "clean".

This module reads files and writes nothing outside an explicit output directory.
"""
from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from typing import Any

# -------------------------------------------------------------- what we look for

# Leaf names with no harmless stdlib meaning -- `x.rmtree()` is destructive
# whatever `x` is. Note `replace`/`rename`/`move` are NOT here: `str.replace` is
# everywhere and flagging it would drown the real findings in noise.
DESTRUCTIVE_LEAF = frozenset({"rmtree", "removedirs", "unlink", "rmdir", "truncate"})

# Names that are only destructive under a filesystem module.
DESTRUCTIVE_DOTTED = frozenset({
    "os.remove", "os.unlink", "os.rmdir", "os.removedirs", "os.truncate",
    "os.rename", "os.renames", "os.replace",
    "shutil.rmtree", "shutil.move",
    "Path.unlink", "Path.rmdir", "Path.replace", "Path.rename",
    "pathlib.Path.unlink", "pathlib.Path.replace",
})

# Shelling out is not itself destructive, but it is a hole in the screen: what
# runs inside is invisible to AST. Reported as its own kind, never as clean.
OPAQUE_DOTTED = frozenset({
    "os.system", "os.popen", "os.execv", "os.execve", "os.spawnv",
    "subprocess.run", "subprocess.call", "subprocess.check_call",
    "subprocess.check_output", "subprocess.Popen", "subprocess.getoutput",
})

WRITE_MODE_CHARS = frozenset("wax+")

# Sources that make a path self-scoped: the module created the directory itself.
TEMP_FACTORIES = frozenset({
    "tempfile.mkdtemp", "tempfile.mkstemp", "tempfile.TemporaryDirectory",
    "tempfile.NamedTemporaryFile", "mkdtemp", "TemporaryDirectory",
})
# Sources that make a path externally controlled.
EXTERNAL_SOURCES = frozenset({
    "sys.argv", "os.environ", "os.getenv", "environ", "getenv",
    "input", "json.load", "json.loads",
})

# ------------------------------------------------------------------ result model

DESTRUCTIVE = "DESTRUCTIVE"
OPAQUE = "OPAQUE_SUBPROCESS"
UNGUARDED_WRITE = "WRITE"

SELF_SCOPED = "SELF_SCOPED"
WRITE_TO_CALLER_PATH = "WRITE_TO_CALLER_PATH"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
UNDETERMINED = "UNDETERMINED"
TEST_CONTEXT = "TEST_CONTEXT"

# Ordered worst-first so a module's headline is its worst finding.
SEVERITY_ORDER = (REVIEW_REQUIRED, UNDETERMINED, WRITE_TO_CALLER_PATH,
                  TEST_CONTEXT, SELF_SCOPED)

CLEAN = "CLEAN"
UNPARSEABLE = "UNPARSEABLE"


@dataclass
class Finding:
    lane: str
    module: str
    line: int
    kind: str
    call: str
    classification: str
    target_expr: str
    why: str

    def to_json(self) -> dict:
        return {
            "lane": self.lane, "module": self.module, "line": self.line,
            "kind": self.kind, "call": self.call,
            "classification": self.classification,
            "target": self.target_expr, "why": self.why,
        }


@dataclass
class ModuleReport:
    lane: str
    module: str
    parsed: bool
    findings: list = field(default_factory=list)
    parse_error: Any = None

    @property
    def status(self) -> str:
        if not self.parsed:
            # Never CLEAN: a module we could not read is not a module we cleared.
            return UNPARSEABLE
        for level in SEVERITY_ORDER:
            if any(f.classification == level for f in self.findings):
                return level
        return CLEAN


# ------------------------------------------------------------------ AST helpers

def dotted_name(node: ast.AST):
    """Best-effort dotted name for a call target: os.path.join -> 'os.path.join'."""
    parts = []
    cur = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        return ".".join(reversed(parts))
    if isinstance(cur, ast.Call):
        # e.g. Path("x").unlink() -- keep the attribute chain, mark the head.
        return ".".join(reversed(parts)) if parts else None
    return ".".join(reversed(parts)) if parts else None


def expr_text(node: Any) -> str:
    if node is None:
        return "<no argument>"
    try:
        return ast.unparse(node)
    except Exception:
        return f"<{type(node).__name__}>"


class _FunctionIndex(ast.NodeVisitor):
    """Maps each node to its enclosing function, and each function to its
    parameter names and local assignments. Deliberately intraprocedural: a
    cross-module tracer would be guessing, and this screen does not guess."""

    def __init__(self, tree: ast.AST):
        self.enclosing = {}
        self.params = {}
        self.assigns = {}
        # `self.x = ...` collected module-wide. An approximation -- it does not
        # separate classes -- but it correctly resolves the TestCase.setUp
        # pattern `self.dir = tempfile.mkdtemp()`, which the first version
        # mis-reported as a caller-supplied path.
        self.attr_assigns = {}
        self._collect_attrs(tree)
        self._walk(tree, None)

    def _collect_attrs(self, tree):
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (isinstance(target, ast.Attribute)
                            and isinstance(target.value, ast.Name)
                            and target.value.id == "self"):
                        self.attr_assigns.setdefault(
                            f"self.{target.attr}", []).append(node.value)
            elif isinstance(node, ast.withitem) and isinstance(node.optional_vars, ast.Attribute):
                tgt = node.optional_vars
                if isinstance(tgt.value, ast.Name) and tgt.value.id == "self":
                    self.attr_assigns.setdefault(
                        f"self.{tgt.attr}", []).append(node.context_expr)

    def _walk(self, node, fn):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fn = node
            args = node.args
            names = [a.arg for a in list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs)]
            if args.vararg:
                names.append(args.vararg.arg)
            if args.kwarg:
                names.append(args.kwarg.arg)
            self.params[fn] = set(names)
            self.assigns.setdefault(fn, {})
        if fn is not None:
            self.enclosing[node] = fn
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.assigns.setdefault(fn, {}).setdefault(target.id, []).append(node.value)
            elif isinstance(node, ast.withitem) and isinstance(node.optional_vars, ast.Name):
                self.assigns.setdefault(fn, {}).setdefault(
                    node.optional_vars.id, []).append(node.context_expr)
        for child in ast.iter_child_nodes(node):
            self._walk(child, fn)


def _classify_target(target: Any, fn, index: _FunctionIndex, depth: int = 0):
    """Where did this path come from? Returns (classification, reason).

    Depth-limited so a self-referential assignment cannot spin. Running out of
    depth yields UNDETERMINED, which is the honest answer.
    """
    if target is None or depth > 6:
        return UNDETERMINED, "could not trace the target expression"

    if isinstance(target, ast.Constant):
        return SELF_SCOPED, "target is a literal in this module"

    if isinstance(target, ast.Call):
        name = dotted_name(target.func) or ""
        if name in TEMP_FACTORIES or name.split(".")[-1] in {
            "mkdtemp", "TemporaryDirectory", "mkstemp", "NamedTemporaryFile"
        }:
            return SELF_SCOPED, f"target comes from {name}(), a directory this module created"
        if name in EXTERNAL_SOURCES or name.split(".")[-1] in {"getenv", "load", "loads", "input"}:
            return REVIEW_REQUIRED, f"target comes from {name}(), which is external input"
        if name.endswith("join") or name.endswith("abspath") or name.endswith("realpath"):
            # A join is only as safe as its worst part.
            results = [_classify_target(a, fn, index, depth + 1) for a in target.args]
            if any(r[0] == REVIEW_REQUIRED for r in results):
                return REVIEW_REQUIRED, "path is joined from externally controlled parts"
            if any(r[0] == UNDETERMINED for r in results):
                return UNDETERMINED, "path is joined from a part that could not be traced"
            return SELF_SCOPED, "path is joined from module-local parts"
        return UNDETERMINED, f"target is the result of {name or 'a call'}(), not traced"

    if isinstance(target, ast.Attribute):
        name = dotted_name(target) or ""
        if name in EXTERNAL_SOURCES or name.startswith("sys.argv") or name.startswith("os.environ"):
            return REVIEW_REQUIRED, f"target comes from {name}, which is external input"
        if name.startswith("self."):
            values = index.attr_assigns.get(name)
            if values:
                results = [_classify_target(v, fn, index, depth + 1) for v in values]
                if any(r[0] == REVIEW_REQUIRED for r in results):
                    return REVIEW_REQUIRED, f"{name} is assigned from external input"
                if all(r[0] == SELF_SCOPED for r in results):
                    return SELF_SCOPED, f"{name} is assigned from values this module created"
                return UNDETERMINED, f"{name} has an assignment that could not be traced"
            return UNDETERMINED, f"{name} has no assignment visible in this module"
        if name.startswith("args."):
            return REVIEW_REQUIRED, f"target comes from {name}, a command-line option"
        return UNDETERMINED, f"target is attribute {name}, not traced"

    if isinstance(target, ast.Name):
        if fn is not None and target.id in index.params.get(fn, set()):
            return REVIEW_REQUIRED, (
                f"target is the function parameter '{target.id}' -- the caller "
                "chooses what gets removed"
            )
        values = index.assigns.get(fn, {}).get(target.id) if fn is not None else None
        if values:
            results = [_classify_target(v, fn, index, depth + 1) for v in values]
            if any(r[0] == REVIEW_REQUIRED for r in results):
                return REVIEW_REQUIRED, f"'{target.id}' is assigned from external input"
            if all(r[0] == SELF_SCOPED for r in results):
                return SELF_SCOPED, f"'{target.id}' is assigned from module-local values"
            return UNDETERMINED, f"'{target.id}' has an assignment that could not be traced"
        return UNDETERMINED, f"'{target.id}' has no assignment visible in this function"

    if isinstance(target, ast.Subscript):
        # sys.argv[1] / config["path"] -- the subscript is irrelevant, the
        # container is what says where the value came from. Missing this case
        # made the screen report `shutil.rmtree(sys.argv[1])` as merely
        # UNDETERMINED, which is the one answer it must never give there.
        return _classify_target(target.value, fn, index, depth + 1)

    if isinstance(target, ast.JoinedStr):
        results = [
            _classify_target(v.value, fn, index, depth + 1)
            for v in target.values if isinstance(v, ast.FormattedValue)
        ]
        if any(r[0] == REVIEW_REQUIRED for r in results):
            return REVIEW_REQUIRED, "f-string interpolates externally controlled input"
        if any(r[0] == UNDETERMINED for r in results):
            return UNDETERMINED, "f-string interpolates a value that could not be traced"
        return SELF_SCOPED, "f-string is built from module-local values"

    if isinstance(target, ast.BinOp):
        left = _classify_target(target.left, fn, index, depth + 1)
        right = _classify_target(target.right, fn, index, depth + 1)
        for r in (left, right):
            if r[0] == REVIEW_REQUIRED:
                return REVIEW_REQUIRED, "path is concatenated from externally controlled parts"
        if left[0] == SELF_SCOPED and right[0] == SELF_SCOPED:
            return SELF_SCOPED, "path is concatenated from module-local parts"
        return UNDETERMINED, "path is concatenated from a part that could not be traced"

    return UNDETERMINED, f"target is a {type(target).__name__}, not traced"


# ---------------------------------------------------------------------- the scan

def _has_containment_guard(fn) -> bool:
    """Heuristic: does this function resolve a path and refuse on a bad one?

    The shape being recognised is realpath/abspath + a raise -- i.e. "resolve
    the target, check it is inside my directory, refuse otherwise". It is a
    heuristic and can be fooled, which is why it only ever DOWNGRADES a write.
    A destructive delete is never downgraded by it: removing a caller-supplied
    path stays REVIEW_REQUIRED whatever guards surround it.
    """
    if fn is None:
        return False
    resolves = False
    refuses = False
    for node in ast.walk(fn):
        if isinstance(node, ast.Call):
            name = dotted_name(node.func) or ""
            if name.split(".")[-1] in {"realpath", "abspath", "commonpath", "relpath"}:
                resolves = True
        elif isinstance(node, ast.Raise):
            refuses = True
    return resolves and refuses


def is_test_module(module_path: str) -> bool:
    base = os.path.basename(module_path)
    return base.startswith("test_") or base.endswith("_test.py") or "/tests/" in module_path


def scan_source(source: str, lane: str, module: str) -> ModuleReport:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return ModuleReport(lane, module, False, parse_error=f"{exc.msg} (line {exc.lineno})")

    index = _FunctionIndex(tree)
    in_test = is_test_module(module)
    report = ModuleReport(lane, module, True)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = dotted_name(node.func)
        if name is None:
            continue
        leaf = name.rsplit(".", 1)[-1]
        fn = index.enclosing.get(node)

        if leaf in DESTRUCTIVE_LEAF or name in DESTRUCTIVE_DOTTED:
            target = node.args[0] if node.args else None
            cls, why = _classify_target(target, fn, index)
            if in_test and cls != REVIEW_REQUIRED:
                cls, why = TEST_CONTEXT, f"in a test module; {why}"
            report.findings.append(Finding(
                lane, module, node.lineno, DESTRUCTIVE, name, cls, expr_text(target), why))

        elif name in OPAQUE_DOTTED or (leaf in {"run", "call", "Popen"} and name.startswith("subprocess")):
            cls = TEST_CONTEXT if in_test else UNDETERMINED
            report.findings.append(Finding(
                lane, module, node.lineno, OPAQUE, name, cls,
                expr_text(node.args[0] if node.args else None),
                "shells out; what runs inside is not visible to this screen"))

        elif isinstance(node.func, ast.Name) and node.func.id == "open":
            mode = ""
            if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                mode = str(node.args[1].value)
            for kw in node.keywords:
                if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                    mode = str(kw.value.value)
            if set(mode) & WRITE_MODE_CHARS:
                target = node.args[0] if node.args else None
                cls, why = _classify_target(target, fn, index)
                if cls == REVIEW_REQUIRED:
                    if _has_containment_guard(fn):
                        cls = SELF_SCOPED
                        why = ("write target is caller-supplied, but the function "
                               "resolves the path and raises on one outside its "
                               "directory (heuristic)")
                    else:
                        # A write creates or overwrites; a delete removes a tree.
                        # Both deserve a look, but conflating them makes the
                        # report unreadable, so writes get their own class.
                        cls = WRITE_TO_CALLER_PATH
                        why = (f"writes to a caller-supplied path; {why}. Normal "
                               "for a CLI with an output option -- confirm it "
                               "cannot be pointed at evidence you must keep")
                if in_test and cls not in (REVIEW_REQUIRED,):
                    cls, why = TEST_CONTEXT, f"in a test module; {why}"
                report.findings.append(Finding(
                    lane, module, node.lineno, UNGUARDED_WRITE, f"open(mode={mode!r})",
                    cls, expr_text(target), why))
    return report


def scan_tree(root: str, lane_prefix: str = "") -> list:
    """Walk `root`, parse every .py file, return ModuleReports. Read-only."""
    reports = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in
                             {"__pycache__", ".git", ".pytest_cache", "node_modules"})
        for filename in sorted(filenames):
            if not filename.endswith(".py"):
                continue
            full = os.path.join(dirpath, filename)
            rel = os.path.relpath(full, root)
            lane = rel.split(os.sep)[0] if os.sep in rel else os.path.basename(root)
            if lane_prefix and not lane.startswith(lane_prefix):
                continue
            try:
                with open(full, "r", encoding="utf-8") as fh:   # read-only
                    source = fh.read()
            except (OSError, UnicodeDecodeError) as exc:
                reports.append(ModuleReport(lane, rel, False,
                                            parse_error=f"unreadable: {exc.__class__.__name__}"))
                continue
            reports.append(scan_source(source, lane, rel))
    return reports


def summarize(reports: list) -> dict:
    by_status = {}
    for r in reports:
        by_status[r.status] = by_status.get(r.status, 0) + 1
    lanes = {}
    for r in reports:
        worst = lanes.get(r.lane)
        order = list(SEVERITY_ORDER) + [UNPARSEABLE, CLEAN]
        if worst is None or order.index(r.status) < order.index(worst):
            lanes[r.lane] = r.status
    return {
        "modules_scanned": len(reports),
        "lanes_scanned": len(lanes),
        "modules_by_status": dict(sorted(by_status.items())),
        "lanes_by_status": dict(sorted(lanes.items())),
        "findings": sum(len(r.findings) for r in reports),
        "review_required": sum(
            1 for r in reports for f in r.findings if f.classification == REVIEW_REQUIRED),
        "undetermined": sum(
            1 for r in reports for f in r.findings if f.classification == UNDETERMINED),
    }
