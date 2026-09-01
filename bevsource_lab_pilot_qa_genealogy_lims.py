#!/usr/bin/env python3
"""BevSource lab pilot QA genealogy LIMS.

Demand: bevsource-lab-pilot-qa-genealogy-lims-01
Buyer pairing: BevSource — The Lab / Matt Bonfitto

Synthetic/read-only formula → ingredient lot → pilot batch → package QA
genealogy. Sixty frozen high-acid RTD pilot runs: 45 clean rows reach
RELEASE_REVIEW; 15 predetermined defects stay on HOLD. Release requires
a named human reviewer. Adapters stay simulated.

Official test: python test_bevsource_lab_pilot_qa_genealogy_lims.py
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

DEMAND_ID = "bevsource-lab-pilot-qa-genealogy-lims-01"
SCHEMA = "commons-bevsource-lab-pilot-qa-genealogy-lims/v1"
BUYER = "BevSource — The Lab / Matt Bonfitto"
TRUTH_GATE = "HOLD / BUILD-AND-VERIFY"
HUMAN_REVIEWER_ROLE = "NAMED_HUMAN_REVIEWER"

CURRENT_FORMULA_ID = "FORM-HA-RTD-01"
CURRENT_FORMULA_VERSION = "1.0.0"
REQUIRED_INGREDIENTS = ("ACIDULANT", "CONCENTRATE", "PROCESS_WATER")
PROCESS_STEP = "PILOT_HIGH_ACID_RTD"

VALID_COUNT = 45
WRONG_FORMULA_COUNT = 5
MISSING_LOT_COUNT = 4
FAILED_LINER_COUNT = 3
POSITIVE_MICRO_COUNT = 3
HOLD_COUNT = (
    WRONG_FORMULA_COUNT
    + MISSING_LOT_COUNT
    + FAILED_LINER_COUNT
    + POSITIVE_MICRO_COUNT
)
INPUT_COUNT = VALID_COUNT + HOLD_COUNT

HOLD_CODES = (
    "HOLD_WRONG_FORMULA_VERSION",
    "HOLD_MISSING_INGREDIENT_LOT",
    "HOLD_FAILED_LINER_CHECK",
    "HOLD_POSITIVE_MICROBIOLOGY",
)

EXPECTED_HOLD_COUNTS = {
    "HOLD_WRONG_FORMULA_VERSION": WRONG_FORMULA_COUNT,
    "HOLD_MISSING_INGREDIENT_LOT": MISSING_LOT_COUNT,
    "HOLD_FAILED_LINER_CHECK": FAILED_LINER_COUNT,
    "HOLD_POSITIVE_MICROBIOLOGY": POSITIVE_MICRO_COUNT,
}

LINK_ROLES = (
    "LOT_TO_FORMULA",
    "LOT_TO_BATCH",
    "BATCH_TO_FORMULA",
    "PACKAGE_TO_BATCH",
    "PACKAGE_TO_FORMULA",
    "PACKAGE_TO_LOT",
)

OFFICIAL_BINARY = "python bevsource_lab_pilot_qa_genealogy_lims.py"
OFFICIAL_TEST = "python test_bevsource_lab_pilot_qa_genealogy_lims.py"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _text(value: Any) -> str:
    return str("" if value is None else value).strip()


def _lot_token(ingredient: str, token: str) -> str:
    prefix = {"ACIDULANT": "ACD", "CONCENTRATE": "CON", "PROCESS_WATER": "WTR"}[ingredient]
    return f"LOT-{prefix}-{token}"


def _base_run(index: int) -> dict[str, Any]:
    token = f"{index:03d}"
    return {
        "row_id": f"BEV-{token}",
        "run_id": f"RUN-{token}",
        "formula_id": CURRENT_FORMULA_ID,
        "formula_version": CURRENT_FORMULA_VERSION,
        "ingredient_lots": [
            {"ingredient": name, "lot_id": _lot_token(name, token)}
            for name in REQUIRED_INGREDIENTS
        ],
        "pilot_batch_id": f"BATCH-{token}",
        "package_unit_id": f"PKG-{token}",
        "liner_check": "PASS",
        "microbiology": "NEGATIVE",
        "chemistry": "IN_SPEC",
        "shelf_life": "IN_SPEC",
        "process_step": PROCESS_STEP,
        "exception_type": None,
        "synthetic": True,
        "deidentified": True,
    }


def _exception_run(index: int) -> dict[str, Any]:
    row = _base_run(index)
    if index <= VALID_COUNT + WRONG_FORMULA_COUNT:
        row["formula_version"] = "0.8.0"
        row["exception_type"] = "WRONG_FORMULA_VERSION"
    elif index <= VALID_COUNT + WRONG_FORMULA_COUNT + MISSING_LOT_COUNT:
        missing = REQUIRED_INGREDIENTS[(index - 1) % len(REQUIRED_INGREDIENTS)]
        row["ingredient_lots"] = [
            lot for lot in row["ingredient_lots"] if lot["ingredient"] != missing
        ]
        row["exception_type"] = "MISSING_INGREDIENT_LOT"
    elif index <= VALID_COUNT + WRONG_FORMULA_COUNT + MISSING_LOT_COUNT + FAILED_LINER_COUNT:
        row["liner_check"] = "FAIL"
        row["exception_type"] = "FAILED_LINER_CHECK"
    else:
        row["microbiology"] = "POSITIVE"
        row["exception_type"] = "POSITIVE_MICROBIOLOGY"
    return row


def build_acceptance_fixture() -> list[dict[str, Any]]:
    """Return the frozen 60-row high-acid RTD fixture (45 clean, 15 holds)."""
    rows = [_base_run(index) for index in range(1, VALID_COUNT + 1)]
    rows.extend(_exception_run(index) for index in range(VALID_COUNT + 1, INPUT_COUNT + 1))
    expected = {
        None: VALID_COUNT,
        "WRONG_FORMULA_VERSION": WRONG_FORMULA_COUNT,
        "MISSING_INGREDIENT_LOT": MISSING_LOT_COUNT,
        "FAILED_LINER_CHECK": FAILED_LINER_COUNT,
        "POSITIVE_MICROBIOLOGY": POSITIVE_MICRO_COUNT,
    }
    actual = {name: 0 for name in expected}
    for row in rows:
        actual[row["exception_type"]] += 1
    if len(rows) != INPUT_COUNT or actual != expected:
        raise RuntimeError(f"invalid frozen fixture: rows={len(rows)} split={actual}")
    return rows


def empty_journal() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "demand_id": DEMAND_ID,
        "buyer": BUYER,
        "formulas": {},
        "lots": {},
        "batches": {},
        "packages": {},
        "links": {},
        "reviews": {},
        "holds": [],
        "events": [],
        "processed_rows": {},
        "run_index": {},
        "package_index": {},
        "batch_index": {},
        "interface_live": False,
        "production_writes": 0,
        "automatic_releases": 0,
    }


def _event(journal: dict[str, Any], kind: str, payload: dict[str, Any]) -> None:
    journal["events"].append(
        {"seq": len(journal["events"]) + 1, "kind": kind, **deepcopy(payload)}
    )


def normalize_run(row: dict[str, Any]) -> dict[str, Any]:
    lots = []
    for item in row.get("ingredient_lots") or []:
        lots.append(
            {
                "ingredient": _text(item.get("ingredient")).upper(),
                "lot_id": _text(item.get("lot_id")).upper(),
            }
        )
    return {
        "row_id": _text(row.get("row_id")),
        "run_id": _text(row.get("run_id")),
        "formula_id": _text(row.get("formula_id")).upper(),
        "formula_version": _text(row.get("formula_version")),
        "ingredient_lots": lots,
        "pilot_batch_id": _text(row.get("pilot_batch_id")).upper(),
        "package_unit_id": _text(row.get("package_unit_id")).upper(),
        "liner_check": _text(row.get("liner_check")).upper(),
        "microbiology": _text(row.get("microbiology")).upper(),
        "chemistry": _text(row.get("chemistry")).upper(),
        "shelf_life": _text(row.get("shelf_life")).upper(),
        "process_step": _text(row.get("process_step")).upper(),
        "synthetic": True,
        "deidentified": True,
    }


def classify_run(norm: dict[str, Any]) -> dict[str, Any]:
    if (
        norm["formula_id"] != CURRENT_FORMULA_ID
        or norm["formula_version"] != CURRENT_FORMULA_VERSION
    ):
        return {"ok": False, "code": "HOLD_WRONG_FORMULA_VERSION"}
    present = {lot["ingredient"] for lot in norm["ingredient_lots"] if lot["lot_id"]}
    if present != set(REQUIRED_INGREDIENTS) or any(
        not lot["lot_id"] or not lot["ingredient"] for lot in norm["ingredient_lots"]
    ):
        return {"ok": False, "code": "HOLD_MISSING_INGREDIENT_LOT"}
    if norm["liner_check"] != "PASS":
        return {"ok": False, "code": "HOLD_FAILED_LINER_CHECK"}
    if norm["microbiology"] != "NEGATIVE":
        return {"ok": False, "code": "HOLD_POSITIVE_MICROBIOLOGY"}
    if (
        not norm["run_id"]
        or not norm["pilot_batch_id"]
        or not norm["package_unit_id"]
        or norm["process_step"] != PROCESS_STEP
    ):
        return {"ok": False, "code": "HOLD_MISSING_INGREDIENT_LOT"}
    return {"ok": True}


def _hold(journal: dict[str, Any], norm: dict[str, Any], code: str) -> dict[str, Any]:
    hold = {
        "row_id": norm["row_id"],
        "run_id": norm["run_id"],
        "package_unit_id": norm["package_unit_id"] or None,
        "code": code,
        "state": "HOLD",
        "packages_created": 0,
        "links_created": 0,
        "reviews_created": 0,
        "released": False,
    }
    journal["holds"].append(hold)
    journal["processed_rows"][norm["row_id"]] = {
        "kind": "HOLD",
        "run_id": norm["run_id"],
        "code": code,
    }
    _event(journal, "HOLD", hold)
    return {"kind": "HOLD", **deepcopy(hold)}


def _link_key(
    from_kind: str, from_id: str, to_kind: str, to_id: str, role: str
) -> str:
    return sha256_hex(
        {
            "from_kind": from_kind,
            "from_id": from_id,
            "to_kind": to_kind,
            "to_id": to_id,
            "role": role,
        }
    )


def _add_link(
    journal: dict[str, Any],
    from_kind: str,
    from_id: str,
    to_kind: str,
    to_id: str,
    role: str,
) -> None:
    key = _link_key(from_kind, from_id, to_kind, to_id, role)
    if key in journal["links"]:
        raise RuntimeError(
            f"duplicate genealogy link {role}:{from_kind}:{from_id}->{to_kind}:{to_id}"
        )
    journal["links"][key] = {
        "from_kind": from_kind,
        "from_id": from_id,
        "to_kind": to_kind,
        "to_id": to_id,
        "role": role,
    }


def _entity_exists(journal: dict[str, Any], kind: str, entity_id: str) -> bool:
    tables = {
        "FORMULA": journal["formulas"],
        "LOT": journal["lots"],
        "BATCH": journal["batches"],
        "PACKAGE": journal["packages"],
    }
    return entity_id in tables[kind]


def genealogy_integrity(journal: dict[str, Any]) -> dict[str, Any]:
    orphans = []
    seen: set[tuple[str, str, str, str, str]] = set()
    duplicates = []
    for link in journal["links"].values():
        tuple_key = (
            link["from_kind"],
            link["from_id"],
            link["to_kind"],
            link["to_id"],
            link["role"],
        )
        if tuple_key in seen:
            duplicates.append(tuple_key)
        seen.add(tuple_key)
        if not _entity_exists(journal, link["from_kind"], link["from_id"]):
            orphans.append({"side": "from", **link})
        if not _entity_exists(journal, link["to_kind"], link["to_id"]):
            orphans.append({"side": "to", **link})
    return {
        "orphans": len(orphans),
        "duplicates": len(duplicates),
        "orphan_records": orphans,
        "duplicate_records": duplicates,
        "link_count": len(journal["links"]),
    }


def trace_package(journal: dict[str, Any], package_unit_id: str) -> dict[str, Any]:
    package = journal["packages"].get(package_unit_id)
    if package is None:
        return {"ok": False, "code": "UNKNOWN_PACKAGE"}
    formula_ids = set()
    lot_ids = set()
    batch_ids = set()
    for link in journal["links"].values():
        if link["from_kind"] == "PACKAGE" and link["from_id"] == package_unit_id:
            if link["to_kind"] == "FORMULA":
                formula_ids.add(link["to_id"])
            elif link["to_kind"] == "LOT":
                lot_ids.add(link["to_id"])
            elif link["to_kind"] == "BATCH":
                batch_ids.add(link["to_id"])
    return {
        "ok": True,
        "package_unit_id": package_unit_id,
        "formula_ids": sorted(formula_ids),
        "lot_ids": sorted(lot_ids),
        "batch_ids": sorted(batch_ids),
        "expected_formula": package["formula_id"],
        "expected_lots": sorted(package["lot_ids"]),
        "expected_batch": package["pilot_batch_id"],
    }


def ingest_row(journal: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    norm = normalize_run(row)
    if norm["row_id"] in journal["processed_rows"]:
        _event(
            journal,
            "REPLAY_NOOP",
            {"row_id": norm["row_id"], "run_id": norm["run_id"]},
        )
        return {
            "kind": "REPLAY_NOOP",
            "row_id": norm["row_id"],
            "run_id": norm["run_id"],
        }

    verdict = classify_run(norm)
    if not verdict["ok"]:
        return _hold(journal, norm, verdict["code"])

    formula_key = f"{norm['formula_id']}@{norm['formula_version']}"
    journal["formulas"].setdefault(
        formula_key,
        {
            "formula_id": norm["formula_id"],
            "formula_version": norm["formula_version"],
            "ingredients": list(REQUIRED_INGREDIENTS),
        },
    )
    lot_ids = []
    for lot in norm["ingredient_lots"]:
        lot_ids.append(lot["lot_id"])
        journal["lots"][lot["lot_id"]] = {
            "lot_id": lot["lot_id"],
            "ingredient": lot["ingredient"],
            "formula_id": norm["formula_id"],
            "run_id": norm["run_id"],
        }
        _add_link(
            journal, "LOT", lot["lot_id"], "FORMULA", formula_key, "LOT_TO_FORMULA"
        )
        _add_link(
            journal,
            "LOT",
            lot["lot_id"],
            "BATCH",
            norm["pilot_batch_id"],
            "LOT_TO_BATCH",
        )
    journal["batches"][norm["pilot_batch_id"]] = {
        "pilot_batch_id": norm["pilot_batch_id"],
        "formula_id": norm["formula_id"],
        "formula_version": norm["formula_version"],
        "lot_ids": list(lot_ids),
        "process_step": norm["process_step"],
        "run_id": norm["run_id"],
    }
    _add_link(
        journal,
        "BATCH",
        norm["pilot_batch_id"],
        "FORMULA",
        formula_key,
        "BATCH_TO_FORMULA",
    )
    lineage = {
        "package_unit_id": norm["package_unit_id"],
        "formula_id": norm["formula_id"],
        "formula_version": norm["formula_version"],
        "pilot_batch_id": norm["pilot_batch_id"],
        "lot_ids": sorted(lot_ids),
        "ingredients": sorted(lot["ingredient"] for lot in norm["ingredient_lots"]),
        "liner_check": norm["liner_check"],
        "microbiology": norm["microbiology"],
        "chemistry": norm["chemistry"],
        "shelf_life": norm["shelf_life"],
        "process_step": norm["process_step"],
    }
    lineage_hash = sha256_hex(lineage)
    package = {
        **lineage,
        "lineage_hash": lineage_hash,
        "state": "RELEASE_REVIEW",
        "released": False,
        "released_by": None,
        "interface_state": "SIMULATED",
    }
    journal["packages"][norm["package_unit_id"]] = package
    _add_link(
        journal,
        "PACKAGE",
        norm["package_unit_id"],
        "BATCH",
        norm["pilot_batch_id"],
        "PACKAGE_TO_BATCH",
    )
    _add_link(
        journal,
        "PACKAGE",
        norm["package_unit_id"],
        "FORMULA",
        formula_key,
        "PACKAGE_TO_FORMULA",
    )
    for lot_id in lot_ids:
        _add_link(
            journal,
            "PACKAGE",
            norm["package_unit_id"],
            "LOT",
            lot_id,
            "PACKAGE_TO_LOT",
        )
    review = {
        "run_id": norm["run_id"],
        "package_unit_id": norm["package_unit_id"],
        "formula_id": norm["formula_id"],
        "formula_version": norm["formula_version"],
        "pilot_batch_id": norm["pilot_batch_id"],
        "lot_ids": sorted(lot_ids),
        "lineage_hash": lineage_hash,
        "state": "RELEASE_REVIEW",
        "released": False,
        "released_by": None,
    }
    journal["reviews"][norm["run_id"]] = review
    journal["run_index"][norm["run_id"]] = norm["row_id"]
    journal["package_index"][norm["package_unit_id"]] = norm["row_id"]
    journal["batch_index"][norm["pilot_batch_id"]] = norm["row_id"]
    journal["processed_rows"][norm["row_id"]] = {
        "kind": "RELEASE_REVIEW",
        "run_id": norm["run_id"],
        "package_unit_id": norm["package_unit_id"],
    }
    _event(
        journal,
        "RELEASE_REVIEW",
        {
            "run_id": norm["run_id"],
            "package_unit_id": norm["package_unit_id"],
            "lineage_hash": lineage_hash,
        },
    )
    return {
        "kind": "RELEASE_REVIEW",
        "run_id": norm["run_id"],
        "package_unit_id": norm["package_unit_id"],
        "lineage_hash": lineage_hash,
    }


def release_package(
    journal: dict[str, Any], package_unit_id: str, *, actor_role: str, actor: str
) -> dict[str, Any]:
    package = journal["packages"].get(package_unit_id)
    if package is None:
        return {"ok": False, "code": "UNKNOWN_PACKAGE"}
    if _text(actor_role).upper() != HUMAN_REVIEWER_ROLE or not _text(actor):
        _event(
            journal,
            "RELEASE_DENIED",
            {"package_unit_id": package_unit_id, "code": "AUTONOMOUS_RELEASE_DENIED"},
        )
        return {"ok": False, "code": "AUTONOMOUS_RELEASE_DENIED"}
    if package["released"]:
        return {"ok": True, "duplicate": True, "status": "RELEASED"}
    package["released"] = True
    package["released_by"] = _text(actor)
    package["state"] = "RELEASED"
    review = next(
        item
        for item in journal["reviews"].values()
        if item["package_unit_id"] == package_unit_id
    )
    review["released"] = True
    review["released_by"] = _text(actor)
    review["state"] = "RELEASED"
    _event(
        journal,
        "RELEASED",
        {"package_unit_id": package_unit_id, "released_by": _text(actor)},
    )
    return {"ok": True, "duplicate": False, "status": "RELEASED"}


def replay_into(
    journal: dict[str, Any], rows: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    inbound = deepcopy(rows if rows is not None else build_acceptance_fixture())
    before = {
        "packages": len(journal["packages"]),
        "reviews": len(journal["reviews"]),
        "holds": len(journal["holds"]),
        "links": len(journal["links"]),
    }
    before_hash = journal_hash(journal)
    effects = [ingest_row(journal, row) for row in inbound]
    return {
        "added_packages": len(journal["packages"]) - before["packages"],
        "added_reviews": len(journal["reviews"]) - before["reviews"],
        "added_holds": len(journal["holds"]) - before["holds"],
        "added_links": len(journal["links"]) - before["links"],
        "replay_noops": sum(item["kind"] == "REPLAY_NOOP" for item in effects),
        "hash_identical": journal_hash(journal) == before_hash,
    }


def journal_hash(journal: dict[str, Any]) -> str:
    return sha256_hex(
        {
            "formulas": journal["formulas"],
            "lots": journal["lots"],
            "batches": journal["batches"],
            "packages": journal["packages"],
            "links": journal["links"],
            "reviews": journal["reviews"],
            "holds": journal["holds"],
            "processed_rows": journal["processed_rows"],
        }
    )


def _manifest(journal: dict[str, Any]) -> dict[str, Any]:
    return {
        "demand_id": DEMAND_ID,
        "packages": sorted(journal["packages"]),
        "reviews": sorted(journal["reviews"]),
        "lots": sorted(journal["lots"]),
        "batches": sorted(journal["batches"]),
        "holds": sorted(
            (item["row_id"], item["run_id"], item["code"]) for item in journal["holds"]
        ),
        "links": sorted(
            (
                item["role"],
                item["from_kind"],
                item["from_id"],
                item["to_kind"],
                item["to_id"],
            )
            for item in journal["links"].values()
        ),
    }


def run_gate(rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    inbound = deepcopy(rows if rows is not None else build_acceptance_fixture())
    journal = empty_journal()
    effects = [ingest_row(journal, row) for row in inbound]
    integrity = genealogy_integrity(journal)
    autonomous = [
        release_package(
            journal,
            package_id,
            actor_role="SYSTEM",
            actor="",
        )
        for package_id in sorted(journal["packages"])
    ]
    hold_counts = {code: 0 for code in HOLD_CODES}
    for hold in journal["holds"]:
        hold_counts[hold["code"]] += 1
    traces = [
        trace_package(journal, package_id)
        for package_id in sorted(journal["packages"])
    ]
    manifest = _manifest(journal)
    reviews = sorted(journal["reviews"].values(), key=lambda item: item["run_id"])
    packages = sorted(
        journal["packages"].values(), key=lambda item: item["package_unit_id"]
    )
    result = {
        "schema": SCHEMA,
        "demand_id": DEMAND_ID,
        "buyer": BUYER,
        "truth_gate": TRUTH_GATE,
        "input_rows": len(inbound),
        "release_review": len(journal["reviews"]),
        "holds": len(journal["holds"]),
        "packages": len(journal["packages"]),
        "lots": len(journal["lots"]),
        "batches": len(journal["batches"]),
        "links": len(journal["links"]),
        "orphans": integrity["orphans"],
        "duplicates": integrity["duplicates"],
        "packages_released": sum(item["released"] for item in packages),
        "hold_counts": hold_counts,
        "manifest_sha256": sha256_hex(manifest),
        "audit_sha256": sha256_hex(
            {
                "events": journal["events"],
                "manifest": manifest,
                "truth_gate": TRUTH_GATE,
            }
        ),
        "journal_sha256": journal_hash(journal),
        "reviews": reviews,
        "package_records": packages,
        "hold_records": deepcopy(journal["holds"]),
        "link_records": sorted(
            journal["links"].values(),
            key=lambda item: (
                item["role"],
                item["from_id"],
                item["to_id"],
            ),
        ),
        "traces": traces,
        "effects": effects,
        "autonomous_release_effects": autonomous,
        "integrity": integrity,
        "interface_live": False,
        "interfaces": "SIMULATED_READ_ONLY",
        "production_writes": 0,
        "automatic_releases": 0,
        "autonomous_release": False,
        "pre_sale_transport": "NONE",
        "cash_usd": 0,
    }
    return result


def pass_contract(result: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    checks = {
        "input_rows": result.get("input_rows") == INPUT_COUNT,
        "release_review": result.get("release_review") == VALID_COUNT,
        "holds": result.get("holds") == HOLD_COUNT,
        "packages": result.get("packages") == VALID_COUNT,
        "lots": result.get("lots") == VALID_COUNT * len(REQUIRED_INGREDIENTS),
        "batches": result.get("batches") == VALID_COUNT,
        "packages_released": result.get("packages_released") == 0,
        "hold_counts": result.get("hold_counts") == EXPECTED_HOLD_COUNTS,
        "orphans": result.get("orphans") == 0,
        "duplicates": result.get("duplicates") == 0,
        "interfaces": result.get("interfaces") == "SIMULATED_READ_ONLY",
        "production_writes": result.get("production_writes") == 0,
        "automatic_releases": result.get("automatic_releases") == 0,
        "autonomous_release": result.get("autonomous_release") is False,
    }
    failures.extend(name for name, passed in checks.items() if not passed)
    if not all(
        item.get("code") == "AUTONOMOUS_RELEASE_DENIED"
        for item in result.get("autonomous_release_effects") or []
    ):
        failures.append("autonomous_release_not_denied")
    if any(
        item.get("packages_created")
        or item.get("links_created")
        or item.get("reviews_created")
        or item.get("released")
        for item in result.get("hold_records") or []
    ):
        failures.append("held_record_created_output")
    for review in result.get("reviews") or []:
        if review.get("state") != "RELEASE_REVIEW" or review.get("released"):
            failures.append("review_not_staged")
            break
        if len(review.get("lineage_hash") or "") != 64:
            failures.append("review_hash")
            break
        if review.get("formula_id") != CURRENT_FORMULA_ID:
            failures.append("review_formula")
            break
        if len(review.get("lot_ids") or []) != len(REQUIRED_INGREDIENTS):
            failures.append("review_lots")
            break
    for package in result.get("package_records") or []:
        if package.get("state") != "RELEASE_REVIEW" or package.get("released"):
            failures.append("package_not_review")
            break
        if set(package.get("ingredients") or []) != set(REQUIRED_INGREDIENTS):
            failures.append("package_ingredients")
            break
    for trace in result.get("traces") or []:
        if (
            not trace.get("ok")
            or trace.get("formula_ids") != [f"{CURRENT_FORMULA_ID}@{CURRENT_FORMULA_VERSION}"]
            or trace.get("lot_ids") != trace.get("expected_lots")
            or trace.get("batch_ids") != [trace.get("expected_batch")]
            or len(trace.get("formula_ids") or []) != 1
            or len(trace.get("lot_ids") or []) != len(REQUIRED_INGREDIENTS)
        ):
            failures.append("package_trace")
            break
    return failures


def main() -> int:
    result = run_gate()
    journal = empty_journal()
    for row in build_acceptance_fixture():
        ingest_row(journal, row)
    first_hash = journal_hash(journal)
    replay = replay_into(journal)
    failures = pass_contract(result)
    if any(
        replay[key] != 0
        for key in ("added_packages", "added_reviews", "added_holds", "added_links")
    ):
        failures.append("replay_added_output")
    if replay["replay_noops"] != INPUT_COUNT:
        failures.append("replay_noops")
    if not replay["hash_identical"] or journal_hash(journal) != first_hash:
        failures.append("replay_hash")
    report = {
        "ok": not failures,
        "failures": failures,
        "command": OFFICIAL_TEST,
        "demand_id": DEMAND_ID,
        "buyer": BUYER,
        "input_rows": result["input_rows"],
        "release_review": result["release_review"],
        "holds": result["holds"],
        "packages": result["packages"],
        "lots": result["lots"],
        "batches": result["batches"],
        "links": result["links"],
        "orphans": result["orphans"],
        "duplicates": result["duplicates"],
        "packages_released": result["packages_released"],
        "hold_counts": result["hold_counts"],
        "replay": replay,
        "manifest_sha256": result["manifest_sha256"],
        "audit_sha256": result["audit_sha256"],
        "journal_sha256": result["journal_sha256"],
        "truth_gate": TRUTH_GATE,
        "interfaces": result["interfaces"],
        "pre_sale_transport": "NONE",
        "cash_usd": 0,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
