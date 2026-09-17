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

# Every caller-controlled free-text value that can reach buyer-facing markdown
# passes this single boundary. Compatibility spelling is canonicalized before
# assertion matching; invisible/control text fails closed rather than being
# silently deleted. Punctuation/Markdown is folded before semantic matching so
# visible text such as "Buyer **accepted**" cannot split an assertion.
_FORBIDDEN_RENDERED_ASSERTIONS = (
    re.compile(r"\bbuyer\s+(?:has\s+)?accepted\b", re.I),
    re.compile(r"\baccepted\s+by\s+(?:the\s+)?buyer\b", re.I),
    re.compile(r"\b(?:we|tjlabs)\s+(?:have\s+|has\s+)?(?:been\s+)?awarded\b", re.I),
    re.compile(r"\b(?:work|contract|engagement)\s+(?:(?:was|is)\s+|has\s+been\s+)?awarded\b", re.I),
    re.compile(r"\baward\s+(?:is\s+)?secured\b", re.I),
    re.compile(r"\b(?:already\s+|were\s+|was\s+)?paid\b", re.I),
    re.compile(r"\bpayment\s+(?:(?:was|is)\s+|has\s+been\s+)?(?:received|settled)\b", re.I),
    re.compile(r"\binvoice\s+(?:(?:was|is)\s+|has\s+been\s+)?(?:issued|sent)\b", re.I),
    re.compile(r"\b(?:signed\s+contract|contract\s+(?:(?:was|is)\s+|has\s+been\s+)?signed)\b", re.I),
    re.compile(r"\bbooked\s+revenue\b", re.I),
    re.compile(r"\brecognized\s+revenue\b", re.I),
    re.compile(r"\b(?:existing|current)\s+customer\b", re.I),
    re.compile(r"\bcustomer\s+relationship\s+(?:(?:is|was)\s+)?(?:established|confirmed|active)\b", re.I),
    re.compile(r"\bguaranteed\s+(?:savings|outcome|roi|acceptance|award)\b", re.I),
)


def _has_forbidden_unicode(text: str) -> bool:
    for ch in text:
        category = unicodedata.category(ch)
        if category.startswith("C") or category in {"Zl", "Zp"}:
            return True
    return False


def _commercial_skeleton(text: str) -> str:
    # NFKC has already collapsed compatibility forms. Preserve letters/numbers
    # and turn punctuation/Markdown separators into canonical spaces before
    # testing commercial semantics.
    folded = text.casefold()
    skeleton = "".join(ch if ch.isalnum() else " " for ch in folded)
    return " ".join(skeleton.split())


def _rendered_text(value: Any, where: str, *, max_len: int) -> str:
    if not isinstance(value, str) or not value:
        raise WorkshareError(f"{where} must be a non-empty string <= {max_len}")
    try:
        value.encode("utf-8", "strict")
    except UnicodeEncodeError:
        raise WorkshareError(f"{where} must be Unicode scalar text") from None
    if _has_forbidden_unicode(value):
        raise WorkshareError(f"{where} contains Unicode control/format/private text")

    text = unicodedata.normalize("NFKC", value)
    if _has_forbidden_unicode(text):
        raise WorkshareError(f"{where} normalizes to Unicode control/format/private text")

    # Canonicalize whitespace before claim matching and receipt hashing so
    # spacing variants cannot create semantically equivalent bypasses.
    text = " ".join(text.split()).strip()
    if not text or len(text) > max_len:
        raise WorkshareError(f"{where} must normalize to a non-empty string <= {max_len}")
    skeleton = _commercial_skeleton(text)
    for pattern in _FORBIDDEN_RENDERED_ASSERTIONS:
        if pattern.search(skeleton):
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
    # The byte-identical legacy generation owns schema, economics, evidence
    # state, pack selection, and token gates. This successor adds only the
    # buyer-facing rendered-text truth boundary.
    return _sanitize_normalized(_legacy.normalize_offer(raw))


def render_offer_markdown(normalized: Mapping[str, Any]) -> str:
    # Direct render callers must re-enter the complete normalization contract;
    # they cannot bypass token/economic/evidence gates by forging a normalized
    # mapping and calling the renderer directly.
    checked = normalize_offer(normalized)
    return _legacy.render_offer_markdown(checked)


def compile_offer(raw: Mapping[str, Any]) -> CompiledOffer:
    normalized = normalize_offer(raw)
    encoded = canonical_json(normalized).encode("utf-8")
    receipt = hashlib.sha256(encoded).hexdigest()
    return CompiledOffer(
        normalized=normalized,
        markdown=_legacy.render_offer_markdown(normalized),
        receipt_sha256=receipt,
    )


def _validated_compiled_offer(compiled: CompiledOffer) -> tuple[dict[str, Any], str]:
    # CompiledOffer is a public dataclass, so its fields are caller-controlled
    # at this boundary. A receipt is evidence only if the represented state can
    # be recompiled by the current generation and its derived fields agree.
    if not isinstance(compiled, CompiledOffer):
        raise WorkshareError("compiled offer must be CompiledOffer")
    normalized = normalize_offer(compiled.normalized)
    expected_markdown = _legacy.render_offer_markdown(normalized)
    expected_sha256 = hashlib.sha256(canonical_json(normalized).encode("utf-8")).hexdigest()
    if compiled.markdown != expected_markdown:
        raise WorkshareError("compiled markdown does not match normalized offer")
    if compiled.receipt_sha256 != expected_sha256:
        raise WorkshareError("compiled receipt hash does not match normalized offer")
    return normalized, expected_sha256


def render_receipt_json(compiled: CompiledOffer) -> str:
    normalized, expected_sha256 = _validated_compiled_offer(compiled)
    return canonical_json(
        {
            "schema": "human-reply-paid-workshare-receipt/v1",
            "offer_id": normalized["offer_id"],
            "pack_id": normalized["pack_id"],
            "commercial_state": COMMERCIAL_STATE,
            "normalized_sha256": expected_sha256,
        }
    )


def __getattr__(name: str) -> Any:
    return getattr(_legacy, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_legacy)))
