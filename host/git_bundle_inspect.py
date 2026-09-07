#!/usr/bin/env python3
"""Inspect/recover available objects from Git bundles, without Git or networking.

A valid pack checksum is integrity evidence, not provenance or authentication.
Recovered objects are not a checkout. See docs/git-bundle-inspect.md.
"""
from __future__ import annotations

import argparse
import collections
from collections.abc import Iterator
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import sys
import zlib


class BundleError(ValueError):
    """Malformed, unsupported, or over-budget bundle."""


@dataclasses.dataclass(frozen=True)
class Limits:
    input_bytes: int = 64 * 1024 * 1024
    header_bytes: int = 1024 * 1024
    object_bytes: int = 16 * 1024 * 1024
    decoded_bytes: int = 128 * 1024 * 1024
    objects: int = 50000
    delta_depth: int = 64
    object_links: int = 250000

    def __post_init__(self) -> None:
        if any(value <= 0 for value in dataclasses.asdict(self).values()):
            raise BundleError("all limits must be positive")


@dataclasses.dataclass(frozen=True)
class GitObject:
    kind: str
    data: bytes


@dataclasses.dataclass
class Inspection:
    report: dict
    objects: dict[str, GitObject]


@dataclasses.dataclass
class _Entry:
    offset: int
    kind: int
    data: bytes
    base: str | int | None = None
    oid: str | None = None
    depth: int = 0


_TYPES = {1: "commit", 2: "tree", 3: "blob", 4: "tag"}


def _fail(condition: bool, message: str) -> None:
    if condition:
        raise BundleError(message)


def _oid(kind: str, data: bytes, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    digest.update(f"{kind} {len(data)}\0".encode("ascii"))
    digest.update(data)
    return digest.hexdigest()


def _header(data: bytes, limits: Limits) -> tuple[dict, int]:
    end = data.find(b"\n\n", 0, limits.header_bytes + 1)
    _fail(end < 0 or end + 2 > limits.header_bytes, "missing/oversized bundle header")
    lines = data[:end].split(b"\n")
    signatures = {b"# v2 git bundle": 2, b"# v3 git bundle": 3}
    _fail(lines[0] not in signatures, "unsupported bundle signature")
    version = signatures[lines[0]]
    capabilities: dict[str, str | None] = {}
    prerequisites: list[dict] = []
    references: list[dict] = []
    rows: list[tuple[bool, bytes, bytes]] = []
    phase = 0
    for line in lines[1:]:
        if line.startswith(b"@"):
            _fail(version != 3 or phase != 0, "misplaced bundle capability")
            key, sep, value = line[1:].partition(b"=")
            _fail(not re.fullmatch(rb"[A-Za-z0-9-]+", key), "invalid capability key")
            name = key.decode("ascii")
            _fail(name not in {"object-format", "filter"}, f"unsupported capability: {name}")
            _fail(name in capabilities, "duplicate capability")
            capabilities[name] = value.decode("utf-8", "surrogateescape") if sep else None
            continue
        prerequisite = line.startswith(b"-")
        _fail(prerequisite and phase == 2, "prerequisite follows reference")
        phase = 1 if prerequisite else 2
        object_id, sep, label = (line[1:] if prerequisite else line).partition(b" ")
        _fail(not sep or (not prerequisite and not label), "invalid bundle reference")
        rows.append((prerequisite, object_id, label))
    algorithm = capabilities.get("object-format", "sha1")
    _fail(algorithm not in {"sha1", "sha256"}, "unsupported object format")
    length = hashlib.new(algorithm).digest_size * 2
    seen_refs: set[bytes] = set()
    for prerequisite, object_id, label in rows:
        _fail(not re.fullmatch(rb"[0-9a-f]{" + str(length).encode() + rb"}", object_id),
              "invalid object ID in header")
        if not prerequisite:
            _fail(label in seen_refs, "duplicate reference name")
            seen_refs.add(label)
        record = {"oid": object_id.decode(), "comment" if prerequisite else "name":
                  label.decode("utf-8", "surrogateescape")}
        (prerequisites if prerequisite else references).append(record)
    return {"bundle_version": version, "object_format": algorithm,
            "capabilities": capabilities, "prerequisites": prerequisites,
            "references": references}, end + 2


def _inflate(data: bytes, position: int, end: int, size: int) -> tuple[bytes, int]:
    """Consume exactly one bounded zlib stream; avoid copying the remaining pack."""
    stream = zlib.decompressobj()
    output = bytearray()
    while not stream.eof:
        _fail(position >= end, "truncated compressed object")
        chunk = memoryview(data)[position:min(position + 65536, end)]
        try:
            part = stream.decompress(chunk, size - len(output) + 1)
        except zlib.error as error:
            raise BundleError("invalid compressed object") from error
        output.extend(part)
        _fail(len(output) > size, "inflated object exceeds declared size")
        consumed = len(chunk) - len(stream.unused_data) - len(stream.unconsumed_tail)
        _fail(consumed <= 0 and not part, "compressed object made no progress")
        position += consumed
    _fail(len(output) != size, "inflated object size mismatch")
    return bytes(output), position


def _varint(data: bytes, position: int) -> tuple[int, int]:
    value = 0
    for shift in range(0, 70, 7):
        _fail(position >= len(data), "truncated delta size")
        byte = data[position]
        position += 1
        value |= (byte & 127) << shift
        if not byte & 128:
            return value, position
    raise BundleError("delta size encoding is too long")


def _delta(delta: bytes, limits: Limits, base: bytes | None = None) -> tuple[int, bytes | None]:
    """Validate instructions even for unavailable bases; optionally apply them."""
    base_size, position = _varint(delta, 0)
    result_size, position = _varint(delta, position)
    _fail(max(base_size, result_size) > limits.object_bytes, "delta object size limit exceeded")
    _fail(base is not None and len(base) != base_size, "delta base size mismatch")
    output = bytearray() if base is not None else None
    written = 0
    while position < len(delta):
        opcode = delta[position]
        position += 1
        _fail(opcode == 0, "reserved delta opcode")
        if opcode & 128:
            offset = count = 0
            for bit in range(7):
                if opcode & (1 << bit):
                    _fail(position >= len(delta), "truncated delta copy")
                    byte = delta[position]
                    position += 1
                    if bit < 4:
                        offset |= byte << (8 * bit)
                    else:
                        count |= byte << (8 * (bit - 4))
            count = count or 65536
            _fail(offset + count > base_size, "delta copy outside base")
            if output is not None:
                output.extend(base[offset:offset + count])
        else:
            count = opcode
            _fail(position + count > len(delta), "truncated delta literal")
            if output is not None:
                output.extend(delta[position:position + count])
            position += count
        written += count
        _fail(written > result_size, "delta output exceeds declared size")
    _fail(written != result_size, "delta result size mismatch")
    return result_size, bytes(output) if output is not None else None


def _dependencies(obj: GitObject, hash_bytes: int) -> Iterator[tuple[str, str | None]]:
    """Read object links only, never materialize tree paths or execute contents."""
    if obj.kind == "blob":
        return
    if obj.kind == "tree":
        position = 0
        while position < len(obj.data):
            space = obj.data.find(b" ", position)
            nul = obj.data.find(b"\0", space + 1)
            _fail(space < 0 or nul < 0 or nul + 1 + hash_bytes > len(obj.data), "malformed tree entry")
            mode = obj.data[position:space]
            name = obj.data[space + 1:nul]
            _fail(mode not in {b"40000", b"100644", b"100755", b"120000", b"160000"}
                  or not name or b"/" in name, "malformed tree mode/name")
            target = obj.data[nul + 1:nul + 1 + hash_bytes].hex()
            # Gitlinks name commits in a separate repository, not bundle dependencies.
            if mode != b"160000":
                yield target, "tree" if mode == b"40000" else "blob"
            position = nul + 1 + hash_bytes
        return
    headers, sep, _ = obj.data.partition(b"\n\n")
    _fail(not sep, "missing object header terminator")
    targets = []
    for line in headers.split(b"\n"):
        key, _, value = line.partition(b" ")
        if (obj.kind == "commit" and key in {b"tree", b"parent"}) or (obj.kind == "tag" and key == b"object"):
            _fail(not re.fullmatch(rb"[0-9a-f]{" + str(hash_bytes * 2).encode() + rb"}", value),
                  "malformed object dependency")
            yield value.decode(), "tree" if key == b"tree" else "commit" if key == b"parent" else None
            targets.append(key)
    _fail((obj.kind == "commit" and targets.count(b"tree") != 1)
          or (obj.kind == "tag" and targets.count(b"object") != 1), "missing/duplicate object target")


def inspect_bundle(data: bytes, limits: Limits | None = None) -> Inspection:
    limits = limits or Limits()
    _fail(len(data) > limits.input_bytes, "bundle input size limit exceeded")
    report, pack_start = _header(data, limits)
    algorithm = report["object_format"]
    hash_bytes = hashlib.new(algorithm).digest_size
    pack_end = len(data) - hash_bytes
    _fail(pack_end < pack_start + 12 or data[pack_start:pack_start + 4] != b"PACK", "missing/truncated pack")
    version, count = struct.unpack_from(">II", data, pack_start + 4)
    _fail(version not in {2, 3}, "unsupported pack version")
    _fail(count > limits.objects, "pack object count limit exceeded")
    digest = hashlib.new(algorithm, memoryview(data)[pack_start:pack_end]).digest()
    _fail(digest != data[pack_end:], "pack checksum mismatch")
    entries: list[_Entry] = []
    by_offset: dict[int, _Entry] = {}
    position, decoded = pack_start + 12, 0
    for _ in range(count):
        _fail(position >= pack_end, "truncated pack object header")
        offset = position - pack_start
        byte = data[position]
        position += 1
        kind, size, shift = (byte >> 4) & 7, byte & 15, 4
        _fail(kind not in {*_TYPES, 6, 7}, "invalid pack object type")
        while byte & 128:
            _fail(position >= pack_end or shift > 67, "truncated/oversized object size encoding")
            byte = data[position]
            position += 1
            size |= (byte & 127) << shift
            shift += 7
        _fail(size > limits.object_bytes, "object size limit exceeded")
        decoded += size
        _fail(decoded > limits.decoded_bytes, "total decoded size limit exceeded")
        base = None
        if kind == 7:
            _fail(position + hash_bytes > pack_end, "truncated reference delta")
            base = data[position:position + hash_bytes].hex()
            position += hash_bytes
        elif kind == 6:
            distance = 0
            for _ in range(10):
                _fail(position >= pack_end, "truncated offset delta")
                byte = data[position]
                position += 1
                distance = (distance << 7) + (byte & 127)
                if not byte & 128:
                    break
                distance += 1
            else:
                raise BundleError("offset delta encoding is too long")
            base = offset - distance
            _fail(distance == 0 or base not in by_offset, "offset delta does not name an earlier entry")
        payload, position = _inflate(data, position, pack_end, size)
        if kind in {6, 7}:
            _delta(payload, limits)
        entry = _Entry(offset, kind, payload, base)
        entries.append(entry)
        by_offset[offset] = entry
    _fail(position != pack_end, "extra data after declared pack objects")

    objects: dict[str, GitObject] = {}
    by_oid: dict[str, _Entry] = {}
    waiting: dict[str | int, list[_Entry]] = collections.defaultdict(list)
    queue = collections.deque()
    for entry in entries:
        if entry.kind in _TYPES:
            queue.append(entry)
        else:
            waiting[entry.base].append(entry)
    while queue:
        entry = queue.popleft()
        if entry.oid is not None:
            continue
        if entry.kind in _TYPES:
            obj = GitObject(_TYPES[entry.kind], entry.data)
        else:
            source = by_offset.get(entry.base) if isinstance(entry.base, int) else by_oid.get(entry.base)
            if source is None or source.oid is None:
                continue
            entry.depth = source.depth + 1
            _fail(entry.depth > limits.delta_depth, "delta depth limit exceeded")
            base_obj = objects[source.oid]
            size, _ = _delta(entry.data, limits)
            decoded += size
            _fail(decoded > limits.decoded_bytes, "total decoded size limit exceeded")
            _, content = _delta(entry.data, limits, base_obj.data)
            obj = GitObject(base_obj.kind, content)
        entry.oid = _oid(obj.kind, obj.data, algorithm)
        _fail(entry.oid in objects and objects[entry.oid] != obj, "object ID collision")
        objects[entry.oid] = obj
        by_oid[entry.oid] = entry
        queue.extend(waiting.pop(entry.offset, []))
        queue.extend(waiting.pop(entry.oid, []))

    missing: set[str] = set()
    links = 0
    for obj in objects.values():
        for target, expected in _dependencies(obj, hash_bytes):
            links += 1
            _fail(links > limits.object_links, "object link count limit exceeded")
            if target not in objects:
                missing.add(target)
            elif expected and objects[target].kind != expected:
                raise BundleError("object dependency has wrong type")
    missing.update(ref["oid"] for ref in report["references"] if ref["oid"] not in objects)
    unresolved = [{"offset": e.offset, "base": e.base, "storage": "ref-delta" if e.kind == 7 else "ofs-delta"}
                  for e in entries if e.oid is None]
    partial = bool(report["prerequisites"] or missing or unresolved or "filter" in report["capabilities"])
    report.update({"bundle_sha256": hashlib.sha256(data).hexdigest(),
                   "input_bytes": len(data), "pack_version": version,
                   "pack_checksum": digest.hex(), "pack_checksum_valid": True,
                   "packed_objects": count, "resolved_entries": count - len(unresolved),
                   "unique_recovered_objects": len(objects), "decoded_bytes": decoded,
                   "object_links_checked": links,
                   "unresolved_deltas": unresolved, "missing_object_links": sorted(missing),
                   "recovery_status": "partial" if partial else "self_contained_objects",
                   "restore_verified": False,
                   "note": "Object recovery only; no Git fsck, bundle verify, fetch, or checkout was executed.",
                   "objects": [{"oid": oid, "type": obj.kind, "size": len(obj.data)}
                               for oid, obj in sorted(objects.items())]})
    return Inspection(report, objects)


def inspect_file(path: str | Path, limits: Limits | None = None) -> Inspection:
    limits = limits or Limits()
    # Read at most the limit plus one, including if the source grows during read.
    with Path(path).open("rb") as stream:
        data = stream.read(limits.input_bytes + 1)
    return inspect_bundle(data, limits)


def export_objects(inspection: Inspection, destination: str | Path) -> None:
    """Create a NEW directory containing raw, non-executable object payloads.

    Names derive only from validated content hashes/types, never bundle paths.
    Does not modify a Git repository; refuses an existing destination.
    """
    directory = Path(destination)
    directory.mkdir(mode=0o700, parents=False, exist_ok=False)
    for oid, obj in inspection.objects.items():
        _fail(not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", oid)
              or obj.kind not in _TYPES.values(), "invalid export object")
        with (directory / f"{oid}.{obj.kind}").open("xb") as stream:
            os.chmod(stream.fileno(), 0o600)
            stream.write(obj.data)
    with (directory / "manifest.json").open("x", encoding="utf-8") as stream:
        os.chmod(stream.fileno(), 0o600)
        json.dump(inspection.report, stream, indent=2, sort_keys=True)
        stream.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--extract", type=Path, help="new directory for raw objects and manifest")
    parser.add_argument("--max-input-bytes", type=int, default=Limits().input_bytes)
    args = parser.parse_args(argv)
    try:
        inspection = inspect_file(args.bundle, Limits(input_bytes=args.max_input_bytes))
        if args.extract is not None:
            export_objects(inspection, args.extract)
        print(json.dumps(inspection.report, indent=2, sort_keys=True))
    except (BundleError, OSError) as error:
        print(json.dumps({"error": str(error), "recovery_status": "failed", "restore_verified": False}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
