from __future__ import annotations

import ast
import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

RULES = {
    "CRG000": "source could not be parsed",
    "CRG001": "caller-controlled time participates in a current deadline/expiry comparison",
    "CRG002": "public current-positive surface accepts a caller-selectable time/clock override",
    "CRG003": "public readiness surface can mint READY without a controlling independent authority boundary",
    "CRG004": "public verifier replays retained caller/report time without a process-clock current recheck",
}

_TIME_WORDS = (
    "as_of",
    "asof",
    "evaluated_at",
    "evaluation_time",
    "current_time",
    "now",
    "verifier_now",
    "trusted_as_of",
    "clock",
    "timestamp",
    "time_utc",
)
_DEADLINE_WORDS = (
    "deadline",
    "cutoff",
    "cut_off",
    "close_at",
    "closes_at",
    "expiry",
    "expires",
    "expiration",
    "not_after",
    "valid_until",
    "end_at",
    "due_at",
)
_AUTHORITY_WORDS = (
    "authority",
    "trusted",
    "root",
    "receipt",
    "evidence",
    "verifier",
    "attestation",
    "source_generation",
    "source_root",
    "host_proof",
)
_NONCURRENT_PREFIXES = (
    "HOLD",
    "NOT_",
    "NON_",
    "HISTORICAL",
    "SOURCE_",
    "REVIEW_REQUIRED",
    "OWNER_REVIEW",
    "CANDIDATE_",
    "BLOCKED",
    "INVALID",
    "REJECT",
    "DECLINED",
)
_POSITIVE_EXACT = {
    "READY",
    "VALID",
    "CLEAR",
    "REUSABLE",
    "ALLOCATED_READY",
    "ALLOW_NEW",
    "LEASE_HELD",
    "SEND_READY",
    "INITIAL_OUTREACH_ACQUIRED",
    "CURRENT_VERIFIED",
    "PROTECTED_PRE_SEND",
    "FOLLOWUP_READY",
    "REFERENCE_READY_FOR_OWNER_REVIEW",
}
_POLICY_KEYS = {"path", "rule", "rationale", "owner", "issue", "expires"}
_RULE_RE = re.compile(r"^CRG\d{3}$")
_PROCESS_CLOCK = "<process-clock>"


@dataclass(frozen=True, order=True)
class Finding:
    path: str
    line: int
    col: int
    rule: str
    message: str
    function: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Exemption:
    path: str
    rule: str
    rationale: str
    owner: str
    issue: str
    expires: date


@dataclass(frozen=True)
class _CallSite:
    callee: str
    node: ast.Call
    authority_facts: frozenset[str]


@dataclass
class _FunctionModel:
    node: ast.FunctionDef | ast.AsyncFunctionDef
    params: list[str]
    authority_params: set[str]
    local_defs: dict[str, ast.AST]
    direct_positive_requirements: list[frozenset[str]]
    returned_calls: list[_CallSite]
    all_calls: list[ast.Call]
    direct_time_requirements: list[frozenset[str]]
    direct_retained_replay: bool


class PolicyError(ValueError):
    pass


def _name(node: ast.AST | None) -> str:
    if node is None:
        return ""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.Call):
        return _name(node.func)
    return ""


def _string_key(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _access_tokens(node: ast.AST) -> list[str]:
    out: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            out.append(child.id.lower())
        elif isinstance(child, ast.Attribute):
            out.append(child.attr.lower())
        elif isinstance(child, ast.Subscript):
            key = _string_key(child.slice)
            if key is not None:
                out.append(key.lower())
        elif isinstance(child, ast.Constant) and isinstance(child.value, str):
            out.append(child.value.lower())
    return out


def _has_word(node: ast.AST, words: tuple[str, ...]) -> bool:
    tokens = _access_tokens(node)
    return any(any(word in token for word in words) for token in tokens)


def _function_params(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    args = [*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs]
    names = [arg.arg for arg in args]
    if fn.args.vararg:
        names.append(fn.args.vararg.arg)
    if fn.args.kwarg:
        names.append(fn.args.kwarg.arg)
    return [name for name in names if name not in {"self", "cls"}]


def _public(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return not fn.name.startswith("_")


def _historical_surface(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return "historical" in fn.name.lower()


def _authority_name(name: str) -> bool:
    lower = name.lower()
    return any(word in lower for word in _AUTHORITY_WORDS)


def _positive_state(value: str) -> bool:
    token = value.strip().upper()
    if not token or token.startswith(_NONCURRENT_PREFIXES):
        return False
    if token in _POSITIVE_EXACT:
        return True
    return (
        token.endswith("_READY")
        or token.startswith("READY_")
        or token.endswith("_VERIFIED")
        or token.endswith("_CLEAR")
        or token.startswith("CLEAR_FOR_")
    )


def _module_string_constants(tree: ast.Module) -> dict[str, str]:
    out: dict[str, str] = {}
    for statement in tree.body:
        if isinstance(statement, (ast.Assign, ast.AnnAssign)):
            value = statement.value
            targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                for target in targets:
                    if isinstance(target, ast.Name):
                        out[target.id] = value.value
    return out


def _local_defs(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, ast.AST]:
    out: dict[str, ast.AST] = {}
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    out[target.id] = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
            out[node.target.id] = node.value
        elif isinstance(node, ast.NamedExpr) and isinstance(node.target, ast.Name):
            out[node.target.id] = node.value
    return out


def _expand_expr(node: ast.AST | None, defs: Mapping[str, ast.AST], *, seen: frozenset[str] = frozenset()) -> ast.AST | None:
    if isinstance(node, ast.Name) and node.id in defs and node.id not in seen:
        return _expand_expr(defs[node.id], defs, seen=seen | {node.id})
    return node


def _emitted_strings(
    node: ast.AST | None,
    defs: Mapping[str, ast.AST],
    globals_: Mapping[str, str],
    *,
    seen: frozenset[str] = frozenset(),
) -> set[str]:
    node = _expand_expr(node, defs, seen=seen)
    if node is None:
        return set()
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return {node.value}
    if isinstance(node, ast.Name):
        if node.id in globals_:
            return {globals_[node.id]}
        if node.id in defs and node.id not in seen:
            return _emitted_strings(defs[node.id], defs, globals_, seen=seen | {node.id})
        return set()
    if isinstance(node, ast.Attribute):
        return {node.attr}
    if isinstance(node, ast.IfExp):
        return _emitted_strings(node.body, defs, globals_, seen=seen) | _emitted_strings(
            node.orelse, defs, globals_, seen=seen
        )
    if isinstance(node, ast.Dict):
        out: set[str] = set()
        for value in node.values:
            out |= _emitted_strings(value, defs, globals_, seen=seen)
        return out
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        out: set[str] = set()
        for value in node.elts:
            out |= _emitted_strings(value, defs, globals_, seen=seen)
        return out
    return set()


def _contains_positive(node: ast.AST | None, defs: Mapping[str, ast.AST], globals_: Mapping[str, str]) -> set[str]:
    return {value.strip().upper() for value in _emitted_strings(node, defs, globals_) if _positive_state(value)}


def _authority_refs(node: ast.AST | None, authority_params: set[str]) -> set[str]:
    if node is None:
        return set()
    return {
        child.id
        for child in ast.walk(node)
        if isinstance(child, ast.Name) and child.id in authority_params
    }


def _condition_authority_facts(node: ast.AST, authority_params: set[str], *, truth: bool) -> set[str]:
    if isinstance(node, ast.Name) and node.id in authority_params:
        return {node.id} if truth else set()
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return _condition_authority_facts(node.operand, authority_params, truth=not truth)
    if isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And) and truth:
            out: set[str] = set()
            for value in node.values:
                out |= _condition_authority_facts(value, authority_params, truth=True)
            return out
        if isinstance(node.op, ast.Or) and not truth:
            out: set[str] = set()
            for value in node.values:
                out |= _condition_authority_facts(value, authority_params, truth=False)
            return out
        return set()
    if isinstance(node, ast.Compare) and len(node.ops) == len(node.comparators) == 1:
        left, op, right = node.left, node.ops[0], node.comparators[0]
        name: str | None = None
        if isinstance(left, ast.Name) and left.id in authority_params and isinstance(right, ast.Constant):
            name = left.id
            constant = right.value
        elif isinstance(right, ast.Name) and right.id in authority_params and isinstance(left, ast.Constant):
            name = right.id
            constant = left.value
        else:
            constant = object()
        if name is not None:
            positive = (
                (constant is None and isinstance(op, (ast.IsNot, ast.NotEq)))
                or (constant is None and not truth and isinstance(op, (ast.Is, ast.Eq)))
                or (constant is True and isinstance(op, (ast.Is, ast.Eq)))
                or (constant is False and isinstance(op, (ast.IsNot, ast.NotEq)))
            )
            if truth and positive:
                return {name}
            if not truth and constant is None and isinstance(op, (ast.Is, ast.Eq)):
                return {name}
    if truth and isinstance(node, ast.Call):
        call_name = _name(node.func).lower()
        refs = _authority_refs(node, authority_params)
        if refs and any(word in call_name for word in ("verify", "validate", "authorize", "check")):
            return refs
    return set()


__all__ = [name for name in globals() if not name.startswith("__")]
