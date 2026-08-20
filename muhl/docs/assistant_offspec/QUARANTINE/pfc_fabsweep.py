#!/usr/bin/env python3
"""host/pfc_fabsweep.py — FABRICATION SWEEP: which dot circuit to bake for the model engine (owner: "most of your work
should be in whitebox not python — I BUILT THE TOOLS YOU NEED").

Uses the owner's own fabricator (`sdc_cc` via `pfc_matmul_engine.build_dot`) + `pfc_optimal`-style selection to answer
one question with MEASURED numbers instead of theory:

    at each weight-bit width WB, what is (gates, critical DEPTH, fold rate bd/s, accuracy on REAL model weights)?

Why it matters: `PFC_MODEL_ENGINE_LEVERS §2` says W3×A4 = 7,166g vs W8 = 18,774g and "3-bit is accuracy-safe, 2-bit is
NOT"; §4B measured the A4B runtime matvec at 679,680 bd/s (WB=3) but the current engine runs WB=16 at ~114k bd/s.
That is a ~6x THROUGHPUT lever sitting unpulled — but only if 3-bit holds accuracy on this model's real rows, which is
what the ACC column measures (per-neuron scale, exactly how `pfc_forward._tile` quantizes).

  python host/pfc_fabsweep.py [model.gguf]
"""
import os, sys, time, random, struct
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, "C:/llm/sdc_sandbox")
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
from pfc_matmul_engine import MatmulEngine, build_dot, BLK
from gguf_pp import GGUF, row_bytes
from pfc_fastdeq import dequant_fast as dequant

DEFAULT = "C:/llm/models/mixtral-8x7b-instruct-v0.1.Q4_K_M.gguf"


def depth_of(gates, n_in):
    """critical-path DEPTH of the fabricated netlist = the pfc's own latency (owner: latency is DEPTH, not gate count).
    Structural read only — no run, no ripple (PFC_HARD_WON §7 / host/pfc_speed.py method)."""
    d = {}
    def get(w): return d.get(w, 0)
    for g in gates:
        a, b, o = g[1], g[2], g[0]
        d[o] = max(get(a), get(b)) + 1
    return max(d.values()) if d else 0


def real_rows(path, tensor, n_rows):
    """REAL weight rows off the model (mmap, flat RAM) — accuracy must be measured on the owner's actual weights,
    not random numbers, or the WB choice is a guess."""
    g = GGUF(path)
    if tensor not in g.tensors:
        cand = [n for n in g.tensors if n.endswith("ffn_gate.weight") or n.endswith("attn_q.weight")]
        tensor = cand[0] if cand else list(g.tensors)[0]
    t = g.tensors[tensor]; tid = int(t["type"]); n_in = int(t["dims"][0])
    base = g.data0 + int(t["off"]); rb = row_bytes(tid, n_in); mm = g.mm
    rows = []
    for j in range(n_rows):
        w = dequant(mm[base + j * rb: base + j * rb + rb], tid, n_in)
        rows.append([v for v in w[:BLK]])
    return tensor, rows


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    print(f"=== FABRICATION SWEEP — which dot to bake (model: {os.path.basename(path)}) ===", flush=True)
    tname, rows = real_rows(path, "blk.0.ffn_gate.weight", 24)
    print(f"  accuracy measured on REAL rows of {tname} (24 rows x {BLK} weights)\n", flush=True)
    random.seed(7)
    xs = [[random.randint(-127, 127) for _ in range(BLK)] for _ in range(24)]   # int8 activations (XB=8)
    print(f"  {'WB':>3} {'gates':>9} {'depth':>7} {'bd/s @W=2560':>14} {'exact':>7} {'rel-err(real w)':>16}", flush=True)
    best = None
    for WB in (3, 4, 6, 8, 16):
        try:
            e = MatmulEngine(WB=WB, XB=8)
        except Exception as ex:
            print(f"  {WB:>3}  FABRICATION FAILED: {ex}", flush=True); continue
        dep = depth_of(e.gates, e.n_in)
        # byte-exactness of the fabricated circuit vs an integer dot (fabrication-time verification, allowed)
        lo, hi = -(1 << (WB - 1)), (1 << (WB - 1)) - 1
        ok = 0
        for _ in range(40):
            w = [random.randint(lo, hi) for _ in range(BLK)]; x = [random.randint(-127, 127) for _ in range(BLK)]
            if e.dot1(w, x) == sum(w[i] * x[i] for i in range(BLK)): ok += 1
        # rate at the measured knee (W=2560 lanes, the engine's tile)
        W = 2560
        wl = [[random.randint(lo, hi) for _ in range(BLK)] for _ in range(W)]
        wcols, _ = e.preslice_weights(wl)
        t0 = time.time(); e.fold_presliced(wcols, W, xs[0]); dt = time.time() - t0
        rate = W / dt if dt > 0 else 0
        # ACCURACY on REAL weights: per-neuron scale (exactly pfc_forward._tile), fold vs float reference
        errs = []
        for wrow, x in zip(rows, xs):
            s = (max(abs(v) for v in wrow) / hi) or 1e-9
            q = [max(lo, min(hi, round(v / s))) for v in wrow]
            got = e.dot1(q, x) * s
            ref = sum(wrow[i] * x[i] for i in range(BLK))
            errs.append(abs(got - ref) / (abs(ref) + 1e-9))
        rel = sum(errs) / len(errs)
        print(f"  {WB:>3} {len(e.gates):>9,} {dep:>7} {rate:>14,.0f} {ok:>5}/40 {rel:>15.2%}", flush=True)
        if rel < 0.02 and (best is None or rate > best[1]): best = (WB, rate, len(e.gates), dep, rel)
        e = None
    print()
    if best:
        WB, rate, gts, dep, rel = best
        print(f"  ★ SELECTED WB={WB}: {gts:,} gates, depth {dep}, {rate:,.0f} bd/s, {rel:.2%} rel-err on real weights", flush=True)
        print(f"    (accuracy gate = rel-err < 2%; the leanest circuit that holds accuracy wins — pfc_optimal discipline)", flush=True)
    else:
        print("  no WB met the 2% accuracy gate on real weights — keep WB=16 and pull COUNT levers instead", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
