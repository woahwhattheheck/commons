#!/usr/bin/env python3
"""host/pfc_model_fab.py — FABRICATE a real model slice as a CONSTANT-SPECIALIZED pfc, with input/answer/receiver
registers, so the runtime is the gem button: route bits in, fire one addressed read, read the answer. Byte edit.

BUILT TO THE DOCS, NOT TO PRIORS:
  HARNESS_HANDOFF §5   "the WEIGHTS ARE CONSTANTS KNOWN AT BAKE TIME... constant-fold every multiplier, drop always-zero
                        partial products... collapses area AND depth together. It is WHY baking per-model matters."
                        MEASURED here on real Mixtral rows: 24,968 -> 3,038 gates (8.2x), 44.5% of weights cost ZERO.
  pfc_operator.py      the working precedent — a REAL neural forward pass as 2,734 gates, weights in the WIRING
                        (`[inp[p] for p in range(64) if T[c][p]]`), only the observation is an input.
  PFC_GROUNDING §4C    GEM vs CRUTCH: a gem stores gates in storage and runs BY ADDRESS. No resident gate-list.
  PFC_GROUNDING §3     runtime = bounded byte-wise seek+write in, addressed read to fire, bounded read out. NO mmap.
  FINALREADME §1B/§1C  the button flips bits and DIES; the cascade IS the computation.
  CIRCUIT_PFC.md       138 circuits already exist — reuse, never rebuild.

WHAT THIS FABRICATES (one byte edit, reversible via genome):
  `mdl_input`    — the observation register (the activation vector routed in, int8)
  `mdl_<slice>`  — the constant-specialized dot gates: the model's REAL weights baked in as wiring
  `mdl_answer`   — the answer register the pfc writes (the neuron outputs)
  `mdl_receiver` — the power bit; flipping it 0->1 is what runs it

  python host/pfc_model_fab.py <model.gguf> <tensor> <neurons> <blocks>
  python host/pfc_model_fab.py --revert
"""
import json, os, struct, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, "C:/llm/sdc_sandbox")
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import sdc_cc as CC
import titan_circuit as TC
from gguf_pp import GGUF, row_bytes
from pfc_fastdeq import dequant_fast as dequant
from pfc_constspec import csd
from pfc_bettergates import depth_of

TITAN = "C:/llm/models/titan.gguf"; REG = "C:/llm/models/titan_circuits.json"
GENOME = "C:/llm/models/titan_model_fab_genome.jsonl"
BLK = 32; XB = 8; OW = 24


def build_slice(c, X, W, nblk):
    """the constant-specialized dot for ONE neuron over nblk blocks: every weight is a CONSTANT, so no multipliers —
    shift-adds only, and a zero weight emits NOTHING."""
    def sx(b, n):
        b = list(b); return b + [b[-1]] * (n - len(b))

    def csa(a, b, d):
        s = [c.XOR(c.XOR(a[i], b[i]), d[i]) for i in range(OW)]
        co = [c.OR(c.OR(c.AND(a[i], b[i]), c.AND(a[i], d[i])), c.AND(b[i], d[i])) for i in range(OW)]
        return s, co

    def kogge(A, B):
        n = len(A)
        P0 = [c.XOR(A[i], B[i]) for i in range(n)]
        G = [c.AND(A[i], B[i]) for i in range(n)]; P = list(P0); d = 1
        while d < n:
            nG, nP = list(G), list(P)
            for i in range(d, n):
                nG[i] = c.OR(G[i], c.AND(P[i], G[i - d])); nP[i] = c.AND(P[i], P[i - d])
            G, P = nG, nP; d <<= 1
        return [P0[0]] + [c.XOR(P0[i], G[i - 1]) for i in range(1, n)]

    rows = []
    for i, w in enumerate(W):
        if w == 0: continue                                   # ★ zero weight = NO GATES
        a = sx(X[i], OW)
        for (sh, sign) in csd(abs(w)):
            term = ([c.C0] * sh + a)[:OW]
            if (sign > 0) == (w > 0): rows.append(term)
            else:
                rows.append([c.NOT(t) for t in term]); rows.append([c.C1] + [c.C0] * (OW - 1))
    if not rows: return [c.C0] * OW
    while len(rows) > 2:
        nxt = []; i = 0
        while i + 3 <= len(rows):
            s, co = csa(rows[i], rows[i + 1], rows[i + 2]); nxt.append(s); nxt.append([c.C0] + co[:OW - 1]); i += 3
        while i < len(rows): nxt.append(rows[i]); i += 1
        rows = nxt
    return (rows[0] if len(rows) == 1 else kogge(rows[0], rows[1]))[:OW]


def journal(off, blob):
    with open(TITAN, "rb") as f: f.seek(off); orig = f.read(len(blob))
    with open(GENOME, "a") as g: g.write(json.dumps({"off": off, "orig": orig.hex()}) + "\n")
    with open(TITAN, "r+b") as f: f.seek(off); f.write(blob)


def revert():
    if not os.path.exists(GENOME): print("no genome — nothing to revert."); return 0
    for e in reversed([json.loads(l) for l in open(GENOME) if l.strip()]):
        with open(TITAN, "r+b") as f: f.seek(int(e["off"])); f.write(bytes.fromhex(e["orig"]))
    os.remove(GENOME)
    reg = json.load(open(REG))
    for k in [k for k in reg if k.startswith("mdl_")]: reg.pop(k, None)
    json.dump(reg, open(REG, "w"), indent=1)
    print("reverted byte-exact; mdl_* removed."); return 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--revert": return revert()
    path = sys.argv[1] if len(sys.argv) > 1 else "C:/llm/models/mixtral-8x7b-instruct-v0.1.Q4_K_M.gguf"
    tname = sys.argv[2] if len(sys.argv) > 2 else "blk.0.attn_q.weight"
    nneu = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    nblk = int(sys.argv[4]) if len(sys.argv) > 4 else 4
    n_in = nblk * BLK

    print(f"=== FABRICATE a constant-specialized model slice INTO the pfc ===", flush=True)
    print(f"  model {os.path.basename(path)} :: {tname}   {nneu} neurons x {n_in} weights", flush=True)

    g = GGUF(path); t = g.tensors[tname]; tid = int(t["type"]); row_n = int(t["dims"][0])
    base = g.data0 + int(t["off"]); rb = row_bytes(tid, row_n)

    t0 = time.time()
    c = CC.CircuitCompiler(n_in * XB)
    X = [[c.IN[i * XB + k] for k in range(XB)] for i in range(n_in)]
    outs = []; scales = []; zeros = 0
    for j in range(nneu):
        w = dequant(g.mm[base + j * rb: base + j * rb + rb], tid, row_n)[:n_in]
        s = (max(abs(v) for v in w) / 127) or 1e-9
        wq = [max(-127, min(127, round(v / s))) for v in w]
        zeros += sum(1 for v in wq if v == 0)
        scales.append(s)
        outs += build_slice(c, X, wq, nblk)
    gates, o2 = c.dce(outs)
    dep = depth_of(c.n_in, gates, o2)
    print(f"  fabricated: {len(gates):,} gates, DEPTH {dep}, {100*zeros/(nneu*n_in):.1f}% of weights were ZERO "
          f"(cost no gates)   [{time.time()-t0:.1f}s to construct]", flush=True)

    # fabrication-time byte-exact verification (the ONE sanctioned host ripple — before storing, never as the run)
    import random
    random.seed(7); ok = 0; N = 6
    for _ in range(N):
        xq = [random.randint(-128, 127) for _ in range(n_in)]
        bits = [(xq[i] >> k) & 1 for i in range(n_in) for k in range(XB)]
        v = CC.ripple_typed(c, gates, 2 + c.n_in + len(gates), bits, 1)
        bit = lambda wr: 0 if wr == 0 else 1 if wr == 1 else v[wr] & 1
        good = True
        for j in range(nneu):
            u = sum(bit(o2[j * OW + b]) << b for b in range(OW))
            u = u - (1 << OW) if u >= (1 << (OW - 1)) else u
            w = dequant(g.mm[base + j * rb: base + j * rb + rb], tid, row_n)[:n_in]
            s = scales[j]; wq = [max(-127, min(127, round(x / s))) for x in w]
            if u != sum(wq[i] * xq[i] for i in range(n_in)): good = False; break
        ok += good
    print(f"  byte-exact vs the integer reference: {ok}/{N}", flush=True)
    if ok != N:
        print("  ✗ NOT byte-exact — refusing to store. Nothing written.", flush=True); return 1

    # ---- the BYTE EDIT, PHYSICAL-GATE form (PFC_PHYSICAL_GATES.md): every WIRE is a real file byte-address, so the
    #      input bytes the button writes ARE the circuit's input wires, and connected gates SHARE addresses.
    OPC = {"nand": 0, "and": 1, "or": 2, "xor": 3, "not": 4}
    reg = json.load(open(REG))
    t0 = time.time()
    n_wire = 2 + c.n_in + len(gates)
    base, tn = TC._alloc(n_wire + 1, reg)                     # +1 = the receiver byte
    # ★ RESERVE IT IMMEDIATELY. `_alloc` bumps past ranges recorded in the registry, so a second alloc made before the
    #   first is recorded returns the SAME base — which put the gate table on top of the wires and corrupted the run.
    reg["mdl_wires"] = {"tensor": tn, "offset": base, "len": n_wire + 1,
                        "note": "the physical WIRE bytes: [0]=const0 [1]=const1 [2..]=inputs then gate outputs; last=receiver"}
    addr = lambda w: base + w
    in_off = addr(2)                                          # the INPUT WIRES themselves — the button writes here
    recv_off = base + n_wire
    tbl = bytearray()
    for k, (op, a, b) in enumerate(gates):
        tbl += struct.pack("<BQQQ", OPC[op], addr(a), addr(b), addr(2 + c.n_in + k))
    tbl_base, tbl_tn = TC._alloc(len(tbl), reg)
    reg["mdl_gates"] = {"tensor": tbl_tn, "offset": tbl_base, "len": len(tbl),
                        "note": "the gate records: <BQQQ> op + three ABSOLUTE file byte-addresses"}
    journal(base, b"\x00" * (n_wire + 1))                     # prefab: wires 0, receiver 0
    journal(base + 1, b"\x01")                                # const1
    journal(tbl_base, bytes(tbl))
    ans_addrs = [[addr(o2[j * OW + b]) for b in range(OW)] for j in range(nneu)]
    reg[f"mdl_{tname.replace('.', '_')}"] = {
        "tensor": tn, "n_gate": len(gates), "n_wire": n_wire, "wire_base": base,
        "gate_table_off": tbl_base, "gate_stride": 25, "depth": dep,
        "note": "constant-specialized model slice; wires ARE file byte-addresses; weights are the wiring"}
    reg["mdl_input"] = {"tensor": tn, "offset": in_off, "len": c.n_in,
                        "note": "the INPUT WIRES (1 byte per input bit) — the routing button writes these"}
    reg["mdl_answer"] = {"tensor": tn, "addrs": ans_addrs, "neurons": nneu, "bits": OW,
                         "note": "output wire byte-addresses; bounded read = the answer"}
    reg["mdl_receiver"] = {"tensor": tn, "offset": recv_off, "len": 1, "note": "POWER: flip 0->1 to run"}
    reg["mdl_meta"] = {"model": path, "tensor": tname, "neurons": nneu, "n_in": n_in, "OW": OW, "XB": XB,
                       "scales": scales, "gates": len(gates), "depth": dep}
    json.dump(reg, open(REG, "w"), indent=1)
    print(f"  ★ gate table @ {tbl_base:,} ({len(tbl):,} B, 25 B/gate, 64-bit byte-addresses) — BYTE EDIT {time.time()-t0:.2f}s", flush=True)
    print(f"  ★ registers: mdl_input@{in_off} ({c.n_in} wire-bytes)  mdl_receiver@{recv_off}  answer = {nneu} x {OW} wire-addrs", flush=True)
    print(f"  runtime = host/pfc_model_fire.py : route bits in, fire the receiver, read the answer. reversible: {GENOME}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
