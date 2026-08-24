#!/usr/bin/env python3
"""muhl_fab_chimera_immn_hdvs.py — FABRICATE organ 20 (MUHLCHIH).

PLUMB 3/3: detector bank -> hdvs BUNDLE plane. 20 gates.

  10 detector bits x NOT-NOT buffer (2 g)                        20
  depth 2
  dest FROM FILE: immn detector-bank addresses and hdvs
  vector-input addresses (the inject plane majority-3 READs).
  Chimera writes fresh local outs. Does not second-write hdvs.

Offline manufacture. Does not open titan.gguf. Does not evaluate.
Landed organs 1-19 stay untouched.

  python3 muhl_fab_chimera_immn_hdvs.py          # write .mno + sidecar
  python3 muhl_fab_chimera_immn_hdvs.py --dry    # structural verify only
"""
from __future__ import annotations

import hashlib
import json
import os
import struct
import sys

NAME = "muhl_chimera_immn_hdvs"
MAGIC = b"MUHLCHIH"
GATE_STRIDE = 25
OP_NAND, OP_AND, OP_OR, OP_XOR, OP_NOT = 0, 1, 2, 3, 4

N_LINK = 10
N_GATE = N_LINK * 2
N_IN = N_LINK
N_OUT = N_LINK
DEPTH = 2

W_CONST0 = 0
W_CONST1 = 1
W_IN0 = 2
N_WIRES = 2 + N_IN + N_GATE

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
EXCERPT_DIR = os.path.join(REPO_ROOT, "excerpts", "20260823")
MNO_PATH = os.path.join(EXCERPT_DIR, "muhl_chimera_immn_hdvs.mno")
REG_PATH = os.path.join(EXCERPT_DIR, "chih_circuits.json")
IMMN_REG = os.path.join(EXCERPT_DIR, "immn_circuits.json")
HDVS_REG = os.path.join(EXCERPT_DIR, "hdvs_circuits.json")

# Same layout constants that manufactured the landed immn excerpt.
IMMN_HDR = 28 + 8
IMMN_W_WIN0 = 2
IMMN_W_DET0 = IMMN_W_WIN0 + 32


def in_wire(index):
    return W_IN0 + (index % N_IN)


def dests_from_file():
    """Read landed sidecars. Do not invent addresses."""
    with open(IMMN_REG, encoding="utf-8") as handle:
        immn = json.load(handle)["muhl_immn"]
    with open(HDVS_REG, encoding="utf-8") as handle:
        hdvs = json.load(handle)["muhl_hdvs"]
    inputs = list(immn["input_addrs"])
    if inputs[0] != IMMN_HDR + IMMN_W_WIN0:
        raise RuntimeError("immn input_addrs[0] is not the landed window dest")
    if immn.get("detectors") != 128:
        raise RuntimeError("immn sidecar detectors field is not the landed bank")
    src = [IMMN_HDR + IMMN_W_DET0 + i for i in range(N_LINK)]
    dst = list(hdvs["input_addrs"][:N_LINK])
    if len(dst) != N_LINK:
        raise RuntimeError("hdvs sidecar is missing BUNDLE inject dests")
    return {
        "src_organ": "muhl_immn",
        "src_plane": "detector bank bits 0..9",
        "src_addrs": src,
        "dst_organ": "muhl_hdvs",
        "dst_plane": "BUNDLE inject / vector inputs that majority-3 READs",
        "dst_addrs": dst,
        "immn_sha256": immn["sha256"],
        "hdvs_sha256": hdvs["sha256"],
    }


def build_gates():
    records = []
    next_wire = 2 + N_IN

    def emit(op, a, b):
        nonlocal next_wire
        out = next_wire
        next_wire += 1
        records.append((op, a, b, out))
        return out

    temps = [emit(OP_NOT, in_wire(i), in_wire(i)) for i in range(N_LINK)]
    outs = [emit(OP_NOT, temps[i], temps[i]) for i in range(N_LINK)]
    if len(records) != N_GATE:
        raise RuntimeError("gate count %d != %d" % (len(records), N_GATE))
    if next_wire != N_WIRES:
        raise RuntimeError("wire cursor %d != %d" % (next_wire, N_WIRES))
    return records, outs


def hdr_size():
    return 28 + N_OUT * 8


def wa(base_off, wire):
    return base_off + hdr_size() + wire


def fabricate(base_off=0):
    dests = dests_from_file()
    records, outs = build_gates()
    remap = {outs[i]: wa(base_off, in_wire(i)) for i in range(N_OUT)}
    if len(set(remap.values())) != N_OUT:
        raise RuntimeError("chimera outs are not unique")

    hsz = hdr_size()
    gate_start = hsz + N_WIRES
    total = gate_start + N_GATE * GATE_STRIDE
    blob = bytearray(total)
    blob[0:8] = MAGIC
    struct.pack_into("<IIIII", blob, 8, N_GATE, N_WIRES, N_IN, N_OUT, DEPTH)
    for i in range(N_OUT):
        struct.pack_into("<Q", blob, 28 + i * 8, remap[outs[i]])
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
        "input_addrs": [wa(base_off, in_wire(i)) for i in range(N_IN)],
        "output_addrs": [remap[outs[i]] for i in range(N_OUT)],
        "sha256": hashlib.sha256(blob).hexdigest(),
        "dests": dests,
    }
    return bytes(blob), meta, stored


def verify_physical(blob, meta, stored):
    """Structural receipt only. Does not walk the organ as inference."""
    assert blob[:8] == MAGIC, "bad magic"
    ng, nw, ni, no, dp = struct.unpack_from("<IIIII", blob, 8)
    assert ng == N_GATE and nw == N_WIRES and ni == N_IN and no == N_OUT and dp == DEPTH
    assert len(blob) == meta["len"]
    assert len(stored) == N_GATE
    hsz = hdr_size()
    assert hsz + N_WIRES + N_GATE * GATE_STRIDE == len(blob)

    writers = {}
    off = hsz + N_WIRES
    for i, (eop, ea, eb, eo) in enumerate(stored):
        op, a, b, o = struct.unpack_from("<BQQQ", blob, off)
        assert op == eop and a == ea and b == eb and o == eo, "gate %d record" % i
        assert op == OP_NOT, "gate %d op" % i
        assert o not in writers, "out reused by gates %d and %d" % (writers[o], i)
        writers[o] = i
        off += GATE_STRIDE
    assert len(writers) == N_GATE
    assert [g[0] for g in stored].count(OP_NOT) == N_GATE

    for i in range(N_OUT):
        stored_out = struct.unpack_from("<Q", blob, 28 + i * 8)[0]
        assert stored_out == meta["output_addrs"][i]
        assert stored_out == meta["input_addrs"][i], "buffer out is not input %d" % i

    dests = meta["dests"]
    assert dests["src_addrs"] == [IMMN_HDR + IMMN_W_DET0 + i for i in range(N_LINK)]
    assert len(dests["dst_addrs"]) == N_LINK
    assert blob[hsz + W_CONST0] == 0 and blob[hsz + W_CONST1] == 1
    return True


def write_files(blob, meta):
    os.makedirs(os.path.dirname(MNO_PATH), exist_ok=True)
    with open(MNO_PATH, "wb") as handle:
        handle.write(blob)
    dests = meta["dests"]
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
            "container": "muhl_chimera_immn_hdvs.mno",
            "format": "physical",
            "gate_stride": GATE_STRIDE,
            "input_addrs": meta["input_addrs"],
            "output_addrs": meta["output_addrs"],
            "sha256": meta["sha256"],
            "clock": "NOT-NOT buffer. Local out IS local in. MOVE dests stay in sidecar.",
            "src_organ": dests["src_organ"],
            "src_plane": dests["src_plane"],
            "src_addrs": dests["src_addrs"],
            "dst_organ": dests["dst_organ"],
            "dst_plane": dests["dst_plane"],
            "dst_addrs": dests["dst_addrs"],
            "immn_sha256": dests["immn_sha256"],
            "hdvs_sha256": dests["hdvs_sha256"],
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
    print("MUHLCHIH structural receipt")
    print("  n_gate=%d n_wires=%d n_in=%d n_out=%d depth=%d" % (
        meta["n_gate"], meta["n_wires"], meta["n_in"], meta["n_out"], meta["depth"]))
    print("  len=%d sha256=%s" % (meta["len"], meta["sha256"]))
    print("  dest FROM FILE src=%s dst=%s" % (
        meta["dests"]["src_addrs"], meta["dests"]["dst_addrs"]))
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
