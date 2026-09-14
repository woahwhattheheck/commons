from ._model import *
from ._flow import *

class _Analyzer:
    def __init__(self, tree: ast.Module, path: str):
        self.tree = tree
        self.path = path
        self.globals = _module_string_constants(tree)
        self.functions: dict[str, _FunctionModel] = {}
        top_level = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        function_names = {node.name for node in top_level}
        for fn in top_level:
            params = _function_params(fn)
            authority_params = {name for name in params if _authority_name(name)}
            defs = _local_defs(fn)
            direct, returned_calls, _, _ = _collect_positive_paths(
                fn.body,
                facts=frozenset(),
                authority_params=authority_params,
                defs=defs,
                globals_=self.globals,
                function_names=function_names,
            )
            self.functions[fn.name] = _FunctionModel(
                node=fn,
                params=params,
                authority_params=authority_params,
                local_defs=defs,
                direct_positive_requirements=direct,
                returned_calls=returned_calls,
                all_calls=[
                    call
                    for call in ast.walk(fn)
                    if isinstance(call, ast.Call) and _name(call.func) in function_names
                ],
                direct_time_requirements=_direct_time_requirements(fn, defs),
                direct_retained_replay=_direct_retained_replay(fn, defs),
            )
        self._positive_cache: dict[str, list[frozenset[str]]] = {}
        self._time_cache: dict[str, list[frozenset[str]]] = {}
        self._replay_cache: dict[str, bool] = {}

    def _map_requirements(
        self,
        caller: _FunctionModel,
        call: ast.Call,
        callee: _FunctionModel,
        requirements: Iterable[frozenset[str]],
        facts: frozenset[str] = frozenset(),
    ) -> list[frozenset[str]]:
        params = set(caller.params)
        origins = _origins(caller.node, caller.local_defs)
        out: list[frozenset[str]] = []
        for requirement in requirements:
            mapped = set(facts)
            for parameter in requirement:
                argument = _call_argument(call, callee, parameter)
                if argument is None:
                    continue
                sources = _expr_sources(
                    argument,
                    params=params,
                    origins=origins,
                    defs=caller.local_defs,
                )
                mapped.update(source for source in sources if source in caller.authority_params)
            out.append(frozenset(mapped))
        return out

    def positive_requirements(self, name: str, stack: frozenset[str] = frozenset()) -> list[frozenset[str]]:
        if name in self._positive_cache:
            return self._positive_cache[name]
        if name in stack:
            return [frozenset()]
        fn = self.functions[name]
        out = list(fn.direct_positive_requirements)
        for site in fn.returned_calls:
            callee = self.functions.get(site.callee)
            if callee is None:
                continue
            child = self.positive_requirements(site.callee, stack | {name})
            out.extend(self._map_requirements(fn, site.node, callee, child, site.authority_facts))
        self._positive_cache[name] = out
        return out

    def time_requirements(self, name: str, stack: frozenset[str] = frozenset()) -> list[frozenset[str]]:
        if name in self._time_cache:
            return self._time_cache[name]
        if name in stack:
            return []
        fn = self.functions[name]
        out = list(fn.direct_time_requirements)
        params = set(fn.params)
        origins = _origins(fn.node, fn.local_defs)
        for call in fn.all_calls:
            callee_name = _name(call.func)
            callee = self.functions.get(callee_name)
            if callee is None:
                continue
            for requirement in self.time_requirements(callee_name, stack | {name}):
                mapped: set[str] = set()
                for parameter in requirement:
                    argument = _call_argument(call, callee, parameter)
                    if argument is None:
                        continue
                    sources = _expr_sources(argument, params=params, origins=origins, defs=fn.local_defs)
                    mapped.update(source for source in sources if source in params)
                if mapped:
                    out.append(frozenset(mapped))
        self._time_cache[name] = out
        return out

    def retained_replay(self, name: str, stack: frozenset[str] = frozenset()) -> bool:
        if name in self._replay_cache:
            return self._replay_cache[name]
        if name in stack:
            return True
        fn = self.functions[name]
        if fn.direct_retained_replay:
            self._replay_cache[name] = True
            return True
        unsafe = any(
            self.retained_replay(_name(call.func), stack | {name})
            for call in fn.all_calls
            if _name(call.func) in self.functions
        )
        self._replay_cache[name] = unsafe
        return unsafe

    def findings(self) -> list[Finding]:
        out: list[Finding] = []
        for name, model in self.functions.items():
            fn = model.node
            if not _public(fn) or _historical_surface(fn):
                continue
            positives = self.positive_requirements(name)
            times = self.time_requirements(name)
            if times:
                out.append(
                    Finding(
                        self.path,
                        fn.lineno,
                        fn.col_offset + 1,
                        "CRG001",
                        "caller-derived data reaches a deadline/expiry comparison through this public surface",
                        name,
                    )
                )
            if positives:
                risky_time_params = [
                    parameter
                    for parameter in model.params
                    if any(word in parameter.lower() for word in _TIME_WORDS)
                    and any(isinstance(child, ast.Name) and child.id == parameter for child in ast.walk(fn))
                ]
                if risky_time_params:
                    out.append(
                        Finding(
                            self.path,
                            fn.lineno,
                            fn.col_offset + 1,
                            "CRG002",
                            "public current-positive surface accepts caller-selectable time/clock parameter(s): "
                            + ", ".join(sorted(risky_time_params)),
                            name,
                        )
                    )
                if any(not requirement for requirement in positives):
                    out.append(
                        Finding(
                            self.path,
                            fn.lineno,
                            fn.col_offset + 1,
                            "CRG003",
                            "a current-positive path is not controlled by an actually consumed independent authority parameter",
                            name,
                        )
                    )
            if "verify" in name.lower() and self.retained_replay(name):
                out.append(
                    Finding(
                        self.path,
                        fn.lineno,
                        fn.col_offset + 1,
                        "CRG004",
                        "retained caller/report time reaches a current projection without a process-clock projection used in the verifier result",
                        name,
                    )
                )
        return sorted(set(out))


def analyze_source(source: str | bytes, *, path: str = "<memory>") -> list[Finding]:
    if isinstance(source, bytes):
        try:
            source = source.decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            return [Finding(path, exc.start + 1, 1, "CRG000", "source is not strict UTF-8", None)]
    if not isinstance(source, str):
        raise TypeError("source must be str or bytes")
    try:
        tree = ast.parse(source, filename=path)
    except (SyntaxError, ValueError) as exc:
        line = getattr(exc, "lineno", None) or 1
        col = getattr(exc, "offset", None) or 1
        message = exc.msg if isinstance(exc, SyntaxError) else str(exc)
        return [Finding(path, line, col, "CRG000", f"source parse failure: {message}", None)]
    return _Analyzer(tree, path).findings()


__all__ = [name for name in globals() if not name.startswith("__")]
