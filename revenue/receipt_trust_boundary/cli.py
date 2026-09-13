from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .trust import (
    TrustError,
    bind_external_commitment,
    inspect_receipt,
    load_json_bytes,
    read_plain_file,
    verify_contract,
)


def _emit(value: dict[str, object]) -> None:
    payload = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    os.write(1, payload)


def _load(path: Path):
    return load_json_bytes(read_plain_file(path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Classify self-digests separately from externally committed receipt evidence"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    inspect_p = sub.add_parser("inspect", help="check integrity only; never claims authenticity")
    inspect_p.add_argument("receipt", type=Path)

    bind_p = sub.add_parser("bind", help="bind a receipt to a caller-supplied external commitment")
    bind_p.add_argument("receipt", type=Path)
    bind_p.add_argument("--expected-receipt-sha256", required=True)

    verify_p = sub.add_parser("verify", help="bind receipt and an externally committed semantic contract")
    verify_p.add_argument("receipt", type=Path)
    verify_p.add_argument("--expected-receipt-sha256", required=True)
    verify_p.add_argument("--contract", type=Path, required=True)
    verify_p.add_argument("--expected-contract-sha256", required=True)

    args = parser.parse_args(argv)
    try:
        receipt = _load(args.receipt)
        if args.command == "inspect":
            result = inspect_receipt(receipt)
            _emit(result)
            return 0 if result["self_digest_matches"] else 2
        if args.command == "bind":
            _emit(bind_external_commitment(receipt, args.expected_receipt_sha256))
            return 0
        contract = _load(args.contract)
        _emit(
            verify_contract(
                receipt,
                args.expected_receipt_sha256,
                contract,
                args.expected_contract_sha256,
            )
        )
        return 0
    except TrustError as exc:
        _emit({
            "schema": "receipt-trust-boundary/error-v1",
            "status": "REJECT",
            "error": str(exc),
            "external_commitment_verified": False,
            "semantic_contract_verified": False,
            "source_authenticity_verified": False,
            "buyer_acceptance_verified": False,
            "payment_verified": False,
            "recognized_revenue_verified": False,
        })
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
