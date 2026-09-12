#!/usr/bin/env python3
"""Deterministic exact-engine product-domain audit for PR #12054."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CARRIER_PATH = ROOT / "revenue/kaggriculture/cloud-opponent-league/lark-responsive/pressure_delay_invariance.py"
MECHANICS_PATH = ROOT / "revenue/kaggriculture/cloud-execution-lab/mechanics.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sell(product: str, quantity: int, tag: str) -> dict[str, object]:
    return {"action": "SELL", "type": product, "quantity": quantity, "tag": tag}


def run() -> dict[str, object]:
    candidate = _load_module("_titan_pressure_domain_candidate", CARRIER_PATH)
    mechanics = _load_module("_titan_pressure_domain_mechanics", MECHANICS_PATH)
    exact_products = tuple(mechanics.PRODUCTS)
    if candidate.PRODUCTS != exact_products:
        raise AssertionError(
            f"product domain mismatch: candidate={candidate.PRODUCTS!r} engine={exact_products!r}"
        )

    quote = lambda product, stock: mechanics.market_price(product, stock)
    cases = 0
    safe_cases = 0
    reasons: Counter[str] = Counter()
    per_product: dict[str, dict[str, int]] = {}
    for product in exact_products:
        params = mechanics.MARKET_PARAMS[product]
        i0 = int(params["I0"])
        target = int(params["T"])
        stocks = sorted(
            {
                max(0, i0 - 2 * target),
                max(0, i0 - target),
                max(0, i0 - 1),
                i0,
                i0 + 1,
                i0 + target,
                i0 + 2 * target,
            }
        )
        product_cases = 0
        product_safe = 0
        for stock in stocks:
            for quantity in (1, 2, 3, 5):
                for delay in (0, 1, 2, 5, 13, 34):
                    certificate = candidate.certify_delay_invariance(
                        product,
                        stock,
                        quantity,
                        delay,
                        quote,
                    )
                    oracle = candidate.exhaustive_delay_invariant(
                        product,
                        stock,
                        quantity,
                        delay,
                        quote,
                    )
                    if certificate.safe != oracle:
                        raise AssertionError(
                            (product, stock, quantity, delay, certificate, oracle)
                        )
                    cases += 1
                    product_cases += 1
                    safe_cases += int(certificate.safe)
                    product_safe += int(certificate.safe)
                    reasons[certificate.reason] += 1
        per_product[product] = {"cases": product_cases, "safe": product_safe}

    inventory = {product: 0 for product in exact_products}
    bounds = {product: 4 for product in exact_products}
    partition_cases = 0
    for index, exposed_product in enumerate(exact_products):
        neutral_product = exact_products[(index + 1) % len(exact_products)]
        neutral = _sell(neutral_product, 2, "neutral")
        exposed = _sell(exposed_product, 1, "exposed")
        pressures = {product: 0 for product in exact_products}
        pressures[exposed_product] = 1
        result = candidate.certified_pressure_partition(
            [neutral, exposed],
            pressure_by_product=pressures,
            inventory=inventory,
            max_rival_units=bounds,
            price_by_stock=lambda _product, _stock: 7,
        )
        if result.actions != (exposed, neutral) or not result.changed:
            raise AssertionError((exposed_product, result))
        partition_cases += 1

    invalid = candidate.exact_sale_receipt("CORN", 0, 1, lambda _p, _s: 7)
    if invalid is not None:
        raise AssertionError(f"non-engine CORN was accepted: {invalid}")

    return {
        "schema": "titan.pressure-product-domain-audit.v1",
        "predecessor_commit": "1825dc464c1b1e1ee9a3b0e52e5f38370668d32b",
        "engine_products": list(exact_products),
        "candidate_products": list(candidate.PRODUCTS),
        "domain_identity": True,
        "non_engine_corn_rejected": True,
        "exact_certificate_oracle_cases": cases,
        "exact_certificate_safe_cases": safe_cases,
        "certificate_reasons": dict(sorted(reasons.items())),
        "per_product": per_product,
        "all_product_partition_cases": partition_cases,
        "carrier_sha256": _sha256(CARRIER_PATH),
        "mechanics_sha256": _sha256(MECHANICS_PATH),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    receipt = run()
    encoded = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
