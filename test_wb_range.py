#!/usr/bin/env python3
"""Contract tests for WB-RANGE: remote range reads, indexes, decode, archive.

All network traffic is a localhost Range-capable test server. Nothing leaves
the loopback interface.
"""

from __future__ import annotations

import http.server
import importlib.util
import json
import math
from pathlib import Path
import socketserver
import struct
import tempfile
import threading
import unittest


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "wb_range", ROOT / "host/wb_range.py"
)
wb_range = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(wb_range)


class RangeHandler(http.server.BaseHTTPRequestHandler):
    """Minimal Range-capable file server for rehearsal traffic."""

    payload = b""

    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        header = self.headers.get("Range", "")
        if not header.startswith("bytes="):
            self.send_response(200)
            self.send_header("Content-Length", str(len(self.payload)))
            self.end_headers()
            self.wfile.write(self.payload)
            return
        spec = header[len("bytes="):].split(",")[0]
        start_s, _, end_s = spec.partition("-")
        start = int(start_s)
        end = int(end_s) if end_s else len(self.payload) - 1
        end = min(end, len(self.payload) - 1)
        chunk = self.payload[start:end + 1]
        self.send_response(206)
        self.send_header("Content-Range",
                         "bytes %d-%d/%d" % (start, end, len(self.payload)))
        self.send_header("Content-Length", str(len(chunk)))
        self.end_headers()
        self.wfile.write(chunk)


class RangeServer:
    def __enter__(self):
        handler = type("BoundRangeHandler", (RangeHandler,), {})
        self.server = socketserver.TCPServer(("127.0.0.1", 0), handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       kwargs={"poll_interval": 0.05})
        self.thread.daemon = True
        self.thread.start()
        return self

    @property
    def url(self):
        return "http://127.0.0.1:%d/model.bin" % self.port

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        return False


def build_safetensors(tensors: dict) -> bytes:
    """tensors: name -> (dtype, shape, payload bytes)."""
    header = {}
    cursor = 0
    body = b""
    for name, (dtype, shape, payload) in sorted(tensors.items()):
        header[name] = {
            "dtype": dtype,
            "shape": list(shape),
            "data_offsets": [cursor, cursor + len(payload)],
        }
        cursor += len(payload)
        body += payload
    encoded = json.dumps(header).encode("utf-8")
    return struct.pack("<Q", len(encoded)) + encoded + body


def build_gguf(tensors: dict, alignment: int = 32) -> bytes:
    """tensors: name -> (dims, type_id, payload bytes)."""
    out = bytearray()
    out += b"GGUF"
    out += struct.pack("<I", 3)
    out += struct.pack("<Q", len(tensors))
    out += struct.pack("<Q", 1)
    key = b"general.alignment"
    out += struct.pack("<Q", len(key)) + key
    out += struct.pack("<I", 4)
    out += struct.pack("<I", alignment)
    offset = 0
    for name, (dims, type_id, payload) in sorted(tensors.items()):
        encoded = name.encode("utf-8")
        out += struct.pack("<Q", len(encoded)) + encoded
        out += struct.pack("<I", len(dims))
        for dim in dims:
            out += struct.pack("<Q", dim)
        out += struct.pack("<I", type_id)
        out += struct.pack("<Q", offset)
        offset += len(payload)
        offset = (offset + alignment - 1) // alignment * alignment
    pad = (-len(out)) % alignment
    out += b"\x00" * pad
    cursor = 0
    for name, (dims, type_id, payload) in sorted(tensors.items()):
        out += payload
        cursor += len(payload)
        pad = (-cursor) % alignment
        out += b"\x00" * pad
        cursor += pad
    return bytes(out)


class WbRangeTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.cache = self.work / "cache"
        self.cache.mkdir(parents=True)


class SafetensorsIndexTests(WbRangeTestBase):
    def test_index_and_slice_roundtrip(self):
        weights = [float(i) for i in range(8)]
        payload = struct.pack("<8f", *weights)
        blob = build_safetensors({
            "model.embed_tokens.weight": ("F32", [4, 2], payload),
        })
        RangeHandler.payload = blob
        with RangeServer() as server:
            reader = wb_range.RangeReader(server.url, self.cache)
            index = wb_range.parse_safetensors_index(reader, "model.safetensors")
            index["url"] = server.url
            tensor = index["tensors"]["model.embed_tokens.weight"]
            self.assertEqual(tensor["dtype"], "F32")
            self.assertEqual(tensor["shape"], [4, 2])
            self.assertEqual(tensor["bytes"], 32)
            archive = wb_range.Archive(self.work / "archive")
            full_index = {"schema_version": wb_range.SCHEMA_VERSION,
                          "sources": [index]}
            result = wb_range.slice_tensor(
                full_index, archive, self.cache,
                "model.embed_tokens.weight", decode=True,
                note="roundtrip",
            )
            self.assertEqual(result["status"], "ARCHIVED")
            self.assertEqual(result["decoded"]["count"], 8)
            self.assertEqual(result["decoded"]["head"][:4], [0.0, 1.0, 2.0, 3.0])
            blob_back = archive.read_blob(result["entry"]["id"])
            self.assertEqual(blob_back, payload)

    def test_partial_slice_bounds(self):
        payload = struct.pack("<8f", *[float(i) for i in range(8)])
        blob = build_safetensors({"w": ("F32", [2, 4], payload)})
        RangeHandler.payload = blob
        with RangeServer() as server:
            reader = wb_range.RangeReader(server.url, self.cache)
            index = wb_range.parse_safetensors_index(reader, "m.safetensors")
            index["url"] = server.url
            archive = wb_range.Archive(self.work / "archive")
            full_index = {"schema_version": wb_range.SCHEMA_VERSION,
                          "sources": [index]}
            result = wb_range.slice_tensor(
                full_index, archive, self.cache, "w",
                begin=4, end=8, decode=True,
            )
            self.assertEqual(result["decoded"]["count"], 1)
            self.assertEqual(result["decoded"]["head"], [1.0])
            with self.assertRaises(wb_range.WbRangeError):
                wb_range.slice_tensor(full_index, archive, self.cache, "w",
                                      begin=0, end=64)

    def test_limit_enforced(self):
        blob = build_safetensors({"w": ("F32", [1, 1], struct.pack("<f", 1.0))})
        RangeHandler.payload = blob
        with RangeServer() as server:
            reader = wb_range.RangeReader(server.url, self.cache, limit=8)
            with self.assertRaises(wb_range.WbRangeError):
                reader.read(0, 64)

    def test_cache_serves_offline(self):
        blob = build_safetensors({"w": ("F32", [1, 1], struct.pack("<f", 7.0))})
        RangeHandler.payload = blob
        with RangeServer() as server:
            reader = wb_range.RangeReader(server.url, self.cache)
            first = reader.read(0, 8)
            url = server.url
        reader_offline = wb_range.RangeReader(url, self.cache)
        second = reader_offline.read(0, 8)
        self.assertEqual(first, second)


class GgufIndexTests(WbRangeTestBase):
    def test_gguf_index_offsets(self):
        payload = struct.pack("<4f", 1.0, 2.0, 3.0, 4.0)
        blob = build_gguf({"test.weight": ([4], 0, payload)})
        RangeHandler.payload = blob
        with RangeServer() as server:
            reader = wb_range.RangeReader(server.url, self.cache)
            index = wb_range.parse_gguf_index(reader, "m.gguf")
            self.assertEqual(index["format"], "gguf")
            self.assertEqual(index["alignment"], 32)
            tensor = index["tensors"]["test.weight"]
            self.assertEqual(tensor["dtype"], "F32")
            self.assertEqual(tensor["bytes"], 16)
            begin = tensor["begin"]
            self.assertEqual(begin % 32, 0)
            self.assertEqual(blob[begin:begin + 16], payload)


class DecodeTests(WbRangeTestBase):
    def test_mxfp4_decode_hand_vector(self):
        # nibbles: 0x2 -> +1.0, 0xA -> -1.0 ; scale 127 -> 2^0
        packed = bytes([0xA2])
        scales = bytes([127])
        values = wb_range.decode_mxfp4(packed, scales)
        self.assertEqual(values, [1.0, -1.0])
        # scale 128 doubles
        values = wb_range.decode_mxfp4(packed, bytes([128]))
        self.assertEqual(values, [2.0, -2.0])
        # nibble 0x7 -> +6.0
        values = wb_range.decode_mxfp4(bytes([0x07]), bytes([127]))
        self.assertEqual(values, [6.0, 0.0])

    def test_bf16_decode(self):
        # 1.0 in bf16 is 0x3F80
        values = wb_range.decode_values("BF16", struct.pack("<H", 0x3F80))
        self.assertEqual(values, [1.0])

    def test_f8_e4m3_decode(self):
        # 0x38 = exp 0111 man 000 -> 1.0
        values = wb_range.decode_values("F8_E4M3", bytes([0x38]))
        self.assertEqual(values, [1.0])

    def test_f4_and_e8m0_decode(self):
        # 0xA2: low nibble 0x2 -> +1.0, high nibble 0xA -> -1.0
        values = wb_range.decode_values("F4", bytes([0xA2]))
        self.assertEqual(values, [1.0, -1.0])
        # E8M0: 127 -> 2^0, 129 -> 2^2
        values = wb_range.decode_values("F8_E8M0", bytes([127, 129]))
        self.assertEqual(values, [1.0, 4.0])


class VerifyTests(WbRangeTestBase):
    def test_match_and_drift(self):
        payload = bytes(range(256)) * 64
        RangeHandler.payload = payload
        local = self.work / "local.bin"
        local.write_bytes(payload)
        with RangeServer() as server:
            result = wb_range.verify_ranges(local, server.url, self.cache,
                                            samples=8, span=512, seed=7)
            self.assertEqual(result["status"], "MATCH")
            self.assertEqual(result["matched"], 8)
            drifted = bytearray(payload)
            drifted[1000] ^= 0xFF
            RangeHandler.payload = bytes(drifted)
            cache2 = self.work / "cache2"
            cache2.mkdir()
            # one full-file span: the single sample must cover the flipped byte
            result = wb_range.verify_ranges(local, server.url, cache2,
                                            samples=1, span=len(payload),
                                            seed=1000)
            self.assertEqual(result["status"], "DRIFT")


class AxisTests(WbRangeTestBase):
    def test_axis_and_score(self):
        # vocab 4, width 2; row0=(1,0) row1=(0,1) row2=(1,1) row3=(-1,0)
        rows = [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0], [-1.0, 0.0]]
        payload = b"".join(struct.pack("<2f", *row) for row in rows)
        blob = build_safetensors({"embed": ("F32", [4, 2], payload)})
        RangeHandler.payload = blob
        with RangeServer() as server:
            reader = wb_range.RangeReader(server.url, self.cache)
            index = wb_range.parse_safetensors_index(reader, "m.safetensors")
            index["url"] = server.url
            full_index = {"schema_version": wb_range.SCHEMA_VERSION,
                          "sources": [index]}
            archive = wb_range.Archive(self.work / "archive")
            cut = wb_range.cut_axis(full_index, archive, self.cache, "embed",
                                    [(0, 1)], note="x-over-y")
            self.assertEqual(cut["dimensions"], 2)
            axis_id = cut["entry"]["id"]
            scored = wb_range.score_rows(full_index, archive, self.cache,
                                         "embed", axis_id, [0, 1, 2, 3])
            cosines = {item["row"]: item["cosine"] for item in scored["scores"]}
            # axis = normalize(row0 - row1) = (0.7071, -0.7071)
            self.assertAlmostEqual(cosines[0], math.sqrt(0.5), places=5)
            self.assertAlmostEqual(cosines[1], -math.sqrt(0.5), places=5)
            self.assertAlmostEqual(cosines[2], 0.0, places=5)
            self.assertAlmostEqual(cosines[3], -math.sqrt(0.5), places=5)

    def test_axis_rejects_non_float(self):
        blob = build_safetensors({"q": ("U8", [2, 2], bytes([1, 2, 3, 4]))})
        RangeHandler.payload = blob
        with RangeServer() as server:
            reader = wb_range.RangeReader(server.url, self.cache)
            index = wb_range.parse_safetensors_index(reader, "m.safetensors")
            index["url"] = server.url
            full_index = {"schema_version": wb_range.SCHEMA_VERSION,
                          "sources": [index]}
            archive = wb_range.Archive(self.work / "archive")
            with self.assertRaises(wb_range.WbRangeError):
                wb_range.cut_axis(full_index, archive, self.cache, "q",
                                  [(0, 1)])


class ArchiveTests(WbRangeTestBase):
    def test_manifest_records_and_dedupes(self):
        archive = wb_range.Archive(self.work / "archive")
        first = archive.put("slice", b"payload", {"tensor": "w"})
        second = archive.put("slice", b"payload", {"tensor": "w"})
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(len(archive.manifest["entries"]), 1)
        reloaded = wb_range.Archive(self.work / "archive")
        self.assertEqual(reloaded.read_blob(first["id"]), b"payload")


if __name__ == "__main__":
    unittest.main()
