#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source-bound metamorphic safety screen for TITAN V3 overlay patchers.

The first rule proves the Python ``seq[-0:] == seq[:]`` fixed-point hazard:
a non-negative removal count is computed with ``max(0, len(seq) - keep)``
and then used unguarded as the negative start of a mutating slice loop.

The verifier never imports or executes the untrusted handoff. It validates the
transport and tar member set, parses Python with ``ast``, and emits a stable
machine-readable proof/counterexample report.
"""
from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import io
import json
import tarfile
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping, Sequence

SCHEMA = "titan-v3-overlay-metamorphic-screen/v1"
DEFAULT_HANDOFF_SHA256 = (
    "f68792bf7f0fb269864ef4ab25967292e2d4cd03439dbc5c52b98dfcebd1b728"
)
DEFAULT_HANDOFF_BYTES = 27_500
EXPECTED_MEMBERS = frozenset(
    {
        "revenue/kaggriculture/cloud-execution-lab/candidates/v3/.gitignore",
        "revenue/kaggriculture/cloud-execution-lab/candidates/v3/FILES.json",
        "revenue/kaggriculture/cloud-execution-lab/candidates/v3/README.md",
        "revenue/kaggriculture/cloud-execution-lab/candidates/v3/V3-MANIFEST.json",
        "revenue/kaggriculture/cloud-execution-lab/candidates/v3/apply_v3.py",
        "revenue/kaggriculture/cloud-execution-lab/candidates/v3/build_v3.py",
        "revenue/kaggriculture/cloud-execution-lab/candidates/v3/overlay/checks/test_v3_features.py",
        "revenue/kaggriculture/cloud-execution-lab/candidates/v3/overlay/checks/test_v3_l01.py",
        "revenue/kaggriculture/cloud-execution-lab/candidates/v3/overlay/e11_rival_sell.py",
        "revenue/kaggriculture/cloud-execution-lab/candidates/v3/overlay/e20_hire_guard.py",
        "revenue/kaggriculture/cloud-execution-lab/candidates/v3/overlay/l01_mechanics.py",
        "revenue/kaggriculture/cloud-execution-lab/candidates/v3/overlay/rival_model.py",
        "revenue/kaggriculture/cloud-execution-lab/candidates/v3/overlay/shop_arb.py",
    }
)


class AuditError(RuntimeError):
    """Fail-closed input or source error."""


@dataclass(frozen=True)
class CountDefinition:
    name: str
    sequence: str
    keep_expr: str
    keep_value: int | None
    line: int


@dataclass(frozen=True)
class Finding:
    id: str
    severity: str
    rule: str
    invariant: str
    path: str
    function: str
    line: int
    count_definition_line: int
    count_variable: str
    sequence_variable: str
    keep_expression: str
    keep_value: int | None
    mutation_observed: bool
    proof: Mapping[str, object]
    metamorphic_counterexamples: Mapping[str, object]


def _canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, separators=(",", ": ")) + "\n"
    ).encode("utf-8")


def _normalize_member(name: str) -> str:
    while name.startswith("./"):
        name = name[2:]
    pure = PurePosixPath(name)
    if not name or pure.is_absolute() or any(
        part in {"", ".", ".."} for part in pure.parts
    ):
        raise AuditError(f"unsafe tar member: {name!r}")
    normalized = str(pure)
    if normalized.startswith("/"):
        raise AuditError(f"absolute tar member: {name!r}")
    return normalized


def read_handoff(
    encoded_path: Path,
    *,
    expected_sha256: str = DEFAULT_HANDOFF_SHA256,
    expected_bytes: int = DEFAULT_HANDOFF_BYTES,
    expected_members: frozenset[str] | None = EXPECTED_MEMBERS,
) -> tuple[dict[str, bytes], dict[str, object]]:
    """Authenticate, safely decode, and read regular UTF-8 handoff members."""
    try:
        compact = b"".join(encoded_path.read_bytes().split())
        archive = base64.b64decode(compact, validate=True)
    except (OSError, ValueError) as exc:
        raise AuditError(f"cannot decode handoff: {exc}") from exc

    digest = hashlib.sha256(archive).hexdigest()
    if digest != expected_sha256:
        raise AuditError(f"handoff sha256 mismatch: {digest} != {expected_sha256}")
    if len(archive) != expected_bytes:
        raise AuditError(
            f"handoff byte count mismatch: {len(archive)} != {expected_bytes}"
        )

    files: dict[str, bytes] = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
            for member in bundle.getmembers():
                if not member.isfile():
                    raise AuditError(
                        "non-regular tar member rejected: "
                        f"{member.name!r} type={member.type!r}"
                    )
                normalized = _normalize_member(member.name)
                if normalized in files:
                    raise AuditError(f"duplicate normalized tar member: {normalized}")
                stream = bundle.extractfile(member)
                if stream is None:
                    raise AuditError(f"missing tar payload: {normalized}")
                files[normalized] = stream.read()
    except (tarfile.TarError, OSError) as exc:
        raise AuditError(f"invalid gzip tar handoff: {exc}") from exc

    names = frozenset(files)
    if expected_members is not None and names != expected_members:
        missing = sorted(expected_members - names)
        extra = sorted(names - expected_members)
        raise AuditError(f"handoff member mismatch: missing={missing} extra={extra}")

    member_digests = {
        name: {"bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest()}
        for name, blob in sorted(files.items())
    }
    custody = {
        "encoded_path": encoded_path.as_posix(),
        "archive_sha256": digest,
        "archive_bytes": len(archive),
        "member_count": len(files),
        "members": member_digests,
    }
    return files, custody


def _int_constants(tree: ast.Module) -> dict[str, int]:
    constants: dict[str, int] = {}
    for stmt in tree.body:
        if not isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            continue
        if isinstance(stmt, ast.Assign):
            targets = list(stmt.targets)
            value = stmt.value
        else:
            targets = [stmt.target]
            value = stmt.value
        if (
            isinstance(value, ast.Constant)
            and isinstance(value.value, int)
            and not isinstance(value.value, bool)
        ):
            for target in targets:
                if isinstance(target, ast.Name):
                    constants[target.id] = int(value.value)
    return constants


def _unparse(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:  # pragma: no cover
        return node.__class__.__name__


def _resolve_int(node: ast.AST, constants: Mapping[str, int]) -> int | None:
    if (
        isinstance(node, ast.Constant)
        and isinstance(node.value, int)
        and not isinstance(node.value, bool)
    ):
        return int(node.value)
    if isinstance(node, ast.Name):
        return constants.get(node.id)
    return None


def _match_count_definition(
    stmt: ast.stmt, constants: Mapping[str, int]
) -> CountDefinition | None:
    """Match ``n = max(0, len(seq) - keep)`` exactly."""
    if (
        isinstance(stmt, ast.Assign)
        and len(stmt.targets) == 1
        and isinstance(stmt.targets[0], ast.Name)
    ):
        target = stmt.targets[0].id
        value = stmt.value
    elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
        target = stmt.target.id
        value = stmt.value
    else:
        return None
    if (
        not isinstance(value, ast.Call)
        or not isinstance(value.func, ast.Name)
        or value.func.id != "max"
    ):
        return None
    if len(value.args) != 2 or value.keywords:
        return None
    zero, delta = value.args
    if not (isinstance(zero, ast.Constant) and zero.value == 0):
        return None
    if not isinstance(delta, ast.BinOp) or not isinstance(delta.op, ast.Sub):
        return None
    left, keep = delta.left, delta.right
    if not (
        isinstance(left, ast.Call)
        and isinstance(left.func, ast.Name)
        and left.func.id == "len"
        and len(left.args) == 1
        and not left.keywords
        and isinstance(left.args[0], ast.Name)
    ):
        return None
    return CountDefinition(
        name=target,
        sequence=left.args[0].id,
        keep_expr=_unparse(keep),
        keep_value=_resolve_int(keep, constants),
        line=int(getattr(stmt, "lineno", 0)),
    )


def _slice_count_name(node: ast.AST) -> tuple[str, str] | None:
    """Return (sequence, count) for ``sequence[-count:]``."""
    if not isinstance(node, ast.Subscript) or not isinstance(node.value, ast.Name):
        return None
    sl = node.slice
    if not isinstance(sl, ast.Slice) or sl.upper is not None or sl.step is not None:
        return None
    lower = sl.lower
    if not (
        isinstance(lower, ast.UnaryOp)
        and isinstance(lower.op, ast.USub)
        and isinstance(lower.operand, ast.Name)
    ):
        return None
    return node.value.id, lower.operand.id


def _terminates(block: Sequence[ast.stmt]) -> bool:
    return bool(block) and isinstance(
        block[-1], (ast.Return, ast.Raise, ast.Continue, ast.Break)
    )


def _test_proves_positive(test: ast.AST, name: str) -> bool:
    if isinstance(test, ast.Name) and test.id == name:
        return True
    if (
        isinstance(test, ast.Compare)
        and isinstance(test.left, ast.Name)
        and test.left.id == name
        and len(test.ops) == 1
        and len(test.comparators) == 1
    ):
        rhs = test.comparators[0]
        if (
            isinstance(rhs, ast.Constant)
            and rhs.value == 0
            and isinstance(test.ops[0], (ast.Gt, ast.NotEq))
        ):
            return True
    if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And):
        return any(_test_proves_positive(part, name) for part in test.values)
    return False


def _test_proves_zero(test: ast.AST, name: str) -> bool:
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        return isinstance(test.operand, ast.Name) and test.operand.id == name
    if (
        isinstance(test, ast.Compare)
        and isinstance(test.left, ast.Name)
        and test.left.id == name
        and len(test.ops) == 1
        and len(test.comparators) == 1
    ):
        rhs = test.comparators[0]
        return (
            isinstance(rhs, ast.Constant)
            and rhs.value == 0
            and isinstance(test.ops[0], ast.Eq)
        )
    return False


def _body_mutates(block: Sequence[ast.stmt]) -> bool:
    for node in ast.walk(ast.Module(body=list(block), type_ignores=[])):
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Delete)):
            return True
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr in {
                "append",
                "clear",
                "discard",
                "extend",
                "insert",
                "pop",
                "remove",
                "reverse",
                "setdefault",
                "sort",
                "update",
            }:
                return True
    return False


def _counterexamples(keep: int | None) -> dict[str, object]:
    if keep is None or keep < 0:
        return {
            "status": "symbolic",
            "reason": "keep value is not a non-negative module constant",
        }
    initial = keep + 92
    first_extra = max(0, initial - keep)
    after_first = initial - len(list(range(initial))[-first_extra:])
    second_extra = max(0, after_first - keep)
    after_second = after_first - len(list(range(after_first))[-second_extra:])
    equal_extra = max(0, keep - keep)
    equal_after = keep - len(list(range(keep))[-equal_extra:])
    independent_after = initial - len(list(range(initial))[-first_extra:])
    return {
        "exact_target_fixed_point": {
            "input_site_count": keep,
            "computed_extra": equal_extra,
            "python_slice": f"sites[-{equal_extra}:]",
            "loop_iterations": keep,
            "expected_output_site_count": keep,
            "observed_output_site_count": equal_after,
        },
        "repeat_application": {
            "input_site_count": initial,
            "after_first_application": after_first,
            "after_second_application": after_second,
            "expected_second_application": after_first,
        },
        "shared_object_alias": {
            "two_route_keys_one_object_input": initial,
            "after_first_key": after_first,
            "after_second_alias_key": after_second,
            "independent_deepcopy_each_key": [independent_after, independent_after],
        },
    }


def _proof(keep: int | None) -> dict[str, object]:
    proof: dict[str, object] = {
        "language_identity": "For any sequence s, s[-0:] == s[:].",
        "zero_reachable": "max(0, len(s) - keep) == 0 whenever len(s) <= keep.",
        "consequence": (
            "An unguarded mutating loop over s[-count:] visits the entire "
            "sequence when count is zero."
        ),
    }
    if keep is not None:
        proof.update(
            {
                "keep_value": keep,
                "count_when_equal": max(0, keep - keep),
                "iterations_when_equal": len(
                    list(range(keep))[-max(0, keep - keep) :]
                ),
            }
        )
    return proof


def _finding_id(path: str, function: str, line: int, count: str) -> str:
    key = (
        f"negative-zero-mutating-slice\0{path}\0{function}\0{line}\0{count}"
    ).encode()
    return hashlib.sha256(key).hexdigest()[:20]


def _scan_block(
    block: Sequence[ast.stmt],
    *,
    path: str,
    function: str,
    constants: Mapping[str, int],
    definitions: dict[str, CountDefinition],
    positive_guards: frozenset[str] = frozenset(),
) -> list[Finding]:
    findings: list[Finding] = []
    local_defs = dict(definitions)
    terminated_zero_guards: set[str] = set()

    for stmt in block:
        definition = _match_count_definition(stmt, constants)
        if definition is not None:
            local_defs[definition.name] = definition

        if isinstance(stmt, ast.If):
            names = set(local_defs)
            true_positive = {
                name for name in names if _test_proves_positive(stmt.test, name)
            }
            true_zero = {name for name in names if _test_proves_zero(stmt.test, name)}
            findings.extend(
                _scan_block(
                    stmt.body,
                    path=path,
                    function=function,
                    constants=constants,
                    definitions=local_defs,
                    positive_guards=positive_guards | frozenset(true_positive),
                )
            )
            findings.extend(
                _scan_block(
                    stmt.orelse,
                    path=path,
                    function=function,
                    constants=constants,
                    definitions=local_defs,
                    positive_guards=positive_guards | frozenset(true_zero),
                )
            )
            if true_zero and _terminates(stmt.body):
                terminated_zero_guards.update(true_zero)
            continue

        if isinstance(stmt, ast.For):
            matched = _slice_count_name(stmt.iter)
            if matched is not None:
                sequence, count_name = matched
                definition = local_defs.get(count_name)
                guarded = (
                    count_name in positive_guards
                    or count_name in terminated_zero_guards
                )
                if (
                    definition is not None
                    and definition.sequence == sequence
                    and not guarded
                ):
                    mutation = _body_mutates(stmt.body)
                    line = int(getattr(stmt, "lineno", 0))
                    findings.append(
                        Finding(
                            id=_finding_id(path, function, line, count_name),
                            severity="critical" if mutation else "high",
                            rule="negative-zero-mutating-slice",
                            invariant=(
                                "patcher must be a fixed point when the sequence "
                                "is already at or below its target"
                            ),
                            path=path,
                            function=function,
                            line=line,
                            count_definition_line=definition.line,
                            count_variable=count_name,
                            sequence_variable=sequence,
                            keep_expression=definition.keep_expr,
                            keep_value=definition.keep_value,
                            mutation_observed=mutation,
                            proof=_proof(definition.keep_value),
                            metamorphic_counterexamples=_counterexamples(
                                definition.keep_value
                            ),
                        )
                    )
            findings.extend(
                _scan_block(
                    stmt.body,
                    path=path,
                    function=function,
                    constants=constants,
                    definitions=local_defs,
                    positive_guards=positive_guards,
                )
            )
            findings.extend(
                _scan_block(
                    stmt.orelse,
                    path=path,
                    function=function,
                    constants=constants,
                    definitions=local_defs,
                    positive_guards=positive_guards,
                )
            )
            continue

        for field in ("body", "orelse", "finalbody"):
            nested = getattr(stmt, field, None)
            if isinstance(nested, list):
                findings.extend(
                    _scan_block(
                        nested,
                        path=path,
                        function=function,
                        constants=constants,
                        definitions=local_defs,
                        positive_guards=positive_guards,
                    )
                )
        handlers = getattr(stmt, "handlers", None)
        if isinstance(handlers, list):
            for handler in handlers:
                findings.extend(
                    _scan_block(
                        handler.body,
                        path=path,
                        function=function,
                        constants=constants,
                        definitions=local_defs,
                        positive_guards=positive_guards,
                    )
                )
    return findings


def analyze_source(path: str, source: bytes) -> list[Finding]:
    try:
        text = source.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AuditError(f"non-UTF-8 Python source {path}: {exc}") from exc
    try:
        tree = ast.parse(text, filename=path)
    except SyntaxError as exc:
        raise AuditError(f"cannot parse Python source {path}: {exc}") from exc
    constants = _int_constants(tree)
    findings: list[Finding] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            findings.extend(
                _scan_block(
                    node.body,
                    path=path,
                    function=node.name,
                    constants=constants,
                    definitions={},
                )
            )
        elif isinstance(node, ast.ClassDef):
            for method in node.body:
                if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    findings.extend(
                        _scan_block(
                            method.body,
                            path=path,
                            function=f"{node.name}.{method.name}",
                            constants=constants,
                            definitions={},
                        )
                    )
    return findings


def build_report(
    files: Mapping[str, bytes], custody: Mapping[str, object]
) -> dict[str, object]:
    findings: list[Finding] = []
    python_paths = sorted(path for path in files if path.endswith(".py"))
    for path in python_paths:
        findings.extend(analyze_source(path, files[path]))
    findings.sort(key=lambda item: (item.path, item.line, item.function, item.id))
    data = [asdict(item) for item in findings]
    return {
        "schema": SCHEMA,
        "custody": dict(custody),
        "scope": {
            "python_files_scanned": len(python_paths),
            "python_paths": python_paths,
            "execution_policy": "AST-only; handoff code is never imported or executed",
        },
        "summary": {
            "finding_count": len(data),
            "critical_count": sum(
                item["severity"] == "critical" for item in data
            ),
            "high_count": sum(item["severity"] == "high" for item in data),
            "safe_to_materialize": not any(
                item["severity"] == "critical" for item in data
            ),
        },
        "findings": data,
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--encoded-handoff", type=Path, required=True)
    parser.add_argument("--expected-sha256", default=DEFAULT_HANDOFF_SHA256)
    parser.add_argument("--expected-bytes", type=int, default=DEFAULT_HANDOFF_BYTES)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--require-path",
        action="append",
        default=[],
        help="Require at least one finding for this exact repository path.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    files, custody = read_handoff(
        args.encoded_handoff,
        expected_sha256=args.expected_sha256,
        expected_bytes=args.expected_bytes,
    )
    report = build_report(files, custody)
    finding_paths = {item["path"] for item in report["findings"]}
    missing = sorted(set(args.require_path) - finding_paths)
    if missing:
        raise AuditError(f"required predecessor finding missing: {missing}")
    encoded = _canonical_json(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(encoded)
    print(
        "METAGUARD_REPORT",
        hashlib.sha256(encoded).hexdigest(),
        report["summary"]["finding_count"],
        report["summary"]["critical_count"],
        args.output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
