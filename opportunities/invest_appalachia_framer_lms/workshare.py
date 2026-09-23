from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

# Compatibility constants. Runtime semantics capture an independent immutable
# generation at import time and do not late-resolve these globals.
SCHEMA = "invest_appalachia_framer_lms.partner_workshare.v1"
OPPORTUNITY_ID = "INVEST-APPALACHIA-FRAMER-LMS-20260916"
QUALIFICATION_GENERATION_SHA256 = "79e1bfc46617239e1c05b4c22e97e4d6672743103041e2b6b7b3e71bd6d1b30d"
WORKSHARE_SHA256 = "33548cdf0b30a664b847eeea0eb6ad6d7a06b2a8d35ddfa91be0953d1f564636"
REQUIREMENTS_SHA256 = "5d012da1612cb220cfe0d7c4c02c47175a726bad1254855240c24afa6926ef66"
SOURCE_MANIFEST_SHA256 = "a70c78c77a7084ef9cf1499f0e7831e2031d4e635405c8955df25b57c6f01093"
PRICE_USD = 24000
BUYER_CAP_USD = 60000


class WorkshareError(ValueError):
    pass


def _make_semantic_generation():
    """Capture the reviewed commercial generation against post-import rebinding."""
    schema = "invest_appalachia_framer_lms.partner_workshare.v1"
    opportunity_id = "INVEST-APPALACHIA-FRAMER-LMS-20260916"
    qualification_sha256 = "79e1bfc46617239e1c05b4c22e97e4d6672743103041e2b6b7b3e71bd6d1b30d"
    workshare_sha256 = "33548cdf0b30a664b847eeea0eb6ad6d7a06b2a8d35ddfa91be0953d1f564636"
    requirements_sha256 = "5d012da1612cb220cfe0d7c4c02c47175a726bad1254855240c24afa6926ef66"
    source_sha256 = "a70c78c77a7084ef9cf1499f0e7831e2031d4e635405c8955df25b57c6f01093"
    source_binding = {"generation_id": "framer-reviewed-sources-20260919", "source_manifest_sha256": source_sha256, "requirements_sha256": requirements_sha256}
    base = Path(__file__).resolve().parent
    price_usd = 24000
    buyer_cap_usd = 60000

    error = WorkshareError
    json_dumps = json.dumps
    json_loads = json.loads
    sha256 = hashlib.sha256
    type_fn = type
    dict_type = dict
    set_fn = set
    any_fn = any
    str_type = str
    type_error = TypeError
    value_error = ValueError
    unicode_error = UnicodeError
    recursion_error = RecursionError
    overflow_error = OverflowError
    os_error = OSError
    json_decode_error = json.JSONDecodeError

    def canon(value: Any) -> bytes:
        try:
            return json_dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8", "strict")
        except (type_error, value_error, unicode_error, recursion_error, overflow_error) as exc:
            raise error(f"cannot canonicalize: {exc}") from exc

    def dgst(value: Any) -> str:
        return sha256(canon(value)).hexdigest()

    def exact(value: Any, keys: set[str], where: str) -> dict[str, Any]:
        if type_fn(value) is not dict_type or set_fn(value) != keys:
            raise error(f"{where}: exact object contract mismatch")
        return value

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in items:
            if key in out:
                raise error(f"duplicate JSON key: {key!r}")
            out[key] = value
        return out

    def reject_constant(token: str) -> Any:
        raise error(f"invalid JSON constant: {token}")

    def load(path: Path) -> Any:
        try:
            value = json_loads(
                path.read_text(encoding="utf-8"),
                object_pairs_hook=pairs,
                parse_constant=reject_constant,
            )
            canon(value)
            return value
        except error:
            raise
        except (os_error, unicode_error, json_decode_error, value_error, recursion_error, overflow_error) as exc:
            raise error(f"invalid JSON: {exc}") from exc

    def validate_sources(requirements=None, source_manifest=None) -> None:
        requirements = load(base / "requirements.json") if requirements is None else requirements
        source_manifest = load(base / "source_generation.json") if source_manifest is None else source_manifest
        if dgst(requirements) != requirements_sha256:
            raise error("requirements do not match reviewed source generation")
        if dgst(source_manifest) != source_sha256:
            raise error("source manifest does not match reviewed source generation")

    def validate_qualification(current_packet: Any) -> None:
        if dgst(current_packet) != qualification_sha256:
            raise error("qualification generation changed; workshare requires review")

    def validate_ws(value: Any) -> dict[str, Any]:
        captured = canon(value)
        if sha256(captured).hexdigest() != workshare_sha256:
            raise error("workshare does not match reviewed commercial generation")
        ws = exact(
            json_loads(captured),
            {
                "schema",
                "opportunity_id",
                "qualification_generation_sha256",
                "source_generation",
                "commercial",
                "scope",
                "excludes",
                "qualified_prime_must_own",
                "single_writer_gate",
                "authority",
            },
            "workshare",
        )
        if ws["schema"] != schema or ws["opportunity_id"] != opportunity_id:
            raise error("workshare identity mismatch")
        if ws["qualification_generation_sha256"] != qualification_sha256:
            raise error("qualification-generation binding mismatch")
        if ws["source_generation"] != source_binding:
            raise error("source-generation binding mismatch")

        commercial = exact(
            ws["commercial"],
            {"price_usd", "commercial_status", "buyer_budget_integration_state"},
            "commercial",
        )
        if commercial != {
            "price_usd": price_usd,
            "commercial_status": "PROPOSED_NOT_ACCEPTED",
            "buyer_budget_integration_state": "UNRESOLVED_QUALIFIED_PRIME_MUST_INTEGRATE_WITH_60000_CAP",
        }:
            raise error("commercial truth mismatch")

        gate = exact(
            ws["single_writer_gate"],
            {
                "fresh_opportunity_and_route_census_required",
                "muse_dm_clearance_required",
                "maximum_external_messages_if_cleared",
            },
            "single_writer_gate",
        )
        if gate != {
            "fresh_opportunity_and_route_census_required": True,
            "muse_dm_clearance_required": True,
            "maximum_external_messages_if_cleared": 1,
        }:
            raise error("single-writer gate mismatch")

        authority = exact(
            ws["authority"],
            {
                "partner_contact_authorized",
                "buyer_contact_authorized",
                "submission_authorized",
                "signature_authorized",
                "contract_acceptance_authorized",
                "payment_authorized",
                "award_or_revenue_asserted",
            },
            "authority",
        )
        if any_fn(item is not False for item in authority.values()):
            raise error("external/commercial authority must remain all false")
        return ws

    def evaluate_generation(current_packet: Any, workshare: Any, requirements=None, source_manifest=None) -> dict[str, Any]:
        validate_qualification(current_packet)
        validate_sources(requirements, source_manifest)
        ws = validate_ws(workshare)
        receipt = {
            "schema": "invest_appalachia_framer_lms.partner_workshare_receipt.v2",
            "opportunity_id": opportunity_id,
            "qualification_generation_sha256": qualification_sha256,
            "workshare_sha256": workshare_sha256,
            "source_generation": dict_type(source_binding),
            "buyer_source_status": "RECOVERED_BUYER_DOCUMENTS",
            "bidder_response_status": "INCOMPLETE",
            "us_prime_eligibility": "UNVERIFIED",
            "prime_posture": "NO_CHANGE_PRIME_HOLD",
            "workshare_posture": "READY_FOR_INTERNAL_QUALIFIED_PRIME_SELECTION",
            "specialist_price_usd": price_usd,
            "buyer_budget_cap_usd": buyer_cap_usd,
            "buyer_budget_fit": "UNRESOLVED_QUALIFIED_PRIME_MUST_INTEGRATE_WITH_60000_CAP",
            "commercial_status": "PROPOSED_NOT_ACCEPTED",
            "money_state": "NO_ACCEPTANCE_NO_RECEIVABLE_NO_REVENUE",
            "fresh_opportunity_and_route_census_required": True,
            "muse_dm_clearance_required": True,
            "maximum_external_messages_if_cleared": 1,
            **{key: False for key in ws["authority"]},
        }
        receipt["receipt_sha256"] = dgst(receipt)
        return receipt

    return canon, dgst, load, validate_qualification, validate_ws, evaluate_generation


(
    canonical_json,
    digest,
    load_json,
    validate_qualification_generation,
    validate_workshare,
    evaluate,
) = _make_semantic_generation()
del _make_semantic_generation


def _make_main(evaluate_fn, load_fn, path_type, json_dumps, error_type):
    base = path_type(__file__).resolve().parent

    def main(argv=None) -> int:
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--current-packet", required=True, type=path_type)
        parser.add_argument("--workshare", required=True, type=path_type)
        parser.add_argument("--requirements", type=path_type, default=base / "requirements.json")
        parser.add_argument("--source-manifest", type=path_type, default=base / "source_generation.json")
        args = parser.parse_args(argv)
        try:
            receipt = evaluate_fn(load_fn(args.current_packet), load_fn(args.workshare), load_fn(args.requirements), load_fn(args.source_manifest))
        except error_type as exc:
            parser.error(str(exc))
        print(json_dumps(receipt, indent=2, sort_keys=True))
        return 0

    return main


main = _make_main(evaluate, load_json, Path, json.dumps, WorkshareError)
del _make_main


if __name__ == "__main__":
    raise SystemExit(main())
