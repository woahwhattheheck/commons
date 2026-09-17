from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Mapping
from typing import Any

from . import _core_legacy as _legacy

SCHEMA = _legacy.SCHEMA
COMMERCIAL_STATE = _legacy.COMMERCIAL_STATE
WorkshareError = _legacy.WorkshareError
CompiledOffer = _legacy.CompiledOffer
strict_json_loads = _legacy.strict_json_loads
canonical_json = _legacy.canonical_json
pack_catalog = _legacy.pack_catalog
render_receipt_json = _legacy.render_receipt_json

# Screen the canonicalized text that is actually rendered, not only the raw
# spelling supplied by a caller. NFKC closes compatibility forms (for example
# full-width ASCII); all Unicode control/format/private/surrogate/unassigned
# code points are rejected so invisible separators cannot split assertions.
_FORBIDDEN_RENDERED_ASSERTIONS = (
    re.compile(r"\bbuyer (?:has )?accepted\b", re.I),
    re.compile(r"\b(?:we|tjlabs) (?:have |has )?(?:been )?awarded\b", re.I),
    re.compile(r"\baward (?:is )?secured\b", re.I),
    re.compile(r"\b(?:already |were |was )?paid\b", re.I),
    re.compile(r"\bpayment (?:was |is )?received\b", re.I),
    re.compile(r"\bbooked revenue\b", re.I),
    re.compile(r"\brecognized revenue\b", re.I),
    re.compile(r"\bsigned contract\b", re.I),
    re.compile(r"\b(?:existing|current) customer\b", re.I),
    re.compile(r"\bguaranteed (?:savings|outcome|roi|acceptance|award)\b", re.I),
)


def _rendered_text(value: Any, where: str, *, max_len: int) -> str:
    if not isinstance(value, str) or not value:
        raise WorkshareError(f"{where} must be a non-empty string <= {max_len}")
    try:
        value.encode("utf-8", "strict")
    except UnicodeEncodeError:
        raise WorkshareError(f"{where} must be Unicode scalar text") from None

    text = unicodedata.normalize("NFKC", value)
    if any(unicodedata.category(ch).startswith("C") for ch in text):
        raise WorkshareError(f"{where} contains Unicode control/format/private text")
    # Make whitespace semantics canonical before screening and receipt hashing.
    text = " ".join(text.split()).strip()
    if not text:
        raise WorkshareError(f"{where} must not be blank")
    if len(text) > max_len:
        raise WorkshareError(f"{where} must be a non-empty string <= {max_len}")
    for pattern in _FORBIDDEN_RENDERED_ASSERTIONS:
        if pattern.search(text):
            raise WorkshareError(f"{where} contains unsupported commercial/outcome assertion")
    return text


def _sanitize_normalized(normalized: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(normalized, Mapping):
        raise WorkshareError("normalized offer must be an object")
    out = dict(normalized)
    out["counterparty_label"] = _rendered_text(
        out.get("counterparty_label"), "counterparty_label", max_len=160
    )
    out["opportunity_label"] = _rendered_text(
        out.get("opportunity_label"), "opportunity_label", max_len=160
    )

    scope = out.get("scope")
    if not isinstance(scope, Mapping):
        raise WorkshareError("scope must be an object")
    scope_out = dict(scope)
    scope_out["one_line"] = _rendered_text(
        scope_out.get("one_line"), "scope.one_line", max_len=320
    )
    bounds = scope_out.get("input_bounds")
    if not isinstance(bounds, list) or not 1 <= len(bounds) <= 8:
        raise WorkshareError("scope.input_bounds must be an array of 1..8 one-line strings")
    clean_bounds = [
        _rendered_text(item, f"scope.input_bounds[{index}]", max_len=240)
        for index, item in enumerate(bounds)
    ]
    if len(set(clean_bounds)) != len(clean_bounds):
        raise WorkshareError("scope.input_bounds contains duplicate item after normalization")
    scope_out["input_bounds"] = clean_bounds
    out["scope"] = scope_out
    return out


def normalize_offer(raw: Mapping[str, Any]) -> dict[str, Any]:
    # Legacy normalization retains all already-reviewed schema/economics gates;
    # this successor adds the single caller-rendered-text boundary requested by
    # the post-merge review.
    return _sanitize_normalized(_legacy.normalize_offer(raw))


def render_offer_markdown(normalized: Mapping[str, Any]) -> str:
    # Direct render callers cannot bypass the same text boundary that compile
    # uses. Static pack text remains code-owned in the byte-identical legacy
    # module.
    return _legacy.render_offer_markdown(_sanitize_normalized(normalized))


def compile_offer(raw: Mapping[str, Any]) -> CompiledOffer:
    normalized = normalize_offer(raw)
    encoded = canonical_json(normalized).encode("utf-8")
    receipt = hashlib.sha256(encoded).hexdigest()
    return CompiledOffer(
        normalized=normalized,
        markdown=_legacy.render_offer_markdown(normalized),
        receipt_sha256=receipt,
    )


def __getattr__(name: str) -> Any:
    # Preserve compatibility for non-public legacy helpers without reopening
    # the public compile/render authority boundary above.
    return getattr(_legacy, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_legacy)))
