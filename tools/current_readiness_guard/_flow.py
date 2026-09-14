from ._model import *

def _always_exits(statements: Sequence[ast.stmt]) -> bool:
    if not statements:
        return False
    for statement in statements:
        if isinstance(statement, (ast.Return, ast.Raise)):
            return True
        if isinstance(statement, ast.If) and statement.orelse:
            if _always_exits(statement.body) and _always_exits(statement.orelse):
                return True
    return False


def _same_module_calls(node: ast.AST | None, function_names: set[str]) -> list[ast.Call]:
    if node is None:
        return []
    return [
        child
        for child in ast.walk(node)
        if isinstance(child, ast.Call) and _name(child.func) in function_names
    ]


def _collect_positive_paths(
    statements: Sequence[ast.stmt],
    *,
    facts: frozenset[str],
    authority_params: set[str],
    defs: Mapping[str, ast.AST],
    globals_: Mapping[str, str],
    function_names: set[str],
) -> tuple[list[frozenset[str]], list[_CallSite], bool, frozenset[str]]:
    requirements: list[frozenset[str]] = []
    calls: list[_CallSite] = []
    current = set(facts)
    for statement in statements:
        if isinstance(statement, ast.Return):
            expanded = _expand_expr(statement.value, defs)
            if _contains_positive(expanded, defs, globals_):
                requirements.append(frozenset(current))
            for call in _same_module_calls(expanded, function_names):
                calls.append(_CallSite(_name(call.func), call, frozenset(current)))
            return requirements, calls, False, frozenset(current)
        if isinstance(statement, ast.Raise):
            return requirements, calls, False, frozenset(current)
        if isinstance(statement, ast.If):
            true_facts = frozenset(current | _condition_authority_facts(statement.test, authority_params, truth=True))
            false_facts = frozenset(current | _condition_authority_facts(statement.test, authority_params, truth=False))
            body_req, body_calls, body_fall, body_end = _collect_positive_paths(
                statement.body,
                facts=true_facts,
                authority_params=authority_params,
                defs=defs,
                globals_=globals_,
                function_names=function_names,
            )
            if statement.orelse:
                else_req, else_calls, else_fall, else_end = _collect_positive_paths(
                    statement.orelse,
                    facts=false_facts,
                    authority_params=authority_params,
                    defs=defs,
                    globals_=globals_,
                    function_names=function_names,
                )
            else:
                else_req, else_calls, else_fall, else_end = [], [], True, false_facts
            requirements.extend(body_req)
            requirements.extend(else_req)
            calls.extend(body_calls)
            calls.extend(else_calls)
            if body_fall and else_fall:
                current = set(body_end & else_end)
            elif body_fall:
                current = set(body_end)
            elif else_fall:
                current = set(else_end)
            else:
                return requirements, calls, False, frozenset(current)
            continue
        if isinstance(statement, (ast.For, ast.AsyncFor, ast.While, ast.Try, ast.With, ast.AsyncWith, ast.Match)):
            nested_blocks: list[Sequence[ast.stmt]] = []
            if hasattr(statement, "body"):
                nested_blocks.append(statement.body)
            if hasattr(statement, "orelse"):
                nested_blocks.append(statement.orelse)
            if isinstance(statement, ast.Try):
                nested_blocks.extend(handler.body for handler in statement.handlers)
                nested_blocks.append(statement.finalbody)
            if isinstance(statement, ast.Match):
                nested_blocks.extend(case.body for case in statement.cases)
            for block in nested_blocks:
                req, nested_calls, _, _ = _collect_positive_paths(
                    block,
                    facts=frozenset(current),
                    authority_params=authority_params,
                    defs=defs,
                    globals_=globals_,
                    function_names=function_names,
                )
                requirements.extend(req)
                calls.extend(nested_calls)
    return requirements, calls, True, frozenset(current)


def _assignment_targets(node: ast.AST) -> list[str]:
    targets: list[ast.AST] = []
    if isinstance(node, ast.Assign):
        targets.extend(node.targets)
    elif isinstance(node, (ast.AnnAssign, ast.NamedExpr)):
        targets.append(node.target)

    def names(target: ast.AST) -> list[str]:
        if isinstance(target, ast.Name):
            return [target.id]
        if isinstance(target, (ast.Tuple, ast.List)):
            out: list[str] = []
            for item in target.elts:
                out.extend(names(item))
            return out
        return []

    out: list[str] = []
    for target in targets:
        out.extend(names(target))
    return out


def _assignment_value(node: ast.AST) -> ast.AST | None:
    if isinstance(node, ast.Assign):
        return node.value
    if isinstance(node, ast.AnnAssign):
        return node.value
    if isinstance(node, ast.NamedExpr):
        return node.value
    return None


def _trusted_clock_call(node: ast.Call) -> bool:
    name = _name(node.func).lower()
    if name in {"datetime.now", "datetime.utcnow", "time.time", "time.time_ns", "_process_now"}:
        return True
    if name.endswith(".datetime.now") or name.endswith(".datetime.utcnow"):
        return True
    return name.endswith("process_now") or name.endswith("current_utc") or name.endswith("utc_now")


def _expr_sources(
    node: ast.AST | None,
    *,
    params: set[str],
    origins: Mapping[str, set[str]],
    defs: Mapping[str, ast.AST],
    seen: frozenset[str] = frozenset(),
) -> set[str]:
    node = _expand_expr(node, defs, seen=seen)
    if node is None:
        return set()
    if isinstance(node, ast.Name):
        if node.id in origins:
            return set(origins[node.id])
        if node.id in params:
            return {node.id}
        return set()
    if isinstance(node, ast.Call):
        if _trusted_clock_call(node):
            return {_PROCESS_CLOCK}
        out = _expr_sources(node.func, params=params, origins=origins, defs=defs, seen=seen)
        for arg in node.args:
            out |= _expr_sources(arg, params=params, origins=origins, defs=defs, seen=seen)
        for keyword in node.keywords:
            out |= _expr_sources(keyword.value, params=params, origins=origins, defs=defs, seen=seen)
        return out
    out: set[str] = set()
    for child in ast.iter_child_nodes(node):
        out |= _expr_sources(child, params=params, origins=origins, defs=defs, seen=seen)
    return out


def _origins(fn: ast.FunctionDef | ast.AsyncFunctionDef, defs: Mapping[str, ast.AST]) -> dict[str, set[str]]:
    params = set(_function_params(fn))
    out: dict[str, set[str]] = {name: {name} for name in params}
    for _ in range(12):
        changed = False
        for node in ast.walk(fn):
            value = _assignment_value(node)
            if value is None:
                continue
            sources = _expr_sources(value, params=params, origins=out, defs=defs)
            for target in _assignment_targets(node):
                before = set(out.get(target, set()))
                merged = before | sources
                if merged != before:
                    out[target] = merged
                    changed = True
        if not changed:
            break
    return out


def _deadline_expr(node: ast.AST) -> bool:
    return _has_word(node, _DEADLINE_WORDS)


def _direct_time_requirements(
    fn: ast.FunctionDef | ast.AsyncFunctionDef,
    defs: Mapping[str, ast.AST],
) -> list[frozenset[str]]:
    params = set(_function_params(fn))
    origins = _origins(fn, defs)
    out: list[frozenset[str]] = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.Compare):
            continue
        operands = [node.left, *node.comparators]
        for left in operands:
            sources = _expr_sources(left, params=params, origins=origins, defs=defs)
            caller_sources = frozenset(source for source in sources if source in params)
            if not caller_sources:
                continue
            if any(right is not left and _deadline_expr(right) for right in operands):
                out.append(caller_sources)
                break
    return out


def _call_argument(call: ast.Call, callee: _FunctionModel, parameter: str) -> ast.AST | None:
    try:
        index = callee.params.index(parameter)
    except ValueError:
        return None
    if index < len(call.args):
        return call.args[index]
    for keyword in call.keywords:
        if keyword.arg == parameter:
            return keyword.value
    return None


def _projection_call(call: ast.Call) -> bool:
    name = _name(call.func).lower()
    return any(
        word in name
        for word in ("compile", "evaluate", "qualify", "project", "semantic", "readiness", "gate", "state")
    )


def _retained_time_argument(call: ast.Call, *, params: set[str], origins: Mapping[str, set[str]], defs: Mapping[str, ast.AST]) -> bool:
    for keyword in call.keywords:
        sources = _expr_sources(keyword.value, params=params, origins=origins, defs=defs)
        if sources & params and (
            keyword.arg is not None and any(word in keyword.arg.lower() for word in _TIME_WORDS)
            or _has_word(keyword.value, _TIME_WORDS)
        ):
            return True
    for argument in call.args:
        sources = _expr_sources(argument, params=params, origins=origins, defs=defs)
        if sources & params and _has_word(argument, _TIME_WORDS):
            return True
    return False


def _process_projection_result_used(
    fn: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    params: set[str],
    origins: Mapping[str, set[str]],
    defs: Mapping[str, ast.AST],
) -> bool:
    process_targets: set[str] = set()
    for node in ast.walk(fn):
        value = _assignment_value(node)
        if not isinstance(value, ast.Call) or not _projection_call(value):
            continue
        supplied = [*value.args, *(keyword.value for keyword in value.keywords)]
        if any(
            _PROCESS_CLOCK in _expr_sources(arg, params=params, origins=origins, defs=defs)
            for arg in supplied
        ):
            process_targets.update(_assignment_targets(node))
    for node in ast.walk(fn):
        if isinstance(node, ast.Return):
            if any(isinstance(child, ast.Name) and child.id in process_targets for child in ast.walk(node)):
                return True
            if isinstance(node.value, ast.Call) and _projection_call(node.value):
                supplied = [*node.value.args, *(keyword.value for keyword in node.value.keywords)]
                if any(
                    _PROCESS_CLOCK in _expr_sources(arg, params=params, origins=origins, defs=defs)
                    for arg in supplied
                ):
                    return True
    return False


def _direct_retained_replay(fn: ast.FunctionDef | ast.AsyncFunctionDef, defs: Mapping[str, ast.AST]) -> bool:
    params = set(_function_params(fn))
    origins = _origins(fn, defs)
    retained = any(
        isinstance(node, ast.Call)
        and _projection_call(node)
        and _retained_time_argument(node, params=params, origins=origins, defs=defs)
        for node in ast.walk(fn)
    )
    if not retained:
        return False
    return not _process_projection_result_used(fn, params=params, origins=origins, defs=defs)


__all__ = [name for name in globals() if not name.startswith("__")]
