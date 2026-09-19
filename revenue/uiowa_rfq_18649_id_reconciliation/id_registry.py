#!/usr/bin/env python3
"""Deterministic namespace-qualified identifier reconciliation for UIOWA-103.

The resolver never joins records merely because their local identifiers look alike.
Every identity is the exact tuple (namespace, kind, original_id). Cross-component
equivalence and references must be stated explicitly in the input manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

SCHEMA_VERSION = "uiowa-id-map/v1"
OUTPUT_VERSION = "uiowa-id-map/output-v1"
KINDS = ("source", "observation", "finding", "recommendation", "service")
RELATIONS = ("equivalent", "references")
MAX_MANIFEST_BYTES = 2_000_000


class RegistryError(ValueError):
    """Manifest or identity contract is invalid."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise RegistryError(f"duplicate JSON key: {key!r}")
        out[key] = value
    return out


def loads_strict(payload: str) -> dict[str, Any]:
    try:
        value = json.loads(payload, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise RegistryError(f"invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise RegistryError("manifest root must be a JSON object")
    return value


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise RegistryError(f"cannot read manifest {path}: {exc}") from exc
    if len(raw) > MAX_MANIFEST_BYTES:
        raise RegistryError(
            f"manifest exceeds {MAX_MANIFEST_BYTES} byte safety limit: {len(raw)}"
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RegistryError("manifest must be UTF-8") from exc
    return loads_strict(text)


def _validate_text(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise RegistryError(f"{field} must be a string")
    if not value:
        raise RegistryError(f"{field} must not be empty")
    if value != value.strip():
        raise RegistryError(f"{field} must not have leading/trailing whitespace")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise RegistryError(f"{field} must not contain ASCII control characters")
    return value


def _validate_kind(value: Any, field: str = "kind") -> str:
    kind = _validate_text(value, field)
    if kind not in KINDS:
        raise RegistryError(f"{field} must be one of {list(KINDS)}, got {kind!r}")
    return kind


def _quote_exact(value: str) -> str:
    # quote() always leaves RFC-3986 unreserved bytes alone; all delimiters are encoded.
    return quote(value, safe="")


@dataclass(frozen=True, order=True)
class Identity:
    namespace: str
    kind: str
    original_id: str

    @classmethod
    def from_obj(cls, obj: Any, field: str) -> "Identity":
        if not isinstance(obj, dict):
            raise RegistryError(f"{field} must be an object")
        required = {"namespace", "kind", "original_id"}
        missing = required - set(obj)
        if missing:
            raise RegistryError(f"{field} missing fields: {sorted(missing)}")
        unknown = set(obj) - required
        if unknown:
            raise RegistryError(f"{field} has unsupported fields: {sorted(unknown)}")
        return cls(
            namespace=_validate_text(obj["namespace"], f"{field}.namespace"),
            kind=_validate_kind(obj["kind"], f"{field}.kind"),
            original_id=_validate_text(obj["original_id"], f"{field}.original_id"),
        )

    @property
    def canonical_id(self) -> str:
        return (
            "urn:uiowa-id:v1:"
            f"{self.kind}:{_quote_exact(self.namespace)}:{_quote_exact(self.original_id)}"
        )

    def as_obj(self) -> dict[str, str]:
        return {
            "namespace": self.namespace,
            "kind": self.kind,
            "original_id": self.original_id,
        }


def _identity_from_record(record: dict[str, Any], index: int) -> Identity:
    return Identity(
        namespace=_validate_text(record.get("namespace"), f"records[{index}].namespace"),
        kind=_validate_kind(record.get("kind"), f"records[{index}].kind"),
        original_id=_validate_text(
            record.get("original_id"), f"records[{index}].original_id"
        ),
    )


def _normalized_optional(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _validate_text(value, field)


def _record_payload(record: Any, index: int) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise RegistryError(f"records[{index}] must be an object")
    required = {"namespace", "kind", "original_id"}
    missing = required - set(record)
    if missing:
        raise RegistryError(f"records[{index}] missing fields: {sorted(missing)}")
    allowed = required | {"label", "source_path", "source_revision", "notes"}
    unknown = set(record) - allowed
    if unknown:
        raise RegistryError(f"records[{index}] unsupported fields: {sorted(unknown)}")
    ident = _identity_from_record(record, index)
    return {
        **ident.as_obj(),
        "label": _normalized_optional(record.get("label"), f"records[{index}].label"),
        "source_path": _normalized_optional(
            record.get("source_path"), f"records[{index}].source_path"
        ),
        "source_revision": _normalized_optional(
            record.get("source_revision"), f"records[{index}].source_revision"
        ),
        "notes": _normalized_optional(record.get("notes"), f"records[{index}].notes"),
    }


def _link_payload(link: Any, index: int) -> dict[str, Any]:
    if not isinstance(link, dict):
        raise RegistryError(f"links[{index}] must be an object")
    required = {"link_id", "relation", "from", "to", "basis"}
    missing = required - set(link)
    if missing:
        raise RegistryError(f"links[{index}] missing fields: {sorted(missing)}")
    unknown = set(link) - required
    if unknown:
        raise RegistryError(f"links[{index}] unsupported fields: {sorted(unknown)}")
    link_id = _validate_text(link["link_id"], f"links[{index}].link_id")
    relation = _validate_text(link["relation"], f"links[{index}].relation")
    if relation not in RELATIONS:
        raise RegistryError(
            f"links[{index}].relation must be one of {list(RELATIONS)}, got {relation!r}"
        )
    return {
        "link_id": link_id,
        "relation": relation,
        "from": Identity.from_obj(link["from"], f"links[{index}].from"),
        "to": Identity.from_obj(link["to"], f"links[{index}].to"),
        "basis": _validate_text(link["basis"], f"links[{index}].basis"),
    }


class Registry:
    def __init__(self, manifest: dict[str, Any]):
        if manifest.get("schema_version") != SCHEMA_VERSION:
            raise RegistryError(
                f"schema_version must be {SCHEMA_VERSION!r}, "
                f"got {manifest.get('schema_version')!r}"
            )
        allowed_top = {"schema_version", "records", "links", "description"}
        unknown_top = set(manifest) - allowed_top
        if unknown_top:
            raise RegistryError(f"unsupported top-level fields: {sorted(unknown_top)}")
        raw_records = manifest.get("records")
        raw_links = manifest.get("links")
        if not isinstance(raw_records, list) or not raw_records:
            raise RegistryError("records must be a non-empty array")
        if not isinstance(raw_links, list):
            raise RegistryError("links must be an array")
        description = manifest.get("description")
        if description is not None:
            _validate_text(description, "description")

        self.description = description
        self.records: dict[Identity, dict[str, Any]] = {}
        for i, raw in enumerate(raw_records):
            payload = _record_payload(raw, i)
            ident = Identity(
                payload["namespace"], payload["kind"], payload["original_id"]
            )
            if ident in self.records:
                raise RegistryError(
                    "duplicate identity tuple: "
                    f"{ident.namespace!r}/{ident.kind!r}/{ident.original_id!r}"
                )
            self.records[ident] = payload

        self.links: list[dict[str, Any]] = []
        seen_link_ids: set[str] = set()
        for i, raw in enumerate(raw_links):
            link = _link_payload(raw, i)
            if link["link_id"] in seen_link_ids:
                raise RegistryError(f"duplicate link_id: {link['link_id']!r}")
            seen_link_ids.add(link["link_id"])
            if link["from"] not in self.records:
                raise RegistryError(
                    f"links[{i}] from identity does not exist: "
                    f"{link['from'].canonical_id}"
                )
            if link["to"] not in self.records:
                raise RegistryError(
                    f"links[{i}] to identity does not exist: "
                    f"{link['to'].canonical_id}"
                )
            if link["relation"] == "equivalent" and (
                link["from"].kind != link["to"].kind
            ):
                raise RegistryError(
                    f"links[{i}] equivalent identities must have the same kind"
                )
            if link["relation"] == "equivalent" and link["from"] == link["to"]:
                raise RegistryError(f"links[{i}] equivalent self-link is redundant")
            self.links.append(link)

        self._index: dict[tuple[str, str], list[Identity]] = {}
        for ident in self.records:
            self._index.setdefault((ident.kind, ident.original_id), []).append(ident)
        for candidates in self._index.values():
            candidates.sort(key=lambda x: x.canonical_id)

        self._equivalence_sets = self._build_equivalence_sets()

    @classmethod
    def from_path(cls, path: Path) -> "Registry":
        return cls(load_manifest(path))

    def _build_equivalence_sets(self) -> dict[Identity, tuple[str, tuple[Identity, ...]]]:
        parent: dict[Identity, Identity] = {ident: ident for ident in self.records}

        def find(x: Identity) -> Identity:
            trail: list[Identity] = []
            while parent[x] != x:
                trail.append(x)
                x = parent[x]
            for item in trail:
                parent[item] = x
            return x

        def union(a: Identity, b: Identity) -> None:
            ra, rb = find(a), find(b)
            if ra == rb:
                return
            # Deterministic root choice avoids input-order dependence.
            if ra.canonical_id <= rb.canonical_id:
                parent[rb] = ra
            else:
                parent[ra] = rb

        for link in sorted(self.links, key=lambda item: item["link_id"]):
            if link["relation"] == "equivalent":
                union(link["from"], link["to"])

        groups: dict[Identity, list[Identity]] = {}
        for ident in sorted(self.records, key=lambda x: x.canonical_id):
            groups.setdefault(find(ident), []).append(ident)

        out: dict[Identity, tuple[str, tuple[Identity, ...]]] = {}
        for members in groups.values():
            members = sorted(members, key=lambda x: x.canonical_id)
            kind = members[0].kind
            if any(item.kind != kind for item in members):
                raise RegistryError("internal error: mixed-kind equivalence class")
            digest_payload = "\n".join(item.canonical_id for item in members).encode("utf-8")
            digest = hashlib.sha256(digest_payload).hexdigest()[:24]
            set_id = f"urn:uiowa-equivalence:v1:{kind}:{digest}"
            member_tuple = tuple(members)
            for item in members:
                out[item] = (set_id, member_tuple)
        return out

    def normalized_manifest(self) -> dict[str, Any]:
        records = []
        for ident in sorted(self.records, key=lambda x: x.canonical_id):
            payload = self.records[ident]
            row = {k: payload[k] for k in ("namespace", "kind", "original_id")}
            for key in ("label", "source_path", "source_revision", "notes"):
                if payload[key] is not None:
                    row[key] = payload[key]
            records.append(row)

        links = []
        for link in sorted(self.links, key=lambda x: x["link_id"]):
            links.append(
                {
                    "link_id": link["link_id"],
                    "relation": link["relation"],
                    "from": link["from"].as_obj(),
                    "to": link["to"].as_obj(),
                    "basis": link["basis"],
                }
            )
        out: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "records": records,
            "links": links,
        }
        if self.description is not None:
            out["description"] = self.description
        return out

    @property
    def manifest_digest(self) -> str:
        raw = json.dumps(
            self.normalized_manifest(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def resolve(
        self, *, kind: str, original_id: str, namespace: str | None = None
    ) -> dict[str, Any]:
        kind = _validate_kind(kind, "kind")
        original_id = _validate_text(original_id, "original_id")
        if namespace is not None:
            namespace = _validate_text(namespace, "namespace")
            ident = Identity(namespace, kind, original_id)
            if ident not in self.records:
                return {
                    "status": "not_found",
                    "query": {
                        "namespace": namespace,
                        "kind": kind,
                        "original_id": original_id,
                    },
                    "candidates": [],
                }
            return {
                "status": "resolved",
                "query": {
                    "namespace": namespace,
                    "kind": kind,
                    "original_id": original_id,
                },
                "record": self._render_record(ident),
            }

        candidates = self._index.get((kind, original_id), [])
        query = {"namespace": None, "kind": kind, "original_id": original_id}
        if not candidates:
            return {"status": "not_found", "query": query, "candidates": []}
        if len(candidates) == 1:
            return {
                "status": "resolved",
                "query": query,
                "record": self._render_record(candidates[0]),
            }
        # Even explicitly-equivalent identities remain ambiguous when the caller omits
        # namespace. This makes the non-silent-join contract observable at the API edge.
        return {
            "status": "ambiguous",
            "query": query,
            "candidates": [self._render_record(item) for item in candidates],
        }

    def _render_record(self, ident: Identity) -> dict[str, Any]:
        payload = self.records[ident]
        set_id, members = self._equivalence_sets[ident]
        rendered: dict[str, Any] = {
            "canonical_id": ident.canonical_id,
            "namespace": ident.namespace,
            "kind": ident.kind,
            "original_id": ident.original_id,
            "equivalence_set_id": set_id,
            "equivalence_members": [member.canonical_id for member in members],
        }
        for key in ("label", "source_path", "source_revision", "notes"):
            if payload[key] is not None:
                rendered[key] = payload[key]
        return rendered

    def collisions(self) -> list[dict[str, Any]]:
        out = []
        for (kind, original_id), candidates in sorted(
            self._index.items(), key=lambda item: (item[0][0], item[0][1])
        ):
            if len(candidates) <= 1:
                continue
            out.append(
                {
                    "kind": kind,
                    "original_id": original_id,
                    "namespace_count": len(candidates),
                    "namespaces": [item.namespace for item in candidates],
                    "canonical_ids": [item.canonical_id for item in candidates],
                    "equivalence_set_ids": sorted(
                        {self._equivalence_sets[item][0] for item in candidates}
                    ),
                }
            )
        return out

    def output(self) -> dict[str, Any]:
        rendered_links = []
        for link in sorted(self.links, key=lambda item: item["link_id"]):
            rendered_links.append(
                {
                    "link_id": link["link_id"],
                    "relation": link["relation"],
                    "from_canonical_id": link["from"].canonical_id,
                    "to_canonical_id": link["to"].canonical_id,
                    "basis": link["basis"],
                }
            )
        namespaces: dict[str, int] = {}
        kinds: dict[str, int] = {kind: 0 for kind in KINDS}
        for ident in self.records:
            namespaces[ident.namespace] = namespaces.get(ident.namespace, 0) + 1
            kinds[ident.kind] += 1
        return {
            "schema_version": OUTPUT_VERSION,
            "manifest_digest_sha256": self.manifest_digest,
            "summary": {
                "record_count": len(self.records),
                "link_count": len(self.links),
                "collision_group_count": len(self.collisions()),
                "namespaces": dict(sorted(namespaces.items())),
                "kinds": kinds,
            },
            "records": [
                self._render_record(ident)
                for ident in sorted(self.records, key=lambda x: x.canonical_id)
            ],
            "links": rendered_links,
            "collision_groups": self.collisions(),
        }


def _dump(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    validate_p = sub.add_parser("validate", help="validate a manifest and print summary")
    validate_p.add_argument("manifest", type=Path)

    build_p = sub.add_parser("build", help="emit the deterministic reconciled mapping")
    build_p.add_argument("manifest", type=Path)
    build_p.add_argument("--output", type=Path)

    resolve_p = sub.add_parser("resolve", help="resolve one local ID")
    resolve_p.add_argument("manifest", type=Path)
    resolve_p.add_argument("--kind", required=True, choices=KINDS)
    resolve_p.add_argument("--id", dest="original_id", required=True)
    resolve_p.add_argument("--namespace")

    args = parser.parse_args(argv)
    try:
        registry = Registry.from_path(args.manifest)
        if args.command == "validate":
            result = registry.output()
            print(
                "OK "
                f"records={result['summary']['record_count']} "
                f"links={result['summary']['link_count']} "
                f"collisions={result['summary']['collision_group_count']} "
                f"digest={result['manifest_digest_sha256']}"
            )
            return 0
        if args.command == "build":
            payload = _dump(registry.output())
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(payload, encoding="utf-8")
            else:
                sys.stdout.write(payload)
            return 0
        if args.command == "resolve":
            result = registry.resolve(
                kind=args.kind,
                original_id=args.original_id,
                namespace=args.namespace,
            )
            sys.stdout.write(_dump(result))
            if result["status"] == "resolved":
                return 0
            if result["status"] == "ambiguous":
                return 3
            return 4
    except (RegistryError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
