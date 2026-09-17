from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

# Public compatibility constants. Runtime semantics below capture one cooperative
# in-process generation and do not late-resolve these globals. CPython closure cells
# remain reflectively writable by hostile same-process code; the emitted receipt makes
# that unsupported boundary explicit instead of claiming machine-strong immutability.
SCHEMA = "invest_appalachia_framer_lms.partner_workshare.v1"
OPPORTUNITY_ID = "INVEST-APPALACHIA-FRAMER-LMS-20260916"
QUALIFICATION_GENERATION_SHA256 = "13018ee1b2fe14b3b8171acc734e0ea57a52006a5e96f095600e88bcbca63a02"
WORKSHARE_SHA256 = "9825e29c23028dffb23158f7b1db8fb751ba45c0ecedad681764d77bc5ac3b4d"
PRICE_USD = 24000
BUYER_CAP_USD = 60000
PUBLIC_API_BOUNDARY = "COOPERATIVE_IN_PROCESS_ONLY_NOT_HOSTILE_RUNTIME"


class WorkshareError(ValueError):
    pass


def _make_semantic_generation():
    """Capture the reviewed commercial generation for cooperative in-process use."""

    schema = "invest_appalachia_framer_lms.partner_workshare.v1"
    opportunity_id = "INVEST-APPALACHIA-FRAMER-LMS-20260916"
    qualification_sha256 = "13018ee1b2fe14b3b8171acc734e0ea57a52006a5e96f095600e88bcbca63a02"
    workshare_sha256 = "9825e29c23028dffb23158f7b1db8fb751ba45c0ecedad681764d77bc5ac3b4d"
    price_usd = 24000
    buyer_cap_usd = 60000
    integrity_boundary_items = (
        ("schema", "invest_appalachia_framer_lms.integrity_boundary.v1"),
        ("public_api_boundary", "COOPERATIVE_IN_PROCESS_ONLY_NOT_HOSTILE_RUNTIME"),
        ("resists_module_global_rebinding", True),
        ("resists_cpython_closure_cell_mutation", False),
        ("hostile_same_process_python_supported", False),
        ("machine_strong_same_process_integrity_claimed", False),
        ("externally_isolated_source_verified_runner_provided", False),
    )

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

    def boundary_projection() -> dict[str, Any]:
        return dict_type(integrity_boundary_items)

    def validate_qualification(current_packet: Any) -> None:
        if dgst(current_packet) != qualification_sha256:
            raise error("qualification generation changed; workshare requires review")

    def validate_ws(value: Any) -> dict[str, Any]:
        if dgst(value) != workshare_sha256:
            raise error("workshare does not match reviewed commercial generation")
        ws = exact(
            value,
            {
                "schema",
                "opportunity_id",
                "qualification_generation_sha256",
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

    def evaluate_generation(current_packet: Any, workshare: Any) -> dict[str, Any]:
        validate_qualification(current_packet)
        ws = validate_ws(workshare)
        receipt = {
            "schema": "invest_appalachia_framer_lms.partner_workshare_receipt.v1",
            "opportunity_id": opportunity_id,
            "qualification_generation_sha256": qualification_sha256,
            "workshare_sha256": workshare_sha256,
            "integrity_boundary": boundary_projection(),
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


def _make_main(evaluate_fn, load_fn, path_type, json_dumps):
    def main() -> int:
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--current-packet", required=True, type=path_type)
        parser.add_argument("--workshare", required=True, type=path_type)
        args = parser.parse_args()
        print(
            json_dumps(
                evaluate_fn(load_fn(args.current_packet), load_fn(args.workshare)),
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    return main


main = _make_main(evaluate, load_json, Path, json.dumps)
del _make_main


if __name__ == "__main__":
    raise SystemExit(main())
