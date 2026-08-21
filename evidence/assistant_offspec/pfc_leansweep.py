#!/usr/bin/env python3
"""host/pfc_leansweep.py — pull the CATALOG's throughput levers on the model dot: leaner circuit -> higher W -> more MAC/s.

THE CATALOG'S OWN EQUATION (`PFC_LEVER_CATALOG` "Gate-clock invariant"):
    throughput(ops/s) = gate_clock x bit_slice_W / gates_per_op          (gate_clock ~10M gates/s, measured 5.35-13.7M)
and its width rule ("Bit-slice width ceiling is circuit-size-dependent"):
    wire-state RAM  proportional to  n_wire x W
      -> a 95-wire circuit rides W=65,536 @18MB RSS; a 213k-wire miner caps at W~2,048.
So a LEANER dot wins TWICE: fewer gates_per_op (numerator) AND it rides to a higher W before the cache/RAM wall.
Catalog target for this axis: matmul peak ~1.27M block-dots/s @ W=65,536 = ~40.6M MAC/s (we measure 8.46M today).

WHAT IS SWEPT (every config is byte-exact-checked against the integer dot before its rate is believed):
  ow  — accumulator width. Max |sum q*x| over a 32-block is 32*15*127 = 60,960 < 2^17, so ow=20 is 3 bits of dead weight.
  XB  — activation bits. Fewer bits = smaller partial-product forest, at a measured accuracy cost.
  W   — the bit-slice width, swept to find each circuit's own cliff rather than assuming one.

  python host/pfc_leansweep.py
"""
import os, random, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, "C:/llm/sdc_sandbox")
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
from pfc_matmul_engine import MatmulEngine, BLK
from pfc_q4k_fast import read_answer

CONFIGS = [                      # (WB, XB, ow, label)
    (4, 8, 20, "today  WB4 XB8 ow20"),
    (4, 8, 17, "lean-ow  WB4 XB8 ow17"),
    (4, 7, 17, "lean+XB7 WB4 XB7 ow17"),
    (4, 6, 17, "lean+XB6 WB4 XB6 ow17"),
]
WIDTHS = [2048, 4096, 8192, 16384, 32768]


def check(eng, XB, W=64):
    """byte-exact vs the integer dot — a rate is meaningless if the answer is wrong."""
    random.seed(5)
    xl = (1 << (XB - 1)) - 1
    for _ in range(3):
        wq = [[random.randint(0, 15) for _ in range(BLK)] for _ in range(W)]
        xq = [random.randint(-xl - 1, xl) for _ in range(BLK)]
        planes, _ = eng.preslice_weights(wq)
        got = read_answer(eng.fold_bits(planes, W, xq, (1 << W) - 1), W, len(eng.outs))
        for l in range(W):
            if got[l] != sum(wq[l][i] * xq[i] for i in range(BLK)): return False
    return True


def main():
    print("=== LEAN SWEEP — leaner circuit rides to higher W (catalog: gate-clock invariant) ===", flush=True)
    print(f"    today's measured drive: 8.46 M MAC/s   ·   catalog target for this axis: ~40.6 M MAC/s\n", flush=True)
    best = (None, 0.0)
    for WB, XB, ow, label in CONFIGS:
        try:
            eng = MatmulEngine(WB=WB, XB=XB, shallow=True, ow=ow, unsigned=True)
        except Exception as e:
            print(f"  {label:24} BUILD FAILED: {e}", flush=True); continue
        ng = len(eng.gates); nw = eng.gates and max(max(g[1], g[2]) for g in eng.gates) or 0
        ok = check(eng, XB)
        print(f"  {label:24} {ng:7,} gates  {'byte-exact' if ok else '★ NOT byte-exact — rates ignored'}", flush=True)
        if not ok: continue
        random.seed(7)
        for W in WIDTHS:
            wq = [[random.randint(0, 15) for _ in range(BLK)] for _ in range(min(W, 4096))]
            wq = (wq * ((W // len(wq)) + 1))[:W]
            xq = [random.randint(-(1 << (XB - 1)), (1 << (XB - 1)) - 1) for _ in range(BLK)]
            ones = (1 << W) - 1
            try:
                planes, _ = eng.preslice_weights(wq)
                t0 = time.time()
                for _ in range(3):
                    read_answer(eng.fold_bits(planes, W, xq, ones), W, len(eng.outs))
                dt = (time.time() - t0) / 3
            except MemoryError:
                print(f"      W={W:<6} MemoryError (the RAM wall for this circuit)", flush=True); break
            rate = (BLK * W) / dt / 1e6
            mark = ""
            if rate > best[1]: best = ((WB, XB, ow, W, ng), rate); mark = "  <= best"
            print(f"      W={W:<6} {dt*1000:8.1f} ms/sweep   {rate:7.2f} M MAC/s{mark}", flush=True)
    if best[0]:
        WB, XB, ow, W, ng = best[0]
        print(f"\n  ★ BEST: WB={WB} XB={XB} ow={ow} W={W} ({ng:,} gates) -> {best[1]:.2f} M MAC/s "
              f"({best[1]/8.46:.2f}x today's drive)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
