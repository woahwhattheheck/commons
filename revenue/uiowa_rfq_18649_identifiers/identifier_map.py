"""UIOWA-103: lossless, deterministic identifier crosswalk; no inference engine.

All identifiers remain scoped to an explicit origin and entity kind. Equivalence
is an overlay, never an overwrite of source records or an assessment finding.
"""
from __future__ import annotations

import argparse
import base64
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

SCHEMA = "uiowa-identifiers/v1"
MAX_BYTES = 8 * 1024 * 1024
MAX_ROWS = 20000
Key = tuple[str, str, str]


class InputError(ValueError):
    """Malformed input; distinct from well-formed but unresolved references."""


def canonical(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError, RecursionError) as exc:
        raise InputError("Input must contain finite JSON values") from exc


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for name, value in pairs:
        if name in result:
            raise InputError(f"Duplicate JSON object key: {name!r}")
        result[name] = value
    return result


def read_document(path: Path) -> tuple[Any, dict]:
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise InputError(f"Input exceeds {MAX_BYTES} bytes")
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                          parse_constant=lambda value: _bad_constant(value))
        provenance = {"path": path.as_posix(), "sha256": hashlib.sha256(raw).hexdigest(),
                      "git_blob_sha": hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()}
        return data, provenance
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise InputError(f"Invalid UTF-8 JSON: {exc}") from exc


def load_json(path: Path) -> Any:
    return read_document(path)[0]


def _bad_constant(value: str) -> Any:
    raise InputError(f"Non-finite JSON constant: {value}")


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 1024:
        raise InputError(f"{label} must be a nonblank string of at most 1024 characters")
    return value  # Deliberately no trimming, case folding, or Unicode normalization.


def key(value: Any) -> Key:
    if not isinstance(value, dict) or set(value) != {"origin", "kind", "id"}:
        raise InputError("A qualified key has exactly origin, kind, and id")
    return tuple(_text(value[name], name) for name in ("origin", "kind", "id"))


def key_object(value: Key) -> dict[str, str]:
    return dict(zip(("origin", "kind", "id"), value))


def intrinsic_id(value: Key) -> str:
    # Reversible encoding of the whole tuple: no truncation or delimiter collision.
    raw = canonical(list(value)).encode("ascii")
    return "urn:tjlabs:id:v1:" + base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _rows(document: dict, name: str) -> list[dict]:
    rows = document.get(name, [])
    if not isinstance(rows, list) or len(rows) > MAX_ROWS or any(not isinstance(r, dict) for r in rows):
        raise InputError(f"{name} must be a list of at most {MAX_ROWS} objects")
    return rows


def reconcile(document: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic, lossless crosswalk and explicit join diagnostics.

    Record order and equivalence-edge order do not affect the result. Unqualified
    targets are candidate searches only; they NEVER resolve automatically.
    """
    # Clone to prohibit input mutation and reject non-JSON values in API calls.
    document = json.loads(canonical(document))
    if not isinstance(document, dict) or document.get("schema") != SCHEMA:
        raise InputError(f"schema must be {SCHEMA!r}")
    records = _rows(document, "records")
    aliases = _rows(document, "equivalences")
    references = _rows(document, "references")
    by_key: dict[Key, list[dict]] = defaultdict(list)
    for record in records:
        k = key(record.get("key"))
        if "data" not in record:
            raise InputError("Every record must preserve its source data")
        if record.get("synthetic") is not None and type(record["synthetic"]) is not bool:
            raise InputError("synthetic must be true, false, or null (unknown)")
        by_key[k].append(record)
    keys = sorted(by_key)
    conflicts = set()
    diagnostics = []
    for k in keys:
        signatures = {canonical({n: v for n, v in r.items() if n != "provenance"}) for r in by_key[k]}
        if len(signatures) > 1:
            conflicts.add(k)
            diagnostics.append({"code": "identity_conflict", "key": key_object(k),
                                "detail": "Same qualified identity has conflicting source records; no version was selected."})
    parent = {k: k for k in keys if k not in conflicts}

    def root(k: Key) -> Key:
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    alias_results = []
    for alias in sorted(aliases, key=canonical):
        left, right = key(alias.get("left")), key(alias.get("right"))
        _text(alias.get("basis"), "equivalence basis")
        if alias.get("decision") != "same_entity":
            raise InputError("Equivalence decision must explicitly be same_entity")
        code = None
        if left not in by_key or right not in by_key:
            code = "equivalence_missing_endpoint"
        elif left in conflicts or right in conflicts:
            code = "equivalence_conflicted_endpoint"
        elif left[1] != right[1]:
            code = "equivalence_kind_mismatch"
        elif by_key[left][0].get("synthetic") is not by_key[right][0].get("synthetic"):
            code = "equivalence_synthetic_mismatch"
        if code:
            diagnostics.append({"code": code, "equivalence": alias})
            alias_results.append({"input": alias, "status": code})
        else:
            a, b = root(left), root(right)
            parent[max(a, b)] = min(a, b)
            alias_results.append({"input": alias, "status": "applied"})
    groups: dict[Key, list[Key]] = defaultdict(list)
    for k in parent:
        groups[root(k)].append(k)

    name_groups: dict[tuple[str, str], list[Key]] = defaultdict(list)
    for k in keys:
        name_groups[k[1:]].append(k)

    def target_result(target: Any) -> dict:
        if not isinstance(target, dict):
            raise InputError("Reference target must be an object")
        if "origin" in target:
            k = key(target)
            if k not in by_key:
                return {"status": "missing", "canonical_id": None, "candidates": []}
            if k in conflicts:
                return {"status": "identity_conflict", "canonical_id": None,
                        "candidates": [key_object(k)]}
            return {"status": "resolved", "canonical_id": intrinsic_id(root(k)),
                    "candidates": [key_object(k)]}
        if set(target) != {"kind", "id"}:
            raise InputError("An unqualified target has exactly kind and id")
        kind, original = _text(target["kind"], "kind"), _text(target["id"], "id")
        candidates = name_groups.get((kind, original), [])
        return {"status": "ambiguous" if len(candidates) > 1 else "origin_required",
                "canonical_id": None, "candidates": [key_object(k) for k in candidates]}

    resolved = []
    seen_refs = set()
    for ref in sorted(references, key=canonical):
        rid = _text(ref.get("id"), "reference id")
        source = key(ref.get("from"))
        _text(ref.get("relation"), "reference relation")
        signature = (source, rid)
        if signature in seen_refs:
            raise InputError(f"Duplicate reference ID within source: {rid!r}")
        seen_refs.add(signature)
        source_result = target_result(key_object(source))
        target = target_result(ref.get("to"))
        state = target["status"] if source_result["status"] == "resolved" else "source_" + source_result["status"]
        item = {"input": ref, "status": state, "from": source_result, "to": target}
        resolved.append(item)
        if state != "resolved":
            diagnostics.append({"code": "reference_" + state, "source": key_object(source), "reference_id": rid})
    collisions = []
    for (kind, original), members in sorted(name_groups.items()):
        if len(members) > 1:
            classes = {root(k) for k in members if k not in conflicts}
            collisions.append({"kind": kind, "id": original,
                               "keys": [key_object(k) for k in members],
                               "state": "explicitly_equivalent" if len(classes) == 1 and not any(k in conflicts for k in members) else "distinct_or_conflicted"})
    result = {
        "schema": SCHEMA,
        "input_extensions": {n: v for n, v in document.items() if n not in {"schema", "records", "equivalences", "references"}},
        "entities": [{"key": key_object(k), "intrinsic_id": intrinsic_id(k),
                      "canonical_id": None if k in conflicts else intrinsic_id(root(k)),
                      "status": "identity_conflict" if k in conflicts else "mapped",
                      "occurrences": len(by_key[k]),
                      "records": [json.loads(r) for r in sorted({canonical(r) for r in by_key[k]})]} for k in keys],
        "equivalence_groups": [{"canonical_id": intrinsic_id(k), "members": [key_object(m) for m in sorted(members)]} for k, members in sorted(groups.items())],
        "equivalences": alias_results,
        "references": resolved,
        "name_collisions": collisions,
        "diagnostics": sorted(diagnostics, key=canonical),
        "summary": {"source_records": len(records), "identities": len(keys),
                    "canonical_groups": len(groups), "identity_conflicts": len(conflicts),
                    "name_collisions": len(collisions), "resolved_references": sum(r["status"] == "resolved" for r in resolved),
                    "unresolved_references": sum(r["status"] != "resolved" for r in resolved),
                    "rejected_equivalences": sum(e["status"] != "applied" for e in alias_results)},
    }
    result["mapping_revision"] = hashlib.sha256(canonical(result).encode("ascii")).hexdigest()
    return result


def emit(result: dict, output: Path | None = None) -> int:
    text = json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False) + "\n"
    if output is None:
        sys.stdout.write(text)
    else:
        # Exclusive creation protects original evidence and existing reports.
        with output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
    summary = result["summary"]
    return int(bool(summary["identity_conflicts"] or summary["unresolved_references"] or summary["rejected_equivalences"]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        return emit(reconcile(load_json(args.input)), args.output)
    except (InputError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
