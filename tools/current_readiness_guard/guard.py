from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from ._model import Exemption, Finding, PolicyError, RULES, _POLICY_KEYS, _RULE_RE
from ._analyzer import analyze_source


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


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise PolicyError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


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
    for index, row in enumerate(data["exemptions"]):
        where = f"exemptions[{index}]"
        if type(row) is not dict or set(row) != _POLICY_KEYS:
            raise PolicyError(f"{where} must contain exactly {sorted(_POLICY_KEYS)}")
        path = row["path"]
        rule = row["rule"]
        if (
            type(path) is not str
            or not path.startswith("revenue/")
            or PurePosixPath(path).is_absolute()
            or ".." in PurePosixPath(path).parts
        ):
            raise PolicyError(f"{where}.path must be a relative revenue/ path")
        if type(rule) is not str or rule not in RULES or rule == "CRG000" or not _RULE_RE.fullmatch(rule):
            raise PolicyError(f"{where}.rule must name an exemptible CRG rule")
        rationale = row["rationale"]
        owner = row["owner"]
        issue = row["issue"]
        if any(type(value) is not str or len(value.strip()) < 3 for value in (rationale, owner, issue)):
            raise PolicyError(f"{where} rationale/owner/issue must be nontrivial strings")
        expires = _parse_expiry(row["expires"], where)
        if expires < today:
            raise PolicyError(f"{where} exemption expired on {expires.isoformat()}")
        key = (path, rule)
        if key in seen:
            raise PolicyError(f"duplicate exemption for {path} {rule}")
        seen.add(key)
        out.append(Exemption(path, rule, rationale.strip(), owner.strip(), issue.strip(), expires))
    return sorted(out, key=lambda item: (item.path, item.rule))


def apply_policy(findings: Iterable[Finding], exemptions: Iterable[Exemption]) -> list[Finding]:
    allowed = {(item.path, item.rule) for item in exemptions}
    return [finding for finding in sorted(findings) if (finding.path, finding.rule) not in allowed]


def scan_paths(
    paths: Iterable[str | Path],
    *,
    root: str | Path = ".",
    exemptions: Iterable[Exemption] = (),
) -> list[Finding]:
    root_path = Path(root).resolve()
    out: list[Finding] = []
    for item in sorted({str(path) for path in paths}):
        candidate = Path(item)
        full = (root_path / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
        try:
            relative = full.relative_to(root_path).as_posix()
        except ValueError:
            out.append(Finding(str(candidate), 1, 1, "CRG000", "scan path escapes repository root", None))
            continue
        if not relative.startswith("revenue/") or not relative.endswith(".py"):
            continue
        try:
            raw = full.read_bytes()
        except OSError as exc:
            out.append(Finding(relative, 1, 1, "CRG000", f"source read failure: {exc}", None))
            continue
        out.extend(analyze_source(raw, path=relative))
    return apply_policy(out, exemptions)
