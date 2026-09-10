#!/usr/bin/env python3
"""Materialize the exact TITAN funding-trace plant-decay chronology closure.

This carrier never edits the canonical source.  It authenticates the current
source, its scheduler-to-mechanics decay binding, and the pinned official
interpreter; inserts the missing deterministic post-market plant-decay stage
into ``_funding_trace()``; compiles the postimage; and emits a deterministic
receipt.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any

OPERATION = "TITAN-V3-FUNDING-PLANT-DECAY-CHRONOLOGY-20260910-01"
SOURCE_GIT_BLOB = "fc7baf5c179818a55037f6a61d92984d81d1a21c"
SCHEDULER_GIT_BLOB = "a483b24dd72b580d7d8811636b54d2d44f391575"
MECHANICS_GIT_BLOB = "044a4f9c0a4a44dde10ada57563238bcaf82075d"
ENGINE_GIT_BLOB = "3c202c7ee921da239356789e266b694635103fc4"
TARGET_FUNCTION = "_funding_trace"
INSERTED_CALL = "m._decay_plants(f, t)"


class MaterializationError(ValueError):
    """A source, dependency, engine, path, or postimage contract failed."""


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_regular(path: Path) -> bytes:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError as exc:
        raise MaterializationError(f"missing file: {path}") from exc
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise MaterializationError(f"expected a regular non-symlink file: {path}")
    return path.read_bytes()


def _name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _single_function(tree: ast.Module, name: str) -> ast.FunctionDef:
    matches = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name]
    if len(matches) != 1:
        raise MaterializationError(f"expected exactly one top-level {name}(), found {len(matches)}")
    return matches[0]


def _call_expr_name(node: ast.stmt) -> str:
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        return _name(node.value.func)
    return ""


def verify_engine(engine_text: str) -> dict[str, Any]:
    """Prove the pinned interpreter calls market, town, then plant decay."""
    try:
        tree = ast.parse(engine_text)
        compile(engine_text, "<official-engine>", "exec")
    except (SyntaxError, ValueError) as exc:
        raise MaterializationError(f"official engine is not valid Python: {exc}") from exc

    decay = _single_function(tree, "_decay_plants")
    interpreter = _single_function(tree, "interpreter")

    market_index = town_index = decay_index = eod_index = None
    for index, statement in enumerate(interpreter.body):
        call_name = _call_expr_name(statement)
        if call_name == "_process_market":
            market_index = index
        elif call_name == "_town_consume":
            town_index = index
        elif isinstance(statement, ast.For):
            calls = [_name(node.func) for node in ast.walk(statement) if isinstance(node, ast.Call)]
            if "_decay_plants" in calls:
                decay_index = index
        elif isinstance(statement, ast.If):
            calls = [_name(node.func) for node in ast.walk(statement) if isinstance(node, ast.Call)]
            if "_end_of_day" in calls:
                eod_index = index

    if None in (market_index, town_index, decay_index, eod_index):
        raise MaterializationError("official interpreter chronology anchors are incomplete")
    if not market_index < town_index < decay_index < eod_index:
        raise MaterializationError("official chronology is not market -> town -> decay -> end-of-day")

    decay_calls = {_name(node.func) for node in ast.walk(decay) if isinstance(node, ast.Call)}
    source = ast.get_source_segment(engine_text, decay) or ""
    required_fragments = (
        "max_lifespan_step",
        "(step - mls) % 2",
        "yield_units",
        '"WEED"',
    )
    if not all(fragment in source for fragment in required_fragments):
        raise MaterializationError("official _decay_plants body does not match the bound lifecycle contract")

    return {
        "market_statement_index": market_index,
        "town_statement_index": town_index,
        "decay_statement_index": decay_index,
        "end_of_day_statement_index": eod_index,
        "decay_call_names": sorted(decay_calls),
    }



def _semantic_function_digest(node: ast.FunctionDef) -> str:
    payload = ast.dump(node, annotate_fields=True, include_attributes=False).encode("utf-8")
    return sha256_bytes(payload)


def _target_names(target: ast.AST) -> set[str]:
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.Tuple, ast.List)):
        result: set[str] = set()
        for item in target.elts:
            result.update(_target_names(item))
        return result
    if isinstance(target, ast.Starred):
        return _target_names(target.value)
    return set()


def _top_level_binding_names(statement: ast.stmt) -> set[str]:
    """Names a top-level statement can bind without entering function bodies."""
    if isinstance(statement, ast.Import):
        return {alias.asname or alias.name.split(".")[0] for alias in statement.names}
    if isinstance(statement, ast.ImportFrom):
        return {alias.asname or alias.name for alias in statement.names if alias.name != "*"}
    if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return {statement.name}
    if isinstance(statement, ast.Assign):
        result: set[str] = set()
        for target in statement.targets:
            result.update(_target_names(target))
        return result
    if isinstance(statement, (ast.AnnAssign, ast.AugAssign)):
        return _target_names(statement.target)
    if isinstance(statement, (ast.For, ast.AsyncFor)):
        result = _target_names(statement.target)
        for child in [*statement.body, *statement.orelse]:
            result.update(_top_level_binding_names(child))
        return result
    if isinstance(statement, (ast.With, ast.AsyncWith)):
        result: set[str] = set()
        for item in statement.items:
            if item.optional_vars is not None:
                result.update(_target_names(item.optional_vars))
        for child in statement.body:
            result.update(_top_level_binding_names(child))
        return result
    if isinstance(statement, ast.If):
        result: set[str] = set()
        for child in [*statement.body, *statement.orelse]:
            result.update(_top_level_binding_names(child))
        return result
    if isinstance(statement, (ast.Try, ast.TryStar)):
        result: set[str] = set()
        for child in [*statement.body, *statement.orelse, *statement.finalbody]:
            result.update(_top_level_binding_names(child))
        for handler in statement.handlers:
            if handler.name:
                result.add(handler.name)
            for child in handler.body:
                result.update(_top_level_binding_names(child))
        return result
    return set()


def verify_runtime_decay_binding(
    source_text: str,
    scheduler_text: str,
    mechanics_text: str,
    engine_text: str,
) -> dict[str, Any]:
    """Bind the inserted ``m._decay_plants`` call to exact official semantics."""
    texts = {
        "source": source_text,
        "scheduler": scheduler_text,
        "mechanics": mechanics_text,
        "official engine": engine_text,
    }
    trees: dict[str, ast.Module] = {}
    for label, text in texts.items():
        try:
            trees[label] = ast.parse(text)
            compile(text, f"<{label}>", "exec")
        except (SyntaxError, ValueError) as exc:
            raise MaterializationError(f"{label} is not valid Python: {exc}") from exc

    source_imports = [
        statement
        for statement in trees["source"].body
        if isinstance(statement, ast.ImportFrom)
        and statement.module == "scheduler"
        and any(alias.name == "*" for alias in statement.names)
    ]
    if len(source_imports) != 1:
        raise MaterializationError(
            "source must contain exactly one `from scheduler import *` binding"
        )

    scheduler_imports: list[tuple[ast.Import, ast.alias]] = []
    for statement in trees["scheduler"].body:
        if not isinstance(statement, ast.Import):
            continue
        for alias in statement.names:
            if alias.name == "mechanics" and alias.asname == "m":
                scheduler_imports.append((statement, alias))
    if len(scheduler_imports) != 1:
        raise MaterializationError(
            "scheduler must contain exactly one `import mechanics as m` binding"
        )
    import_statement = scheduler_imports[0][0]

    if any(
        "__all__" in _top_level_binding_names(statement)
        for statement in trees["scheduler"].body
    ):
        raise MaterializationError(
            "scheduler defines __all__; wildcard export of mechanics binding is unresolved"
        )
    for statement in trees["scheduler"].body:
        if statement is import_statement:
            continue
        if "m" in _top_level_binding_names(statement):
            raise MaterializationError("scheduler rebinds mechanics alias m")

    runtime_decay = _single_function(trees["mechanics"], "_decay_plants")
    official_decay = _single_function(trees["official engine"], "_decay_plants")
    runtime_digest = _semantic_function_digest(runtime_decay)
    official_digest = _semantic_function_digest(official_decay)
    if runtime_digest != official_digest:
        raise MaterializationError(
            "runtime mechanics _decay_plants differs from the official engine"
        )

    return {
        "source_scheduler_wildcard_line": source_imports[0].lineno,
        "scheduler_mechanics_alias_line": import_statement.lineno,
        "runtime_decay_line": runtime_decay.lineno,
        "official_decay_line": official_decay.lineno,
        "decay_semantic_sha256": runtime_digest,
        "implicit_wildcard_export": True,
        "scheduler_rebinds_m": False,
    }


def _is_funding_loop(node: ast.stmt) -> bool:
    if not isinstance(node, ast.For) or not isinstance(node.target, ast.Name) or node.target.id != "t":
        return False
    call = node.iter
    if not isinstance(call, ast.Call) or _name(call.func) != "range" or len(call.args) != 2:
        return False
    start, stop = call.args
    if not isinstance(start, ast.Name) or start.id != "now":
        return False
    return (
        isinstance(stop, ast.BinOp)
        and isinstance(stop.op, ast.Add)
        and isinstance(stop.left, ast.Name)
        and stop.left.id == "end"
        and isinstance(stop.right, ast.Constant)
        and stop.right.value == 1
    )


def inspect_postimage(source_text: str) -> dict[str, Any]:
    try:
        tree = ast.parse(source_text)
        compile(source_text, "<funding-decay-postimage>", "exec")
    except (SyntaxError, ValueError) as exc:
        raise MaterializationError(f"postimage is not valid Python: {exc}") from exc
    fn = _single_function(tree, TARGET_FUNCTION)
    loops = [node for node in fn.body if _is_funding_loop(node)]
    if len(loops) != 1:
        raise MaterializationError(f"postimage has {len(loops)} funding loops")
    loop = loops[0]
    calls = [node for node in ast.walk(fn) if isinstance(node, ast.Call) and _name(node.func) == "m._decay_plants"]
    if len(calls) != 1:
        raise MaterializationError(f"postimage has {len(calls)} m._decay_plants calls")
    call = calls[0]
    if len(call.args) != 2 or not all(isinstance(arg, ast.Name) for arg in call.args):
        raise MaterializationError("decay call arguments are not simple bound names")
    if [arg.id for arg in call.args] != ["f", "t"]:
        raise MaterializationError("decay call must be m._decay_plants(f, t)")
    if not loop.body or not isinstance(loop.body[-1], ast.Expr) or loop.body[-1].value is not call:
        raise MaterializationError("decay must be the final stage of each simulated turn")
    loop_index = fn.body.index(loop)
    if loop_index + 1 >= len(fn.body) or not isinstance(fn.body[loop_index + 1], ast.Return):
        raise MaterializationError("funding loop must still flow directly to its result return")
    prior_name = _call_expr_name(loop.body[-2]) if len(loop.body) >= 2 else ""
    return {
        "function": TARGET_FUNCTION,
        "loop_start_line": loop.lineno,
        "loop_end_line": loop.end_lineno,
        "decay_line": call.lineno,
        "prior_stage_call": prior_name or None,
    }


def patch_source(source_text: str) -> tuple[str, dict[str, Any]]:
    """Insert one decay call at the literal outer-turn boundary."""
    try:
        tree = ast.parse(source_text)
        compile(source_text, "<funding-decay-source>", "exec")
    except (SyntaxError, ValueError) as exc:
        raise MaterializationError(f"source is not valid Python: {exc}") from exc

    fn = _single_function(tree, TARGET_FUNCTION)
    existing = [node for node in ast.walk(fn) if isinstance(node, ast.Call) and _name(node.func) == "m._decay_plants"]
    if existing:
        raise MaterializationError("source already contains a funding-trace plant-decay stage")

    loops = [node for node in fn.body if _is_funding_loop(node)]
    if len(loops) != 1:
        raise MaterializationError(f"expected one outer funding loop, found {len(loops)}")
    loop = loops[0]
    loop_index = fn.body.index(loop)
    if loop_index + 1 >= len(fn.body) or not isinstance(fn.body[loop_index + 1], ast.Return):
        raise MaterializationError("outer funding loop is not immediately followed by the result return")

    return_line = fn.body[loop_index + 1].lineno
    lines = source_text.splitlines(keepends=True)
    newline = "\r\n" if any(line.endswith("\r\n") for line in lines) else "\n"
    insertion = f"        {INSERTED_CALL}{newline}"
    lines.insert(return_line - 1, insertion)
    postimage = "".join(lines)
    details = inspect_postimage(postimage)
    details["insertion_before_source_line"] = return_line
    return postimage, details


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise MaterializationError(f"refusing to overwrite existing output: {path}")
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def materialize(
    source_path: Path,
    scheduler_path: Path,
    mechanics_path: Path,
    engine_path: Path,
    output_path: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    # Authenticate file type before resolving aliases; resolving first would erase
    # the evidence that a caller supplied a symlink.
    inputs = {
        "source": Path(source_path),
        "scheduler": Path(scheduler_path),
        "mechanics": Path(mechanics_path),
        "official_engine": Path(engine_path),
    }
    payloads = {name: _read_regular(path) for name, path in inputs.items()}
    resolved_inputs = {name: path.resolve(strict=True) for name, path in inputs.items()}
    output_resolved = Path(output_path).resolve(strict=False)
    receipt_resolved = Path(receipt_path).resolve(strict=False)
    all_paths = [*resolved_inputs.values(), output_resolved, receipt_resolved]
    if len(set(all_paths)) != len(all_paths):
        raise MaterializationError(
            "source, scheduler, mechanics, engine, output, and receipt paths must be distinct"
        )

    expected_blobs = {
        "source": SOURCE_GIT_BLOB,
        "scheduler": SCHEDULER_GIT_BLOB,
        "mechanics": MECHANICS_GIT_BLOB,
        "official_engine": ENGINE_GIT_BLOB,
    }
    blobs = {name: git_blob_sha1(data) for name, data in payloads.items()}
    for name, expected in expected_blobs.items():
        if blobs[name] != expected:
            label = "engine" if name == "official_engine" else name
            raise MaterializationError(f"{label} Git blob mismatch: {blobs[name]}")

    texts: dict[str, str] = {}
    for name, data in payloads.items():
        try:
            texts[name] = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise MaterializationError(f"{name} must be UTF-8: {exc}") from exc

    engine_contract = verify_engine(texts["official_engine"])
    binding_contract = verify_runtime_decay_binding(
        texts["source"],
        texts["scheduler"],
        texts["mechanics"],
        texts["official_engine"],
    )
    postimage, patch_contract = patch_source(texts["source"])
    post_bytes = postimage.encode("utf-8")

    def identity(name: str) -> dict[str, Any]:
        data = payloads[name]
        return {
            "git_blob_sha1": blobs[name],
            "sha256": sha256_bytes(data),
            "bytes": len(data),
        }

    receipt: dict[str, Any] = {
        "operation": OPERATION,
        "status": "PASS",
        "source": identity("source"),
        "runtime_decay_binding": {
            "scheduler": identity("scheduler"),
            "mechanics": identity("mechanics"),
            "contract": binding_contract,
        },
        "official_engine": {
            **identity("official_engine"),
            "chronology": engine_contract,
        },
        "postimage": {
            "sha256": sha256_bytes(post_bytes),
            "bytes": len(post_bytes),
            "patch_contract": patch_contract,
        },
        "mutation_boundary": {
            "canonical_source_modified": False,
            "canonical_scheduler_modified": False,
            "canonical_mechanics_modified": False,
            "canonical_engine_modified": False,
            "inserted_call": INSERTED_CALL,
        },
    }
    receipt_bytes = (
        json.dumps(receipt, sort_keys=True, indent=2, separators=(",", ": ")) + "\n"
    ).encode("utf-8")
    _atomic_write(output_path, post_bytes)
    try:
        _atomic_write(receipt_path, receipt_bytes)
    except Exception:
        output_path.unlink(missing_ok=True)
        raise
    return receipt

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--scheduler", required=True, type=Path)
    parser.add_argument("--mechanics", required=True, type=Path)
    parser.add_argument("--engine", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args(argv)
    receipt = materialize(
        args.source,
        args.scheduler,
        args.mechanics,
        args.engine,
        args.output,
        args.receipt,
    )
    print(json.dumps({"status": receipt["status"], "postimage_sha256": receipt["postimage"]["sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
