#!/usr/bin/env python3
"""Offline, revision-bound identity joins. No inference of evidence truth or authority."""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

SCHEMA = "uiowa-identifier-bridge/v1"
REPORT_SCHEMA = "uiowa-identifier-bridge-report/v1"
FIELDS = ("namespace", "kind", "local_id", "revision")
MAX_BYTES = 8 * 1024 * 1024


class InputError(ValueError):
    """Invalid input contract; no partial interpretation is returned."""


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def loads(text: str) -> Any:
    def unique(pairs):
        result = {}
        for name, value in pairs:
            if name in result:
                raise InputError(f"duplicate JSON member: {name!r}")
            result[name] = value
        return result

    def constant(value):
        raise InputError(f"non-finite JSON number: {value}")

    try:
        return json.loads(text, object_pairs_hook=unique, parse_constant=constant)
    except (ValueError, RecursionError) as exc:
        raise InputError(str(exc)) from exc


def read_json(path: Path) -> tuple[Any, bytes]:
    with path.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise InputError(f"input exceeds {MAX_BYTES} bytes: {path}")
    try:
        return loads(data.decode("utf-8")), data
    except UnicodeError as exc:
        raise InputError(f"input is not UTF-8: {path}") from exc


def text(value: Any, where: str) -> str:
    if (not isinstance(value, str) or not value.strip()
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise InputError(f"{where}: expected nonblank text without control characters")
    # Deliberately do not trim, case-fold, normalize Unicode, or split delimiters.
    return value


def obj(value: Any, where: str) -> dict:
    if not isinstance(value, dict) or any(not isinstance(k, str) for k in value):
        raise InputError(f"{where}: expected an object with string keys")
    return value


def exact_fields(value: dict, required: set[str], optional: set[str], where: str):
    missing, extra = required - value.keys(), value.keys() - required - optional
    if missing or extra:
        raise InputError(f"{where}: missing={sorted(missing)}, unexpected={sorted(extra)}")


def key(value: Any, partial: bool = False) -> tuple:
    row = obj(value, "key")
    required = {"kind", "local_id"} if partial else set(FIELDS)
    exact_fields(row, required, set(FIELDS) - required, "key")
    for name, val in row.items():
        text(val, f"key.{name}")
    return tuple(row.get(name) for name in FIELDS)


def key_object(parts: tuple) -> dict:
    return {name: value for name, value in zip(FIELDS, parts) if value is not None}


def entity_id(parts: tuple) -> str:
    # A versioned, unambiguous tuple serialization; never delimiter concatenation.
    return "urn:uiowa:entity:v1:" + digest(list(parts))


def _provenance(value: Any, where: str) -> None:
    row = obj(value, where)
    text(row.get("locator"), where + ".locator")


def _rows(packet: dict, name: str) -> list[dict]:
    value = packet.get(name)
    if not isinstance(value, list):
        raise InputError(f"{name}: expected an array")
    return [obj(item, name) for item in value]


def reconcile(packet: dict) -> dict:
    """Return deterministic mappings, unresolved joins, and untouched provenance.

    Crosswalks assert equivalent representations at exact revisions. They do not
    attest authenticity, replace evidence, select the newest version, or rate it.
    """
    obj(packet, "packet")
    exact_fields(packet, {"schema", "records", "crosswalks", "references"},
                 {"extensions"}, "packet")
    if packet["schema"] != SCHEMA:
        raise InputError(f"schema must be {SCHEMA!r}")
    try:
        canonical(packet)
    except (ValueError, TypeError, RecursionError) as exc:
        raise InputError(f"packet is not finite JSON: {exc}") from exc

    records, edges, refs = {}, {}, {}
    by_local = defaultdict(list)
    outgoing = defaultdict(list)
    for row in _rows(packet, "records"):
        exact_fields(row, {"key", "synthetic", "provenance", "payload"}, set(), "record")
        ident = key(row["key"])
        if ident in records:
            raise InputError(f"duplicate qualified key; supply a distinct revision: {ident!r}")
        if row["synthetic"] is not None and type(row["synthetic"]) is not bool:
            raise InputError("record.synthetic: expected true, false, or null (unknown)")
        _provenance(row["provenance"], "record.provenance")
        obj(row["payload"], "record.payload")
        records[ident] = row
        by_local[(ident[1], ident[2])].append(ident)

    for row in _rows(packet, "crosswalks"):
        exact_fields(row, {"id", "from", "to", "basis", "provenance"}, set(), "crosswalk")
        eid = text(row["id"], "crosswalk.id")
        if eid in edges:
            raise InputError(f"duplicate crosswalk id: {eid}")
        src, dst = key(row["from"]), key(row["to"])
        text(row["basis"], "crosswalk.basis")
        _provenance(row["provenance"], "crosswalk.provenance")
        problems = []
        if src not in records or dst not in records:
            problems.append("missing_endpoint")
        if src[1] != dst[1]:
            problems.append("kind_mismatch")
        if src[0] == dst[0] and src[2] == dst[2] and src[3] != dst[3]:
            problems.append("revision_replacement_not_equivalence")
        if src in records and dst in records:
            if records[src]["synthetic"] is not records[dst]["synthetic"]:
                problems.append("synthetic_scope_mismatch")
        edges[eid] = {"input": row, "problems": problems}
        outgoing[src].append((eid, dst))

    for row in _rows(packet, "references"):
        exact_fields(row, {"id", "from", "target", "relation"}, {"extensions"}, "reference")
        rid = text(row["id"], "reference.id")
        if rid in refs:
            raise InputError(f"duplicate reference id: {rid}")
        key(row["from"])
        key(row["target"], partial=True)
        text(row["relation"], "reference.relation")
        refs[rid] = row

    def trace(start: tuple) -> dict:
        current, seen, chain = start, set(), []
        while current in outgoing:
            if current in seen:
                return {"status": "mapping_cycle", "crosswalk_ids": chain}
            seen.add(current)
            links = sorted(outgoing[current])
            chain.extend(eid for eid, _ in links)
            if any(edges[eid]["problems"] for eid, _ in links):
                return {"status": "invalid_crosswalk", "crosswalk_ids": chain}
            targets = {dst for _, dst in links}
            if len(targets) != 1:
                return {"status": "mapping_conflict", "crosswalk_ids": chain}
            current = next(iter(targets))
        return {"status": "mapped" if chain else "identity",
                "resolved_entity_id": entity_id(current),
                "resolved_key": key_object(current), "crosswalk_ids": chain}

    mappings = {ident: trace(ident) for ident in sorted(records)}
    record_output = [{"input": records[ident], "entity_id": entity_id(ident),
                      **mappings[ident]} for ident in sorted(records)]
    reference_output = []
    for rid, row in sorted(refs.items()):
        src, requested = key(row["from"]), key(row["target"], partial=True)
        pool = sorted(by_local.get((requested[1], requested[2]), []))
        candidates = [item for item in pool if all(want is None or want == actual
                      for want, actual in zip(requested, item))]
        result = {"input": row, "candidates": [key_object(x) for x in candidates]}
        if src not in records:
            result["status"] = "missing_source_record"
        elif mappings[src]["status"] not in {"identity", "mapped"}:
            result["status"] = "source_mapping_error"
            result["source_mapping"] = mappings[src]
        elif not candidates:
            nearby = [x for x in pool if requested[0] is None or x[0] == requested[0]]
            result["status"] = "revision_mismatch" if nearby and requested[3] else "missing"
            result["available_versions"] = [key_object(x) for x in nearby]
        elif len(candidates) > 1:
            result["status"] = "ambiguous"
        elif requested[0] is None:
            result["status"] = "namespace_required"
        elif requested[3] is None:
            result["status"] = "revision_required"
        else:
            match = candidates[0]
            route = mappings[match]
            result.update(route)
            result["target_entity_id"] = entity_id(match)
            if route["status"] in {"identity", "mapped"}:
                result["status"] = "resolved"
        reference_output.append(result)

    collisions = [{"kind": kind, "local_id": local,
                   "keys": [key_object(x) for x in sorted(items)]}
                  for (kind, local), items in sorted(by_local.items()) if len(items) > 1]
    normalized = {**packet,
                  "records": [records[x] for x in sorted(records)],
                  "crosswalks": [edges[x]["input"] for x in sorted(edges)],
                  "references": [refs[x] for x in sorted(refs)]}
    counts = defaultdict(int)
    for row in reference_output:
        counts[row["status"]] += 1
    invalid_edges = sum(bool(x["problems"]) for x in edges.values())
    failed_maps = sum(x["status"] not in {"identity", "mapped"} for x in mappings.values())
    unresolved = sum(x["status"] != "resolved" for x in reference_output)
    report = {"schema": REPORT_SCHEMA, "input_sha256": digest(normalized),
              "records": record_output,
              "crosswalks": [edges[x] for x in sorted(edges)],
              "references": reference_output, "local_id_collisions": collisions,
              "extensions": packet.get("extensions", {}),
              "summary": {"records": len(records), "crosswalks": len(edges),
                          "references": len(refs), "reference_statuses": dict(sorted(counts.items())),
                          "unresolved_references": unresolved, "invalid_crosswalks": invalid_edges,
                          "unresolved_record_mappings": failed_maps,
                          "colliding_local_ids": len(collisions)},
              "has_unresolved_joins": bool(unresolved or invalid_edges or failed_maps)}
    report["report_sha256"] = digest(report)
    return report


def _cell(value: Any) -> str:
    return html.escape(str(value), quote=True).replace("|", "&#124;").replace("`", "&#96;").replace("\n", " ")


def render_markdown(report: dict) -> str:
    lines = ["# Identifier reconciliation", "",
             "Record consistency only: not evidence verification, approval, or a University finding.", "",
             "`synthetic: null` means unknown; equivalence assertions do not establish truth.", "",
             "## Summary", "", "```json", json.dumps(report["summary"], sort_keys=True, indent=2), "```", "",
             "## Reference results", "", "| Reference | Relation | Status | Original target | Resolved target |",
             "|---|---|---|---|---|"]
    for row in report["references"]:
        values = [row["input"]["id"], row["input"]["relation"], row["status"],
                  canonical(row["input"]["target"]), canonical(row.get("resolved_key"))]
        lines.append("| " + " | ".join(_cell(x) for x in values) + " |")
    lines += ["", "## Same-looking IDs (not automatically joined)", ""]
    for row in report["local_id_collisions"]:
        lines.append("- " + _cell(row["kind"] + "/" + row["local_id"]) + ": " + _cell(canonical(row["keys"])))
    lines += ["", "Full input records, exact locators, crosswalk bases and candidate keys are retained in report.json.", ""]
    return "\n".join(lines)


def render_csv(report: dict, name: str) -> str:
    """All user-originated values are JSON cells, preserving IDs and avoiding formulas."""
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    if name == "records":
        writer.writerow(["entity_id", "status", "resolved_entity_id", "key_json", "synthetic_json",
                         "crosswalk_ids_json", "provenance_json", "payload_json"])
        for row in report["records"]:
            src = row["input"]
            writer.writerow([row["entity_id"], row["status"], row.get("resolved_entity_id", ""),
                             canonical(src["key"]), canonical(src["synthetic"]),
                             canonical(row["crosswalk_ids"]), canonical(src["provenance"]), canonical(src["payload"])])
    elif name == "references":
        writer.writerow(["reference_id_json", "status", "input_json", "resolution_json"])
        for row in report["references"]:
            writer.writerow([canonical(row["input"]["id"]), row["status"], canonical(row["input"]),
                             canonical({k: v for k, v in row.items() if k != "input"})])
    else:
        raise InputError("CSV name must be records or references")
    return stream.getvalue()


def write_bundle(report: dict, destination: Path) -> None:
    """Create a new bundle only; the manifest is written last as a completion marker."""
    files = {"report.json": json.dumps(report, sort_keys=True, indent=2, ensure_ascii=True) + "\n",
             "report.md": render_markdown(report), "records.csv": render_csv(report, "records"),
             "references.csv": render_csv(report, "references")}
    manifest = {"schema": "uiowa-identifier-bundle/v1", "report_sha256": report["report_sha256"],
                "files": {name: hashlib.sha256(body.encode("utf-8")).hexdigest()
                          for name, body in sorted(files.items())}}
    destination.mkdir()  # No overwrite, including existing directories or symlinks.
    for name, body in sorted(files.items()):
        with (destination / name).open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(body)
    with (destination / "manifest.json").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(manifest, sort_keys=True, indent=2) + "\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path, help="new output directory; existing paths are never overwritten")
    args = parser.parse_args(argv)
    try:
        packet, _ = read_json(args.input)
        report = reconcile(packet)
        if args.out:
            write_bundle(report, args.out)
            print(canonical(report["summary"]))
        else:
            print(json.dumps(report, sort_keys=True, indent=2))
        return 1 if report["has_unresolved_joins"] else 0
    except (InputError, OSError, RecursionError) as exc:
        parser.exit(2, f"identifier bridge: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
