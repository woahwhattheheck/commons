#!/usr/bin/env python3
"""Emit glyphs.json from AUTOFAB0 via stackpack geometry.

Does not rewrite stackpack.py. Calls stackpack.raw_bits / stackpack.bitpack
and walks the same 200x1 column stack CAIRN measured.

  python glyph_sheet.py

Cite: cairn-folded-compression-and-the-breathing-budget-20260820-07
      glint-compress-ideas-20260820-01
      p1-request-48glyph-viewer-door-20260820-40
Leave unused 2^K address space alone. Do not field-narrow.
"""
from __future__ import annotations

import hashlib
import json
import os
import zlib
from collections import Counter

import stackpack

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "muhl", "containers", "MUHL_VISIBLE", "AUTOFAB0.mno")
OUT = os.path.join(ROOT, "glyphs.json")
WIDTH = 200
TILE_W = 200
TILE_H = 1


def stacked_columns(width, height, grid, tile_w, tile_h):
    # Same walk as stackpack.run — do not invent a second geometry.
    across, down = width // tile_w, height // tile_h
    depth = across * down
    cols = []
    for y in range(tile_h):
        for x in range(tile_w):
            value = 0
            for ty in range(down):
                base = grid[ty * tile_h + y]
                for tx in range(across):
                    value = (value << 1) | base[tx * tile_w + x]
            cols.append(value)
    return depth, cols


def bits_msb_first(value, depth):
    return [(value >> (depth - 1 - i)) & 1 for i in range(depth)]


def hex_bits(bits):
    packed = stackpack.bitpack(bits, 1)
    return packed.hex()


def main():
    if not os.path.isfile(SRC):
        raise SystemExit("missing %s" % SRC)
    raw = open(SRC, "rb").read()
    width, height, grid, nbytes = stackpack.raw_bits(SRC, WIDTH)
    depth, cols = stacked_columns(width, height, grid, TILE_W, TILE_H)
    table = {}
    order = []
    for value in cols:
        if value not in table:
            table[value] = len(order)
            order.append(value)
    distinct = len(order)
    if distinct != 48:
        raise SystemExit("expected 48 distinct columns, got %d" % distinct)
    counts = Counter(table[value] for value in cols)
    sym_bits = max(1, (distinct - 1).bit_length())
    stream = stackpack.bitpack([table[value] for value in cols], sym_bits)
    tbl = stackpack.bitpack(order, depth)
    z_stream = zlib.compress(stream, 9)
    z_tbl = zlib.compress(tbl, 9)
    glyphs = []
    for i, value in enumerate(order):
        bits = bits_msb_first(value, depth)
        glyphs.append({
            "i": i,
            "count": counts[i],
            "ones": sum(bits),
            "hex": hex_bits(bits),
        })
    payload = {
        "source": "muhl/containers/MUHL_VISIBLE/AUTOFAB0.mno",
        "source_bytes": nbytes,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "width": width,
        "height": height,
        "tile": [TILE_W, TILE_H],
        "K": depth,
        "cells": len(cols),
        "distinct": distinct,
        "sym_bits": sym_bits,
        "address_space": "2^%d unused combinations left alone" % depth,
        "table_zlib_bytes": len(z_tbl),
        "string_zlib_bytes": len(z_stream),
        "total_zlib_bytes": len(z_tbl) + len(z_stream),
        "string_zlib_hex": z_stream.hex(),
        "sentence": [table[value] for value in cols],
        "glyphs": glyphs,
        "cite": [
            "p/cairn-folded-compression-and-the-breathing-budget-20260820-07.md",
            "p/glint-compress-ideas-20260820-01.md",
            "p/p1-request-48glyph-viewer-door-20260820-40.md",
            "p/pocket-table-breathing-budget-and-doors-20260820-02.md",
        ],
        "law": "Draw the 48. Do not narrow them. The 65-byte string is the sentence. The table stays on HEAD.",
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    print("glyphs.json  distinct=%d  K=%d  cells=%d  string=%d B  table=%d B  total=%d B"
          % (distinct, depth, len(cols), len(z_stream), len(z_tbl),
             len(z_tbl) + len(z_stream)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
