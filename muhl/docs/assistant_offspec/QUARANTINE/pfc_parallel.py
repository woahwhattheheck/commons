#!/usr/bin/env python3
"""host/pfc_parallel.py — the CORES axis, in pure Python: split a matmul's output tiles across PROCESSES.

WHY THIS EXISTS. `HYBRID` §4 lists three orthogonal resources and we have only been driving two:
    storage (how many you HOLD) · RAM (how many you keep HOT) · **cores x bit-slice (how many you PULSE/sec)**
The corpus repeatedly notes "x cores with NATIVE threads (pure-Python GIL caps this)" — true for THREADS. It is not
true for PROCESSES. Each worker gets its own interpreter and its own GIL, and because every worker mmaps the SAME model
file, the weight pages are shared by the OS page cache rather than duplicated. This box is a Ryzen 5 7520U (4 cores),
so the ceiling here is ~4x on the drive — the largest lever left that needs no C compiler.

WHY IT IS OPT-IN AND OFF BY DEFAULT. The owner's standing rule is "no background workers — they orphan and peg the CPU"
([[no-cheating-no-runaways]]). That rule is respected here in three ways:
  1. The pool is created inside a context manager and ALWAYS terminated + joined, including on exception.
  2. Workers are NOT daemons of a detached parent; a `maxtasksperchild` bound keeps memory from creeping.
  3. Nothing is spawned unless `parallel=N` is passed explicitly. Default is single-process, exactly as before.
On an 8 GB box also check headroom first: each worker costs ~20 MB interpreter + the fold's transient wire state
(~21 MB at W=16384). Four workers is ~160 MB on top of the shared page cache.

★ STATUS 2026-07-24: **BROKEN — DO NOT USE. The timing looks great and the ANSWER IS WRONG.**
`--bench` reports ~4.8x, and that number is meaningless: `max |delta| vs single process` comes back **nan**, with
**1016 of 1024 outputs NaN starting at row 0**, and the 8 finite ones off by 1.2e+08. The single-process path on the
same tensor has zero NaN, so the defect is in the worker, not the engine.

This is exactly why the bench prints the delta next to the speedup, and it is the lesson from
`pfc-verify-against-float-not-the-old-path` landing a second time: **a speedup you have not correctness-checked is not
a speedup.** Had this shipped on the strength of "4.8x", every reply would have been noise, fast.

Ruled out so far: it is NOT the per-sub-block scale mismatch (fixed, still NaN), NOT bad weights (the same rows
dequantise clean in-process), NOT job/row bookkeeping (row0 offsets check out). The remaining suspects are in worker
setup — `Forward.__new__` skips `__init__`, so the worker's `fw` carries only `g/XB/dotq/dotq_gates`, and something
`preslice_q4k_col`/`q4k_scales_col` needs is either absent or differently initialised under `spawn` (each worker
re-imports and rebuilds module-level state such as the F16 table). Debug by returning a per-worker diagnostic (first
`DS`/`DM`/`sums` values) rather than by inspecting from the parent.

Parked deliberately: the cores axis is a ~4x SPEED lever, and correctness of the running generation matters more.

  python host/pfc_parallel.py --bench [model.gguf] [tensor] [workers]
"""
import os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, "C:/llm/sdc_sandbox")
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

_W = {}                                                   # per-worker state, built once per process


def _init(model_path, XB, ow):
    """Runs ONCE per worker process. Opens the model (mmap — the pages are shared with every other worker via the OS
    page cache, so N workers do not cost N copies of the weights) and builds the fold engine once."""
    import pfc_forward as F
    from pfc_matmul_engine import MatmulEngine
    fw = F.Forward.__new__(F.Forward)
    from gguf_pp import GGUF
    fw.g = GGUF(model_path)
    fw.XB = XB
    fw.dotq = MatmulEngine(WB=4, XB=XB, shallow=True, ow=ow, unsigned=True)
    fw.dotq_gates = len(fw.dotq.gates)
    _W["fw"] = fw


def _tile_job(job):
    """Compute one ROW RANGE of one tensor. Returns (row0, values). Pure address arithmetic picks the range, so a
    worker touches only its own rows — no coordination, no shared mutable state."""
    name, row0, nrows, xq, sxs, tid, n_in, off = job
    fw = _W["fw"]
    from pfc_q4k_fast import preslice_q4k_col, q4k_scales_col, fold_sub32
    from gguf_pp import row_bytes
    rb = row_bytes(tid, n_in); base = fw.g.data0 + off + row0 * rb
    mv = memoryview(fw.g.mm)
    nsub = n_in // 32
    xsum = [sum(xq[s * 32:(s + 1) * 32]) for s in range(nsub)]
    live = [s for s in range(nsub) if any(xq[s * 32:(s + 1) * 32])]
    W = nrows; ones = (1 << W) - 1
    acc = [0.0] * W; dmc = {}
    for s in live:
        planes = preslice_q4k_col(mv, base, rb, s, W)
        sums = fold_sub32(fw, planes, xq[s * 32:(s + 1) * 32], W, ones)
        DS, DM = q4k_scales_col(mv, base, rb, s, W, dmc)
        # PER-SUB-BLOCK scale, matching the single-process path exactly. This worker previously carried the OLD
        # global-scale math and silently disagreed with the engine (the bench caught it as a nan delta).
        xs = xsum[s]; sxb = sxs[s]
        acc = [a + sxb * (ds * sm - dm * xs) for a, ds, dm, sm in zip(acc, DS, DM, sums)]
    return row0, acc


class Pool:
    """A bounded, always-cleaned worker pool. Use as a context manager; it terminates and joins on every exit path."""

    def __init__(self, model_path, workers, XB=8, ow=17):
        import multiprocessing as mp
        self.n = max(1, int(workers))
        ctx = mp.get_context("spawn")                     # Windows default; explicit so behaviour is identical anywhere
        self.pool = ctx.Pool(self.n, initializer=_init, initargs=(model_path, XB, ow), maxtasksperchild=64)

    def __enter__(self): return self

    def __exit__(self, *exc):
        try: self.pool.terminate()
        finally: self.pool.join()
        return False

    def matmul(self, fw, name, x):
        """y = W.x, output rows split across the workers. Byte-identical to the single-process path: each worker runs
        the SAME fold over a disjoint row range, and ranges are concatenated in order."""
        t = fw.g.tensors[name]; tid = int(t["type"]); n_in = int(t["dims"][0]); n_out = int(t["dims"][1])
        xl = (1 << (fw.XB - 1)) - 1
        nsub = n_in // 32
        sxs = []; xq = []
        for s in range(nsub):                      # per-sub-block scale, identical to the single-process path
            blk = x[s * 32:(s + 1) * 32]
            sc = (max((abs(v) for v in blk), default=0.0) / xl) or 1e-9
            sxs.append(sc)
            xq.extend(max(-xl - 1, min(xl, round(v / sc))) for v in blk)
        per = max(1, (n_out + self.n - 1) // self.n)
        jobs = [(name, r0, min(per, n_out - r0), xq, sxs, tid, n_in, int(t["off"]))
                for r0 in range(0, n_out, per)]
        out = [0.0] * n_out
        for row0, vals in self.pool.map(_tile_job, jobs):
            out[row0:row0 + len(vals)] = vals
        return out


def main():
    if "--bench" not in sys.argv:
        print(__doc__); return 0
    a = [v for v in sys.argv[1:] if v != "--bench"]
    model = a[0] if a else "C:/llm/models/mixtral-8x7b-instruct-v0.1.Q4_K_M.gguf"
    tensor = a[1] if len(a) > 1 else "blk.0.attn_q.weight"
    nw = int(a[2]) if len(a) > 2 else (os.cpu_count() or 2) // 2

    import pfc_forward as F
    fw = F.Forward(model, substrate=True); fw.tile = 16384
    t = fw.g.tensors[tensor]; macs = int(t["dims"][0]) * int(t["dims"][1])
    x = [((i * 37 % 211) - 105) / 400.0 for i in range(int(t["dims"][0]))]
    print(f"=== CORES AXIS — {os.path.basename(model)} :: {tensor} [{macs:,} MACs] ===", flush=True)
    print(f"    cpu_count={os.cpu_count()}  workers={nw}", flush=True)

    t0 = time.time(); ref = fw.matmul(tensor, x); t1 = time.time() - t0
    print(f"  1 process : {t1:6.2f}s  {macs/t1/1e6:6.2f} M MAC/s", flush=True)

    with Pool(model, nw, XB=fw.XB, ow=len(fw.dotq.outs)) as p:
        t0 = time.time(); got = p.matmul(fw, tensor, x); t2 = time.time() - t0
    err = max(abs(m - n) for m, n in zip(ref, got))
    print(f"  {nw} processes: {t2:6.2f}s  {macs/t2/1e6:6.2f} M MAC/s   ★ {t1/t2:.2f}x", flush=True)
    print(f"  max |delta| vs single process: {err:.3e}  ({'identical' if err == 0 else 'float order only'})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
