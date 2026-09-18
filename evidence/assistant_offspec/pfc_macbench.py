#!/usr/bin/env python3
"""host/pfc_macbench.py — the decisive number: MACs/s ACTUALLY achieved on one real matmul, per drive path.

Not a claim about the pfc's speed (that is DEPTH — device-independent). This measures the HOST's drive rate: how fast
this laptop walks the fabricated fold. Knowing it tells us whether the remaining gap is engineering or arithmetic.
"""
import os, struct, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, "C:/llm/sdc_sandbox")
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import pfc_forward as F

MODEL = sys.argv[1] if len(sys.argv) > 1 else "C:/llm/models/mixtral-8x7b-instruct-v0.1.Q4_K_M.gguf"
TENSOR = sys.argv[2] if len(sys.argv) > 2 else "blk.0.attn_q.weight"
TILES = [int(v) for v in (sys.argv[3].split(",") if len(sys.argv) > 3 else ["512", "2048", "8192"])]


def rss():
    import ctypes, ctypes.wintypes as wt
    class PMC(ctypes.Structure):
        _fields_ = [("cb", wt.DWORD), ("PageFaultCount", wt.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t)]
    c = PMC(); c.cb = ctypes.sizeof(PMC)
    ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(c), c.cb)
    return c.WorkingSetSize / 1e6


def main():
    fw = F.Forward(MODEL, substrate=True)
    t = fw.g.tensors[TENSOR]; n_in = int(t["dims"][0]); n_out = int(t["dims"][1])
    macs = n_in * n_out
    print(f"=== MAC BENCH — {os.path.basename(MODEL)} :: {TENSOR}  [{n_in} x {n_out} = {macs:,} MACs]", flush=True)
    print(f"    baseline resident {rss():.1f} MB", flush=True)
    x = [((i * 37 % 211) - 105) / 100.0 for i in range(n_in)]
    best = None
    for tile in TILES:
        fw.tile = tile
        F.Meter.ripple = 0; F.Meter.addressed = 0; F.Meter.pruned = 0
        r0 = rss(); t0 = time.time()
        y = fw.matmul(TENSOR, x, "bench")
        dt = time.time() - t0; r1 = rss()
        rate = macs / dt
        print(f"  tile={tile:<6} {dt:7.2f}s   {rate/1e6:7.2f} M MAC/s   resident {r0:6.1f} -> {r1:6.1f} MB "
              f"(delta {r1-r0:+6.1f})   ripple={F.Meter.ripple:,}", flush=True)
        if best is None or rate > best[1]: best = (tile, rate, r1 - r0)
    tile, rate, dr = best
    print(f"\n  BEST tile={tile}: {rate/1e6:.2f} M MAC/s, resident delta {dr:+.1f} MB", flush=True)
    # what that means for a real token, stated as arithmetic (not a verdict)
    for nm, act in (("Mixtral-8x7B (top-2 of 8)", 12.9e9), ("Mistral-24B dense", 24e9), ("Llama-70B dense", 70e9)):
        print(f"    {nm:<26} {act/1e9:5.1f} B active MAC/token -> {act/rate:8.1f} s/token at this drive rate", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
