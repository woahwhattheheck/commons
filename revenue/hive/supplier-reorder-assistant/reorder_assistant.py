#!/usr/bin/env python3
"""Dependency-free supplier reorder planning and receipt application."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable


SCHEMA = "commons-supplier-reorder-v1"


class ReorderError(ValueError):
    """Raised when an input cannot produce a trustworthy draft."""


def _decimal(value: str, field: str, *, minimum: Decimal = Decimal("0")) -> Decimal:
    try:
        parsed = Decimal(value)
    except (InvalidOperation, TypeError) as exc:
        raise ReorderError(f"{field} must be a decimal") from exc
    if not parsed.is_finite() or parsed < minimum:
        raise ReorderError(f"{field} must be finite and >= {minimum}")
    return parsed


def _integer(value: str, field: str, *, minimum: int = 0) -> int:
    number = _decimal(value, field, minimum=Decimal(minimum))
    if number != number.to_integral_value():
        raise ReorderError(f"{field} must be an integer")
    return int(number)


def _money(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.01")), "f")


def _read_csv(path: Path, required: set[str]) -> list[dict[str, str]]:
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            fields = set(reader.fieldnames or [])
            missing = required - fields
            if missing:
                raise ReorderError(f"{path}: missing columns {sorted(missing)}")
            rows = []
            for line, row in enumerate(reader, start=2):
                normalized = {key: (value or "").strip() for key, value in row.items()}
                normalized["_line"] = str(line)
                rows.append(normalized)
            return rows
    except OSError as exc:
        raise ReorderError(f"cannot read {path}: {exc}") from exc


@dataclass(frozen=True)
class Stock:
    sku: str
    name: str
    on_hand: int
    on_order: int
    allocated: int
    unit: str

    @property
    def position(self) -> int:
        return self.on_hand + self.on_order - self.allocated


@dataclass(frozen=True)
class Rule:
    sku: str
    reorder_at: int
    target_stock: int
    preferred_supplier: str


@dataclass(frozen=True)
class Offer:
    supplier_id: str
    supplier_sku: str
    sku: str
    description: str
    unit_cost: Decimal
    available_qty: int
    lead_days: int
    alternative_for_sku: str


def load_stock(path: Path) -> dict[str, Stock]:
    rows = _read_csv(path, {"sku", "name", "on_hand", "on_order", "allocated", "unit"})
    result: dict[str, Stock] = {}
    for row in rows:
        sku = row["sku"]
        if not sku or sku in result:
            raise ReorderError(f"{path}:{row['_line']}: blank or duplicate sku {sku!r}")
        result[sku] = Stock(
            sku=sku,
            name=row["name"],
            on_hand=_integer(row["on_hand"], f"{sku}.on_hand"),
            on_order=_integer(row["on_order"], f"{sku}.on_order"),
            allocated=_integer(row["allocated"], f"{sku}.allocated"),
            unit=row["unit"],
        )
    return result


def load_rules(path: Path) -> dict[str, Rule]:
    rows = _read_csv(path, {"sku", "reorder_at", "target_stock", "preferred_supplier"})
    result: dict[str, Rule] = {}
    for row in rows:
        sku = row["sku"]
        if not sku or sku in result:
            raise ReorderError(f"{path}:{row['_line']}: blank or duplicate rule sku {sku!r}")
        reorder_at = _integer(row["reorder_at"], f"{sku}.reorder_at")
        target = _integer(row["target_stock"], f"{sku}.target_stock")
        if target <= reorder_at:
            raise ReorderError(f"{sku}.target_stock must exceed reorder_at")
        result[sku] = Rule(sku, reorder_at, target, row["preferred_supplier"])
    return result


def load_catalog(path: Path) -> list[Offer]:
    rows = _read_csv(
        path,
        {
            "supplier_id",
            "supplier_sku",
            "sku",
            "description",
            "unit_cost",
            "available_qty",
            "lead_days",
            "alternative_for_sku",
        },
    )
    seen: set[tuple[str, str]] = set()
    offers = []
    for row in rows:
        key = (row["supplier_id"], row["supplier_sku"])
        if not all(key) or key in seen:
            raise ReorderError(f"{path}:{row['_line']}: blank or duplicate supplier item {key}")
        seen.add(key)
        offers.append(
            Offer(
                supplier_id=key[0],
                supplier_sku=key[1],
                sku=row["sku"],
                description=row["description"],
                unit_cost=_decimal(row["unit_cost"], f"{key}.unit_cost"),
                available_qty=_integer(row["available_qty"], f"{key}.available_qty"),
                lead_days=_integer(row["lead_days"], f"{key}.lead_days"),
                alternative_for_sku=row["alternative_for_sku"],
            )
        )
    return offers


def build_plan(
    stock: dict[str, Stock], rules: dict[str, Rule], offers: Iterable[Offer], as_of: str
) -> dict[str, object]:
    try:
        date.fromisoformat(as_of)
    except ValueError as exc:
        raise ReorderError("as_of must be an ISO date (YYYY-MM-DD)") from exc

    unknown_rules = sorted(set(rules) - set(stock))
    if unknown_rules:
        raise ReorderError(f"rules reference unknown stock skus: {unknown_rules}")

    exact: dict[str, list[Offer]] = defaultdict(list)
    alternatives: dict[str, list[Offer]] = defaultdict(list)
    for offer in offers:
        if offer.sku:
            exact[offer.sku].append(offer)
        if offer.alternative_for_sku:
            alternatives[offer.alternative_for_sku].append(offer)

    po_lines: dict[str, list[dict[str, object]]] = defaultdict(list)
    exceptions: list[dict[str, object]] = []
    evaluated: list[dict[str, object]] = []

    for sku in sorted(rules):
        item, rule = stock[sku], rules[sku]
        needed = max(0, rule.target_stock - item.position) if item.position <= rule.reorder_at else 0
        evaluated.append(
            {
                "sku": sku,
                "inventory_position": item.position,
                "reorder_at": rule.reorder_at,
                "target_stock": rule.target_stock,
                "requested_qty": needed,
            }
        )
        if not needed:
            continue

        candidates = sorted(
            exact.get(sku, []),
            key=lambda offer: (
                offer.supplier_id != rule.preferred_supplier,
                offer.unit_cost,
                offer.lead_days,
                offer.supplier_id,
                offer.supplier_sku,
            ),
        )
        remaining = needed
        for offer in candidates:
            quantity = min(remaining, offer.available_qty)
            if quantity <= 0:
                continue
            po_lines[offer.supplier_id].append(
                {
                    "sku": sku,
                    "supplier_sku": offer.supplier_sku,
                    "description": offer.description or item.name,
                    "quantity": quantity,
                    "unit": item.unit,
                    "unit_cost": _money(offer.unit_cost),
                    "line_total": _money(offer.unit_cost * quantity),
                }
            )
            remaining -= quantity
            if remaining == 0:
                break

        if remaining:
            suggestions = []
            for offer in sorted(
                alternatives.get(sku, []),
                key=lambda candidate: (
                    candidate.supplier_id != rule.preferred_supplier,
                    candidate.unit_cost,
                    candidate.lead_days,
                    candidate.supplier_id,
                    candidate.supplier_sku,
                ),
            ):
                if offer.available_qty <= 0:
                    continue
                suggestions.append(
                    {
                        "supplier_id": offer.supplier_id,
                        "supplier_sku": offer.supplier_sku,
                        "description": offer.description,
                        "available_qty": offer.available_qty,
                        "unit_cost": _money(offer.unit_cost),
                        "lead_days": offer.lead_days,
                        "requires_approval": True,
                    }
                )
            exceptions.append(
                {
                    "sku": sku,
                    "unfilled_qty": remaining,
                    "reason": "exact_item_unavailable",
                    "alternative_suggestions": suggestions,
                    "action": "review_required_no_order_created",
                }
            )

    purchase_orders = []
    for supplier in sorted(po_lines):
        lines = sorted(po_lines[supplier], key=lambda line: (str(line["sku"]), str(line["supplier_sku"])))
        total = sum((Decimal(str(line["line_total"])) for line in lines), Decimal("0"))
        purchase_orders.append(
            {
                "draft_id": f"DRAFT-{as_of.replace('-', '')}-{supplier}",
                "supplier_id": supplier,
                "status": "DRAFT_NOT_SENT",
                "lines": lines,
                "total": _money(total),
            }
        )

    return {
        "schema": SCHEMA,
        "as_of": as_of,
        "purchase_orders": purchase_orders,
        "exceptions": exceptions,
        "evaluated": evaluated,
        "summary": {
            "draft_purchase_orders": len(purchase_orders),
            "draft_lines": sum(len(order["lines"]) for order in purchase_orders),
            "review_required": len(exceptions),
            "orders_sent": 0,
        },
    }


def apply_receipts(
    stock: dict[str, Stock],
    plan: dict[str, object],
    receipt_rows: list[dict[str, str]],
    *,
    pipeline_includes_draft: bool = False,
) -> tuple[dict[str, Stock], dict[str, object]]:
    if plan.get("schema") != SCHEMA:
        raise ReorderError("plan schema is not supported")
    drafted: dict[tuple[str, str, str], int] = {}
    for order in plan.get("purchase_orders", []):
        supplier = str(order["supplier_id"])
        for line in order["lines"]:
            key = (supplier, str(line["supplier_sku"]), str(line["sku"]))
            drafted[key] = drafted.get(key, 0) + int(line["quantity"])

    updated = dict(stock)
    applied: list[dict[str, object]] = []
    seen_receipts: set[str] = set()
    cumulative: dict[tuple[str, str, str], int] = defaultdict(int)
    for row in receipt_rows:
        receipt_id = row["receipt_id"]
        if not receipt_id or receipt_id in seen_receipts:
            raise ReorderError(f"blank or duplicate receipt_id {receipt_id!r}")
        seen_receipts.add(receipt_id)
        key = (row["supplier_id"], row["supplier_sku"], row["sku"])
        quantity = _integer(row["quantity"], f"{receipt_id}.quantity", minimum=1)
        if key not in drafted:
            raise ReorderError(f"{receipt_id}: receipt item was not present in the draft plan")
        cumulative[key] += quantity
        if cumulative[key] > drafted[key]:
            raise ReorderError(f"{receipt_id}: received quantity exceeds drafted quantity")
        if key[2] not in updated:
            raise ReorderError(f"{receipt_id}: unknown stock sku {key[2]}")
        item = updated[key[2]]
        updated[key[2]] = Stock(
            sku=item.sku,
            name=item.name,
            on_hand=item.on_hand + quantity,
            # Drafting never adds units to the imported pipeline. Decrement
            # only when the caller confirms its newer export already did.
            on_order=max(0, item.on_order - quantity) if pipeline_includes_draft else item.on_order,
            allocated=item.allocated,
            unit=item.unit,
        )
        applied.append(
            {
                "receipt_id": receipt_id,
                "received_at": row["received_at"],
                "supplier_id": key[0],
                "supplier_sku": key[1],
                "sku": key[2],
                "quantity": quantity,
            }
        )
    return updated, {
        "schema": SCHEMA,
        "applied_receipts": applied,
        "count": len(applied),
        "pipeline_includes_draft": pipeline_includes_draft,
    }


def write_stock(path: Path, stock: dict[str, Stock]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["sku", "name", "on_hand", "on_order", "allocated", "unit"])
        writer.writeheader()
        for sku in sorted(stock):
            item = stock[sku]
            writer.writerow(item.__dict__)


def command_plan(args: argparse.Namespace) -> None:
    plan = build_plan(load_stock(args.stock), load_rules(args.rules), load_catalog(args.catalog), args.as_of)
    args.out.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def command_receive(args: argparse.Namespace) -> None:
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    receipts = _read_csv(
        args.receipts,
        {"receipt_id", "received_at", "supplier_id", "supplier_sku", "sku", "quantity"},
    )
    updated, log = apply_receipts(
        load_stock(args.stock),
        plan,
        receipts,
        pipeline_includes_draft=args.pipeline_includes_draft,
    )
    write_stock(args.out_stock, updated)
    args.out_log.write_text(json.dumps(log, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan", help="create unsent draft purchase orders")
    plan.add_argument("--stock", type=Path, required=True)
    plan.add_argument("--rules", type=Path, required=True)
    plan.add_argument("--catalog", type=Path, required=True)
    plan.add_argument("--as-of", required=True, help="ISO date used in deterministic draft IDs")
    plan.add_argument("--out", type=Path, required=True)
    plan.set_defaults(func=command_plan)

    receive = sub.add_parser("receive", help="apply supplier receipts to stock")
    receive.add_argument("--stock", type=Path, required=True)
    receive.add_argument("--plan", type=Path, required=True)
    receive.add_argument("--receipts", type=Path, required=True)
    receive.add_argument("--out-stock", type=Path, required=True)
    receive.add_argument("--out-log", type=Path, required=True)
    receive.add_argument(
        "--pipeline-includes-draft",
        action="store_true",
        help="decrement on_order because the imported stock already includes this draft",
    )
    receive.set_defaults(func=command_receive)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        args.func(args)
    except (ReorderError, OSError, json.JSONDecodeError) as exc:
        parser().error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
