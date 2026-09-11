#!/usr/bin/env python3
"""Fail closed if a V4 recomposition drops a landed key or its live runtime plumbing."""
from __future__ import annotations
import argparse, ast, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import build_v3

APPLY_V4 = HERE / "apply_v4.py"
UNKNOWN = object()
SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda,
          ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)

def fail(msg):
    raise SystemExit("V4 PLUMBING FAIL: " + msg)

def require(ok, msg):
    if not ok:
        fail(msg)

def bound(target):
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.Tuple, ast.List)):
        out = set()
        for item in target.elts:
            out |= bound(item)
        return out
    if isinstance(target, ast.Starred):
        return bound(target.value)
    return set()

def imported(node):
    out = set()
    if isinstance(node, ast.Import):
        for a in node.names:
            out.add(a.asname or a.name.split(".", 1)[0])
    elif isinstance(node, ast.ImportFrom):
        for a in node.names:
            out.add(a.asname or a.name)
    return out

def invalidates(node, name):
    if isinstance(node, ast.Assign):
        return any(name in bound(t) for t in node.targets)
    if isinstance(node, (ast.AnnAssign, ast.AugAssign)):
        return name in bound(node.target)
    if isinstance(node, ast.Delete):
        return any(name in bound(t) for t in node.targets)
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return node.name == name
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return name in imported(node)
    return False

def literal(node):
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        return UNKNOWN

def compare_values(a, op, b):
    try:
        if isinstance(op, ast.Eq): return a == b
        if isinstance(op, ast.NotEq): return a != b
        if isinstance(op, ast.Lt): return a < b
        if isinstance(op, ast.LtE): return a <= b
        if isinstance(op, ast.Gt): return a > b
        if isinstance(op, ast.GtE): return a >= b
        if isinstance(op, ast.In): return a in b
        if isinstance(op, ast.NotIn): return a not in b
        if isinstance(op, ast.Is): return a is b
        if isinstance(op, ast.IsNot): return a is not b
    except Exception:
        return UNKNOWN
    return UNKNOWN

def static_truth(node):
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        v = static_truth(node.operand)
        return None if v is None else not v
    if isinstance(node, ast.BoolOp):
        vals = [static_truth(v) for v in node.values]
        if isinstance(node.op, ast.And):
            if False in vals: return False
            if all(v is True for v in vals): return True
            return None
        if isinstance(node.op, ast.Or):
            if True in vals: return True
            if all(v is False for v in vals): return False
            return None
    if isinstance(node, ast.Compare):
        left = literal(node.left)
        if left is UNKNOWN: return None
        for op, rhs in zip(node.ops, node.comparators):
            right = literal(rhs)
            if right is UNKNOWN: return None
            result = compare_values(left, op, right)
            if result is UNKNOWN: return None
            if not result: return False
            left = right
        return True
    value = literal(node)
    if value is UNKNOWN: return None
    try:
        return bool(value)
    except Exception:
        return None

def literal_empty(node):
    value = literal(node)
    return isinstance(value, (tuple, list, set, dict, str, bytes)) and len(value) == 0

def visit_node(node, out):
    if isinstance(node, SCOPES):
        return
    out.append(node)
    if isinstance(node, ast.If):
        visit_node(node.test, out)
        t = static_truth(node.test)
        if t is not False: visit_block(node.body, out)
        if t is not True: visit_block(node.orelse, out)
        return
    if isinstance(node, ast.While):
        visit_node(node.test, out)
        t = static_truth(node.test)
        if t is not False: visit_block(node.body, out)
        if t is not True: visit_block(node.orelse, out)
        return
    if isinstance(node, (ast.For, ast.AsyncFor)):
        visit_node(node.iter, out)
        if not literal_empty(node.iter):
            visit_node(node.target, out)
            visit_block(node.body, out)
        visit_block(node.orelse, out)
        return
    if isinstance(node, ast.IfExp):
        visit_node(node.test, out)
        t = static_truth(node.test)
        if t is not False: visit_node(node.body, out)
        if t is not True: visit_node(node.orelse, out)
        return
    for child in ast.iter_child_nodes(node):
        visit_node(child, out)

def visit_block(stmts, out):
    for stmt in stmts:
        visit_node(stmt, out)
        if isinstance(stmt, (ast.Return, ast.Raise)):
            break

def live_nodes(function):
    out = []
    visit_block(function.body, out)
    return out

def loads(node, name):
    out = []
    visit_node(node, out)
    return any(isinstance(n, ast.Name) and n.id == name and isinstance(n.ctx, ast.Load)
               for n in out)

def literal_keys(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    value = None
    seen = False
    for node in tree.body:
        if isinstance(node, ast.Assign) and any("KEYS" in bound(t) for t in node.targets):
            seen = True
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                raw = literal(node.value)
                if isinstance(raw, (tuple, list)) and all(type(x) is str for x in raw):
                    value = tuple(raw)
                else:
                    value = None
            else:
                value = None
        elif isinstance(node, ast.AnnAssign) and "KEYS" in bound(node.target):
            seen = True
            raw = literal(node.value) if node.value is not None else UNKNOWN
            value = tuple(raw) if isinstance(raw, (tuple, list)) and all(type(x) is str for x in raw) else None
        elif invalidates(node, "KEYS"):
            seen = True
            value = None
    require(seen and value is not None, f"{path}: KEYS must end as one live literal string sequence")
    require(len(value) == len(set(value)), f"{path}: KEYS contains duplicates")
    return value

def final_class(tree, name):
    found = None
    seen = False
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            found, seen = node, True
        elif invalidates(node, name):
            found, seen = None, True
    require(seen and found is not None, f"titan_runtime.py has no final live {name} class")
    return found

def class_bindings(cls):
    funcs = {}
    for node in cls.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs[node.name] = node
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                for name in bound(t): funcs.pop(name, None)
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            for name in bound(node.target): funcs.pop(name, None)
        elif isinstance(node, ast.Delete):
            for t in node.targets:
                for name in bound(t): funcs.pop(name, None)
        elif isinstance(node, ast.ClassDef):
            funcs.pop(node.name, None)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for name in imported(node): funcs.pop(name, None)
    return funcs

def feature_defaults(tree):
    cls = final_class(tree, "Features")
    vals = {}
    for node in cls.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            v = literal(node.value) if node.value is not None else UNKNOWN
            if type(v) is bool: vals[node.target.id] = v
            else: vals.pop(node.target.id, None)
        elif isinstance(node, ast.Assign):
            v = literal(node.value)
            for t in node.targets:
                for name in bound(t):
                    if type(v) is bool and len(node.targets) == 1 and isinstance(t, ast.Name):
                        vals[name] = v
                    else:
                        vals.pop(name, None)
        elif isinstance(node, (ast.AugAssign, ast.Delete, ast.Import, ast.ImportFrom,
                               ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names = set()
            if isinstance(node, ast.AugAssign): names |= bound(node.target)
            elif isinstance(node, ast.Delete):
                for t in node.targets: names |= bound(t)
            elif isinstance(node, (ast.Import, ast.ImportFrom)): names |= imported(node)
            else: names.add(node.name)
            for name in names: vals.pop(name, None)
    return vals

def reachable_agent(tree):
    cls = final_class(tree, "TitanAgent")
    funcs = class_bindings(cls)
    require("act" in funcs, "TitanAgent.act is not a final live method")
    seen, stack = set(), [funcs["act"]]
    while stack:
        fn = stack.pop()
        if fn in seen: continue
        seen.add(fn)
        for n in live_nodes(fn):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and isinstance(n.func.value, ast.Name) and n.func.value.id == "self"):
                target = funcs.get(n.func.attr)
                if target is not None and target not in seen:
                    stack.append(target)
    return seen

def feature_expr(node, key):
    direct = (isinstance(node, ast.Attribute) and node.attr == key
              and isinstance(node.value, ast.Attribute) and node.value.attr == "features"
              and isinstance(node.value.value, ast.Name) and node.value.value.id == "self")
    if direct: return True
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "bool" and len(node.args) == 1 and not node.keywords
            and feature_expr(node.args[0], key))

def reachable_feature(reachable, key):
    return any(feature_expr(n, key) for fn in reachable for n in live_nodes(fn))

def runtime_install_wired(reachable, key, suffix):
    for fn in reachable:
        alias = None
        nodes = sorted(live_nodes(fn), key=lambda n: (getattr(n, "lineno", -1), getattr(n, "col_offset", -1)))
        for n in nodes:
            if isinstance(n, ast.ImportFrom) and n.module == "r04_full_router":
                for a in n.names:
                    if a.name == "install":
                        alias = a.asname or a.name
                continue
            if alias is not None and invalidates(n, alias):
                alias = None
            if alias is None or not isinstance(n, ast.Call): continue
            if not (isinstance(n.func, ast.Name) and n.func.id == alias): continue
            for kw in n.keywords:
                if kw.arg == suffix and feature_expr(kw.value, key):
                    return True
    return False

def top_bools(tree):
    vals = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            v = literal(node.value)
            names = set()
            for t in node.targets: names |= bound(t)
            for name in names:
                if type(v) is bool and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                    vals[name] = v
                else: vals.pop(name, None)
        elif isinstance(node, ast.AnnAssign):
            v = literal(node.value) if node.value is not None else UNKNOWN
            for name in bound(node.target):
                if type(v) is bool and isinstance(node.target, ast.Name): vals[name] = v
                else: vals.pop(name, None)
        elif isinstance(node, (ast.AugAssign, ast.Delete, ast.Import, ast.ImportFrom,
                               ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names = set()
            if isinstance(node, ast.AugAssign): names |= bound(node.target)
            elif isinstance(node, ast.Delete):
                for t in node.targets: names |= bound(t)
            elif isinstance(node, (ast.Import, ast.ImportFrom)): names |= imported(node)
            else: names.add(node.name)
            for name in names: vals.pop(name, None)
    return vals

def find_function(tree, name):
    found = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            found = node
        elif invalidates(node, name):
            found = None
    require(found is not None, f"r04_full_router.py has no final live {name}()")
    return found

def globals_of(fn):
    return {name for n in live_nodes(fn) if isinstance(n, ast.Global) for name in n.names}

def exact_param(node, name):
    if isinstance(node, ast.Name) and node.id == name: return True
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "bool" and len(node.args) == 1 and not node.keywords
            and isinstance(node.args[0], ast.Name) and node.args[0].id == name)

def setter_depends(fn, flag, suffix):
    for n in live_nodes(fn):
        if isinstance(n, ast.Assign):
            if any(flag in bound(t) for t in n.targets) and exact_param(n.value, suffix):
                return True
        elif isinstance(n, ast.AnnAssign):
            if flag in bound(n.target) and n.value is not None and exact_param(n.value, suffix):
                return True
    return False

def function_bindings(tree):
    funcs = {}
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs[n.name] = n
        elif isinstance(n, ast.Assign):
            source = funcs.get(n.value.id) if isinstance(n.value, ast.Name) else None
            names = set()
            for t in n.targets: names |= bound(t)
            for name in names:
                if len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) and source is not None:
                    funcs[name] = source
                else: funcs.pop(name, None)
        elif isinstance(n, ast.AnnAssign):
            source = funcs.get(n.value.id) if n.value is not None and isinstance(n.value, ast.Name) else None
            for name in bound(n.target):
                if isinstance(n.target, ast.Name) and source is not None: funcs[name] = source
                else: funcs.pop(name, None)
        elif isinstance(n, ast.AugAssign):
            for name in bound(n.target): funcs.pop(name, None)
        elif isinstance(n, ast.Delete):
            for t in n.targets:
                for name in bound(t): funcs.pop(name, None)
        elif isinstance(n, ast.ClassDef):
            funcs.pop(n.name, None)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for name in imported(n): funcs.pop(name, None)
    return funcs

def production_functions(tree):
    funcs = function_bindings(tree)
    root = funcs.get("v3_agent")
    if root is None: return set()
    seen, stack = set(), [root]
    while stack:
        fn = stack.pop()
        if fn in seen: continue
        seen.add(fn)
        for n in live_nodes(fn):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                target = funcs.get(n.func.id)
                if target is not None and target not in seen: stack.append(target)
    return seen

def flag_control(test, flag):
    return loads(test, flag) and static_truth(test) is None

def router_behavior_reader(tree, flag):
    for fn in production_functions(tree):
        for n in live_nodes(fn):
            if isinstance(n, (ast.If, ast.While, ast.IfExp)) and flag_control(n.test, flag):
                return True
            if isinstance(n, ast.Call):
                if any(loads(a, flag) for a in n.args): return True
                if any(loads(k.value, flag) for k in n.keywords): return True
    return False

def callable_name(expr, funcs):
    if isinstance(expr, ast.Name) and expr.id in funcs: return expr.id
    if isinstance(expr, ast.IfExp):
        t = static_truth(expr.test)
        if t is True: return callable_name(expr.body, funcs)
        if t is False: return callable_name(expr.orelse, funcs)
    return None

def install_selector(tree, install, flag):
    funcs = function_bindings(tree)
    for stmt in install.body:
        if not isinstance(stmt, ast.If) or not flag_control(stmt.test, flag): continue
        out = []
        visit_block(stmt.body, out)
        for n in out:
            if isinstance(n, ast.Return) and n.value is not None:
                name = callable_name(n.value, funcs)
                if name is not None and name != "v3_agent": return True
    return False

def assert_r04(tree, reachable, key):
    suffix, flag = key.removeprefix("r04_"), key.removeprefix("r04_").upper()
    defaults = top_bools(tree)
    require(defaults.get(flag) is False, f"{key}: router {flag} must be final live False")
    install = find_function(tree, "install")
    args = {a.arg for a in (*install.args.posonlyargs, *install.args.args, *install.args.kwonlyargs)}
    require(suffix in args, f"{key}: install() missing {suffix} parameter")
    require(flag in globals_of(install), f"{key}: install() missing direct global {flag}")
    require(setter_depends(install, flag, suffix), f"{key}: {flag} setter does not depend on {suffix}")
    require(router_behavior_reader(tree, flag) or install_selector(tree, install, flag),
            f"{key}: {flag} has no live behavior-affecting production use")
    require(runtime_install_wired(reachable, key, suffix),
            f"{key}: TitanAgent lacks authentic r04_full_router.install wiring")

def self_tests():
    dead = ast.parse("""def f():
    if not True: return FLAG
    if 1 == 0: return FLAG
    if False and FLAG: return FLAG
    for _ in (): return FLAG
    return None
    return FLAG
""").body[0]
    require(not loads(dead, "FLAG"), "internal dead-code traversal false-passed")

    shadow = ast.parse("""class TitanAgent:
    def act(self): return None
TitanAgent = object()
""")
    try: reachable_agent(shadow)
    except SystemExit: pass
    else: fail("internal final-class binding false-passed")

    methods = ast.parse("""class TitanAgent:
    def act(self): return self.live()
    def live(self): return None
    act = None
""")
    try: reachable_agent(methods)
    except SystemExit: pass
    else: fail("internal final-method binding false-passed")

    router = ast.parse("""PLACE_DELIVERY=False
def helper(x=None): return x
def v3_agent(x=None):
    marker=PLACE_DELIVERY
    return helper(x)
def install(*,place_delivery=None):
    global PLACE_DELIVERY
    if place_delivery is not None: PLACE_DELIVERY=bool(place_delivery)
    return v3_agent
""")
    require(not router_behavior_reader(router, "PLACE_DELIVERY"), "internal no-op flag load false-passed")

    good = ast.parse("""PLACE_DELIVERY=False
def helper(x=None): return x
def v3_agent(x=None):
    if PLACE_DELIVERY: return helper(x)
    return x
def install(*,place_delivery=None):
    global PLACE_DELIVERY
    if place_delivery is not None: PLACE_DELIVERY=bool(place_delivery)
    return v3_agent
""")
    require(router_behavior_reader(good, "PLACE_DELIVERY"), "internal live flag branch missed")

    bad_set = ast.parse("""PLACE_DELIVERY=False
def v3_agent(x=None): return x
def install(*,place_delivery=None):
    global PLACE_DELIVERY
    PLACE_DELIVERY=False
    return v3_agent
""")
    require(not setter_depends(find_function(bad_set, "install"), "PLACE_DELIVERY", "place_delivery"),
            "internal constant setter false-passed")

    runtime_good = ast.parse("""class TitanAgent:
    def act(self): return self.wired()
    def wired(self):
        from r04_full_router import install as ri
        return ri(place_delivery=bool(self.features.r04_place_delivery))
""")
    rr = reachable_agent(runtime_good)
    require(runtime_install_wired(rr, "r04_place_delivery", "place_delivery"),
            "internal valid router provenance missed")

    runtime_bad = ast.parse("""class TitanAgent:
    def act(self):
        import fake
        return fake.install(place_delivery=self.features.r04_place_delivery)
""")
    require(not runtime_install_wired(reachable_agent(runtime_bad), "r04_place_delivery", "place_delivery"),
            "internal arbitrary install false-passed")

    for source in (
        "def install(): return None\ninstall += wrapper\n",
        "def install(): return None\nfrom x import install\n",
        "def install(): return None\ninstall,junk=object(),None\n",
    ):
        try: find_function(ast.parse(source), "install")
        except SystemExit: pass
        else: fail("internal final function rebind false-passed")

    bad_selector = ast.parse("""PLACE_DELIVERY=False
def alt(x=None): return x
def v3_agent(x=None): return x
def install():
    if PLACE_DELIVERY or True: return alt
    return v3_agent
""")
    require(not install_selector(bad_selector, find_function(bad_selector, "install"), "PLACE_DELIVERY"),
            "internal flag-independent selector false-passed")

def check(base_apply):
    self_tests()
    base_keys, head_keys = literal_keys(base_apply), literal_keys(APPLY_V4)
    removed = sorted(set(base_keys) - set(head_keys))
    require(not removed, "recomposition removed landed key(s): " + ", ".join(removed))

    files = build_v3.package_files()
    for name in ("TITAN-CONFIG.json", "titan_runtime.py", "r04_full_router.py"):
        require(name in files, f"materialized package missing {name}")
    config = json.loads(files["TITAN-CONFIG.json"].decode())
    runtime = ast.parse(files["titan_runtime.py"].decode(), filename="titan_runtime.py")
    router = ast.parse(files["r04_full_router.py"].decode(), filename="r04_full_router.py")
    defaults = feature_defaults(runtime)
    reach = reachable_agent(runtime)

    # docs/V4.md: lanes ship OFF; promotion is a separate PR with additional artifacts.
    for key in head_keys:
        require(key in config and type(config[key]) is bool and config[key] is False,
                f"{key}: materialized config must be boolean False")
        require(key in defaults and type(defaults[key]) is bool and defaults[key] is False,
                f"{key}: Features default must be boolean False")
        require(reachable_feature(reach, key), f"{key}: not referenced on TitanAgent.act call chain")
        if key.startswith("r04_"):
            assert_r04(router, reach, key)

    print("V4 PLUMBING OK", "base", list(base_keys), "head", list(head_keys),
          "reachable", sorted(getattr(f, "name", "?") for f in reach))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-apply-v4", type=Path, required=True)
    args = ap.parse_args()
    check(args.base_apply_v4)

if __name__ == "__main__":
    main()
