#!/usr/bin/env python3
"""host/pfc_constspec.py — CONSTANT-SPECIALIZE a real neuron's weights INTO the circuit (HARNESS_HANDOFF §5).

The lever, verbatim from the doc: "In the forward pass the WEIGHTS ARE CONSTANTS KNOWN AT BAKE TIME. A general matmul
circuit is huge; a matmul against KNOWN weights is far smaller — constant-fold every multiplier, drop always-zero
partial products, exploit weight sparsity/structure. This is partial evaluation / circuit specialization, and it
collapses area AND depth together. It is WHY baking per-model matters — bake the weights IN and the circuit
specializes to them."

Every circuit I fabricated before this took the weights as INPUTS, which is the general (huge) form. This measures the
specialized form on REAL model weights: for a given neuron, each weight w_i is a known integer, so w_i * x_i is not a
multiplier at all — it is a fixed shift-add of x_i (canonical signed digit), and w_i == 0 costs NOTHING.

Reports, against the general circuit: gates, critical-path DEPTH, and the weight-sparsity actually present in the model.

  python host/pfc_constspec.py [model.gguf] [tensor] [neurons]
"""
import os, random, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, "C:/llm/sdc_sandbox")
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import sdc_cc as CC
from pfc_bettergates import depth_of
from pfc_dot_depth import build_dot_shallow
from gguf_pp import GGUF, row_bytes
from pfc_fastdeq import dequant_fast as dequant

BLK = 32
XB = 8
OW = 24


def csd(n):
    """canonical signed digit recoding: the fewest nonzero digits, so a constant multiply is the fewest shift-adds."""
    digits = []; i = 0
    while n:
        if n & 1:
            d = 2 - (n & 3)
            digits.append((i, d)); n -= d
        n >>= 1; i += 1
    return digits


def build_specialized(c, X, wq, ow=OW):
    """sum_i w_i * x_i with EVERY w_i a KNOWN CONSTANT: no multipliers at all — shift-adds, and w_i==0 costs nothing."""
    def sx(bits, n):
        b = list(bits); return b + [b[-1]] * (n - len(b))

    def csa(a, b, d):
        s = [c.XOR(c.XOR(a[i], b[i]), d[i]) for i in range(ow)]
        co = [c.OR(c.OR(c.AND(a[i], b[i]), c.AND(a[i], d[i])), c.AND(b[i], d[i])) for i in range(ow)]
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

    rows = []; nz = 0
    for i, w in enumerate(wq):
        if w == 0: continue                                   # ★ a zero weight contributes NO GATES AT ALL
        nz += 1
        a = sx(X[i], ow)
        for (sh, sign) in csd(abs(w)):
            term = ([c.C0] * sh + a)[:ow]                      # x << sh  — a wiring shift, not a multiplier
            if (sign > 0) == (w > 0):
                rows.append(term)
            else:
                rows.append([c.NOT(t) for t in term])          # subtract: ~term, +1 folded below
                rows.append([c.C1] + [c.C0] * (ow - 1))
    if not rows: return [c.C0] * ow, 0
    while len(rows) > 2:
        nxt = []; i = 0
        while i + 3 <= len(rows):
            s, co = csa(rows[i], rows[i + 1], rows[i + 2])
            nxt.append(s); nxt.append([c.C0] + co[:ow - 1]); i += 3
        while i < len(rows): nxt.append(rows[i]); i += 1
        rows = nxt
    out = rows[0] if len(rows) == 1 else kogge(rows[0], rows[1])
    return out[:ow], nz


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "C:/llm/models/mixtral-8x7b-instruct-v0.1.Q4_K_M.gguf"
    tname = sys.argv[2] if len(sys.argv) > 2 else "blk.0.attn_q.weight"
    nneu = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    print(f"=== CONSTANT-SPECIALIZATION on REAL weights — {os.path.basename(path)} :: {tname} ===\n", flush=True)

    g = GGUF(path); t = g.tensors[tname]; tid = int(t["type"]); n_in = int(t["dims"][0])
    base = g.data0 + int(t["off"]); rb = row_bytes(tid, n_in)

    # ---- the GENERAL circuit (weights are INPUTS) — what every circuit I fabricated before this looked like
    cg, og = build_dot_shallow(8, XB, BLK)
    gg, o2 = cg.dce(og)
    gen_gates = len(gg); gen_depth = depth_of(cg.n_in, gg, o2)
    print(f"  GENERAL (weights as INPUTS): {gen_gates:,} gates, DEPTH {gen_depth}   [per {BLK}-weight block]", flush=True)

    # ---- the SPECIALIZED circuit (this neuron's REAL weights baked in as constants)
    tot_g = 0; tot_d = 0; tot_nz = 0; nblk = 0
    zeros = 0; total_w = 0
    for j in range(nneu):
        w = dequant(g.mm[base + j * rb: base + j * rb + rb], tid, n_in)
        s = (max(abs(v) for v in w) / 127) or 1e-9
        wq = [max(-127, min(127, round(v / s))) for v in w[:BLK]]
        total_w += len(wq); zeros += sum(1 for v in wq if v == 0)
        c = CC.CircuitCompiler(BLK * XB)
        X = [[c.IN[i * XB + k] for k in range(XB)] for i in range(BLK)]
        outs, nz = build_specialized(c, X, wq)
        gates, oo = c.dce(outs)
        tot_g += len(gates); tot_d += depth_of(c.n_in, gates, oo); tot_nz += nz; nblk += 1
        # fabrication-time byte-exact check (the one sanctioned host ripple)
        random.seed(100 + j)
        ok = True
        for _ in range(6):
            xq = [random.randint(-128, 127) for _ in range(BLK)]
            v = CC.ripple_typed(c, gates, 2 + c.n_in + len(gates),
                                [(xq[i] >> k) & 1 for i in range(BLK) for k in range(XB)], 1)
            bit = lambda wr: 0 if wr == 0 else 1 if wr == 1 else v[wr] & 1
            u = sum(bit(oo[b]) << b for b in range(OW)); u = u - (1 << OW) if u >= (1 << (OW - 1)) else u
            if u != sum(wq[i] * xq[i] for i in range(BLK)): ok = False; break
        if j == 0:
            print(f"  SPECIALIZED (real weights BAKED IN as constants): {len(gates):,} gates, DEPTH "
                  f"{depth_of(c.n_in, gates, oo)}, byte-exact={ok}", flush=True)
    avg_g = tot_g / nblk; avg_d = tot_d / nblk
    print(f"\n  averaged over {nblk} real neurons:", flush=True)
    print(f"     gates  {gen_gates:>8,}  ->  {avg_g:>10,.0f}   = {gen_gates/max(avg_g,1):.1f}x FEWER", flush=True)
    print(f"     DEPTH  {gen_depth:>8}  ->  {avg_d:>10.0f}   = {gen_depth/max(avg_d,1):.1f}x SHALLOWER", flush=True)
    print(f"     weight sparsity in the real rows: {zeros}/{total_w} = {100*zeros/max(total_w,1):.1f}% "
          f"of weights cost ZERO gates", flush=True)
    print(f"\n  ⇒ this is why baking per-model matters: the weights stop being inputs and become the wiring.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
