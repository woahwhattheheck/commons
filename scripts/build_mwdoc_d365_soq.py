#!/usr/bin/env python3
"""Build and validate the deterministic public-safe MWDOC readiness packet."""
from __future__ import annotations

import argparse
import copy
import html
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "revenue" / "mwdoc_d365_soq"
SOURCE = PACKET / "source.json"
READINESS = PACKET / "readiness.json"
READINESS_HTML = PACKET / "readiness.html"
SCHEMA_FILE = PACKET / "readiness.schema.json"

READINESS_SCHEMA = "commons-mwdoc-d365-readiness/v2"
DECISION = "NO_GO_AS_PRIME; PROVISIONAL_PARTNER_RESEARCH_ONLY; CONDITIONAL_SUBCONTRACTOR_ONLY"
VERIFIED_PUBLIC = "VERIFIED_PUBLIC"


class PacketError(ValueError):
    """Raised when a source record cannot support a truthful readiness packet."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PacketError(message)


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(data, dict), f"{path.name} must contain a JSON object")
    return data


def load_source() -> dict[str, Any]:
    source = read_json(SOURCE)
    for key in (
        "schema",
        "id",
        "observed_at",
        "official_sources",
        "schedule",
        "score_weights",
        "mandatory_gate_keys",
        "evidence_state_factors",
        "targets",
        "reference_slots",
        "proposed_subcontract_scope",
        "outreach_draft",
        "rate_sheet",
        "agreement_checklist",
        "truth_flags",
    ):
        require(key in source, f"source missing {key}")
    require(
        source["schema"] == "commons-mwdoc-d365-source/v1",
        "unexpected source schema",
    )
    require(isinstance(source["targets"], list) and len(source["targets"]) >= 4,
            "source must contain at least four research targets")
    return source


def number(value: float) -> int | float:
    rounded = round(value, 2)
    return int(rounded) if rounded.is_integer() else rounded


def project_target(
    target: dict[str, Any],
    index: int,
    score_weights: dict[str, Any],
    mandatory_keys: list[str],
    state_factors: dict[str, Any],
) -> dict[str, Any]:
    evidence = target.get("evidence")
    require(isinstance(evidence, dict), f"target {index} missing evidence")
    score = 0.0
    mandatory_gates: list[dict[str, Any]] = []

    for key, raw_weight in score_weights.items():
        require(isinstance(raw_weight, (int, float)) and not isinstance(raw_weight, bool),
                f"weight {key} must be numeric")
        row = evidence.get(key)
        require(isinstance(row, dict), f"target {index} missing evidence for {key}")
        state = row.get("state")
        factor = state_factors.get(state)
        require(
            isinstance(factor, (int, float)) and not isinstance(factor, bool),
            f"target {index} has unsupported evidence state for {key}",
        )
        score += float(raw_weight) * float(factor)
        if key in mandatory_keys:
            sources = row.get("sources")
            require(isinstance(sources, list), f"target {index} sources for {key} must be a list")
            mandatory_gates.append(
                {
                    "key": key,
                    "state": state,
                    "state_factor": number(float(factor)),
                    "evidenced": state == VERIFIED_PUBLIC,
                    "source_count": len(sources),
                }
            )

    missing = [
        gate["key"] for gate in mandatory_gates if not gate["evidenced"]
    ]
    total = sum(float(weight) for weight in score_weights.values())
    require(total > 0, "score weights must total more than zero")
    return {
        "company": target["company"],
        "target_persona": target["target_persona"],
        "proposed_role": target["proposed_role"],
        "computed_score": number(score),
        "max_score": number(total),
        "score_percent": number(score * 100 / total),
        "mandatory_gates": mandatory_gates,
        "missing_mandatory_gates": missing,
        "status": (
            "EVIDENCE_COMPLETE_REQUIRES_OWNER_DECISION"
            if not missing
            else "PROVISIONAL_RESEARCH_ONLY"
        ),
        "evidence_source": f"source.json#/targets/{index}",
    }


def build_packet(source: dict[str, Any]) -> dict[str, Any]:
    score_weights = source["score_weights"]
    mandatory_keys = source["mandatory_gate_keys"]
    state_factors = source["evidence_state_factors"]
    require(isinstance(score_weights, dict), "score_weights must be an object")
    require(isinstance(mandatory_keys, list), "mandatory_gate_keys must be a list")
    require(isinstance(state_factors, dict), "evidence_state_factors must be an object")
    require(
        all(key in score_weights for key in mandatory_keys),
        "every mandatory gate must have a weight",
    )

    return {
        "schema": READINESS_SCHEMA,
        "id": source["id"],
        "observed_at": source["observed_at"],
        "source_path": "source.json",
        "official_sources": copy.deepcopy(source["official_sources"]),
        "schedule": copy.deepcopy(source["schedule"]),
        "decision": DECISION,
        "score_weights": copy.deepcopy(score_weights),
        "mandatory_gate_keys": list(mandatory_keys),
        "targets": [
            project_target(
                target,
                index,
                score_weights,
                mandatory_keys,
                state_factors,
            )
            for index, target in enumerate(source["targets"])
        ],
        "reference_slots": copy.deepcopy(source["reference_slots"]),
        "proposed_subcontract_scope": copy.deepcopy(source["proposed_subcontract_scope"]),
        "outreach_draft": copy.deepcopy(source["outreach_draft"]),
        "rate_sheet": copy.deepcopy(source["rate_sheet"]),
        "agreement_checklist": copy.deepcopy(source["agreement_checklist"]),
        "truth_flags": copy.deepcopy(source["truth_flags"]),
    }


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    raise PacketError(f"unsupported JSON Schema type {expected!r}")


def schema_errors(
    value: Any,
    schema: dict[str, Any],
    path: str = "$",
) -> list[str]:
    """Validate the JSON Schema subset declared by this checked-in packet."""
    errors: list[str] = []
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path} must equal {schema['const']!r}")

    expected = schema.get("type")
    if expected is not None:
        require(isinstance(expected, str), f"{path} schema type must be a string")
        if not _matches_type(value, expected):
            return errors + [f"{path} must be a {expected}"]

    if isinstance(value, dict):
        required = schema.get("required", [])
        require(isinstance(required, list), f"{path} required must be a list")
        errors.extend(f"{path}.{key} is required" for key in required if key not in value)

        properties = schema.get("properties", {})
        require(isinstance(properties, dict), f"{path} properties must be an object")
        for key, child_schema in properties.items():
            if key in value:
                require(
                    isinstance(child_schema, dict),
                    f"{path}.{key} schema must be an object",
                )
                errors.extend(schema_errors(value[key], child_schema, f"{path}.{key}"))

        additional = schema.get("additionalProperties", True)
        for key, child in value.items():
            if key in properties:
                continue
            if additional is False:
                errors.append(f"{path}.{key} is not allowed")
            elif isinstance(additional, dict):
                errors.extend(schema_errors(child, additional, f"{path}.{key}"))
        minimum_properties = schema.get("minProperties")
        if minimum_properties is not None and len(value) < minimum_properties:
            errors.append(f"{path} must have at least {minimum_properties} properties")

    if isinstance(value, list):
        minimum_items = schema.get("minItems")
        if minimum_items is not None and len(value) < minimum_items:
            errors.append(f"{path} must contain at least {minimum_items} items")
        maximum_items = schema.get("maxItems")
        if maximum_items is not None and len(value) > maximum_items:
            errors.append(f"{path} must contain at most {maximum_items} items")
        item_schema = schema.get("items")
        if item_schema is not None:
            require(isinstance(item_schema, dict), f"{path} items schema must be an object")
            for index, child in enumerate(value):
                errors.extend(schema_errors(child, item_schema, f"{path}[{index}]"))

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        minimum = schema.get("minimum")
        if minimum is not None and value < minimum:
            errors.append(f"{path} must be at least {minimum}")
        maximum = schema.get("maximum")
        if maximum is not None and value > maximum:
            errors.append(f"{path} must be at most {maximum}")
        exclusive_minimum = schema.get("exclusiveMinimum")
        if exclusive_minimum is not None and value <= exclusive_minimum:
            errors.append(f"{path} must be greater than {exclusive_minimum}")
    return errors


def validate_packet(packet: dict[str, Any]) -> None:
    for key in (
        "schema",
        "id",
        "observed_at",
        "source_path",
        "official_sources",
        "schedule",
        "decision",
        "score_weights",
        "mandatory_gate_keys",
        "targets",
        "reference_slots",
        "proposed_subcontract_scope",
        "outreach_draft",
        "rate_sheet",
        "agreement_checklist",
        "truth_flags",
    ):
        require(key in packet, f"readiness packet missing {key}")
    require(packet["schema"] == READINESS_SCHEMA, "unexpected readiness schema")
    require(packet["source_path"] == "source.json", "unexpected source path")
    require(packet["decision"] == DECISION, "unexpected readiness decision")
    require(
        isinstance(packet["targets"], list) and len(packet["targets"]) >= 4,
        "packet must contain at least four research targets",
    )
    require(
        isinstance(packet["reference_slots"], list)
        and len(packet["reference_slots"]) == 2,
        "packet must contain exactly two reference slots",
    )
    require(
        all(
            isinstance(row, dict)
            and row.get("status") == "OWNER_PRIVATE_EVIDENCE_REQUIRED"
            and row.get("public_contact_data") is False
            for row in packet["reference_slots"]
        ),
        "reference slots must remain public-safe and incomplete",
    )
    require(
        all(value is False for value in packet["truth_flags"].values()),
        "readiness packet must not claim external action or commercial completion",
    )

    for index, target in enumerate(packet["targets"]):
        for key in (
            "company",
            "computed_score",
            "max_score",
            "score_percent",
            "mandatory_gates",
            "missing_mandatory_gates",
            "status",
            "evidence_source",
        ):
            require(key in target, f"target {index} missing {key}")
        gates = target["mandatory_gates"]
        require(
            len(gates) == len(packet["mandatory_gate_keys"]),
            f"target {index} has incomplete mandatory gate projection",
        )
        require(
            target["missing_mandatory_gates"],
            f"target {index} cannot be represented as RFQ-ready without new evidence",
        )
        require(
            target["status"] == "PROVISIONAL_RESEARCH_ONLY",
            f"target {index} has an unsupported readiness status",
        )
    errors = schema_errors(packet, read_json(SCHEMA_FILE))
    require(not errors, "readiness packet fails schema: " + "; ".join(errors))


def render_html(packet: dict[str, Any]) -> str:
    rows = []
    for target in packet["targets"]:
        missing = ", ".join(target["missing_mandatory_gates"])
        rows.append(
            "<tr>"
            f"<td>{html.escape(target['company'])}</td>"
            f"<td>{html.escape(target['proposed_role'])}</td>"
            f"<td>{target['computed_score']}/{target['max_score']}</td>"
            f"<td>{html.escape(missing)}</td>"
            "<td>Research only — incomplete mandatory evidence</td>"
            "</tr>"
        )
    target_rows = "\n".join(rows)
    return f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MWDOC FIN. 2026-001 readiness</title>
<style>body{{font:16px/1.5 system-ui;max-width:1080px;margin:auto;padding:2rem;color:#172033}}h1,h2{{color:#0a4b78}}.hold{{padding:1rem;border-left:6px solid #b42318;background:#fff1f0}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ccd;padding:.6rem;text-align:left;vertical-align:top}}code{{background:#eef;padding:.1rem .3rem}}</style>
<body><h1>MWDOC RFQ FIN. 2026-001 readiness</h1>
<p><code>{html.escape(packet["id"])}</code> · observed {html.escape(packet["observed_at"][:10])}</p>
<div class="hold"><strong>NO-GO AS PRIME / PROVISIONAL PARTNER RESEARCH ONLY / CONDITIONAL SUBCONTRACTOR ONLY.</strong> Public-evidence readiness packet only—not an SOQ, legal opinion, partner recommendation, customer reference, bid, submission, award, or qualification claim.</div>
<h2>Research-target evidence matrix</h2>
<table><thead><tr><th>Company</th><th>Role</th><th>Evidence score</th><th>Mandatory evidence still missing</th><th>Current status</th></tr></thead><tbody>
{target_rows}
</tbody></table>
<h2>Bounded scope</h2>
<p>Commons supports only non-production AP-to-report regression and reconciliation work under a separately verified prime. It is not D365, GCC, public-agency, customer, production, or reference evidence.</p>
<h2>Deadlines</h2><ul><li>Q&amp;A addendum expected by September 4 per the received notice.</li><li>SOQ due September 25, 2026 at 5:00 p.m. Pacific.</li></ul>
<p><a href="README.md">Full handoff</a> · <a href="readiness.json">Generated readiness packet</a> · <a href="readiness.schema.json">Packet schema</a> · <a href="source.json">Source evidence</a> · <a href="rate-sheet-template.csv">Rate template</a></p>
</body></html>
"""


def write_packet(packet: dict[str, Any]) -> None:
    READINESS.write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    READINESS_HTML.write_text(render_html(packet), encoding="utf-8")


def load() -> dict[str, Any]:
    packet = build_packet(load_source())
    validate_packet(packet)
    require(
        read_json(READINESS) == packet,
        "readiness.json is stale; run scripts/build_mwdoc_d365_soq.py --write",
    )
    return packet


def summary(packet: dict[str, Any]) -> str:
    result = {
        "decision": packet["decision"],
        "external_action": False,
        "id": packet["id"],
        "reference_slots_ready": 0,
        "targets": len(packet["targets"]),
        "targets_with_complete_mandatory_evidence": sum(
            not target["missing_mandatory_gates"] for target in packet["targets"]
        ),
    }
    return json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="write the deterministic JSON and no-login HTML projection",
    )
    args = parser.parse_args(argv)
    packet = build_packet(load_source())
    validate_packet(packet)
    if args.write:
        write_packet(packet)
    else:
        require(
            read_json(READINESS) == packet,
            "readiness.json is stale; run scripts/build_mwdoc_d365_soq.py --write",
        )
    print(summary(packet), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
