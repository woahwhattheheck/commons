"""Lossless preparation adapters for existing workshare/workbench JSON interfaces.

These are record importers, not replacements for the parent compiler's semantic
verification. Original input is retained as provenance in every adapted packet.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

try:
    from .identity_map import MappingError, SCHEMA, canonical, digest, identity, obj, seq, strict_loads, text
except ImportError:
    from identity_map import MappingError, SCHEMA, canonical, digest, identity, obj, seq, strict_loads, text


def empty_packet(synthetic: bool) -> dict:
    if type(synthetic) is not bool:
        raise MappingError("synthetic label must be explicit")
    return {"schema": SCHEMA, "synthetic": synthetic, "records": [], "canonical_entities": [],
            "mappings": [], "references": [], "component_inputs": []}


def record(namespace: str, kind: str, raw_id: str, version: str | None, payload: dict) -> dict:
    value = {"namespace": namespace, "kind": kind, "id": raw_id, "version": version,
             "payload": copy.deepcopy(payload)}
    identity(value, "adapted record")
    return value


def ref(record_value: dict) -> dict:
    return {k: record_value[k] for k in ("namespace", "kind", "id", "version")}


def _origin(document: dict, namespace: str, locator: str) -> dict:
    text(namespace, "namespace")
    text(locator, "input locator")
    obj(document, "input")
    return {"namespace": namespace, "locator": locator, "document_sha256": digest(document),
            "original_document": copy.deepcopy(document), "verification": "STRUCTURE_ONLY_NOT_COMPILER_VERIFICATION"}


def adapt_authority(document: dict, namespace: str, *, synthetic: bool, locator: str) -> dict:
    """Import v2 evidence-authority *records* without accepting their authority.

    The normalized version is explicitly the authority-generation snapshot, not a
    claimed document revision. Native content digests, source references, claims,
    dimensions, numeric fields and extensions are preserved, not interpreted.
    """
    packet = empty_packet(synthetic)
    packet["component_inputs"].append(_origin(document, namespace, locator))
    if document.get("schema") != "uiowa-rfq18649-evidence-authority/v2":
        raise MappingError("Expected evidence-authority/v2")
    generation = text(document.get("generation"), "authority.generation")
    groups: set[str] = set()
    for source in seq(document.get("sources"), "authority.sources"):
        obj(source, "source")
        sid = text(source.get("source_id"), "source.source_id")
        group = text(source.get("group"), "source.group")
        text(source.get("source_ref"), "source.source_ref")
        source_row = record(namespace, "source", sid, generation, source)
        source_row["version_scope"] = "authority_generation_snapshot"
        source_row["origin_locator"] = f"{locator}#/sources/{len(packet['records'])}"
        packet["records"].append(source_row)
        groups.add(group)
        packet["references"].append({"reference_id": "authority-group:" + digest([namespace, sid, generation]),
            "from": ref(source_row), "to": {"kind": "service", "id": group, "version": None},
            "relation": "scoped_to_group", "native_dimension": source.get("dimension")})
    for group in sorted(groups):
        row = record(namespace, "service", group, None, {"group": group, "scope": "assessment_group_not_application_inventory"})
        row["origin_locator"] = locator + "#/sources/*/group"
        packet["records"].append(row)
    return packet


def adapt_handoff(document: dict, namespace: str, *, locator: str) -> dict:
    """Import the actual workbench draft-handoff/v1 shape as observations.

    The receipt is retained solely as an input binding. Notes remain analyst
    statements, never verified findings. Native dimension values are not renamed.
    """
    obj(document, "handoff")
    if document.get("schema") != "uiowa-rfq18649-analyst-handoff-draft/v1":
        raise MappingError("Expected analyst-handoff-draft/v1")
    if document.get("status") != "DRAFT_NON_AUTHORITATIVE" or document.get("report_mode") != "UNTRUSTED_INSPECTION":
        raise MappingError("Handoff must retain its draft, untrusted mode")
    flags = obj(document.get("authority"), "handoff.authority")
    expected = {"buyer_approved", "prime_approved", "current_evidence_review_authority", "submission_authorized",
                "signature_authorized", "invoice_or_payment_authorized", "recognized_revenue"}
    if not expected.issubset(flags) or any(value is not False for value in flags.values()):
        raise MappingError("Draft handoff must retain false authority flags")
    packet = empty_packet(document.get("synthetic_demo"))
    packet["component_inputs"].append(_origin(document, namespace, locator))
    receipt = text(document.get("report_receipt_sha256"), "handoff.receipt")
    if len(receipt) != 64 or any(c not in "0123456789abcdef" for c in receipt):
        raise MappingError("Handoff receipt must be a lowercase SHA-256 string")
    groups: set[str] = set()
    cells: set[tuple] = set()
    for i, note in enumerate(seq(document.get("cell_notes"), "handoff.cell_notes")):
        obj(note, "cell note")
        group = text(note.get("group"), "note.group")
        dimension = text(note.get("dimension"), "note.dimension")
        if (group, dimension) in cells:
            raise MappingError(f"Duplicate handoff cell {group}/{dimension}")
        cells.add((group, dimension))
        groups.add(group)
        row = record(namespace, "observation", canonical([group, dimension]), receipt, note)
        row.update({"version_scope": "report_receipt_binding", "evidence_class": "ANALYST_NOTE_NOT_VERIFIED_OBSERVATION",
                    "origin_locator": f"{locator}#/cell_notes/{i}"})
        packet["records"].append(row)
        packet["references"].append({"reference_id": "handoff-group:" + digest([namespace, group, dimension, receipt]),
            "from": ref(row), "to": {"kind": "service", "id": group, "version": None},
            "relation": "scoped_to_group", "native_disposition": note.get("disposition")})
    for group in sorted(groups):
        packet["records"].append(record(namespace, "service", group, None,
            {"group": group, "scope": "assessment_group_not_application_inventory"}))
    return packet


def combine(packets: list[dict], *, canonical_entities: list[dict], mappings: list[dict]) -> dict:
    """Compose explicit normalized inputs without overwriting equal-looking IDs."""
    if not packets:
        raise MappingError("At least one component packet is required")
    if any(type(p.get("synthetic")) is not bool for p in packets):
        raise MappingError("Every component requires its explicit synthetic boolean")
    if len({p["synthetic"] for p in packets}) != 1:
        raise MappingError("Synthetic and nonsynthetic collections must remain separate")
    result = empty_packet(packets[0]["synthetic"])
    for packet in packets:
        if packet.get("schema") != SCHEMA:
            raise MappingError("Component schema mismatch")
        for field in ("records", "references", "mappings", "canonical_entities"):
            result[field].extend(copy.deepcopy(seq(packet.get(field), field)))
        result["component_inputs"].extend(copy.deepcopy(packet.get("component_inputs", [])))
    result["canonical_entities"].extend(copy.deepcopy(canonical_entities))
    result["mappings"].extend(copy.deepcopy(mappings))
    # Preserve any unrecognized component-level fields, including empty or null.
    result["component_extensions"] = [{k: copy.deepcopy(v) for k, v in p.items()
        if k not in {"schema", "synthetic", "records", "references", "mappings", "canonical_entities", "component_inputs"}}
        for p in packets]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("format", choices=["authority", "handoff"])
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--synthetic", action="store_true", help="explicit source label for authority bundles only")
    args = parser.parse_args(argv)
    try:
        document = strict_loads(args.input.read_text(encoding="utf-8"))
        if args.format == "authority":
            packet = adapt_authority(document, args.namespace, synthetic=args.synthetic, locator=str(args.input))
        else:
            if args.synthetic and document.get("synthetic_demo") is not True:
                raise MappingError("--synthetic must not relabel a nonsynthetic handoff")
            packet = adapt_handoff(document, args.namespace, locator=str(args.input))
        with args.output.open("x", encoding="utf-8", newline="") as handle:
            handle.write(json.dumps(packet, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
        print(f"Imported {len(packet['records'])} records; original document retained; no compiler verification asserted")
        return 0
    except (MappingError, OSError, ValueError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
