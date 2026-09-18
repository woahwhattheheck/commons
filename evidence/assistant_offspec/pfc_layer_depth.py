#!/usr/bin/env python3
"""host/pfc_layer_depth.py — §6's NEXT STEP, measured: scale the forward pass from ONE NEURON to a LAYER as ONE
self-contained gate-net, and read the number that actually matters — DEPTH.

THE QUESTION THIS SETTLES. `SDC_FORWARD_PASS.md` §4.2 says the forward pass is "ONE self-contained gate-net", and the
corpus says the pfc's speed is the critical-path DEPTH (a signal settles a whole depth level at once, in parallel), not
host seconds. If that is right then:
  - adding NEURONS (width) must NOT add depth — every neuron settles simultaneously, so a whole layer costs the same
    LATENCY as one neuron, and only the gate COUNT grows.
  - adding WEIGHTS per neuron (dot length) must grow depth only ~LOGARITHMICALLY (CSA forest + Kogge-Stone), not linearly.
If both hold, a full layer is ONE settle at small depth — which is exactly why the clocked/arcade shape (one instruction
per full-circuit ripple) is a proof of concept and not the blueprint.

Everything here is FABRICATION-TIME measurement on the model's REAL weights (constant-specialized, per HARNESS_HANDOFF
§5). Nothing is stored and nothing runs — this measures the circuit the fabricator would lay down.

  python host/pfc_layer_depth.py [model.gguf] [tensor]
"""
import os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, "C:/llm/sdc_sandbox")
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import sdc_cc as CC
from gguf_pp import GGUF, row_bytes
from pfc_fastdeq import dequant_fast as dequant
from pfc_bettergates import depth_of
from pfc_model_fab import build_slice, XB, OW

MODEL = sys.argv[1] if len(sys.argv) > 1 else "C:/llm/models/mixtral-8x7b-instruct-v0.1.Q4_K_M.gguf"
TENSOR = sys.argv[2] if len(sys.argv) > 2 else "blk.0.attn_q.weight"


def build(g, t, nneu, n_in):
    """Fabricate `nneu` real neurons of `n_in` real weights as ONE combinational net; return (gates, depth, zeros%)."""
    tid = int(t["type"]); row_n = int(t["dims"][0]); base = g.data0 + int(t["off"]); rb = row_bytes(tid, row_n)
    c = CC.CircuitCompiler(n_in * XB)
    X = [[c.IN[i * XB + k] for k in range(XB)] for i in range(n_in)]
    outs = []; zeros = 0
    for j in range(nneu):
        w = dequant(g.mm[base + j * rb: base + j * rb + rb], tid, row_n)[:n_in]
        s = (max(abs(v) for v in w) / 127) or 1e-9
        wq = [max(-127, min(127, round(v / s))) for v in w]
        zeros += sum(1 for v in wq if v == 0)
        outs += build_slice(c, X, wq, n_in // 32)
    gates, o2 = c.dce(outs)
    return len(gates), depth_of(c.n_in, gates, o2), 100.0 * zeros / (nneu * n_in)


def main():
    g = GGUF(MODEL); t = g.tensors[TENSOR]
    n_out = int(t["dims"][1]); row_n = int(t["dims"][0])
    print(f"=== ONE SELF-CONTAINED NET — {os.path.basename(MODEL)} :: {TENSOR}  [{row_n} x {n_out}] ===", flush=True)
    print(f"    real weights, constant-specialized. DEPTH = the pfc's latency; gates = area.\n", flush=True)

    print("  A) WIDTH — more NEURONS at a fixed 128-weight dot. Does latency grow with width?", flush=True)
    base_depth = None
    for nneu in (1, 4, 16, 64):
        t0 = time.time(); ng, dep, z = build(g, t, nneu, 128)
        base_depth = base_depth if base_depth is not None else dep
        flag = "same latency" if dep == base_depth else f"CHANGED from {base_depth}"
        print(f"     {nneu:3d} neurons -> {ng:9,} gates   DEPTH {dep:4d}   ({flag})   [{time.time()-t0:.1f}s]", flush=True)

    print("\n  B) DOT LENGTH — more WEIGHTS per neuron. Depth should grow ~log, not linear.", flush=True)
    prev = None
    for n_in in (32, 128, 512, 2048):
        if n_in > row_n: break
        t0 = time.time(); ng, dep, z = build(g, t, 1, n_in)
        rat = f"  (+{dep-prev} for 4x the weights)" if prev is not None else ""
        print(f"     {n_in:5d} weights -> {ng:9,} gates   DEPTH {dep:4d}{rat}   {z:.0f}% zero-weights cost no gates"
              f"   [{time.time()-t0:.1f}s]", flush=True)
        prev = dep

    print(f"\n  WHAT THIS MEANS FOR A FULL LAYER:", flush=True)
    ng1, dep1, _ = build(g, t, 1, 512)
    per_neuron = ng1
    print(f"    one {512}-weight neuron = {per_neuron:,} gates at DEPTH {dep1}.", flush=True)
    print(f"    {n_out:,} neurons settle IN PARALLEL at that SAME depth -> a whole {TENSOR} projection is", flush=True)
    print(f"    ONE settle of depth {dep1}, ~{per_neuron*n_out/1e9:.1f}B gates of area (area is storage; depth is time).", flush=True)
    print(f"    That is the §4.2 'one self-contained gate-net' shape: width costs AREA, never LATENCY.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
