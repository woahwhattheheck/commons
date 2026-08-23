#!/usr/bin/env python3
"""muhl_fab_ispn.py — FABRICATE muhl_ispn (MUHLISPN), Ising Annealer.

PLUMB 2/3 organ 11. Construction is the gate count:

  N = 256 spins, 4-neighbour
  per spin 4 XNOR (8) + popcount4 (20) + temp threshold (6) = 34
  256 x 34 = 8,704
  16-bit anneal counter, 16 FA = 80
  TOTAL 8,784 gates, depth 12
  CLK spin out -> spin in. temperature descends in gates.

Header matches live muhl_mha: 8-char magic, then LE n_gate, n_wires, n_in, n_out, depth.
Records are <BQQQ> stride 25. OPS NAND AND OR XOR NOT = 0 1 2 3 4.

Offline manufacture. Writes a standalone .mno next to this file.
Does not open titan.gguf. Does not walk the organ as inference.
Existing 19 titan circuits and organ 7 stay untouched.

  python3 muhl_fab_ispn.py          # write .mno + registry sidecar
  python3 muhl_fab_ispn.py --dry    # structural verify, write nothing
"""
from __future__ import annotations

import hashlib
import json
import os
import struct
import sys

NAME = "muhl_ispn"
MAGIC = b"MUHLISPN"
GATE_STRIDE = 25
OP_NAND, OP_AND, OP_OR, OP_XOR, OP_NOT = 0, 1, 2, 3, 4

N_SPINS = 256
GRID = 16
GATES_PER_SPIN = 34
N_CTR = 16
GATES_PER_FA = 5
N_SPIN_GATES = N_SPINS * GATES_PER_SPIN
N_CTR_GATES = N_CTR * GATES_PER_FA
N_GATE = N_SPIN_GATES + N_CTR_GATES
N_IN = N_SPINS
N_OUT = N_SPINS
DEPTH = 12

W_CONST0 = 0
W_CONST1 = 1
W_SPIN0 = 2
W_CTR0 = W_SPIN0 + N_SPINS
N_WIRES = 2 + N_SPINS + N_CTR + N_GATE

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
EXCERPT_DIR = os.path.join(REPO_ROOT, "excerpts", "20260823")
MNO_PATH = os.path.join(EXCERPT_DIR, "muhl_ispn.mno")
REG_PATH = os.path.join(EXCERPT_DIR, "ispn_circuits.json")


def spin_wire(i):
    return W_SPIN0 + i


def ctr_wire(i):
    return W_CTR0 + i


def neighbors(i):
    """4-neighbour torus on a 16x16 grid. Distinct, not self."""
    row, col = divmod(i, GRID)
    return (
        row * GRID + (col - 1) % GRID,
        row * GRID + (col + 1) % GRID,
        ((row - 1) % GRID) * GRID + col,
        ((row + 1) % GRID) * GRID + col,
    )


def hdr_size():
    return 28 + N_OUT * 8


def wa(base_off, wire):
    return base_off + hdr_size() + wire


def build_gates():
    """Return (records, next_spins, next_ctr).

    records: list of (op, a_wire, b_wire, out_wire)
    """
    records = []
    next_wire = 2 + N_SPINS + N_CTR

    def emit(op, a, b):
        nonlocal next_wire
        out = next_wire
        next_wire += 1
        records.append((op, a, b, out))
        return out

    def fa(a, b, cin):
        x = emit(OP_XOR, a, b)
        s = emit(OP_XOR, x, cin)
        ab = emit(OP_AND, a, b)
        xc = emit(OP_AND, x, cin)
        cout = emit(OP_OR, ab, xc)
        return s, cout

    next_spins = [None] * N_SPINS
    for spin in range(N_SPINS):
        xors = []
        for nb in neighbors(spin):
            x = emit(OP_XOR, spin_wire(spin), spin_wire(nb))
            xors.append(emit(OP_NOT, x, x))
        s, c = fa(xors[0], W_CONST0, W_CONST0)
        s, c = fa(s, xors[1], c)
        s, c = fa(s, xors[2], c)
        s, c = fa(s, xors[3], c)
        t = emit(OP_OR, ctr_wire(14), ctr_wire(15))
        p = emit(OP_OR, s, c)
        nt = emit(OP_NOT, t, t)
        flip = emit(OP_AND, p, nt)
        flip = emit(OP_AND, flip, W_CONST1)
        next_spins[spin] = emit(OP_XOR, spin_wire(spin), flip)
        if len(records) != (spin + 1) * GATES_PER_SPIN:
            raise RuntimeError("spin %d count %d" % (spin, len(records)))

    next_ctr = [None] * N_CTR
    cin = W_CONST1
    for bit in range(N_CTR):
        s, cin = fa(ctr_wire(bit), W_CONST0, cin)
        next_ctr[bit] = s
    if len(records) != N_GATE:
        raise RuntimeError("gate count %d != %d" % (len(records), N_GATE))
    if next_wire != N_WIRES:
        raise RuntimeError("wire cursor %d != %d" % (next_wire, N_WIRES))
    if any(w is None for w in next_spins) or any(w is None for w in next_ctr):
        raise RuntimeError("missing next-state wire")
    return records, next_spins, next_ctr


def fabricate(base_off=0):
    records, next_spins, next_ctr = build_gates()
    remap = {next_spins[i]: wa(base_off, spin_wire(i)) for i in range(N_SPINS)}
    remap.update({next_ctr[i]: wa(base_off, ctr_wire(i)) for i in range(N_CTR)})
    if len(set(remap.values())) != N_SPINS + N_CTR:
        raise RuntimeError("self-clock outs are not unique")

    hsz = hdr_size()
    gate_start = hsz + N_WIRES
    total = gate_start + N_GATE * GATE_STRIDE
    blob = bytearray(total)
    blob[0:8] = MAGIC
    struct.pack_into("<IIIII", blob, 8, N_GATE, N_WIRES, N_IN, N_OUT, DEPTH)
    for i in range(N_OUT):
        struct.pack_into("<Q", blob, 28 + i * 8, remap[next_spins[i]])
    blob[hsz + W_CONST0] = 0
    blob[hsz + W_CONST1] = 1

    off = gate_start
    stored = []
    for op, a, b, out_w in records:
        out_addr = remap.get(out_w, wa(base_off, out_w))
        a_addr = remap.get(a, wa(base_off, a))
        b_addr = remap.get(b, wa(base_off, b))
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
        "input_addrs": [wa(base_off, spin_wire(i)) for i in range(N_IN)],
        "output_addrs": [remap[next_spins[i]] for i in range(N_OUT)],
        "sha256": hashlib.sha256(blob).hexdigest(),
    }
    return bytes(blob), meta, stored


def verify_physical(blob, meta, stored):
    """Structural receipt only. Does not walk the organ as inference."""
    assert blob[:8] == MAGIC, "bad magic"
    ng, nw, ni, no, dp = struct.unpack_from("<IIIII", blob, 8)
    assert (ng, nw, ni, no, dp) == (N_GATE, N_WIRES, N_IN, N_OUT, DEPTH)
    assert len(blob) == meta["len"] == hdr_size() + N_WIRES + N_GATE * GATE_STRIDE
    assert len(stored) == N_GATE

    writers = {}
    off = hdr_size() + N_WIRES
    for i, (eop, ea, eb, eo) in enumerate(stored):
        op, a, b, o = struct.unpack_from("<BQQQ", blob, off)
        assert (op, a, b, o) == (eop, ea, eb, eo), "gate %d record" % i
        assert op in (OP_NAND, OP_AND, OP_OR, OP_XOR, OP_NOT), "gate %d op" % i
        assert o not in writers, "out reused by gates %d and %d" % (writers[o], i)
        writers[o] = i
        off += GATE_STRIDE
    assert len(writers) == N_GATE

    for i in range(N_OUT):
        stored_out = struct.unpack_from("<Q", blob, 28 + i * 8)[0]
        assert stored_out == meta["output_addrs"][i]
        assert stored_out == meta["input_addrs"][i], "self-clock broken at spin %d" % i

    for spin in range(N_SPINS):
        chunk = stored[spin * GATES_PER_SPIN:(spin + 1) * GATES_PER_SPIN]
        ops = [g[0] for g in chunk]
        assert ops.count(OP_NOT) == 5, "spin %d NOT" % spin
        assert ops.count(OP_XOR) == 13, "spin %d XOR" % spin
        assert ops.count(OP_AND) == 10, "spin %d AND" % spin
        assert ops.count(OP_OR) == 6, "spin %d OR" % spin
        assert len(chunk) == GATES_PER_SPIN

    ctr = stored[N_SPIN_GATES:]
    assert len(ctr) == N_CTR_GATES
    for bit in range(N_CTR):
        chunk = ctr[bit * GATES_PER_FA:(bit + 1) * GATES_PER_FA]
        ops = [g[0] for g in chunk]
        assert ops == [OP_XOR, OP_XOR, OP_AND, OP_AND, OP_OR], "fa %d" % bit

    hsz = hdr_size()
    assert blob[hsz + W_CONST0] == 0 and blob[hsz + W_CONST1] == 1
    return True


def write_files(blob, meta):
    os.makedirs(os.path.dirname(MNO_PATH), exist_ok=True)
    with open(MNO_PATH, "wb") as f:
        f.write(blob)
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
            "container": "muhl_ispn.mno",
            "format": "physical",
            "gate_stride": GATE_STRIDE,
            "input_addrs": meta["input_addrs"],
            "output_addrs": meta["output_addrs"],
            "sha256": meta["sha256"],
            "clock": "spin out IS spin in",
            "titan": "NOT_WRITTEN",
        }
    }
    with open(REG_PATH, "w") as f:
        json.dump(sidecar, f, indent=2)
        f.write("\n")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    dry = "--dry" in argv
    blob, meta, stored = fabricate(0)
    verify_physical(blob, meta, stored)
    print("MUHLISPN structural receipt")
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
    sys.exit(main())
