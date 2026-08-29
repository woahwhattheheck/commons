#!/usr/bin/env python3
"""WB-RANGE: White Box remote range unit.

Reads stored model weights by address over HTTP Range requests. The file
stays where it sits; the tool fetches only the byte ranges a question
needs, caches them content-addressed, and records every read in a local
manifest. Safetensors and GGUF indexes are built from header bytes only.

Subcommands: index, slice, verify, axis, score, archive, serve.
Stdlib only. No numpy. No executor.
"""

from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import math
import os
from pathlib import Path, PurePosixPath
import random
import re
import socketserver
import struct
import sys
import time
import urllib.error
import urllib.request


SCHEMA_VERSION = "commons-wb-range/v1"
DEFAULT_LIMIT_BYTES = 64 * 1024 * 1024
HF_API = "https://huggingface.co/api/models/{repo}?blobs=true"
HF_RESOLVE = "https://huggingface.co/{repo}/resolve/{rev}/{name}"
USER_AGENT = "wb-range/1.0 (commons; stdlib)"

SAFETENSORS_DTYPES = {
    "BOOL": ("<?", 1),
    "U8": ("<B", 1),
    "I8": ("<b", 1),
    "U16": ("<H", 2),
    "I16": ("<h", 2),
    "F16": ("<e", 2),
    "BF16": (None, 2),
    "U32": ("<I", 4),
    "I32": ("<i", 4),
    "F32": ("<f", 4),
    "U64": ("<Q", 8),
    "I64": ("<q", 8),
    "F64": ("<d", 8),
    "F8_E4M3": (None, 1),
    "F8_E5M2": (None, 1),
    "F8_E8M0": (None, 1),
    "F4": (None, 1),
}

# OCP MX E2M1 magnitudes indexed by (exp << 1 | mantissa).
E2M1_TABLE = (0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0)

GGUF_VALUE_TYPES = {
    0: ("<B", 1), 1: ("<b", 1), 2: ("<H", 2), 3: ("<h", 2),
    4: ("<I", 4), 5: ("<i", 4), 6: ("<f", 4), 7: ("<?", 1),
    10: ("<Q", 8), 11: ("<q", 8), 12: ("<d", 8),
}
GGML_TYPE_SIZES = {
    0: ("F32", 1, 4), 1: ("F16", 1, 2), 2: ("Q4_0", 32, 18),
    3: ("Q4_1", 32, 20), 6: ("Q5_0", 32, 22), 7: ("Q5_1", 32, 24),
    8: ("Q8_0", 32, 34), 9: ("Q8_1", 32, 40),
    10: ("Q2_K", 256, 84), 11: ("Q3_K", 256, 110), 12: ("Q4_K", 256, 144),
    13: ("Q5_K", 256, 176), 14: ("Q6_K", 256, 210), 15: ("Q8_K", 256, 292),
    16: ("IQ2_XXS", 256, 66), 17: ("IQ2_XS", 256, 74),
    18: ("IQ3_XXS", 256, 98), 19: ("IQ1_S", 256, 50),
    20: ("IQ4_NL", 32, 18), 21: ("IQ3_S", 256, 110),
    22: ("IQ2_S", 256, 82), 23: ("IQ4_XS", 256, 136),
    24: ("I8", 1, 1), 25: ("I16", 1, 2), 26: ("I32", 1, 4),
    27: ("I64", 1, 8), 28: ("F64", 1, 8), 29: ("IQ1_M", 256, 56),
    30: ("BF16", 1, 2),
}


class WbRangeError(AssertionError):
    """A range, index, decode, or archive contract was violated."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _safe_name(raw: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", raw).strip("._")
    if not name:
        raise WbRangeError("empty safe name")
    return name[:120]


class RangeReader:
    """HTTP Range reader with a content-addressed local chunk cache."""

    def __init__(self, url: str, cache_dir: Path, *, limit: int = DEFAULT_LIMIT_BYTES,
                 use_cache: bool = True):
        if not url.startswith("https://") and not url.startswith("http://127.0.0.1") \
                and not url.startswith("http://localhost"):
            raise WbRangeError("url must be https (or localhost for rehearsal)")
        self.url = url
        self.cache_dir = Path(cache_dir)
        self.limit = int(limit)
        self.use_cache = use_cache
        self.chunks_dir = self.cache_dir / "chunks"
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.cache_dir / "cache_manifest.json"
        self.manifest = self._load_manifest()

    def _load_manifest(self) -> dict:
        if self.manifest_path.is_file():
            with self.manifest_path.open(encoding="utf-8") as handle:
                value = json.load(handle)
            if isinstance(value, dict) and value.get("schema_version") == SCHEMA_VERSION:
                return value
        return {"schema_version": SCHEMA_VERSION, "entries": {}}

    def _save_manifest(self) -> None:
        encoded = json.dumps(self.manifest, ensure_ascii=False, indent=1,
                             sort_keys=True) + "\n"
        self.manifest_path.write_text(encoded, encoding="utf-8", newline="\n")

    def _cache_key(self, offset: int, length: int) -> str:
        return hashlib.sha1(
            ("%s|%d|%d" % (self.url, offset, length)).encode("utf-8")
        ).hexdigest()

    def read(self, offset: int, length: int) -> bytes:
        if offset < 0 or length <= 0:
            raise WbRangeError("range must be offset >= 0, length > 0")
        if length > self.limit:
            raise WbRangeError(
                "range length %d exceeds limit %d; raise the limit deliberately"
                % (length, self.limit)
            )
        key = self._cache_key(offset, length)
        entry = self.manifest["entries"].get(key)
        if self.use_cache and entry:
            chunk_path = self.chunks_dir / entry["file"]
            if chunk_path.is_file():
                data = chunk_path.read_bytes()
                if _sha256(data) == entry["sha256"] and len(data) == length:
                    return data
        data = self._fetch(offset, length)
        digest = _sha256(data)
        file_name = digest + ".bin"
        (self.chunks_dir / file_name).write_bytes(data)
        self.manifest["entries"][key] = {
            "url": self.url,
            "offset": offset,
            "length": length,
            "sha256": digest,
            "file": file_name,
            "fetched_utc": _utc_now(),
        }
        self._save_manifest()
        return data

    def _fetch(self, offset: int, length: int) -> bytes:
        request = urllib.request.Request(
            self.url,
            headers={
                "Range": "bytes=%d-%d" % (offset, offset + length - 1),
                "User-Agent": USER_AGENT,
                "Accept-Encoding": "identity",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                status = getattr(response, "status", 200)
                if status == 206:
                    data = response.read()
                elif status == 200:
                    data = response.read(length)
                    response.close()
                else:
                    raise WbRangeError("unexpected HTTP status %s" % status)
        except urllib.error.HTTPError as exc:
            raise WbRangeError(
                "HTTP %s on range %d+%d" % (exc.code, offset, length)
            ) from exc
        except urllib.error.URLError as exc:
            raise WbRangeError("fetch failed: %s" % exc.reason) from exc
        if len(data) < length:
            raise WbRangeError(
                "short read: wanted %d bytes, got %d" % (length, len(data))
            )
        if len(data) > length:
            data = data[:length]
        return data

    def remote_size(self) -> int:
        data = self._fetch_raw(0, 1)
        return data

    def _fetch_raw(self, offset: int, length: int) -> int:
        request = urllib.request.Request(
            self.url,
            headers={
                "Range": "bytes=%d-%d" % (offset, offset + length - 1),
                "User-Agent": USER_AGENT,
                "Accept-Encoding": "identity",
            },
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            content_range = response.headers.get("Content-Range", "")
            response.read(1)
        match = re.match(r"bytes \d+-\d+/(\d+|\*)", content_range)
        if not match or match.group(1) == "*":
            raise WbRangeError("server did not report total size")
        return int(match.group(1))


def hf_file_list(repo: str, revision: str = "main") -> list[dict]:
    if not re.fullmatch(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+", repo):
        raise WbRangeError("repo must look like owner/name")
    request = urllib.request.Request(
        HF_API.format(repo=repo), headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    siblings = payload.get("siblings")
    if not isinstance(siblings, list):
        raise WbRangeError("hub returned no file list")
    files = []
    for item in siblings:
        name = item.get("rfilename")
        if isinstance(name, str) and name:
            files.append({"name": name, "size": item.get("size")})
    files.sort(key=lambda entry: entry["name"])
    return files


def parse_safetensors_index(reader: RangeReader, file_name: str) -> dict:
    prefix = reader.read(0, 8)
    (header_len,) = struct.unpack("<Q", prefix)
    if header_len <= 0 or header_len > 512 * 1024 * 1024:
        raise WbRangeError("implausible safetensors header length %d" % header_len)
    header = json.loads(reader.read(8, header_len).decode("utf-8"))
    if not isinstance(header, dict) or not header:
        raise WbRangeError("safetensors header must be a nonempty object")
    data_base = 8 + header_len
    tensors = {}
    metadata = header.get("__metadata__", {})
    for name, info in sorted(header.items()):
        if name == "__metadata__":
            continue
        if set(info) < {"dtype", "shape", "data_offsets"}:
            raise WbRangeError("tensor %s missing required fields" % name)
        dtype = info["dtype"]
        if dtype not in SAFETENSORS_DTYPES:
            raise WbRangeError("tensor %s has unsupported dtype %s" % (name, dtype))
        begin, end = info["data_offsets"]
        if begin < 0 or end < begin:
            raise WbRangeError("tensor %s has bad data offsets" % name)
        tensors[name] = {
            "dtype": dtype,
            "shape": [int(dim) for dim in info["shape"]],
            "begin": data_base + begin,
            "end": data_base + end,
            "bytes": end - begin,
        }
    return {
        "format": "safetensors",
        "file": file_name,
        "data_base": data_base,
        "metadata": metadata if isinstance(metadata, dict) else {},
        "tensors": tensors,
    }


class _GgufCursor:
    def __init__(self, reader: RangeReader):
        self.reader = reader
        self.pos = 0

    def take(self, length: int) -> bytes:
        data = self.reader.read(self.pos, length)
        self.pos += length
        return data

    def unpack(self, fmt: str):
        size = struct.calcsize(fmt)
        return struct.unpack(fmt, self.take(size))

    def string(self) -> str:
        (length,) = self.unpack("<Q")
        if length > 16 * 1024 * 1024:
            raise WbRangeError("implausible gguf string length")
        return self.take(length).decode("utf-8")


def _gguf_metadata_value(cursor: _GgufCursor, value_type: int):
    if value_type in GGUF_VALUE_TYPES:
        fmt, _ = GGUF_VALUE_TYPES[value_type]
        return cursor.unpack(fmt)[0]
    if value_type == 8:
        return cursor.string()
    if value_type == 9:
        (element_type,) = cursor.unpack("<I")
        (count,) = cursor.unpack("<Q")
        if count > 1_000_000:
            raise WbRangeError("implausible gguf array length")
        if element_type == 8:
            return [cursor.string() for _ in range(count)]
        if element_type not in GGUF_VALUE_TYPES:
            raise WbRangeError("unsupported gguf array element type %d" % element_type)
        fmt, size = GGUF_VALUE_TYPES[element_type]
        raw = cursor.take(size * count)
        return list(struct.unpack("<%d%s" % (count, fmt[1:]), raw))
    raise WbRangeError("unsupported gguf metadata type %d" % value_type)


def parse_gguf_index(reader: RangeReader, file_name: str) -> dict:
    cursor = _GgufCursor(reader)
    magic = cursor.take(4)
    if magic != b"GGUF":
        raise WbRangeError("not a gguf file")
    (version,) = cursor.unpack("<I")
    if version not in (2, 3):
        raise WbRangeError("unsupported gguf version %d" % version)
    (tensor_count,) = cursor.unpack("<Q")
    (kv_count,) = cursor.unpack("<Q")
    if tensor_count > 10_000_000 or kv_count > 1_000_000:
        raise WbRangeError("implausible gguf counts")
    metadata = {}
    for _ in range(kv_count):
        key = cursor.string()
        (value_type,) = cursor.unpack("<I")
        metadata[key] = _gguf_metadata_value(cursor, value_type)
    alignment = metadata.get("general.alignment", 32)
    if not isinstance(alignment, int) or alignment <= 0 or alignment > 4096:
        alignment = 32
    tensors = {}
    for _ in range(tensor_count):
        name = cursor.string()
        (n_dims,) = cursor.unpack("<I")
        if n_dims > 8:
            raise WbRangeError("implausible gguf tensor rank")
        dims = list(cursor.unpack("<%dQ" % n_dims)) if n_dims else []
        (type_id,) = cursor.unpack("<I")
        (rel_offset,) = cursor.unpack("<Q")
        elements = 1
        for dim in dims:
            elements *= dim
        type_name, block, block_bytes = GGML_TYPE_SIZES.get(
            type_id, ("TYPE_%d" % type_id, 0, 0)
        )
        byte_size = None
        if block:
            if elements % block:
                raise WbRangeError("tensor %s not divisible by block" % name)
            byte_size = elements // block * block_bytes
        tensors[name] = {
            "dtype": type_name,
            "shape": dims,
            "rel_offset": rel_offset,
            "bytes": byte_size,
        }
    data_base = (cursor.pos + alignment - 1) // alignment * alignment
    for name, info in tensors.items():
        info["begin"] = data_base + info["rel_offset"]
        info["end"] = info["begin"] + info["bytes"] if info["bytes"] is not None else None
    return {
        "format": "gguf",
        "file": file_name,
        "version": version,
        "alignment": alignment,
        "data_base": data_base,
        "metadata": metadata,
        "tensors": tensors,
    }


def build_index(repo_or_url: str, cache_dir: Path, *, revision: str = "main",
                limit: int = DEFAULT_LIMIT_BYTES,
                name_filter: str | None = None) -> dict:
    started = _utc_now()
    sources = []
    if repo_or_url.startswith("https://") or repo_or_url.startswith("http://"):
        files = [{"name": PurePosixPath(repo_or_url.split("?")[0]).name,
                  "size": None, "url": repo_or_url}]
    else:
        files = []
        for entry in hf_file_list(repo_or_url, revision):
            name = entry["name"]
            if name.endswith((".safetensors", ".gguf")):
                files.append({
                    "name": name,
                    "size": entry.get("size"),
                    "url": HF_RESOLVE.format(repo=repo_or_url, rev=revision, name=name),
                })
        if not files:
            raise WbRangeError("no safetensors or gguf files in repo")
    pattern = re.compile(name_filter) if name_filter else None
    total_tensor_bytes = 0
    for file_entry in files:
        if pattern and not pattern.search(file_entry["name"]):
            continue
        reader = RangeReader(file_entry["url"], cache_dir, limit=limit)
        if file_entry["name"].endswith(".safetensors"):
            parsed = parse_safetensors_index(reader, file_entry["name"])
        else:
            parsed = parse_gguf_index(reader, file_entry["name"])
        parsed["url"] = file_entry["url"]
        parsed["declared_size"] = file_entry.get("size")
        total_tensor_bytes += sum(t["bytes"] or 0 for t in parsed["tensors"].values())
        sources.append(parsed)
    if not sources:
        raise WbRangeError("name filter excluded every weight file")
    tensor_count = sum(len(source["tensors"]) for source in sources)
    return {
        "schema_version": SCHEMA_VERSION,
        "target": repo_or_url,
        "revision": revision,
        "built_utc": started,
        "file_count": len(sources),
        "tensor_count": tensor_count,
        "tensor_bytes": total_tensor_bytes,
        "sources": sources,
    }


def find_tensor(index: dict, tensor_name: str) -> tuple[dict, dict]:
    matches = []
    for source in index["sources"]:
        tensors = source["tensors"]
        if tensor_name in tensors:
            return source, tensors[tensor_name]
        matches.extend(
            name for name in tensors if tensor_name.lower() in name.lower()
        )
    if len(matches) == 1:
        for source in index["sources"]:
            if matches[0] in source["tensors"]:
                return source, source["tensors"][matches[0]]
    sample = sorted(matches)[:12]
    raise WbRangeError(
        "tensor %r not found; %d partial matches: %s"
        % (tensor_name, len(matches), ", ".join(sample) or "none")
    )


def decode_values(dtype: str, data: bytes, count: int | None = None) -> list[float]:
    if dtype == "BF16":
        if len(data) % 2:
            raise WbRangeError("bf16 payload has odd length")
        words = struct.unpack("<%dH" % (len(data) // 2), data)
        raw = b"".join(struct.pack("<I", word << 16) for word in words)
        values = list(struct.unpack("<%df" % (len(data) // 2), raw))
    elif dtype == "F8_E4M3":
        values = [_f8_decode(byte, 4, 3) for byte in data]
    elif dtype == "F8_E5M2":
        values = [_f8_decode(byte, 5, 2) for byte in data]
    elif dtype == "F8_E8M0":
        values = [2.0 ** (byte - 127) for byte in data]
    elif dtype == "F4":
        values = []
        for index in range(len(data) * 2):
            byte = data[index // 2]
            nibble = byte & 0x0F if index % 2 == 0 else (byte >> 4) & 0x0F
            sign = -1.0 if nibble & 0x08 else 1.0
            values.append(sign * E2M1_TABLE[nibble & 0x07])
    else:
        entry = SAFETENSORS_DTYPES.get(dtype)
        if entry is None or entry[0] is None:
            raise WbRangeError("no decoder for dtype %s" % dtype)
        fmt, size = entry
        if len(data) % size:
            raise WbRangeError("payload length not divisible by element size")
        values = [float(v) for v in struct.unpack("<%d%s" % (len(data) // size, fmt[1:]), data)]
    if count is not None:
        values = values[:count]
    return values


def _f8_decode(byte: int, exp_bits: int, man_bits: int) -> float:
    sign = -1.0 if byte & 0x80 else 1.0
    exponent = (byte >> man_bits) & ((1 << exp_bits) - 1)
    mantissa = byte & ((1 << man_bits) - 1)
    bias = (1 << (exp_bits - 1)) - 1
    if exponent == 0:
        return sign * mantissa * (2.0 ** (1 - bias - man_bits))
    if exponent == (1 << exp_bits) - 1:
        return math.nan
    return sign * (1.0 + mantissa / (1 << man_bits)) * (2.0 ** (exponent - bias))


def decode_mxfp4(packed: bytes, scales: bytes, *, block: int = 32) -> list[float]:
    values = []
    elements_per_byte = 2
    total = len(packed) * elements_per_byte
    expected_scales = (total + block - 1) // block
    if len(scales) < expected_scales:
        raise WbRangeError(
            "mxfp4 scales short: need %d, have %d" % (expected_scales, len(scales))
        )
    for index in range(total):
        byte = packed[index // 2]
        nibble = byte & 0x0F if index % 2 == 0 else (byte >> 4) & 0x0F
        sign = -1.0 if nibble & 0x08 else 1.0
        magnitude = E2M1_TABLE[nibble & 0x07]
        scale = 2.0 ** (scales[index // block] - 127)
        values.append(sign * magnitude * scale)
    return values


class Archive:
    """The archive of answers: every slice, axis, and verdict, hashed."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "blobs").mkdir(exist_ok=True)
        self.manifest_path = self.root / "manifest.json"
        if self.manifest_path.is_file():
            with self.manifest_path.open(encoding="utf-8") as handle:
                self.manifest = json.load(handle)
            if self.manifest.get("schema_version") != SCHEMA_VERSION:
                raise WbRangeError("archive manifest schema drift")
        else:
            self.manifest = {"schema_version": SCHEMA_VERSION, "entries": []}
            self._save()

    def _save(self) -> None:
        encoded = json.dumps(self.manifest, ensure_ascii=False, indent=1,
                             sort_keys=True) + "\n"
        self.manifest_path.write_text(encoded, encoding="utf-8", newline="\n")

    def put(self, kind: str, payload: bytes, record: dict) -> dict:
        digest = _sha256(payload)
        blob_name = "%s.bin" % digest
        (self.root / "blobs" / blob_name).write_bytes(payload)
        entry = {
            "id": "%s-%s" % (kind, digest[:16]),
            "kind": kind,
            "sha256": digest,
            "bytes": len(payload),
            "blob": "blobs/%s" % blob_name,
            "recorded_utc": _utc_now(),
        }
        entry.update(record)
        self.manifest["entries"] = [
            item for item in self.manifest["entries"] if item["id"] != entry["id"]
        ]
        self.manifest["entries"].append(entry)
        self._save()
        return entry

    def get(self, entry_id: str) -> dict:
        for entry in self.manifest["entries"]:
            if entry["id"] == entry_id:
                return entry
        raise WbRangeError("no archive entry %r" % entry_id)

    def read_blob(self, entry_id: str) -> bytes:
        entry = self.get(entry_id)
        data = (self.root / entry["blob"]).read_bytes()
        if _sha256(data) != entry["sha256"]:
            raise WbRangeError("archive blob hash drift for %s" % entry_id)
        return data


def slice_tensor(index: dict, archive: Archive, cache_dir: Path, tensor_name: str,
                 *, begin: int | None = None, end: int | None = None,
                 decode: bool = False, limit: int = DEFAULT_LIMIT_BYTES,
                 note: str = "") -> dict:
    source, tensor = find_tensor(index, tensor_name)
    if tensor["end"] is None or tensor["bytes"] is None:
        raise WbRangeError("tensor %s has unknown extent" % tensor_name)
    start = tensor["begin"] if begin is None else tensor["begin"] + begin
    stop = tensor["end"] if end is None else tensor["begin"] + end
    if start < tensor["begin"] or stop > tensor["end"] or stop <= start:
        raise WbRangeError("slice range outside tensor extent")
    reader = RangeReader(source["url"], cache_dir, limit=limit)
    payload = reader.read(start, stop - start)
    record = {
        "source_url": source["url"],
        "file": source["file"],
        "tensor": tensor_name,
        "dtype": tensor["dtype"],
        "shape": tensor["shape"],
        "range": [start, stop],
        "note": note,
    }
    entry = archive.put("slice", payload, record)
    result = {"status": "ARCHIVED", "entry": entry}
    if decode:
        values = decode_values(tensor["dtype"], payload)
        result["decoded"] = {
            "count": len(values),
            "min": min(values) if values else None,
            "max": max(values) if values else None,
            "mean": (sum(values) / len(values)) if values else None,
            "head": values[:8],
        }
    return result


def verify_ranges(local_path: Path, remote_url: str, cache_dir: Path, *,
                  samples: int = 16, span: int = 4096, seed: int = 1337,
                  limit: int = DEFAULT_LIMIT_BYTES) -> dict:
    local_path = Path(local_path)
    if not local_path.is_file():
        raise WbRangeError("local file not found: %s" % local_path)
    local_size = local_path.stat().st_size
    reader = RangeReader(remote_url, cache_dir, limit=limit, use_cache=False)
    remote_size = reader.remote_size()
    if samples <= 0 or span <= 0:
        raise WbRangeError("samples and span must be positive")
    rng = random.Random(seed)
    results = []
    compared = 0
    with local_path.open("rb") as handle:
        for _ in range(samples):
            ceiling = min(local_size, remote_size) - span
            if ceiling < 0:
                raise WbRangeError("span larger than file")
            offset = rng.randint(0, ceiling)
            handle.seek(offset)
            local_bytes = handle.read(span)
            remote_bytes = reader.read(offset, span)
            match = local_bytes == remote_bytes
            compared += span
            results.append({
                "offset": offset,
                "span": span,
                "local_sha256": _sha256(local_bytes),
                "remote_sha256": _sha256(remote_bytes),
                "match": match,
            })
    matches = sum(1 for item in results if item["match"])
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "MATCH" if matches == samples else "DRIFT",
        "local": str(local_path),
        "remote": remote_url,
        "local_size": local_size,
        "remote_size": remote_size,
        "size_agree": local_size == remote_size,
        "samples": samples,
        "matched": matches,
        "bytes_compared": compared,
        "seed": seed,
        "results": results,
    }


def _embedding_row(source: dict, tensor: dict, row: int, cache_dir: Path,
                   limit: int) -> list[float]:
    dtype = tensor["dtype"]
    if dtype not in ("F32", "F16", "F64", "BF16", "F8_E4M3", "F8_E5M2"):
        raise WbRangeError("axis needs a float dtype, tensor is %s" % dtype)
    shape = tensor["shape"]
    if len(shape) != 2:
        raise WbRangeError("embedding tensor must be 2-D, got %s" % shape)
    rows, width = shape
    if row < 0 or row >= rows:
        raise WbRangeError("row %d outside [0, %d)" % (row, rows))
    elem = SAFETENSORS_DTYPES[dtype][1]
    offset = tensor["begin"] + row * width * elem
    reader = RangeReader(source["url"], cache_dir, limit=limit)
    data = reader.read(offset, width * elem)
    return decode_values(dtype, data)


def cut_axis(index: dict, archive: Archive, cache_dir: Path, tensor_name: str,
             pairs: list[tuple[int, int]], *, limit: int = DEFAULT_LIMIT_BYTES,
             note: str = "") -> dict:
    if not pairs:
        raise WbRangeError("axis needs at least one row pair")
    source, tensor = find_tensor(index, tensor_name)
    accum = None
    rows_used = []
    for positive, negative in pairs:
        pos = _embedding_row(source, tensor, positive, cache_dir, limit)
        neg = _embedding_row(source, tensor, negative, cache_dir, limit)
        diff = [p - n for p, n in zip(pos, neg)]
        accum = diff if accum is None else [a + d for a, d in zip(accum, diff)]
        rows_used.append([positive, negative])
    count = float(len(pairs))
    axis = [value / count for value in accum]
    norm = math.sqrt(sum(value * value for value in axis))
    if norm == 0.0:
        raise WbRangeError("axis vector is zero")
    axis = [value / norm for value in axis]
    payload = struct.pack("<%df" % len(axis), *axis)
    record = {
        "tensor": tensor_name,
        "dtype": tensor["dtype"],
        "pairs": rows_used,
        "dimensions": len(axis),
        "note": note,
    }
    entry = archive.put("axis", payload, record)
    return {"status": "ARCHIVED", "entry": entry, "dimensions": len(axis)}


def score_rows(index: dict, archive: Archive, cache_dir: Path, tensor_name: str,
               axis_id: str, rows: list[int], *,
               limit: int = DEFAULT_LIMIT_BYTES) -> dict:
    source, tensor = find_tensor(index, tensor_name)
    axis_data = archive.read_blob(axis_id)
    axis_entry = archive.get(axis_id)
    width = len(axis_data) // 4
    axis = struct.unpack("<%df" % width, axis_data)
    if tensor["shape"][1] != width:
        raise WbRangeError("axis width %d != tensor width %d"
                           % (width, tensor["shape"][1]))
    scores = []
    for row in rows:
        values = _embedding_row(source, tensor, row, cache_dir, limit)
        norm = math.sqrt(sum(v * v for v in values))
        dot = sum(a * v for a, v in zip(axis, values))
        scores.append({"row": row, "cosine": (dot / norm) if norm else 0.0})
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "SCORED",
        "tensor": tensor_name,
        "axis": axis_id,
        "axis_note": axis_entry.get("note", ""),
        "scores": scores,
    }


def load_index(path: Path) -> dict:
    with Path(path).open(encoding="utf-8") as handle:
        index = json.load(handle)
    if index.get("schema_version") != SCHEMA_VERSION:
        raise WbRangeError("index schema drift")
    return index


def write_json(path: Path, value: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(value, ensure_ascii=False, indent=1, sort_keys=False) + "\n"
    path.write_text(encoded, encoding="utf-8", newline="\n")


PANEL_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>WB-RANGE</title>
<style>
:root {
  --bg: #0d0f11; --panel: #15191d; --edge: #2c343c; --text: #b8c4ce;
  --dim: #6b7885; --amber: #e8a13a; --ok: #46c07a; --bad: #e05545;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--bg); color: var(--text);
  font: 13px/1.45 Consolas, "Cascadia Mono", "Courier New", monospace;
  padding: 10px;
}
header {
  display: flex; align-items: center; gap: 14px;
  border: 1px solid var(--edge); background: var(--panel);
  padding: 8px 12px; margin-bottom: 10px;
}
header .title { font-weight: bold; letter-spacing: 2px; color: var(--text); }
header .sub { color: var(--dim); letter-spacing: 1px; }
.lamp {
  display: inline-block; width: 10px; height: 10px; border-radius: 50%;
  border: 1px solid var(--dim); margin-right: 6px; vertical-align: middle;
}
.lamp.on { background: var(--ok); border-color: var(--ok);
  box-shadow: 0 0 6px var(--ok); }
.lamp.warn { background: var(--amber); border-color: var(--amber);
  box-shadow: 0 0 6px var(--amber); }
.lamp.err { background: var(--bad); border-color: var(--bad);
  box-shadow: 0 0 6px var(--bad); }
.stat { color: var(--dim); } .stat b { color: var(--text); font-weight: normal; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
fieldset {
  border: 1px solid var(--edge); background: var(--panel); padding: 10px 12px;
}
legend {
  color: var(--amber); letter-spacing: 2px; font-size: 11px; padding: 0 6px;
}
label { display: block; color: var(--dim); margin: 8px 0 2px; font-size: 11px;
  letter-spacing: 1px; }
input, select {
  width: 100%; background: #0b0d0f; color: var(--text);
  border: 1px solid var(--edge); padding: 5px 7px; font: inherit;
}
input:focus { outline: 1px solid var(--amber); }
button {
  background: #1d2329; color: var(--text); border: 1px solid var(--edge);
  padding: 6px 14px; font: inherit; letter-spacing: 1px; cursor: pointer;
  margin-top: 10px;
}
button:hover { border-color: var(--amber); color: var(--amber); }
button:disabled { opacity: 0.4; cursor: default; }
button.primary { border-color: var(--amber); color: var(--amber); }
.row { display: flex; gap: 10px; } .row > div { flex: 1; }
.list {
  margin-top: 8px; max-height: 180px; overflow-y: auto;
  border: 1px solid var(--edge); background: #0b0d0f; padding: 4px;
}
.list div { padding: 2px 6px; cursor: pointer; white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis; }
.list div:hover { background: #1d2329; color: var(--amber); }
.kv { color: var(--dim); font-size: 12px; margin-top: 6px; white-space: pre-wrap; }
.kv b { color: var(--text); font-weight: normal; }
#log {
  height: 160px; overflow-y: auto; background: #0b0d0f;
  border: 1px solid var(--edge); padding: 6px 8px; font-size: 12px;
}
#log .ok { color: var(--ok); } #log .err { color: var(--bad); }
#log .dim { color: var(--dim); }
.full { grid-column: 1 / -1; }
</style>
</head>
<body>
<header>
  <span class="title">WB-RANGE</span>
  <span class="sub">WHITE BOX REMOTE RANGE UNIT</span>
  <span class="stat"><span id="lamp-conn" class="lamp"></span>LINK</span>
  <span class="stat"><span id="lamp-index" class="lamp"></span>INDEX</span>
  <span class="stat">LIMIT <input id="limit" type="number" value="64" min="1"
    style="width:70px;display:inline-block"> MB</span>
  <span class="stat" id="clock"></span>
</header>
<div class="grid">

<fieldset>
  <legend>TARGET</legend>
  <label>REPO OR URL</label>
  <input id="repo" value="moonshotai/Kimi-K3">
  <label>REVISION</label>
  <input id="rev" value="main">
  <div class="row">
    <div><label>FILE FILTER (REGEX, OPTIONAL)</label>
    <input id="filter" placeholder="shard-0001|embed"></div>
    <div><label>&nbsp;</label>
    <button id="btn-index" class="primary">BUILD INDEX</button></div>
  </div>
  <div class="kv" id="index-kv">no index loaded</div>
</fieldset>

<fieldset>
  <legend>INDEX</legend>
  <label>FILTER TENSORS</label>
  <input id="tensor-filter" placeholder="embed / attn / expert">
  <div class="list" id="tensor-list"></div>
  <div class="kv" id="tensor-kv"></div>
</fieldset>

<fieldset>
  <legend>SLICE</legend>
  <label>TENSOR</label>
  <input id="slice-tensor">
  <div class="row">
    <div><label>BEGIN (REL BYTES, BLANK = 0)</label><input id="slice-begin"></div>
    <div><label>END (REL BYTES, BLANK = ALL)</label><input id="slice-end"></div>
  </div>
  <label>NOTE</label>
  <input id="slice-note" placeholder="question this slice answers">
  <button id="btn-slice" class="primary">FETCH + ARCHIVE</button>
  <button id="btn-decode">FETCH + DECODE</button>
  <div class="kv" id="slice-kv"></div>
</fieldset>

<fieldset>
  <legend>VERIFY</legend>
  <label>LOCAL FILE</label>
  <input id="verify-local" placeholder="C:\path\to\local.gguf">
  <label>REMOTE URL</label>
  <input id="verify-remote" placeholder="https://...resolve/main/file.gguf">
  <div class="row">
    <div><label>SAMPLES</label><input id="verify-samples" type="number" value="16"></div>
    <div><label>SPAN BYTES</label><input id="verify-span" type="number" value="4096"></div>
    <div><label>SEED</label><input id="verify-seed" type="number" value="1337"></div>
  </div>
  <button id="btn-verify" class="primary">VERIFY BYTE-EXACT</button>
  <div class="kv" id="verify-kv"></div>
</fieldset>

<fieldset>
  <legend>AXIS</legend>
  <label>EMBEDDING TENSOR</label>
  <input id="axis-tensor" placeholder="model.embed_tokens.weight">
  <label>ROW PAIRS POS:NEG (COMMA SEP)</label>
  <input id="axis-pairs" placeholder="12045:882, 9381:112">
  <label>NOTE</label>
  <input id="axis-note" placeholder="what this axis isolates">
  <button id="btn-axis" class="primary">CUT AXIS</button>
  <div class="kv" id="axis-kv"></div>
</fieldset>

<fieldset>
  <legend>SCORE</legend>
  <label>AXIS ID</label>
  <input id="score-axis" placeholder="axis-...">
  <label>ROWS (COMMA SEP)</label>
  <input id="score-rows" placeholder="12045, 882, 99120">
  <button id="btn-score" class="primary">SCORE ROWS</button>
  <div class="kv" id="score-kv"></div>
</fieldset>

<fieldset class="full">
  <legend>ARCHIVE</legend>
  <button id="btn-archive">REFRESH</button>
  <div class="list" id="archive-list" style="max-height:140px"></div>
</fieldset>

<fieldset class="full">
  <legend>LOG</legend>
  <div id="log"></div>
</fieldset>

</div>
<script>
const $ = (id) => document.getElementById(id);
let INDEX = null;

function log(msg, cls) {
  const line = document.createElement("div");
  line.className = cls || "dim";
  const ts = new Date().toISOString().slice(11, 19);
  line.textContent = ts + "Z  " + msg;
  $("log").appendChild(line);
  $("log").scrollTop = $("log").scrollHeight;
}

async function api(path, body) {
  const response = await fetch(path, {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body || {}),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || ("HTTP " + response.status));
  return data;
}

function limitBytes() {
  return Math.max(1, parseInt($("limit").value || "64", 10)) * 1024 * 1024;
}

$("btn-index").onclick = async () => {
  $("btn-index").disabled = true;
  log("index build: " + $("repo").value);
  try {
    const data = await api("/api/index", {
      target: $("repo").value, revision: $("rev").value,
      filter: $("filter").value || null, limit: limitBytes(),
    });
    INDEX = data.index;
    $("lamp-index").className = "lamp on";
    $("index-kv").innerHTML =
      "files <b>" + INDEX.file_count + "</b>  tensors <b>" + INDEX.tensor_count +
      "</b>  tensor bytes <b>" + INDEX.tensor_bytes.toLocaleString() + "</b>";
    log("index: " + INDEX.tensor_count + " tensors, " +
        INDEX.tensor_bytes + " bytes", "ok");
    renderTensorList();
  } catch (e) { log("index failed: " + e.message, "err"); }
  $("btn-index").disabled = false;
};

function renderTensorList() {
  const filter = ($("tensor-filter").value || "").toLowerCase();
  const list = $("tensor-list");
  list.innerHTML = "";
  if (!INDEX) return;
  let shown = 0;
  for (const source of INDEX.sources) {
    for (const [name, t] of Object.entries(source.tensors)) {
      if (filter && !name.toLowerCase().includes(filter)) continue;
      if (++shown > 400) return;
      const row = document.createElement("div");
      row.textContent = name + "  " + t.dtype + "  [" + t.shape.join("x") + "]";
      row.onclick = () => {
        $("slice-tensor").value = name;
        $("tensor-kv").innerHTML = "file <b>" + source.file + "</b>  begin <b>" +
          t.begin + "</b>  bytes <b>" + (t.bytes === null ? "?" : t.bytes) + "</b>";
      };
      list.appendChild(row);
    }
  }
}
$("tensor-filter").oninput = renderTensorList;

async function doSlice(decode) {
  const body = {
    tensor: $("slice-tensor").value, decode: decode,
    note: $("slice-note").value, limit: limitBytes(),
  };
  if ($("slice-begin").value) body.begin = parseInt($("slice-begin").value, 10);
  if ($("slice-end").value) body.end = parseInt($("slice-end").value, 10);
  log("slice: " + body.tensor);
  try {
    const data = await api("/api/slice", body);
    const e = data.entry;
    let text = "archived <b>" + e.id + "</b>  bytes <b>" + e.bytes +
      "</b>  sha256 <b>" + e.sha256.slice(0, 16) + "...</b>";
    if (data.decoded) {
      text += "\nmin " + data.decoded.min + "  max " + data.decoded.max +
        "  mean " + data.decoded.mean;
    }
    $("slice-kv").innerHTML = text;
    log("slice archived: " + e.id + " (" + e.bytes + " bytes)", "ok");
  } catch (e2) { log("slice failed: " + e2.message, "err"); }
}
$("btn-slice").onclick = () => doSlice(false);
$("btn-decode").onclick = () => doSlice(true);

$("btn-verify").onclick = async () => {
  log("verify: " + $("verify-local").value);
  try {
    const data = await api("/api/verify", {
      local: $("verify-local").value, remote: $("verify-remote").value,
      samples: parseInt($("verify-samples").value, 10),
      span: parseInt($("verify-span").value, 10),
      seed: parseInt($("verify-seed").value, 10),
      limit: limitBytes(),
    });
    const lamp = data.status === "MATCH" ? "ok" : "err";
    $("verify-kv").innerHTML =
      "status <b>" + data.status + "</b>  matched <b>" + data.matched + "/" +
      data.samples + "</b>  bytes <b>" + data.bytes_compared +
      "</b>  sizes agree <b>" + data.size_agree + "</b>";
    log("verify " + data.status + " " + data.matched + "/" + data.samples, lamp);
  } catch (e) { log("verify failed: " + e.message, "err"); }
};

$("btn-axis").onclick = async () => {
  const pairs = $("axis-pairs").value.split(",").map(s => s.trim())
    .filter(Boolean).map(s => s.split(":").map(x => parseInt(x, 10)));
  log("axis cut: " + JSON.stringify(pairs));
  try {
    const data = await api("/api/axis", {
      tensor: $("axis-tensor").value, pairs: pairs,
      note: $("axis-note").value, limit: limitBytes(),
    });
    $("axis-kv").innerHTML = "axis <b>" + data.entry.id + "</b>  dims <b>" +
      data.dimensions + "</b>";
    $("score-axis").value = data.entry.id;
    log("axis archived: " + data.entry.id, "ok");
  } catch (e) { log("axis failed: " + e.message, "err"); }
};

$("btn-score").onclick = async () => {
  const rows = $("score-rows").value.split(",").map(s => parseInt(s.trim(), 10))
    .filter(n => !isNaN(n));
  try {
    const data = await api("/api/score", {
      tensor: $("axis-tensor").value, axis: $("score-axis").value,
      rows: rows, limit: limitBytes(),
    });
    $("score-kv").innerHTML = data.scores.map(
      s => "row <b>" + s.row + "</b>  cos <b>" + s.cosine.toFixed(5) + "</b>"
    ).join("\n");
    log("scored " + data.scores.length + " rows", "ok");
  } catch (e) { log("score failed: " + e.message, "err"); }
};

$("btn-archive").onclick = async () => {
  try {
    const data = await api("/api/archive", {});
    const list = $("archive-list");
    list.innerHTML = "";
    for (const e of data.entries.slice().reverse()) {
      const row = document.createElement("div");
      row.textContent = e.recorded_utc + "  " + e.id + "  " + e.bytes + "B  " +
        (e.note || e.tensor || "");
      list.appendChild(row);
    }
    log("archive: " + data.entries.length + " entries", "ok");
  } catch (e) { log("archive failed: " + e.message, "err"); }
};

setInterval(() => {
  $("clock").textContent = new Date().toISOString().slice(0, 19) + "Z";
}, 1000);
fetch("/api/status", {method: "POST", body: "{}"})
  .then(r => r.json())
  .then(() => { $("lamp-conn").className = "lamp on"; log("panel online", "ok"); })
  .catch(() => { $("lamp-conn").className = "lamp err"; });
</script>
</body>
</html>
"""


class PanelHandler(http.server.BaseHTTPRequestHandler):
    server_version = "WBRangePanel/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("panel: " + fmt % args + "\n")

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            body = PANEL_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self._send_json({"error": "not found"}, 404)

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b"{}"
            request = json.loads(body.decode("utf-8") or "{}")
            if not isinstance(request, dict):
                raise WbRangeError("request body must be a JSON object")
            self._route(request)
        except WbRangeError as exc:
            self._send_json({"error": str(exc)}, 400)
        except Exception as exc:  # panel must report, not die
            self._send_json({"error": "%s: %s" % (type(exc).__name__, exc)}, 500)

    def _route(self, request: dict) -> None:
        state = self.server.state
        limit = int(request.get("limit") or DEFAULT_LIMIT_BYTES)
        if self.path == "/api/status":
            self._send_json({"status": "ONLINE", "schema_version": SCHEMA_VERSION})
        elif self.path == "/api/index":
            index = build_index(
                str(request["target"]), state["cache_dir"],
                revision=str(request.get("revision") or "main"),
                limit=limit,
                name_filter=request.get("filter") or None,
            )
            state["index"] = index
            write_json(state["index_path"], index)
            self._send_json({"status": "INDEXED", "index": index})
        elif self.path == "/api/slice":
            index = self._index(state)
            result = slice_tensor(
                index, state["archive"], state["cache_dir"],
                str(request["tensor"]),
                begin=request.get("begin"), end=request.get("end"),
                decode=bool(request.get("decode")), limit=limit,
                note=str(request.get("note") or ""),
            )
            self._send_json(result)
        elif self.path == "/api/verify":
            result = verify_ranges(
                Path(str(request["local"])), str(request["remote"]),
                state["cache_dir"],
                samples=int(request.get("samples") or 16),
                span=int(request.get("span") or 4096),
                seed=int(request.get("seed") or 1337),
                limit=limit,
            )
            state["archive"].put(
                "verify",
                json.dumps(result, sort_keys=True).encode("utf-8"),
                {"local": result["local"], "remote": result["remote"],
                 "verdict": result["status"], "note": "byte-exactness rehearsal"},
            )
            self._send_json(result)
        elif self.path == "/api/axis":
            index = self._index(state)
            pairs = request.get("pairs")
            if not isinstance(pairs, list) or not all(
                isinstance(p, list) and len(p) == 2 for p in pairs
            ):
                raise WbRangeError("pairs must be [[pos, neg], ...]")
            result = cut_axis(
                index, state["archive"], state["cache_dir"],
                str(request["tensor"]),
                [(int(p[0]), int(p[1])) for p in pairs],
                limit=limit, note=str(request.get("note") or ""),
            )
            self._send_json(result)
        elif self.path == "/api/score":
            index = self._index(state)
            result = score_rows(
                index, state["archive"], state["cache_dir"],
                str(request["tensor"]), str(request["axis"]),
                [int(r) for r in request.get("rows") or []],
                limit=limit,
            )
            self._send_json(result)
        elif self.path == "/api/archive":
            self._send_json({"entries": state["archive"].manifest["entries"]})
        else:
            self._send_json({"error": "unknown endpoint"}, 404)

    def _index(self, state: dict) -> dict:
        if state.get("index") is None:
            if state["index_path"].is_file():
                state["index"] = load_index(state["index_path"])
            else:
                raise WbRangeError("no index; build one first")
        return state["index"]


def serve(work_dir: Path, port: int) -> int:
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    state = {
        "cache_dir": work_dir / "cache",
        "archive": Archive(work_dir / "archive"),
        "index_path": work_dir / "wb_range_index.json",
        "index": None,
    }
    if state["index_path"].is_file():
        state["index"] = load_index(state["index_path"])

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    with Server(("127.0.0.1", port), PanelHandler) as httpd:
        httpd.state = state
        print(json.dumps({
            "status": "SERVING",
            "url": "http://127.0.0.1:%d/" % port,
            "work_dir": str(work_dir),
        }, sort_keys=True))
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    index_cmd = commands.add_parser("index", help="build a tensor index from headers")
    index_cmd.add_argument("target", help="owner/repo or a direct file URL")
    index_cmd.add_argument("--revision", default="main")
    index_cmd.add_argument("--filter", default=None, help="regex over file names")
    index_cmd.add_argument("--work-dir", type=Path, default=Path("wb-range-out"))
    index_cmd.add_argument("--limit", type=int, default=DEFAULT_LIMIT_BYTES)
    index_cmd.add_argument("--output", type=Path, default=None)

    slice_cmd = commands.add_parser("slice", help="fetch a tensor byte range")
    slice_cmd.add_argument("index", type=Path)
    slice_cmd.add_argument("tensor")
    slice_cmd.add_argument("--begin", type=int, default=None)
    slice_cmd.add_argument("--end", type=int, default=None)
    slice_cmd.add_argument("--decode", action="store_true")
    slice_cmd.add_argument("--note", default="")
    slice_cmd.add_argument("--work-dir", type=Path, default=Path("wb-range-out"))
    slice_cmd.add_argument("--limit", type=int, default=DEFAULT_LIMIT_BYTES)

    verify_cmd = commands.add_parser("verify", help="byte-exact local vs remote")
    verify_cmd.add_argument("local", type=Path)
    verify_cmd.add_argument("remote")
    verify_cmd.add_argument("--samples", type=int, default=16)
    verify_cmd.add_argument("--span", type=int, default=4096)
    verify_cmd.add_argument("--seed", type=int, default=1337)
    verify_cmd.add_argument("--work-dir", type=Path, default=Path("wb-range-out"))
    verify_cmd.add_argument("--limit", type=int, default=DEFAULT_LIMIT_BYTES)

    axis_cmd = commands.add_parser("axis", help="cut a semantic axis from row pairs")
    axis_cmd.add_argument("index", type=Path)
    axis_cmd.add_argument("tensor")
    axis_cmd.add_argument("pairs", help="pos:neg,pos:neg,...")
    axis_cmd.add_argument("--note", default="")
    axis_cmd.add_argument("--work-dir", type=Path, default=Path("wb-range-out"))
    axis_cmd.add_argument("--limit", type=int, default=DEFAULT_LIMIT_BYTES)

    score_cmd = commands.add_parser("score", help="score rows against an axis")
    score_cmd.add_argument("index", type=Path)
    score_cmd.add_argument("tensor")
    score_cmd.add_argument("axis")
    score_cmd.add_argument("rows", help="comma separated row ids")
    score_cmd.add_argument("--work-dir", type=Path, default=Path("wb-range-out"))
    score_cmd.add_argument("--limit", type=int, default=DEFAULT_LIMIT_BYTES)

    archive_cmd = commands.add_parser("archive", help="list the archive of answers")
    archive_cmd.add_argument("--work-dir", type=Path, default=Path("wb-range-out"))

    serve_cmd = commands.add_parser("serve", help="run the control panel")
    serve_cmd.add_argument("--port", type=int, default=7863)
    serve_cmd.add_argument("--work-dir", type=Path, default=Path("wb-range-out"))
    return parser


def _parse_pairs(raw: str) -> list[tuple[int, int]]:
    pairs = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        left, sep, right = item.partition(":")
        if not sep:
            raise WbRangeError("pair %r must be pos:neg" % item)
        pairs.append((int(left), int(right)))
    return pairs


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "serve":
        return serve(args.work_dir, args.port)

    work_dir = Path(getattr(args, "work_dir", Path("wb-range-out")))
    cache_dir = work_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    if args.command == "index":
        index = build_index(args.target, cache_dir, revision=args.revision,
                            limit=args.limit, name_filter=args.filter)
        output = args.output or (work_dir / "wb_range_index.json")
        write_json(output, index)
        print(json.dumps({
            "status": "INDEXED",
            "files": index["file_count"],
            "tensors": index["tensor_count"],
            "tensor_bytes": index["tensor_bytes"],
            "output": str(output),
        }, sort_keys=True))
        return 0

    if args.command == "verify":
        result = verify_ranges(args.local, args.remote, cache_dir,
                               samples=args.samples, span=args.span,
                               seed=args.seed, limit=args.limit)
        archive = Archive(work_dir / "archive")
        archive.put("verify",
                    json.dumps(result, sort_keys=True).encode("utf-8"),
                    {"local": result["local"], "remote": result["remote"],
                     "verdict": result["status"],
                     "note": "byte-exactness rehearsal"})
        summary = {key: result[key] for key in
                   ("status", "matched", "samples", "bytes_compared", "size_agree")}
        print(json.dumps(summary, sort_keys=True))
        return 0 if result["status"] == "MATCH" else 1

    index = load_index(args.index)
    archive = Archive(work_dir / "archive")

    if args.command == "slice":
        result = slice_tensor(index, archive, cache_dir, args.tensor,
                              begin=args.begin, end=args.end,
                              decode=args.decode, limit=args.limit,
                              note=args.note)
        print(json.dumps(result, sort_keys=True, default=str))
        return 0
    if args.command == "axis":
        result = cut_axis(index, archive, cache_dir, args.tensor,
                          _parse_pairs(args.pairs), limit=args.limit,
                          note=args.note)
        print(json.dumps(result, sort_keys=True))
        return 0
    if args.command == "score":
        rows = [int(item) for item in args.rows.split(",") if item.strip()]
        result = score_rows(index, archive, cache_dir, args.tensor,
                            args.axis, rows, limit=args.limit)
        print(json.dumps(result, sort_keys=True))
        return 0
    if args.command == "archive":
        print(json.dumps(archive.manifest, sort_keys=True))
        return 0
    raise WbRangeError("unhandled command")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except WbRangeError as exc:
        print("INVALID: %s" % exc, file=sys.stderr)
        raise SystemExit(2)
