#!/usr/bin/env python3
"""host/pfc_hotpath.py — measure the REAL hot paths (bit-sliced accumulation), not the per-call unpack path.

`pfc_fabsweep` measured `fold_presliced` (unpacks every call) and got ~100k bd/s — but `PFC_MODEL_ENGINE_LEVERS §4B`
measured **457,754 bd/s @W=8192** and the A4B matvec at **679,680 bd/s** using the ACCUMULATE paths
(`matmul_column_W` = fold blocks + bit-sliced ripple-add + unpack ONCE, and `sharedx_column` = the owner's shared-x
masked-accumulate, +1.63x). Those are what `pfc_forward.matmul` actually calls. This measures a FULL matmul column
(nb blocks x W neurons) through each, so the number is the engine's true per-token cost driver.

  python host/pfc_hotpath.py
"""
import os, sys, time, random
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, "C:/llm/sdc_sandbox")
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
from pfc_matmul_engine import MatmulEngine, BLK


def bench(WB, W, nb, ACCW=44):
    """one full matmul column: W neurons x nb blocks. Returns (bd/s per path, byte-exactness)."""
    e = MatmulEngine(WB=WB, XB=8)
    lo, hi = -(1 << (WB - 1)), (1 << (WB - 1)) - 1
    random.seed(11)
    wb_blocks, xq_blocks, wl_blocks = [], [], []
    for b in range(nb):
        wl = [[random.randint(lo, hi) for _ in range(BLK)] for _ in range(W)]
        wcols, _ = e.preslice_weights(wl)                    # FABRICATION (cached to storage at runtime)
        wb_blocks.append(wcols); wl_blocks.append(wl)
        xq_blocks.append([random.randint(-127, 127) for _ in range(BLK)])
    total_bd = W * nb
    ref = [sum(wl_blocks[b][l][i] * xq_blocks[b][i] for b in range(nb) for i in range(BLK)) for l in (0, W // 2, W - 1)]
    out = {}
    t0 = time.time(); r1 = e.matmul_column_W(wb_blocks, W, xq_blocks, ACCW=ACCW); d1 = time.time() - t0
    ok1 = [r1[0], r1[W // 2], r1[W - 1]] == ref
    out["matmul_column_W (bit-sliced accum)"] = (total_bd / d1, ok1, d1)
    t0 = time.time(); r2 = e.sharedx_column(wb_blocks, W, xq_blocks, ACCW=ACCW); d2 = time.time() - t0
    ok2 = [r2[0], r2[W // 2], r2[W - 1]] == ref
    out["sharedx_column (masked-accum)"] = (total_bd / d2, ok2, d2)
    return out, total_bd


def main():
    print("=== HOT-PATH RATE — full matmul columns through the ACCUMULATE paths (what pfc_forward.matmul calls) ===\n", flush=True)
    print(f"  {'WB':>3} {'W':>6} {'nb':>4} {'path':>36} {'bd/s':>12} {'exact':>7}", flush=True)
    best = None
    for WB in (8, 16):
        for (W, nb) in ((2560, 16), (8192, 16)):
            try:
                res, total = bench(WB, W, nb)
            except Exception as ex:
                print(f"  {WB:>3} {W:>6} {nb:>4}  FAILED: {ex}", flush=True); continue
            for name, (rate, ok, dt) in res.items():
                print(f"  {WB:>3} {W:>6} {nb:>4} {name:>36} {rate:>12,.0f} {str(ok):>7}", flush=True)
                if ok and (best is None or rate > best[0]): best = (rate, WB, W, name)
    print()
    if best:
        rate, WB, W, name = best
        print(f"  ★ FASTEST byte-exact path: {name}  WB={WB} W={W} = {rate:,.0f} block-dots/s", flush=True)
        for label, bd in (("Mixtral routed", 398e6), ("Mixtral routed+sparse15%", 98.9e6),
                          ("A4B routed", 74.1e6), ("A4B routed+sparse15%", 40.6e6)):
            print(f"      {label:>26}: {bd/rate:>8,.0f} s/token", flush=True)
        print(f"\n    x the TERSE OUTPUT-CONTRACT operator (measured 220 tok -> 2 tok) = the answer costs 2 of those,", flush=True)
        print(f"    and MEMOIZE makes any repeat instant. Those are the levers that turn s/token into time-to-answer.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
