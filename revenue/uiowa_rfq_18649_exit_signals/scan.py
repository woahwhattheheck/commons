"""Read-only AST scan: can this tool signal a finding to whoever runs it?

Nothing here executes, imports or modifies the code it reads. It parses source and
answers one question per entrypoint, and refuses to guess when it cannot answer.

Classes
    GATE           a non-zero exit is reachable from the entrypoint
    REPORT_ONLY    no non-zero exit path exists; it always returns 0
    INDETERMINATE  an exit value could not be resolved statically

INDETERMINATE is not a rounding error, it is the point. The engagement rule is that
missing evidence stays UNKNOWN, and that applies to this tool's own output: a
`sys.exit(compute())` whose value cannot be resolved is NOT reported as a gate and
NOT reported as report-only.

Two things it deliberately does not treat as a signal:

  * a `sys.exit(1)` in unreachable code. A naive "does the source contain exit(1)"
    check calls that a gate. It is dead text. There is a fixture for it.
  * an uncaught exception. A crash also exits non-zero, but it says the tool broke,
    not that the subject has findings. Reported separately as CRASH_AS_SIGNAL.

Stated limitation, not buried: reachability here is SHALLOW. It detects statements
made dead by an unconditional terminator earlier in the same block, and resolves
`sys.exit(f())` one level into a same-module function. It does not do interprocedural
or path-sensitive analysis. Anything it cannot resolve becomes INDETERMINATE rather
than an assumption in either direction.
"""

import ast
import os
import re

GATE = "GATE"
REPORT_ONLY = "REPORT_ONLY"
INDETERMINATE = "INDETERMINATE"

# Words that, printed to stdout, mean the tool believes something is wrong.
FAILURE_VOCABULARY = (
    "fail", "error", "missing", "broken", "unresolved", "invalid", "reject",
    "violation", "overdue", "conflict", "not found", "mismatch", "overclaim",
    "insufficient", "discarded",
)
_FAILURE_RE = re.compile("|".join(re.escape(word) for word in FAILURE_VOCABULARY),
                         re.IGNORECASE)

TERMINATORS = (ast.Return, ast.Raise, ast.Continue, ast.Break)


# ------------------------------------------------------------- dead-code marking

def _mark_dead(tree):
    """Attach `_dead` to every statement unreachable because an earlier statement
    in the same block unconditionally left it."""
    def walk_block(statements, dead_already):
        dead = dead_already
        for statement in statements:
            statement._dead = dead
            if not dead and _is_terminator(statement):
                dead = True
            for field in ("body", "orelse", "finalbody"):
                inner = getattr(statement, field, None)
                if isinstance(inner, list):
                    walk_block(inner, statement._dead)
            for handler in getattr(statement, "handlers", []) or []:
                handler._dead = statement._dead
                walk_block(handler.body, statement._dead)
        return dead

    for node in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            inner = getattr(node, field, None)
            if isinstance(inner, list) and inner and not hasattr(inner[0], "_dead"):
                walk_block(inner, False)
    return tree


def _is_terminator(statement):
    if isinstance(statement, TERMINATORS):
        return True
    if isinstance(statement, ast.Expr) and _exit_call(statement.value) is not None:
        return True
    return False


def _exit_call(node):
    """Return the exit call node if this expression is sys.exit()/exit()/SystemExit."""
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr == "exit":
        if isinstance(func.value, ast.Name) and func.value.id in ("sys", "os"):
            return node
    if isinstance(func, ast.Name) and func.id in ("exit", "SystemExit"):
        return node
    return None


# ------------------------------------------------------------- value resolution

def _const_int(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, bool):
        return int(node.value)
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if isinstance(node, ast.Constant) and node.value is None:
        return 0
    return None


def _function_returns(tree, name):
    """Non-dead return values of a top-level function, as (ints, unresolved_count)."""
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            ints, unresolved = [], 0
            for inner in ast.walk(node):
                if isinstance(inner, ast.Return) and not getattr(inner, "_dead", False):
                    if inner.value is None:
                        ints.append(0)
                        continue
                    value = _const_int(inner.value)
                    if value is None:
                        unresolved += 1
                    else:
                        ints.append(value)
            return ints, unresolved
    return None, 0


# ------------------------------------------------------------------ the scan

def scan_source(source, tool_name="(source)"):
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return {"tool": tool_name, "classification": INDETERMINATE,
                "reason": f"source did not parse: {exc}",
                "has_main_guard": False, "emits_contract_status": False,
                "dead_nonzero_exits": 0, "unresolved_exits": 0,
                "raises_uncaught": False, "failure_vocabulary_printed": [],
                "findings": [{"code": "UNPARSEABLE", "detail": str(exc)}]}

    _mark_dead(tree)

    has_main_guard = any(
        isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name) and node.test.left.id == "__name__"
        for node in tree.body)

    reachable_nonzero = False
    dead_nonzero = 0
    unresolved = 0

    for node in ast.walk(tree):
        call = _exit_call(node)
        if call is None:
            continue
        dead = getattr(node, "_dead", False) or _enclosing_dead(tree, node)
        if not call.args:
            continue  # sys.exit() with no argument is exit 0
        value = _const_int(call.args[0])
        if value is None:
            # sys.exit(main()) -- resolve one level into a same-module function.
            argument = call.args[0]
            if isinstance(argument, ast.Call) and isinstance(argument.func, ast.Name):
                ints, inner_unresolved = _function_returns(tree, argument.func.id)
                if ints is None:
                    unresolved += 1
                    continue
                if any(code != 0 for code in ints) and not dead:
                    reachable_nonzero = True
                if inner_unresolved:
                    unresolved += inner_unresolved
                continue
            unresolved += 1
            continue
        if value != 0:
            if dead:
                dead_nonzero += 1
            else:
                reachable_nonzero = True

    printed = _printed_failure_words(tree)
    emits_status = _emits_contract_status(tree, source)

    if reachable_nonzero:
        classification = GATE
        reason = "a non-zero exit is reachable from the entrypoint"
    elif unresolved:
        classification = INDETERMINATE
        reason = (f"{unresolved} exit value(s) could not be resolved statically; "
                  f"not assumed to be a gate and not assumed to be report-only")
    else:
        classification = REPORT_ONLY
        reason = "no reachable non-zero exit path was found"

    raises_uncaught = _has_uncaught_raise(tree)

    findings = []
    if classification == REPORT_ONLY:
        if printed:
            findings.append({
                "code": "FALSE_CLEAN",
                "severity": "HIGH",
                "detail": f"prints failure vocabulary ({', '.join(sorted(set(printed))[:4])}) "
                          f"but always exits 0, so a runner records a clean result "
                          f"for a run that reported a problem",
                "remedy": "return a non-zero code on the same condition, or wrap the "
                          "tool with wrap.py and declare a fallback rule",
            })
        else:
            findings.append({
                "code": "NO_SIGNAL_PATH",
                "severity": "MEDIUM",
                "detail": "cannot return non-zero under any input; indistinguishable "
                          "from a clean run by anything except a human reading stdout",
                "remedy": "adopt contract.emit(), or wrap the tool with wrap.py",
            })
        if raises_uncaught:
            findings.append({
                "code": "CRASH_AS_SIGNAL",
                "severity": "LOW",
                "detail": "the only non-zero exit available is an uncaught exception; "
                          "a crash says the tool broke, not that the subject has findings",
                "remedy": "distinguish INPUT_ERROR (code 2) from FINDINGS (code 1)",
            })
    if dead_nonzero:
        findings.append({
            "code": "DEAD_GATE",
            "severity": "HIGH",
            "detail": f"{dead_nonzero} non-zero exit(s) sit in unreachable code; a "
                      f"grep-based check would report this tool as gated",
            "remedy": "remove the dead branch or restore the path that reaches it",
        })
    if classification == INDETERMINATE:
        if emits_status:
            # Found while running the fixtures: t_contract.py is statically
            # unresolvable (it exits with a function's return value) and yet a runner
            # has nothing to infer, because the tool states its own status at runtime.
            # Reporting that as a defect would push authors away from the contract.
            findings.append({
                "code": "RUNTIME_DECLARED_STATUS",
                "severity": "INFO",
                "detail": "exit value is not statically resolvable, but the tool emits "
                          "a KIT-STATUS line, so a runner reads its status rather than "
                          "inferring one",
                "remedy": "none; this is the intended shape",
            })
        else:
            findings.append({
                "code": "UNRESOLVED_EXIT",
                "severity": "MEDIUM",
                "detail": reason,
                "remedy": "exit with a literal contract code, or emit a KIT-STATUS line "
                          "a runner can read instead of inferring",
            })
    if not emits_status:
        findings.append({
            "code": "NO_CONTRACT_LINE",
            "severity": "INFO",
            "detail": "emits no KIT-STATUS line, so a runner must infer meaning from "
                      "the exit code alone",
            "remedy": "call contract.emit() before returning",
        })

    return {
        "tool": tool_name,
        "classification": classification,
        "reason": reason,
        "has_main_guard": has_main_guard,
        "emits_contract_status": emits_status,
        "dead_nonzero_exits": dead_nonzero,
        "unresolved_exits": unresolved,
        "raises_uncaught": raises_uncaught,
        "failure_vocabulary_printed": sorted(set(printed)),
        "findings": findings,
    }


def _enclosing_dead(tree, target):
    for node in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            block = getattr(node, field, None)
            if not isinstance(block, list):
                continue
            for statement in block:
                if getattr(statement, "_dead", False):
                    for inner in ast.walk(statement):
                        if inner is target:
                            return True
    return False


# Emitting the status line through contract.emit()/status_line() leaves no literal
# "KIT-STATUS" in the caller's source. A substring check therefore reported
# contract-conformant tools -- audit_kit.py among them -- as having no contract line.
# Found by test_auditor_scan_of_itself_is_classified on the first run.
_CONTRACT_EMITTERS = ("emit", "status_line")


def _emits_contract_status(tree, source):
    if "KIT-STATUS" in source:
        return True
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or getattr(node, "_dead", False):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in _CONTRACT_EMITTERS:
            if isinstance(func.value, ast.Name) and func.value.id == "contract":
                return True
        if isinstance(func, ast.Name) and func.id in _CONTRACT_EMITTERS \
                and "contract" in source:
            return True
    return False


def _printed_failure_words(tree):
    words = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "print"):
            continue
        if getattr(node, "_dead", False):
            continue
        for argument in node.args:
            for piece in ast.walk(argument):
                if isinstance(piece, ast.Constant) and isinstance(piece.value, str):
                    words.extend(match.group(0).lower()
                                 for match in _FAILURE_RE.finditer(piece.value))
    return words


def _has_uncaught_raise(tree):
    handled = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            for inner in ast.walk(node):
                if isinstance(inner, ast.Raise):
                    handled.add(id(inner))
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise) and id(node) not in handled \
                and not getattr(node, "_dead", False):
            return True
    return False


def scan_file(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            source = handle.read()
    except (OSError, UnicodeDecodeError) as exc:
        return {"tool": path, "classification": INDETERMINATE,
                "reason": f"unreadable: {exc}", "has_main_guard": False,
                "emits_contract_status": False, "dead_nonzero_exits": 0,
                "unresolved_exits": 0, "raises_uncaught": False,
                "failure_vocabulary_printed": [],
                "findings": [{"code": "UNREADABLE", "severity": "MEDIUM",
                              "detail": str(exc), "remedy": "check file encoding"}]}
    return scan_source(source, tool_name=path)


def scan_tree(root, lane_prefix=None):
    """Scan every Python entrypoint under root. Read-only; opens nothing else.

    lane_prefix restricts the scan to top-level directories whose name starts with
    it, so an audit can be scoped to one engagement's lanes inside a larger repo.
    """
    results, skipped = [], 0
    for directory, subdirs, filenames in os.walk(root):
        subdirs[:] = [d for d in subdirs if d not in ("__pycache__", ".git")]
        if lane_prefix and os.path.abspath(directory) == os.path.abspath(root):
            subdirs[:] = [d for d in subdirs if d.startswith(lane_prefix)]
        if os.path.basename(directory).startswith("."):
            continue
        for filename in sorted(filenames):
            if not filename.endswith(".py"):
                continue
            path = os.path.join(directory, filename)
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    source = handle.read()
            except (OSError, UnicodeDecodeError):
                results.append(scan_file(path))
                continue
            if "__main__" not in source:
                skipped += 1
                continue
            result = scan_source(source, tool_name=os.path.relpath(path, root))
            result["lane"] = os.path.relpath(directory, root).split(os.sep)[0]
            results.append(result)
    return {"root": root, "lane_prefix": lane_prefix or "",
            "entrypoints": results,
            "non_entrypoint_files_skipped": skipped}
