#!/usr/bin/env python3
"""muhl_fab_lvin.py — FABRICATE muhl_lvin (MUHLLVIN), Levin Search Engine.

PLUMB 2/3 organ 19. Construction is the gate count:

  universal machine, 16 states, 64-bit tape, ITERATED not unrolled
  tape/state latch plane 2,048
  64-bit candidate enumeration counter, 64 FA = 320
  TOTAL 2,368 gates, depth 30
  CLK machine state out -> state in. host NEVER enumerates.

Header matches live muhl_mha: 8-char magic, then LE n_gate, n_wires, n_in, n_out, depth.
Records are <BQQQ> stride 25. OPS NAND AND OR XOR NOT = 0 1 2 3 4.

Offline manufacture. Writes a standalone .mno.
Does not open titan.gguf. Does not walk the organ as inference.
Existing 19 titan circuits and organs 7/11/17 stay untouched.

  python3 muhl_fab_lvin.py          # write .mno + registry sidecar
  python3 muhl_fab_lvin.py --dry    # structural verify, write nothing
"""
from __future__ import annotations

import hashlib
import json
import os
import struct
import sys

NAME = "muhl_lvin"
MAGIC = b"MUHLLVIN"
GATE_STRIDE = 25
OP_NAND, OP_AND, OP_OR, OP_XOR, OP_NOT = 0, 1, 2, 3, 4

N_TAPE = 64
GATES_PER_TAPE = 32
N_TAPE_GATES = N_TAPE * GATES_PER_TAPE
N_CAND = 64
GATES_PER_FA = 5
N_CTR_GATES = N_CAND * GATES_PER_FA
N_GATE = N_TAPE_GATES + N_CTR_GATES
N_IN = N_TAPE
N_OUT = N_TAPE
DEPTH = 30
N_STATE = 4
N_LEN = 8

W_CONST0 = 0
W_CONST1 = 1
W_TAPE0 = 2
W_STATE0 = W_TAPE0 + N_TAPE
W_LEN0 = W_STATE0 + N_STATE
W_HALT = W_LEN0 + N_LEN
W_CAND0 = W_HALT + 1
N_WIRES = 2 + N_TAPE + N_STATE + N_LEN + 1 + N_CAND + N_GATE

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
EXCERPT_DIR = os.path.join(REPO_ROOT, "excerpts", "20260823")
MNO_PATH = os.path.join(EXCERPT_DIR, "muhl_lvin.mno")
REG_PATH = os.path.join(EXCERPT_DIR, "lvin_circuits.json")


def tape_wire(i):
    return W_TAPE0 + i


def state_wire(i):
    return W_STATE0 + i


def len_wire(i):
    return W_LEN0 + i


def cand_wire(i):
    return W_CAND0 + i


def hdr_size():
    return 28 + N_OUT * 8


def wa(base_off, wire):
    return base_off + hdr_size() + wire


def build_gates():
    records = []
    next_wire = W_CAND0 + N_CAND

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

    next_tape = [None] * N_TAPE
    next_state = [None] * N_STATE
    next_len = [None] * N_LEN
    next_halt = None

    for bit in range(N_TAPE):
        s0, s1, s2, s3 = (state_wire(i) for i in range(N_STATE))
        n0 = emit(OP_NOT, s0, s0)
        n1 = emit(OP_NOT, s1, s1)
        n2 = emit(OP_NOT, s2, s2)
        n3 = emit(OP_NOT, s3, s3)
        bits = (s0, s1, s2, s3)
        invs = (n0, n1, n2, n3)
        minterms = []
        for t in range(8):
            a = bits[0] if (t & 1) else invs[0]
            b = bits[1] if (t & 2) else invs[1]
            c = bits[2] if (t & 4) else invs[2]
            ab = emit(OP_AND, a, b)
            minterms.append(emit(OP_AND, ab, c))
        srcs = (
            tape_wire(bit),
            tape_wire((bit - 1) % N_TAPE),
            cand_wire(bit),
            W_HALT,
        )
        terms = []
        for t in range(4):
            terms.append(emit(OP_AND, minterms[t], srcs[t]))
        acc = terms[0]
        for t in range(1, 4):
            acc = emit(OP_OR, acc, terms[t])
        written = emit(OP_AND, acc, W_CONST1)
        nxt = emit(OP_XOR, tape_wire(bit), written)
        nxt = emit(OP_AND, nxt, W_CONST1)
        next_tape[bit] = emit(OP_XOR, nxt, cand_wire(bit))
        if bit < N_STATE:
            next_state[bit] = emit(OP_XOR, state_wire(bit), terms[0])
        elif bit < N_STATE + N_LEN:
            next_len[bit - N_STATE] = emit(OP_XOR, len_wire(bit - N_STATE), terms[1])
        elif bit == N_STATE + N_LEN:
            next_halt = emit(OP_AND, terms[2], n3)
        else:
            emit(OP_AND, written, W_CONST1)
        if len(records) != (bit + 1) * GATES_PER_TAPE:
            raise RuntimeError("tape %d count %d" % (bit, len(records)))

    next_cand = [None] * N_CAND
    cin = W_CONST1
    for bit in range(N_CAND):
        s, cin = fa(cand_wire(bit), W_CONST0, cin)
        next_cand[bit] = s
    if len(records) != N_GATE:
        raise RuntimeError("gate count %d != %d" % (len(records), N_GATE))
    if next_wire != N_WIRES:
        raise RuntimeError("wire cursor %d != %d" % (next_wire, N_WIRES))
    if any(w is None for w in next_tape + next_state + next_len + next_cand):
        raise RuntimeError("missing next-state wire")
    if next_halt is None:
        raise RuntimeError("missing halt wire")
    return records, next_tape, (next_state, next_len, next_halt, next_cand)


def fabricate(base_off=0):
    records, next_tape, extras = build_gates()
    next_state, next_len, next_halt, next_cand = extras
    remap = {next_tape[i]: wa(base_off, tape_wire(i)) for i in range(N_TAPE)}
    remap.update({next_state[i]: wa(base_off, state_wire(i)) for i in range(N_STATE)})
    remap.update({next_len[i]: wa(base_off, len_wire(i)) for i in range(N_LEN)})
    remap[next_halt] = wa(base_off, W_HALT)
    remap.update({next_cand[i]: wa(base_off, cand_wire(i)) for i in range(N_CAND)})
    if len(set(remap.values())) != N_TAPE + N_STATE + N_LEN + 1 + N_CAND:
        raise RuntimeError("self-clock outs are not unique")

    hsz = hdr_size()
    gate_start = hsz + N_WIRES
    total = gate_start + N_GATE * GATE_STRIDE
    blob = bytearray(total)
    blob[0:8] = MAGIC
    struct.pack_into("<IIIII", blob, 8, N_GATE, N_WIRES, N_IN, N_OUT, DEPTH)
    for i in range(N_OUT):
        struct.pack_into("<Q", blob, 28 + i * 8, remap[next_tape[i]])
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
        "input_addrs": [wa(base_off, tape_wire(i)) for i in range(N_IN)],
        "output_addrs": [remap[next_tape[i]] for i in range(N_OUT)],
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
        assert o not in writers, "out reused"
        writers[o] = i
        off += GATE_STRIDE
    assert len(writers) == N_GATE

    for i in range(N_OUT):
        stored_out = struct.unpack_from("<Q", blob, 28 + i * 8)[0]
        assert stored_out == meta["output_addrs"][i] == meta["input_addrs"][i]

    ctr = stored[N_TAPE_GATES:]
    assert len(ctr) == N_CTR_GATES
    for bit in range(N_CAND):
        ops = [g[0] for g in ctr[bit * GATES_PER_FA:(bit + 1) * GATES_PER_FA]]
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
            "container": "muhl_lvin.mno",
            "format": "physical",
            "gate_stride": GATE_STRIDE,
            "input_addrs": meta["input_addrs"],
            "output_addrs": meta["output_addrs"],
            "sha256": meta["sha256"],
            "clock": "tape out IS tape in",
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
    print("MUHLLVIN structural receipt")
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
