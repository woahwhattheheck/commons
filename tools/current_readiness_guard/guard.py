from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, asdict
from datetime import date, datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

RULES = {
    "CRG000": "source could not be parsed",
    "CRG001": "caller-controlled time participates in a current deadline/expiry comparison",
    "CRG002": "public current-positive surface accepts a caller-selectable time/clock override",
    "CRG003": "public readiness surface can mint READY from a single caller packet without independent authority",
    "CRG004": "public verifier replays retained caller/report time without reacquiring process time",
}

_TIME_WORDS = (
    "as_of", "asof", "evaluated_at", "evaluation_time", "current_time", "now",
    "verifier_now", "trusted_as_of", "clock", "timestamp", "time_utc",
)
_DEADLINE_WORDS = (
    "deadline", "cutoff", "cut_off", "close_at", "closes_at", "expiry", "expires",
    "expiration", "not_after", "valid_until", "end_at", "due_at",
)
_AUTHORITY_WORDS = (
    "authority", "trusted", "root", "receipt", "evidence", "verifier", "attestation",
    "source_generation", "source_root", "host_proof",
)
_READINESS_FUNCTION_WORDS = (
    "evaluate", "qualify", "compile", "verify", "decide", "readiness", "ready", "gate", "build",
)
_POSITIVE_EXACT = {"READY", "VALID", "CLEAR", "REUSABLE", "ALLOCATED_READY"}
_NONCURRENT = {"HOLD", "HISTORICAL_ONLY", "NON_CURRENT", "REVIEW_REQUIRED", "SOURCE_REFRESH_REQUIRED"}
_POLICY_KEYS = {"path", "rule", "rationale", "owner", "issue", "expires"}
_RULE_RE = re.compile(r"^CRG\d{3}$")


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
    toks = _access_tokens(node)
    return any(any(word in tok for word in words) for tok in toks)


def _contains_name(node: ast.AST, names: set[str]) -> bool:
    return any(isinstance(child, ast.Name) and child.id in names for child in ast.walk(node))


def _function_params(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    args = [*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs]
    names = [a.arg for a in args]
    if fn.args.vararg:
        names.append(fn.args.vararg.arg)
    if fn.args.kwarg:
        names.append(fn.args.kwarg.arg)
    return [n for n in names if n not in {"self", "cls"}]


def _public(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return not fn.name.startswith("_")


def _readiness_function(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    low = fn.name.lower()
    return any(word in low for word in _READINESS_FUNCTION_WORDS) and "historical" not in low


def _positive_strings(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """Return positive state literals plausibly emitted, not merely inspected."""
    out: set[str] = set()

    def harvest(node: ast.AST | None) -> None:
        if node is None:
            return
        for child in ast.walk(node):
            if isinstance(child, ast.Constant) and isinstance(child.value, str):
                value = child.value.strip().upper()
                if value in _POSITIVE_EXACT or value.endswith("_READY"):
                    out.add(value)

    for child in ast.walk(fn):
        if isinstance(child, ast.Return):
            harvest(child.value)
            continue
        if isinstance(child, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
            if isinstance(child, ast.Assign):
                targets = list(child.targets)
                value = child.value
            else:
                targets = [child.target]
                value = child.value
            target_tokens: list[str] = []
            for target in targets:
                target_tokens.extend(_access_tokens(target))
            if any(any(word in tok for word in ("state", "status", "disposition", "decision", "result")) for tok in target_tokens):
                harvest(value)
    return out


def _noncurrent_strings(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    out = set()
    for child in ast.walk(fn):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            value = child.value.strip().upper()
            if value in _NONCURRENT:
                out.add(value)
    return out


def _caller_time_expr(node: ast.AST, params: set[str], tainted: set[str]) -> bool:
    if _contains_name(node, tainted):
        return True
    if not _contains_name(node, params):
        return False
    return _has_word(node, _TIME_WORDS)


def _deadline_expr(node: ast.AST) -> bool:
    return _has_word(node, _DEADLINE_WORDS)


def _assignment_targets(node: ast.AST) -> list[str]:
    targets: list[ast.AST] = []
    if isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
        if isinstance(node, ast.Assign):
            targets.extend(node.targets)
        else:
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


def _time_taint(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    params = set(_function_params(fn))
    tainted: set[str] = set()
    for _ in range(8):
        before = set(tainted)
        for node in ast.walk(fn):
            value = _assignment_value(node)
            if value is None:
                continue
            if _caller_time_expr(value, params, tainted):
                tainted.update(_assignment_targets(node))
        if tainted == before:
            break
    return tainted


def _process_clock_sampled(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for child in ast.walk(fn):
        if not isinstance(child, ast.Call):
            continue
        name = _name(child.func).lower()
        if name in {"datetime.now", "datetime.utcnow", "time.time", "time.time_ns", "_process_now"}:
            return True
        if name.endswith(".now") and not child.args:
            return True
        if name.endswith("process_now") or name.endswith("current_utc") or name.endswith("utc_now"):
            return True
    return False


def _rule_001(path: str, fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[Finding]:
    if not _public(fn):
        return []
    params = set(_function_params(fn))
    tainted = _time_taint(fn)
    for node in ast.walk(fn):
        if not isinstance(node, ast.Compare):
            continue
        operands = [node.left, *node.comparators]
        for i, left in enumerate(operands):
            for j, right in enumerate(operands):
                if i != j and _caller_time_expr(left, params, tainted) and _deadline_expr(right):
                    return [Finding(
                        path, node.lineno, node.col_offset + 1, "CRG001",
                        "caller-derived time is compared with a deadline/expiry boundary; current readiness can be backdated",
                        fn.name,
                    )]
    return []


def _rule_002(path: str, fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[Finding]:
    if not _public(fn) or not _readiness_function(fn):
        return []
    positives = _positive_strings(fn)
    if not positives:
        return []
    params = _function_params(fn)
    risky = [p for p in params if any(word in p.lower() for word in _TIME_WORDS)]
    if not risky:
        return []
    return [Finding(
        path, fn.lineno, fn.col_offset + 1, "CRG002",
        f"public current-positive surface accepts caller-selectable time/clock parameter(s): {', '.join(risky)}",
        fn.name,
    )]


def _rule_003(path: str, fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[Finding]:
    if not _public(fn) or not _readiness_function(fn) or fn.name.lower().startswith("verify"):
        return []
    positives = _positive_strings(fn)
    if not positives:
        return []
    params = _function_params(fn)
    if not params:
        return []
    if any(any(word in p.lower() for word in _AUTHORITY_WORDS) for p in params):
        return []
    return [Finding(
        path, fn.lineno, fn.col_offset + 1, "CRG003",
        f"public readiness surface can emit {sorted(positives)!r} from one caller data parameter without independent authority/root/receipt evidence",
        fn.name,
    )]


def _retained_time_expr(node: ast.AST, params: set[str]) -> bool:
    return _contains_name(node, params) and _has_word(node, _TIME_WORDS)


def _call_is_current_projection(call: ast.Call) -> bool:
    name = _name(call.func).lower()
    return any(word in name for word in ("compile", "evaluate", "qualify", "project", "semantic", "readiness", "gate"))


def _rule_004(path: str, fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[Finding]:
    if not _public(fn) or "verify" not in fn.name.lower():
        return []
    if _process_clock_sampled(fn):
        return []
    params = set(_function_params(fn))
    for child in ast.walk(fn):
        if not isinstance(child, ast.Call) or not _call_is_current_projection(child):
            continue
        supplied = [*child.args, *(kw.value for kw in child.keywords)]
        if any(_retained_time_expr(arg, params) for arg in supplied):
            return [Finding(
                path, child.lineno, child.col_offset + 1, "CRG004",
                "public verifier replays caller/report retained time into a current projection without sampling process UTC",
                fn.name,
            )]
    return []


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
        return [Finding(path, line, col, "CRG000", f"source parse failure: {exc.msg if isinstance(exc, SyntaxError) else exc}", None)]

    out: list[Finding] = []
    functions = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    for fn in functions:
        out.extend(_rule_001(path, fn))
        out.extend(_rule_002(path, fn))
        out.extend(_rule_003(path, fn))
        out.extend(_rule_004(path, fn))
    return sorted(set(out))


def _parse_expiry(value: Any, where: str) -> date:
    if type(value) is not str:
        raise PolicyError(f"{where}.expires must be YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise PolicyError(f"{where}.expires must be canonical YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise PolicyError(f"{where}.expires must be canonical YYYY-MM-DD")
    return parsed


def load_policy(raw: bytes | str, *, today: date | None = None) -> list[Exemption]:
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise PolicyError("policy is not strict UTF-8") from exc
    try:
        data = json.loads(raw, object_pairs_hook=_no_duplicate_keys)
    except (json.JSONDecodeError, PolicyError) as exc:
        if isinstance(exc, PolicyError):
            raise
        raise PolicyError("policy is invalid JSON") from exc
    if type(data) is not dict or set(data) != {"schema", "exemptions"}:
        raise PolicyError("policy must contain exactly schema + exemptions")
    if data["schema"] != "commons-current-readiness-guard-policy/v1":
        raise PolicyError("unsupported policy schema")
    if type(data["exemptions"]) is not list:
        raise PolicyError("policy.exemptions must be a list")
    today = today or datetime.now(timezone.utc).date()
    out: list[Exemption] = []
    seen: set[tuple[str, str]] = set()
    for i, row in enumerate(data["exemptions"]):
        where = f"exemptions[{i}]"
        if type(row) is not dict or set(row) != _POLICY_KEYS:
            raise PolicyError(f"{where} must contain exactly {sorted(_POLICY_KEYS)}")
        path = row["path"]
        rule = row["rule"]
        if type(path) is not str or not path.startswith("revenue/") or PurePosixPath(path).is_absolute() or ".." in PurePosixPath(path).parts:
            raise PolicyError(f"{where}.path must be a relative revenue/ path")
        if type(rule) is not str or rule not in RULES or rule == "CRG000" or not _RULE_RE.fullmatch(rule):
            raise PolicyError(f"{where}.rule must name an exemptible CRG rule")
        rationale = row["rationale"]
        owner = row["owner"]
        issue = row["issue"]
        if any(type(v) is not str or len(v.strip()) < 3 for v in (rationale, owner, issue)):
            raise PolicyError(f"{where} rationale/owner/issue must be nontrivial strings")
        expires = _parse_expiry(row["expires"], where)
        if expires < today:
            raise PolicyError(f"{where} exemption expired on {expires.isoformat()}")
        key = (path, rule)
        if key in seen:
            raise PolicyError(f"duplicate exemption for {path} {rule}")
        seen.add(key)
        out.append(Exemption(path, rule, rationale.strip(), owner.strip(), issue.strip(), expires))
    return sorted(out, key=lambda x: (x.path, x.rule))


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise PolicyError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def apply_policy(findings: Iterable[Finding], exemptions: Iterable[Exemption]) -> list[Finding]:
    allowed = {(x.path, x.rule) for x in exemptions}
    return [f for f in sorted(findings) if (f.path, f.rule) not in allowed]


def scan_paths(paths: Iterable[str | Path], *, root: str | Path = ".", exemptions: Iterable[Exemption] = ()) -> list[Finding]:
    root_path = Path(root).resolve()
    out: list[Finding] = []
    for item in sorted({str(p) for p in paths}):
        p = Path(item)
        full = (root_path / p).resolve() if not p.is_absolute() else p.resolve()
        try:
            rel = full.relative_to(root_path).as_posix()
        except ValueError:
            out.append(Finding(str(p), 1, 1, "CRG000", "scan path escapes repository root", None))
            continue
        if not rel.startswith("revenue/") or not rel.endswith(".py"):
            continue
        try:
            raw = full.read_bytes()
        except OSError as exc:
            out.append(Finding(rel, 1, 1, "CRG000", f"source read failure: {exc}", None))
            continue
        out.extend(analyze_source(raw, path=rel))
    return apply_policy(out, exemptions)
