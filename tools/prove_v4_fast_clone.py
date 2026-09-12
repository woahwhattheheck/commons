#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Seal the existing fold's literal-string grammar and prove its actual tape clone."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics
import sys
import time
import types


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def literal_string(node):
    if isinstance(node, ast.Constant) and type(node.value) is str:
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return literal_string(node.left) + literal_string(node.right)
    raise ValueError("nonliteral string concatenation in fast-clone generator seam")


def seal(text):
    """Normalize ONLY the existing fast-clone helper's all-literal NEW argument."""
    calls = [node for node in ast.walk(ast.parse(text))
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
             and node.func.id == "_replace_once" and len(node.args) == 4
             and isinstance(node.args[3], ast.Constant)
             and node.args[3].value == "R04 V4 reviewed fast tape clone helper"]
    require(len(calls) == 1, "missing/duplicate fast-clone helper edit")
    call = calls[0]
    require(not call.keywords, "unexpected helper edit kwargs")
    value = call.args[2]
    joined = literal_string(value)
    raw = text.encode("utf-8")
    lines = raw.splitlines(keepends=True)
    start = sum(map(len, lines[:value.lineno-1])) + value.col_offset
    end = sum(map(len, lines[:value.end_lineno-1])) + value.end_col_offset
    out = raw[:start] + repr(joined).encode("utf-8") + raw[end:]
    tree = ast.parse(out.decode("utf-8"))
    compile(tree, "sealed-apply-v4.py", "exec")
    return out


def main():
    require(len(sys.argv) == 5, "usage: proof.py apply_v4.py hardened_recipe.py tapes.py checker.py")
    apply_path, recipe_path, tapes_path, checker_path = map(Path, sys.argv[1:])
    recipe = ast.parse(recipe_path.read_text(encoding="utf-8"))
    values = [node.value for node in recipe.body if isinstance(node, ast.Assign)
              and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
              and node.targets[0].id == "HELPER"]
    require(len(values) == 1, "recipe HELPER binding is ambiguous")
    helper = ast.literal_eval(values[0])
    require(type(helper) is str, "recipe HELPER is not a literal string")
    clone_module = types.ModuleType("_fast_clone_corpus")
    exec(compile("import copy\n" + helper, "hardened-HELPER", "exec"), clone_module.__dict__)

    # Static final checker grammar, not candidate execution or checker main().
    require(blob(checker_path.read_bytes()) == "12a3eb23dd1052a769baa16ce861890f21911e14", "checker blob drift")
    spec = importlib.util.spec_from_file_location("_trusted_fastclone_checker", checker_path)
    require(spec is not None and spec.loader is not None, "checker loader missing")
    checker = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = checker
    spec.loader.exec_module(checker)
    unsealed = apply_path.read_bytes()
    text = unsealed.decode("utf-8")
    sealed = seal(text)
    program = checker._parse_static_apply_v4(sealed.decode("utf-8"))
    # Check the static parser's authenticated replacement list.
    clone_edits = [edit for path, edits in program[1] for edit in edits
                   if edit[2] in {"R04 V4 reviewed fast tape clone helper", "R04 V4 fast tape clone hot path"}]
    require(len(clone_edits) == 2, "expected exactly two fast-clone edits")
    for old, new, label in clone_edits:
        require(old != new and old, "inert helper edit")
    require(any("_r04_clone_tape_action(tape[step])" in new for _, new, _ in clone_edits), "missing hot-path call")
    apply_path.write_bytes(sealed)

    require(blob(tapes_path.read_bytes()) == "a43289b9cc5e34a2481fddf652762a7d92f427ef", "tape blob drift")
    tspec = importlib.util.spec_from_file_location("_frozen_fastclone_tapes", tapes_path)
    require(tspec is not None and tspec.loader is not None, "tape loader missing")
    tapes_module = importlib.util.module_from_spec(tspec)
    tspec.loader.exec_module(tapes_module)
    tapes = tapes_module.load_tapes()
    require(len(tapes) == 13 and all(len(t) == 719 for t in tapes), "wrong tape corpus dimensions")
    actions = [action for tape in tapes for action in tape]
    clone = clone_module._r04_clone_tape_action
    for index, action in enumerate(actions):
        require(clone_module._r04_is_fast_tape_action(action), f"unexpected fallback at {index}")
        result = clone(action)
        require(result == copy.deepcopy(action) and list(result) == list(action), f"copy mismatch at {index}")
        require(result is not action, f"top alias at {index}")
        for key in ("farmer", "hands", "market"):
            require(result[key] is not action[key], f"root alias at {index}/{key}")
        for key in ("hands", "market"):
            require(all(a is not b for a, b in zip(result[key], action[key])), f"row alias at {index}/{key}")

    def timed(fn):
        start = time.perf_counter()
        for action in actions:
            fn(action)
        return time.perf_counter() - start
    deep, fast = [], []
    timed(copy.deepcopy); timed(clone)
    for i in range(9):
        if i % 2:
            fast.append(timed(clone)); deep.append(timed(copy.deepcopy))
        else:
            deep.append(timed(copy.deepcopy)); fast.append(timed(clone))
    speedup = statistics.median(deep) / statistics.median(fast)
    receipt = {"actions": len(actions), "fallbacks": 0, "rounds": 9,
               "median_speedup": speedup, "deepcopy_median_s": statistics.median(deep),
               "clone_median_s": statistics.median(fast),
               "sealed_apply_blob": blob(sealed), "unsealed_apply_blob": blob(unsealed),
               "hardened_recipe_blob": blob(recipe_path.read_bytes()),
               "static_checker_blob": blob(checker_path.read_bytes()),
               "tapes_blob": blob(tapes_path.read_bytes()),
               "scope": "corpus mechanism + static apply grammar only; NOT full package/game proof"}
    print(json.dumps(receipt, sort_keys=True), flush=True)
    require(speedup >= 1.50, f"actual corpus speed gate failed: {speedup:.3f}x < 1.50x")
    print("PASS 9347 action equivalence/detachment, zero fallback, actual-corpus >=1.50x, static checker grammar")


if __name__ == "__main__":
    main()
