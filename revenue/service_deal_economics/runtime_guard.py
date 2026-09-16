from __future__ import annotations

from types import FunctionType, ModuleType
from typing import Any, Callable, Iterable


_MISSING = object()


def freeze_call_graph(
    *roots: Callable[..., Any],
    bindings: Iterable[tuple[object, str]] = (),
) -> Callable[[], bool]:
    """Capture a transitive Python call graph and return a closure-only guard.

    Globals and referenced module attributes are identity-bound selectively.
    Reachable class/instance namespaces are also snapshotted so a stable object
    cannot hide an in-place replacement of an authority-bearing method (for
    example ``json.JSONEncoder.encode``, a cached JSON encoder method, or
    ``hmac.HMAC.__init__``).

    Whole module namespaces are deliberately *not* snapshotted: this module
    installs guarded public CURRENT wrappers after capture, and unrelated module
    names may legitimately appear later. Authority-bearing module attributes are
    already covered by the selective global/attribute bindings below.

    The returned guard accepts no arguments. Snapshots and check primitives are
    held only in closure cells, so callers cannot inject alternate trust/time
    dependencies through keyword/default parameters.
    """

    global_bindings: list[tuple[dict[str, Any], str, object]] = []
    attr_bindings: list[tuple[object, str, object, bool]] = []
    function_bindings: list[tuple[FunctionType, object, object, object]] = []
    namespace_bindings: list[tuple[object, tuple[tuple[str, object], ...]]] = []
    seen_globals: set[tuple[int, str]] = set()
    seen_attrs: set[tuple[int, str, bool]] = set()
    seen_functions: set[int] = set()
    seen_namespaces: set[int] = set()

    def capture_namespace(owner: object) -> None:
        if isinstance(owner, (FunctionType, ModuleType)):
            return
        marker = id(owner)
        if marker in seen_namespaces:
            return
        try:
            namespace = vars(owner)
        except TypeError:
            return
        seen_namespaces.add(marker)
        namespace_bindings.append((owner, tuple(namespace.items())))

    def capture_attr(owner: object, name: str) -> object:
        is_namespace = isinstance(owner, (ModuleType, type))
        key = (id(owner), name, is_namespace)
        if key in seen_attrs:
            if is_namespace:
                return vars(owner).get(name, _MISSING)
            return getattr(owner, name, _MISSING)
        seen_attrs.add(key)
        capture_namespace(owner)
        if is_namespace:
            value = vars(owner).get(name, _MISSING)
        else:
            value = getattr(owner, name, _MISSING)
        attr_bindings.append((owner, name, value, is_namespace))
        capture_namespace(value)
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
            capture_namespace(value)
            if isinstance(value, FunctionType):
                capture_function(value)
            elif isinstance(value, (ModuleType, type)):
                # co_names mixes global and attribute names. Conservative
                # over-binding is intentional: an irrelevant monkeypatch may
                # fail closed, but a mutated trust dependency cannot mint CURRENT.
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
    namespaces_snapshot = tuple(namespace_bindings)
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
        for owner, expected_items in namespaces_snapshot:
            try:
                current = get_vars(owner)
            except TypeError:
                return False
            if len(current) != len(expected_items):
                return False
            for name, expected in expected_items:
                if current.get(name, missing) is not expected:
                    return False
        return True

    return intact
