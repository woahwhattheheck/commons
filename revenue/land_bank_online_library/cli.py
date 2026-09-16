"""CLI for the Land Bank T12-09-26 non-authorizing teaming carrier."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .core import EvidenceRef, PaidWorkshare, PrimeCandidate, SourceCustody, compile_readiness, render_markdown

_ALLOWED_TOP = {"source_custody", "prime", "paid_workshare"}
_ALLOWED_SOURCE = {
    "candidate_buyer_source_path",
    "candidate_buyer_source_label",
    "candidate_buyer_source_locator",
    "expected_sha256",
    "secondary_listing_refs",
}
_ALLOWED_PRIME = {"legal_name", "evidence"}
_ALLOWED_WORKSHARE = {"owner", "deliverables", "acceptance_criteria", "exclusions", "commercial_state"}
_ALLOWED_REF = {"label", "locator", "note"}


def _load(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_bytes())
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise ValueError("invalid input JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("input must be a JSON object")
    return data


def _strict_object(value: Any, *, name: str, allowed: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ValueError(f"{name} contains unknown keys: {', '.join(unknown)}")
    return value


def _string_list(value: Any, *, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{name} must be a list of strings")
    return tuple(value)


def _ref(value: Any) -> EvidenceRef | None:
    if value is None:
        return None
    obj = _strict_object(value, name="evidence reference", allowed=_ALLOWED_REF)
    return EvidenceRef(
        label=obj.get("label", ""),
        locator=obj.get("locator", ""),
        note=obj.get("note", ""),
    )


def _refs(value: Any) -> tuple[EvidenceRef, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError("secondary_listing_refs must be a list")
    out: list[EvidenceRef] = []
    for item in value:
        ref = _ref(item)
        if ref is not None:
            out.append(ref)
    return tuple(out)


def compile_from_dict(data: dict[str, Any]) -> dict[str, Any]:
    unknown_top = sorted(set(data) - _ALLOWED_TOP)
    if unknown_top:
        raise ValueError(f"input contains unknown top-level keys: {', '.join(unknown_top)}")

    source_data = _strict_object(data.get("source_custody", {}), name="source_custody", allowed=_ALLOWED_SOURCE)
    prime_data = _strict_object(data.get("prime", {}), name="prime", allowed=_ALLOWED_PRIME)
    workshare_data = _strict_object(data.get("paid_workshare", {}), name="paid_workshare", allowed=_ALLOWED_WORKSHARE)

    raw_evidence = prime_data.get("evidence", {})
    if not isinstance(raw_evidence, dict):
        raise ValueError("prime.evidence must be an object")

    path_value = source_data.get("candidate_buyer_source_path")
    if path_value is not None and not isinstance(path_value, str):
        raise ValueError("candidate_buyer_source_path must be a string or null")

    source = SourceCustody(
        candidate_buyer_source_path=path_value,
        candidate_buyer_source_label=source_data.get("candidate_buyer_source_label", "Candidate buyer source"),
        candidate_buyer_source_locator=source_data.get("candidate_buyer_source_locator", ""),
        expected_sha256=source_data.get("expected_sha256", ""),
        secondary_listing_refs=_refs(source_data.get("secondary_listing_refs")),
    )
    prime = PrimeCandidate(
        legal_name=prime_data.get("legal_name", ""),
        evidence={str(key): _ref(value) for key, value in raw_evidence.items()},
    )
    workshare = PaidWorkshare(
        owner=workshare_data.get("owner", ""),
        deliverables=_string_list(workshare_data.get("deliverables", []), name="paid_workshare.deliverables"),
        acceptance_criteria=_string_list(workshare_data.get("acceptance_criteria", []), name="paid_workshare.acceptance_criteria"),
        exclusions=_string_list(workshare_data.get("exclusions", []), name="paid_workshare.exclusions"),
        commercial_state=workshare_data.get("commercial_state", "PAID_SCOPE_TO_BE_AGREED"),
    )
    return compile_readiness(source_custody=source, prime=prime, workshare=workshare)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--markdown-out", type=Path)
    args = parser.parse_args(argv)

    try:
        pack = compile_from_dict(_load(args.input))
    except (TypeError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2

    rendered = json.dumps(pack, sort_keys=True, indent=2) + "\n"
    if args.json_out:
        args.json_out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    if args.markdown_out:
        args.markdown_out.write_text(render_markdown(pack), encoding="utf-8")

    # Deliberately non-authorizing: no public JSON document or locally retained
    # file can turn this CLI into a procurement/submission authority oracle.
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
