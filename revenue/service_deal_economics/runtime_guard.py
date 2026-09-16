from __future__ import annotations

from types import FunctionType, ModuleType
from typing import Any, Callable, Iterable


_MISSING = object()


def freeze_call_graph(
    *roots: Callable[..., Any],
    bindings: Iterable[tuple[object, str]] = (),
) -> Callable[[], bool]:
    """Capture the reachable Python call graph and return an integrity guard.

    The guard records identities of every global used by the supplied Python
    function roots. When a reachable global is a module or class, attributes
    named by that function's bytecode are captured too; Python function-valued
    attributes are traversed recursively. This closes the common "stable
    function object, mutable __globals__" hole without making historical/test
    helpers inaccessible.

    The returned function keeps all snapshots in closure cells and uses only
    captured builtins while checking them, so rebinding this module after import
    cannot bless a modified authority graph.
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
                # co_names contains both global and attribute names. Capturing
                # matching attributes is intentionally conservative: a benign
                # unrelated rebind may fail closed, but cannot mint CURRENT.
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

    def intact(
        _globals: tuple[tuple[dict[str, Any], str, object], ...] = globals_snapshot,
        _attrs: tuple[tuple[object, str, object, bool], ...] = attrs_snapshot,
        _funcs: tuple[tuple[FunctionType, object, object, object], ...] = functions_snapshot,
        _missing: object = missing,
        _getattr: Callable[[object, str, object], object] = getattr,
        _vars: Callable[[object], dict[str, Any]] = vars,
    ) -> bool:
        for namespace, name, expected in _globals:
            if namespace.get(name, _missing) is not expected:
                return False
        for owner, name, expected, is_namespace in _attrs:
            if is_namespace:
                actual = _vars(owner).get(name, _missing)
            else:
                actual = _getattr(owner, name, _missing)
            if actual is not expected:
                return False
        for fn, code, defaults, kwdefaults in _funcs:
            if fn.__code__ is not code or fn.__defaults__ is not defaults or fn.__kwdefaults__ is not kwdefaults:
                return False
        return True

    return intact
