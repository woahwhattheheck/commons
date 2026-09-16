from __future__ import annotations

from types import FunctionType, ModuleType
from typing import Any, Callable, Iterable


_MISSING = object()


def freeze_call_graph(
    *roots: Callable[..., Any],
    bindings: Iterable[tuple[object, str]] = (),
) -> Callable[[], bool]:
    """Capture a transitive Python call graph and return a closure-only guard.

    Every global used by the supplied Python function roots is identity-bound.
    Module/class attributes named by bytecode are identity-bound too, and any
    Python function-valued dependency is traversed recursively. This detects the
    important case where a stable function object still resolves mutable values
    from its live ``__globals__`` mapping.

    The returned guard accepts no arguments and keeps its snapshots plus the
    builtins it needs in closure cells, so callers cannot supply alternate
    snapshots/check primitives through Python keyword/default injection.
    """

    global_bindings: list[tuple[dict[str, Any], str, object]] = []
    attr_bindings: list[tuple[object, str, object, bool]] = []
    function_bindings: list[tuple[FunctionType, object, object, object]] = []
    seen_globals: set[tuple[int, str]] = set()
    seen_attrs: set[tuple[int, str, bool]] = set()
    seen_functions: set[int] = set()

    def capture_attr(owner: object, name: str) -> object:
        is_namespace = isinstance(owner, (ModuleType, type))
        key = (id(owner), name, is_namespace)
        if key in seen_attrs:
            if is_namespace:
                return vars(owner).get(name, _MISSING)
            return getattr(owner, name, _MISSING)
        seen_attrs.add(key)
        if is_namespace:
            value = vars(owner).get(name, _MISSING)
        else:
            value = getattr(owner, name, _MISSING)
        attr_bindings.append((owner, name, value, is_namespace))
        if isinstance(value, FunctionType):
            capture_function(value)
        return value

    def capture_function(fn: FunctionType) -> None:
        marker = id(fn)
        if marker in seen_functions:
            return
        seen_functions.add(marker)
        function_bindings.append((fn, fn.__code__, fn.__defaults__, fn.__kwdefaults__))
        names = tuple(fn.__code__.co_names)
        namespace = fn.__globals__
        for name in names:
            if name not in namespace:
                continue
            value = namespace[name]
            gkey = (id(namespace), name)
            if gkey not in seen_globals:
                seen_globals.add(gkey)
                global_bindings.append((namespace, name, value))
            if isinstance(value, FunctionType):
                capture_function(value)
            elif isinstance(value, (ModuleType, type)):
                # co_names mixes global and attribute names. Conservative
                # over-binding is intentional: it may fail closed on an
                # irrelevant monkeypatch, but it cannot mint CURRENT.
                for attr_name in names:
                    if attr_name == name:
                        continue
                    if attr_name in vars(value) or hasattr(value, attr_name):
                        capture_attr(value, attr_name)

    for root in roots:
        if not isinstance(root, FunctionType):
            raise TypeError("freeze_call_graph roots must be Python functions")
        capture_function(root)
    for owner, name in tuple(bindings):
        capture_attr(owner, name)

    globals_snapshot = tuple(global_bindings)
    attrs_snapshot = tuple(attr_bindings)
    functions_snapshot = tuple(function_bindings)
    missing = _MISSING
    get_attr = getattr
    get_vars = vars

    def intact() -> bool:
        for namespace, name, expected in globals_snapshot:
            if namespace.get(name, missing) is not expected:
                return False
        for owner, name, expected, is_namespace in attrs_snapshot:
            if is_namespace:
                actual = get_vars(owner).get(name, missing)
            else:
                actual = get_attr(owner, name, missing)
            if actual is not expected:
                return False
        for fn, code, defaults, kwdefaults in functions_snapshot:
            if fn.__code__ is not code or fn.__defaults__ is not defaults or fn.__kwdefaults__ is not kwdefaults:
                return False
        return True

    return intact
