#!/usr/bin/env python3
"""muhl_fab_socr.py — FABRICATE muhl_socr (MUHLSOCR), sandpile / SOC.

PLUMB 2/3 organ 8. Construction is the gate count:

  16x16 = 256 cells, 3-bit height, topple at 4, NO TUNING PARAMETER
  per cell 4-neighbour 3-bit adds (4x15=60) + detect 1 + clear 1 = 62
  256 x 62                                                    15,872  depth 14
  CLK height out -> height in

Threshold 4 is bit 2. Detect is that bit. Clear subtracts 4 by XORing
it off. Four neighbour topple-bits (N,E,S,W, wrap-16) are added back
with four 15-gate 3-bit adders. Dest from this lattice, not invented.

Header matches live muhl_mha: 8-char magic, then LE n_gate, n_wires, n_in, n_out, depth.
Records are <BQQQ> stride 25. OPS NAND AND OR XOR NOT = 0 1 2 3 4.

Offline manufacture. Writes a standalone .mno next to this file.
Does not open titan.gguf. Does not evaluate the organ.
Existing titan circuits and landed excerpts stay untouched.

  python3 muhl_fab_socr.py          # write .mno + registry sidecar
  python3 muhl_fab_socr.py --dry    # structural verify, write nothing
"""
from __future__ import annotations

import hashlib
import json
import os
import struct
import sys

NAME = "muhl_socr"
MAGIC = b"MUHLSOCR"
GATE_STRIDE = 25
OP_NAND, OP_AND, OP_OR, OP_XOR, OP_NOT = 0, 1, 2, 3, 4

GRID = 16
N_CELLS = GRID * GRID
BITS = 3
GATES_PER_ADD = 15
N_NEIGH = 4
GATES_PER_CELL = N_NEIGH * GATES_PER_ADD + 2
N_GATE = N_CELLS * GATES_PER_CELL
N_IN = N_CELLS * BITS
N_OUT = N_IN
DEPTH = 14
GATES_PER_FA = 5

W_CONST0 = 0
W_CONST1 = 1
W_H0 = 2
N_WIRES = 2 + N_IN + N_GATE

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
EXCERPT_DIR = os.path.join(REPO_ROOT, "excerpts", "20260823")
MNO_PATH = os.path.join(EXCERPT_DIR, "muhl_socr.mno")
REG_PATH = os.path.join(EXCERPT_DIR, "socr_circuits.json")

# N, E, S, W. Wrap-16. Dest from the lattice.
NEIGH_DELTA = ((0, -1), (1, 0), (0, 1), (-1, 0))


def cell_xy(cell):
    return cell % GRID, cell // GRID


def cell_at(x, y):
    return (x % GRID) + (y % GRID) * GRID


def neighbors(cell):
    x, y = cell_xy(cell)
    return tuple(cell_at(x + dx, y + dy) for dx, dy in NEIGH_DELTA)


def height_wire(cell, bit):
    return W_H0 + cell * BITS + bit


def build_gates():
    """Return records and the 768 remapped next-height wires.

    records: list of (op, a_wire, b_wire, out_wire)
    next_height[i] remaps onto height bit i on store.
    """
    records = []
    next_height = [None] * N_IN
    next_wire = 2 + N_IN

    def emit(op, a, b):
        nonlocal next_wire
        out = next_wire
        next_wire += 1
        records.append((op, a, b, out))
        return out

    def fa(a, b, cin):
        start = len(records)
        x = emit(OP_XOR, a, b)
        s = emit(OP_XOR, x, cin)
        ab = emit(OP_AND, a, b)
        xc = emit(OP_AND, x, cin)
        cout = emit(OP_OR, ab, xc)
        if len(records) - start != GATES_PER_FA:
            raise RuntimeError("FA gate count")
        return s, cout

    def add3(a0, a1, a2, b0, b1, b2):
        """15-gate 3-bit ripple adder. Carry-out is unused (height stays 3-bit)."""
        start = len(records)
        s0, c0 = fa(a0, b0, W_CONST0)
        s1, c1 = fa(a1, b1, c0)
        s2, _c2 = fa(a2, b2, c1)
        if len(records) - start != GATES_PER_ADD:
            raise RuntimeError("add3 gate count %d" % (len(records) - start))
        return s0, s1, s2

    for cell in range(N_CELLS):
        start = len(records)
        h0 = height_wire(cell, 0)
        h1 = height_wire(cell, 1)
        h2 = height_wire(cell, 2)
        acc = (h0, h1, h2)
        for neigh in neighbors(cell):
            grain = height_wire(neigh, 2)
            acc = add3(acc[0], acc[1], acc[2], grain, W_CONST0, W_CONST0)
        # Topple-at-4 is bit 2. Add grains first, then subtract 4 by
        # XORing the original high bit back off. AND+XOR sit on the
        # last carry-sum so declared depth is 14.
        detect = emit(OP_AND, acc[2], W_CONST1)
        cleared = emit(OP_XOR, detect, h2)
        if len(records) - start != GATES_PER_CELL:
            raise RuntimeError("cell %d gate count %d" % (cell, len(records) - start))
        base = cell * BITS
        next_height[base] = acc[0]
        next_height[base + 1] = acc[1]
        next_height[base + 2] = cleared

    if len(records) != N_GATE:
        raise RuntimeError("gate count %d != %d" % (len(records), N_GATE))
    if next_wire != N_WIRES:
        raise RuntimeError("wire cursor %d != %d" % (next_wire, N_WIRES))
    if any(wire is None for wire in next_height):
        raise RuntimeError("missing next-height wire")
    return records, next_height


def hdr_size():
    return 28 + N_OUT * 8


def wa(base_off, wire):
    return base_off + hdr_size() + wire


def fabricate(base_off=0):
    records, next_height = build_gates()
    remap = {next_height[i]: wa(base_off, height_wire(i // BITS, i % BITS)) for i in range(N_IN)}
    if len(set(remap.values())) != N_IN:
        raise RuntimeError("self-clock outs are not unique")

    hsz = hdr_size()
    gate_start = hsz + N_WIRES
    total = gate_start + N_GATE * GATE_STRIDE
    blob = bytearray(total)
    blob[0:8] = MAGIC
    struct.pack_into("<IIIII", blob, 8, N_GATE, N_WIRES, N_IN, N_OUT, DEPTH)
    for i in range(N_OUT):
        struct.pack_into("<Q", blob, 28 + i * 8, remap[next_height[i]])
    blob[hsz + W_CONST0] = 0
    blob[hsz + W_CONST1] = 1

    off = gate_start
    stored = []
    for op, a, b, out_w in records:
        out_addr = remap.get(out_w, wa(base_off, out_w))
        a_addr = wa(base_off, a)
        b_addr = wa(base_off, b)
        struct.pack_into("<BQQQ", blob, off, op, a_addr, b_addr, out_addr)
        stored.append((op, a_addr, b_addr, out_addr))
        off += GATE_STRIDE

    meta = {
        "name": NAME,
        "magic": MAGIC.decode(),
        "n_gate": N_GATE,
        "n_wires": N_WIRES,
        "n_in": N_IN,
        "n_out": N_OUT,
        "depth": DEPTH,
        "len": total,
        "base_off": base_off,
        "input_addrs": [wa(base_off, height_wire(i // BITS, i % BITS)) for i in range(N_IN)],
        "output_addrs": [remap[next_height[i]] for i in range(N_OUT)],
        "neighbors": [list(neighbors(cell)) for cell in range(N_CELLS)],
        "sha256": hashlib.sha256(blob).hexdigest(),
    }
    return bytes(blob), meta, stored


def verify_physical(blob, meta, stored):
    """Structural receipt only. Does not walk the organ as inference."""
    assert blob[:8] == MAGIC, "bad magic"
    ng, nw, ni, no, dp = struct.unpack_from("<IIIII", blob, 8)
    assert ng == N_GATE and nw == N_WIRES and ni == N_IN and no == N_OUT and dp == DEPTH
    assert len(blob) == meta["len"]
    assert meta["n_gate"] == N_GATE
    assert len(stored) == N_GATE
    hsz = hdr_size()
    assert hsz + N_WIRES + N_GATE * GATE_STRIDE == len(blob)

    writers = {}
    off = hsz + N_WIRES
    for i, (eop, ea, eb, eo) in enumerate(stored):
        op, a, b, o = struct.unpack_from("<BQQQ", blob, off)
        assert op == eop and a == ea and b == eb and o == eo, "gate %d record" % i
        assert op in (OP_NAND, OP_AND, OP_OR, OP_XOR, OP_NOT), "gate %d op" % i
        assert o not in writers, "out reused by gates %d and %d" % (writers[o], i)
        writers[o] = i
        off += GATE_STRIDE
    assert len(writers) == N_GATE

    input_addresses = {wa(meta["base_off"], wire) for wire in range(W_H0 + N_IN)}
    valid_addresses = {wa(meta["base_off"], wire) for wire in range(N_WIRES)}
    wire_depth = {address: 0 for address in input_addresses}
    max_gate_depth = 0
    for _op, a, b, out in stored:
        assert a in wire_depth and b in wire_depth
        assert a in valid_addresses and b in valid_addresses and out in valid_addresses
        gate_depth = max(wire_depth[a], wire_depth[b]) + 1
        max_gate_depth = max(max_gate_depth, gate_depth)
        if out not in input_addresses:
            wire_depth[out] = gate_depth
    assert max_gate_depth == DEPTH, "depth %d != %d" % (max_gate_depth, DEPTH)

    for i in range(N_OUT):
        stored_out = struct.unpack_from("<Q", blob, 28 + i * 8)[0]
        assert stored_out == meta["output_addrs"][i]
        assert stored_out == meta["input_addrs"][i], "self-clock broken at bit %d" % i

    fa_ops = [OP_XOR, OP_XOR, OP_AND, OP_AND, OP_OR]
    for cell in range(N_CELLS):
        chunk = stored[cell * GATES_PER_CELL:(cell + 1) * GATES_PER_CELL]
        adds = chunk[:60]
        assert chunk[60][0] == OP_AND, "cell %d detect" % cell
        assert chunk[61][0] == OP_XOR, "cell %d clear" % cell
        assert len(adds) == 60
        for adder in range(N_NEIGH):
            block = adds[adder * GATES_PER_ADD:(adder + 1) * GATES_PER_ADD]
            for fa_i in range(3):
                ops = [g[0] for g in block[fa_i * GATES_PER_FA:(fa_i + 1) * GATES_PER_FA]]
                assert ops == fa_ops, "cell %d add %d fa %d" % (cell, adder, fa_i)
        owned = neighbors(cell)
        assert len(set(owned)) == N_NEIGH
        assert cell not in owned
        assert meta["neighbors"][cell] == list(owned)

    assert blob[hsz + W_CONST0] == 0 and blob[hsz + W_CONST1] == 1
    return True


def write_files(blob, meta):
    os.makedirs(os.path.dirname(MNO_PATH), exist_ok=True)
    with open(MNO_PATH, "wb") as handle:
        handle.write(blob)
    sidecar = {
        NAME: {
            "name": NAME,
            "magic": meta["magic"],
            "n_gate": meta["n_gate"],
            "n_wires": meta["n_wires"],
            "n_in": meta["n_in"],
            "n_out": meta["n_out"],
            "depth": meta["depth"],
            "len": meta["len"],
            "offset": 0,
            "container": "muhl_socr.mno",
            "format": "physical",
            "gate_stride": GATE_STRIDE,
            "grid": "16x16 wrap, 3-bit height, topple at 4",
            "adders": "4 neighbour 3-bit ripple adds, 15 g each",
            "input_addrs": meta["input_addrs"],
            "output_addrs": meta["output_addrs"],
            "sha256": meta["sha256"],
            "clock": "height out IS height in",
            "requested_offset_band": "OWNER_LOCAL_ALLOCATOR; not chosen in public tree",
            "titan": "NOT_WRITTEN",
        }
    }
    with open(REG_PATH, "w", encoding="utf-8") as handle:
        json.dump(sidecar, handle, indent=2)
        handle.write("\n")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    dry = "--dry" in argv
    blob, meta, stored = fabricate(0)
    verify_physical(blob, meta, stored)
    print("MUHLSOCR structural receipt")
    print("  n_gate=%d n_wires=%d n_in=%d n_out=%d depth=%d" % (
        meta["n_gate"], meta["n_wires"], meta["n_in"], meta["n_out"], meta["depth"]))
    print("  len=%d sha256=%s" % (meta["len"], meta["sha256"]))
    print("  self-clock: output_addrs == input_addrs (%d)" % N_OUT)
    print("  titan: NOT_WRITTEN")
    if dry:
        print("  --dry: no files written")
        return 0
    write_files(blob, meta)
    print("  wrote %s" % MNO_PATH)
    print("  wrote %s" % REG_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
