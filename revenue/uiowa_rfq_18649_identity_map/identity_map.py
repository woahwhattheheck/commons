#!/usr/bin/env python3
"""Offline namespace-safe joins. Mapping resolves identities, not evidence truth."""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SCHEMA = "uiowa-identity-map/v1"
KINDS = {"source", "observation", "finding", "recommendation", "service"}


class MappingError(ValueError):
    """An input does not satisfy the interchange contract."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def strict_loads(text: str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict:
        result: dict = {}
        for key, value in items:
            if key in result:
                raise MappingError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def bad_number(value: str) -> None:
        raise MappingError(f"Non-finite JSON number: {value}")

    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=bad_number)
    except (ValueError, TypeError) as exc:
        raise MappingError(str(exc)) from exc


def text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MappingError(f"{label}: expected a nonempty string")
    # Identity strings are exact: no stripping, case folding, or Unicode normalization.
    return value


def obj(value: Any, label: str) -> dict:
    if not isinstance(value, dict):
        raise MappingError(f"{label}: expected an object")
    return value


def seq(value: Any, label: str) -> list:
    if not isinstance(value, list):
        raise MappingError(f"{label}: expected a list")
    return value


def identity(value: Any, label: str, *, version_required: bool = True) -> tuple:
    value = obj(value, label)
    namespace = text(value.get("namespace"), label + ".namespace")
    kind = text(value.get("kind"), label + ".kind")
    if kind not in KINDS:
        raise MappingError(f"{label}.kind: unsupported kind {kind!r}")
    raw_id = text(value.get("id"), label + ".id")
    if version_required:
        # None means explicitly unknown version, not an empty string or latest.
        if "version" not in value:
            raise MappingError(f"{label}.version: required; use null for unknown")
        version = value["version"]
        if version is not None:
            text(version, label + ".version")
        return namespace, kind, raw_id, version
    return namespace, kind, raw_id


def key(value: tuple) -> str:
    return canonical(list(value))


def scoped_id(value: tuple) -> str:
    # Full digest; JSON tuple framing avoids separator and escaping collisions.
    return "sid:" + digest(list(value))


def ref_key(value: dict) -> tuple:
    return identity(value, "reference target")


def _sorted(values: list) -> list:
    return sorted(values, key=canonical)


def reconcile(packet: dict) -> dict:
    """Preserve raw records and resolve only explicit, unambiguous identity links.

    All lists are order-independent. Duplicate identical records retain occurrence
    counts. Different payloads for the same fully qualified version are conflicts.
    A canonical mapping is a user-supplied assertion with retained rationale, not
    an inferred equivalence or a maturity/approval decision.
    """
    obj(packet, "packet")
    if packet.get("schema") != SCHEMA:
        raise MappingError(f"Expected schema {SCHEMA}")
    if type(packet.get("synthetic")) is not bool:
        raise MappingError("packet.synthetic: explicit boolean required")
    seq(packet.get("records"), "records")
    seq(packet.get("canonical_entities"), "canonical_entities")
    seq(packet.get("mappings"), "mappings")
    seq(packet.get("references"), "references")
    # Validate JSON compatibility before doing partial work.
    digest(packet)

    variants: dict[tuple, dict[str, dict]] = defaultdict(dict)
    occurrences: Counter = Counter()
    entities: dict[tuple, set[tuple]] = defaultdict(set)
    for record in packet["records"]:
        ident = identity(record, "record")
        obj(record.get("payload"), "record.payload")
        fingerprint = digest(record)
        variants[ident][fingerprint] = copy.deepcopy(record)
        occurrences[(ident, fingerprint)] += 1
        entities[ident[:3]].add(ident)

    canon: dict[tuple, dict] = {}
    for entity in packet["canonical_entities"]:
        obj(entity, "canonical entity")
        kind = text(entity.get("kind"), "canonical.kind")
        if kind not in KINDS:
            raise MappingError("canonical.kind: unsupported kind")
        ident = (kind, text(entity.get("id"), "canonical.id"))
        if ident in canon:
            raise MappingError(f"Duplicate canonical entity: {key(ident)}")
        canon[ident] = copy.deepcopy(entity)

    mapping_rows: dict[tuple, list[dict]] = defaultdict(list)
    mapping_ids: set[str] = set()
    diagnostics: list[dict] = []
    for mapping in packet["mappings"]:
        obj(mapping, "mapping")
        mid = text(mapping.get("mapping_id"), "mapping.mapping_id")
        if mid in mapping_ids:
            raise MappingError(f"Duplicate mapping ID: {mid}")
        mapping_ids.add(mid)
        source = identity(mapping.get("source"), "mapping.source", version_required=False)
        # Entity-level mappings apply across versions, but never choose a version.
        if "version" in mapping["source"]:
            raise MappingError("mapping.source is entity-scoped; version must be omitted")
        target = obj(mapping.get("canonical"), "mapping.canonical")
        target_key = (text(target.get("kind"), "mapping.canonical.kind"),
                      text(target.get("id"), "mapping.canonical.id"))
        text(mapping.get("rationale"), "mapping.rationale")
        text(mapping.get("basis"), "mapping.basis")
        if source[1] != target_key[0]:
            raise MappingError(f"Mapping {mid} changes kind")
        if target_key not in canon:
            raise MappingError(f"Mapping {mid} names an unknown canonical entity")
        if source not in entities:
            diagnostics.append({"code": "MAPPING_SOURCE_ABSENT", "mapping_id": mid, "source": list(source)})
        mapping_rows[source].append(copy.deepcopy(mapping))

    def mapped(entity: tuple) -> tuple[str, list, list]:
        rows = _sorted(mapping_rows.get(entity, []))
        targets = sorted({key((r["canonical"]["kind"], r["canonical"]["id"])) for r in rows})
        if not targets:
            return "UNMAPPED", [], rows
        if len(targets) > 1:
            return "AMBIGUOUS_MAPPING", [json.loads(t) for t in targets], rows
        return "MAPPED", [json.loads(targets[0])], rows

    registry: list[dict] = []
    for ident in sorted(variants, key=key):
        mapping_state, targets, rows = mapped(ident[:3])
        record_state = "IDENTITY_CONFLICT" if len(variants[ident]) > 1 else "UNIQUE_RECORD"
        if record_state == "IDENTITY_CONFLICT":
            diagnostics.append({"code": record_state, "identity": list(ident), "variant_count": len(variants[ident])})
        if mapping_state == "AMBIGUOUS_MAPPING":
            diagnostics.append({"code": mapping_state, "identity": list(ident), "candidates": targets})
        registry.append({
            "identity": list(ident), "scoped_id": scoped_id(ident[:3]),
            "version_id": scoped_id(ident), "record_state": record_state,
            "mapping_state": mapping_state, "canonical_candidates": targets,
            "mapping_assertions": rows,
            "variants": [{"record_sha256": fp, "occurrences": occurrences[(ident, fp)], "record": record}
                         for fp, record in sorted(variants[ident].items())],
        })

    # A label collision is informative, not an error and never a join instruction.
    labels: dict[tuple, set[str]] = defaultdict(set)
    for namespace, kind, rid in entities:
        labels[(kind, rid)].add(namespace)
    collisions = [{"kind": kind, "raw_id": rid, "namespaces": sorted(namespaces)}
                  for (kind, rid), namespaces in sorted(labels.items()) if len(namespaces) > 1]

    resolutions: list[dict] = []
    seen_refs: set[str] = set()
    for reference in packet["references"]:
        obj(reference, "reference")
        rid = text(reference.get("reference_id"), "reference.reference_id")
        if rid in seen_refs:
            raise MappingError(f"Duplicate reference ID: {rid}")
        seen_refs.add(rid)
        source = identity(reference.get("from"), "reference.from")
        target = obj(reference.get("to"), "reference.to")
        text(reference.get("relation"), "reference.relation")
        target_kind = text(target.get("kind"), "reference.to.kind")
        if target_kind not in KINDS:
            raise MappingError("reference.to.kind: unsupported kind")
        target_id = text(target.get("id"), "reference.to.id")
        # Omitted namespace means LOCAL, never search-all fallback.
        namespace = text(target.get("namespace", source[0]), "reference.to.namespace")
        entity_key = (namespace, target_kind, target_id)
        if "version" in target:
            if target["version"] is not None:
                text(target["version"], "reference.to.version")
            candidate = entity_key + (target["version"],)
            candidates = {candidate} if candidate in variants else set()
        else:
            candidates = entities.get(entity_key, set())
        result = {"reference_id": rid, "original": copy.deepcopy(reference),
                  "namespace_rule": "EXPLICIT" if "namespace" in target else "LOCAL_DEFAULT",
                  "target_candidates": [list(x) for x in sorted(candidates, key=key)],
                  "canonical_target": None, "target_version_id": None}
        if source not in variants:
            result["status"] = "MISSING_FROM_RECORD"
        elif len(variants[source]) > 1:
            result["status"] = "FROM_IDENTITY_CONFLICT"
        elif not candidates:
            result["status"] = "MISSING_TARGET"
        elif len(candidates) > 1:
            result["status"] = "AMBIGUOUS_VERSION"
        else:
            selected = next(iter(candidates))
            result["target_version_id"] = scoped_id(selected)
            if len(variants[selected]) > 1:
                result["status"] = "TARGET_IDENTITY_CONFLICT"
            else:
                state, targets, _ = mapped(selected[:3])
                if state == "AMBIGUOUS_MAPPING":
                    result["status"] = "AMBIGUOUS_MAPPING"
                elif state == "UNMAPPED":
                    result["status"] = "RESOLVED_SCOPED_ONLY"
                else:
                    result["status"] = "RESOLVED_CANONICAL"
                    result["canonical_target"] = targets[0]
        resolutions.append(result)

    # The input digest uses normalized top-level lists, while preserving payload
    # list order. Original input is not mutated and all extension fields survive.
    normalized_input = copy.deepcopy(packet)
    for field in ("records", "canonical_entities", "mappings", "references"):
        normalized_input[field] = _sorted(normalized_input[field])
    result = {
        "schema": "uiowa-identity-map-result/v1", "synthetic": packet["synthetic"],
        "status": "IDENTITY_RECONCILIATION_ONLY",
        "current_evidence_review_authority": False,
        "source_packet_sha256": digest(normalized_input),
        "input_extensions": {k: copy.deepcopy(v) for k, v in packet.items()
                             if k not in {"schema", "synthetic", "records", "canonical_entities", "mappings", "references"}},
        "canonical_entities": _sorted(list(canon.values())),
        "mapping_assertions": _sorted(copy.deepcopy(packet["mappings"])),
        "registry": registry, "label_collisions": collisions,
        "references": sorted(resolutions, key=lambda r: r["reference_id"]),
        "diagnostics": _sorted(diagnostics),
        "reference_status_counts": dict(sorted(Counter(r["status"] for r in resolutions).items())),
    }
    result["result_sha256"] = digest(result)
    return result


def render_markdown(result: dict) -> str:
    def cell(value: Any) -> str:
        return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("|", "&#124;").replace("\r", " ").replace("\n", "<br>")
    lines = ["# Identifier reconciliation", "",
             "SYNTHETIC PREPARATION — NOT UNIVERSITY FINDINGS" if result["synthetic"] else "DRAFT IDENTITY RECONCILIATION — NOT AN ASSESSMENT",
             "", "Mapping consistency does not establish source authenticity, maturity, approval, or equivalence of observed practice.",
             "", f"Result digest: `{result['result_sha256']}`", "",
             "## Reference outcomes", "", "| Reference | Status | Namespace rule | Target |", "|---|---|---|---|"]
    for row in result["references"]:
        target = row["canonical_target"] or row["target_candidates"]
        lines.append("| " + " | ".join(cell(v) for v in (row["reference_id"], row["status"], row["namespace_rule"], canonical(target))) + " |")
    lines += ["", "## Same labels, distinct namespaces", ""]
    for row in result["label_collisions"]:
        lines.append(f"- {cell(row['kind'])} `{cell(row['raw_id'])}`: {cell(', '.join(row['namespaces']))}. No automatic join.")
    if not result["label_collisions"]:
        lines.append("No cross-namespace label collisions in the supplied collection.")
    lines += ["", "## Exact record and mapping register", "", "| Original identity including version | Record state | Mapping state | Canonical candidates |", "|---|---|---|---|"]
    for row in result["registry"]:
        lines.append("| " + " | ".join(cell(v) for v in (canonical(row["identity"]), row["record_state"], row["mapping_state"], canonical(row["canonical_candidates"]))) + " |")
    lines += ["", "## Diagnostics", ""]
    lines.extend("- " + cell(canonical(d)) for d in result["diagnostics"])
    if not result["diagnostics"]:
        lines.append("No record/mapping conflicts detected. Missing reference targets are listed above.")
    lines += ["", "## Interpretation", "", "RESOLVED_SCOPED_ONLY is a real local reference, not an unresolved identity. RESOLVED_CANONICAL additionally follows explicit mapping assertions. AMBIGUOUS_VERSION requires an exact version; no newest-version inference is made. Missing local IDs never fall back to a same-looking record in a different component. Full original records, mappings, and reference metadata remain in JSON.", ""]
    return "\n".join(lines)


def csv_text(rows: list[dict], fields: list[str]) -> str:
    # JSON-encoded cells preserve null, empty, numeric, list, Unicode and formula-
    # looking values without treating raw strings as spreadsheet expressions.
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(fields)
    for row in rows:
        writer.writerow([canonical(row.get(field)) for field in fields])
    return out.getvalue()


def artifacts(result: dict) -> dict[str, str]:
    return {
        "identity-map.json": json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
        "identity-map.md": render_markdown(result),
        "references.csv": csv_text(result["references"], ["reference_id", "status", "namespace_rule", "target_candidates", "canonical_target", "original"]),
        "registry.csv": csv_text(result["registry"], ["identity", "scoped_id", "version_id", "record_state", "mapping_state", "canonical_candidates", "mapping_assertions", "variants"]),
    }


def write_artifacts(outputs: dict[str, str], directory: Path) -> None:
    # A new directory prevents accidental replacement of an earlier run.
    directory.mkdir(parents=True, exist_ok=False)
    for name, content in outputs.items():
        with (directory / name).open("x", encoding="utf-8", newline="") as handle:
            handle.write(content)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path, help="new output directory")
    args = parser.parse_args(argv)
    try:
        result = reconcile(strict_loads(args.input.read_text(encoding="utf-8")))
        write_artifacts(artifacts(result), args.output)
        print(canonical({"result_sha256": result["result_sha256"], "reference_status_counts": result["reference_status_counts"], "output": str(args.output)}))
        return 0
    except (MappingError, OSError, ValueError, TypeError, RecursionError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
