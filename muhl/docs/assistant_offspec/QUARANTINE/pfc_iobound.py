#!/usr/bin/env python3
"""host/pfc_iobound.py — is a matmul CPU-bound or DISK-bound? The answer decides which lever is worth pulling.

WHY THIS MATTERS, AND WHY I HAD IT BACKWARDS. I have been treating resident RAM as something to keep LOW (flat-RAM is
the pfc's containment property, and it is real). But `BIG_MODEL_RAM.md` states the throughput side plainly:

    "the bias is the opposite of 'minimize': PUSH RAM USAGE AS HIGH AS AVAILABLE, because more resident = better.
     per-token time = compute + (1 - r) * W / B_disk, where r = fraction of weights resident.
     r -> 1 drives the streaming term -> 0 -> compute-bound -> fastest."

Both are true and they are about different things: **flat resident RAM is the pfc's cost property** (the gates and the
model never become resident *as the compute's working set*), while **the OS page cache holding weight bytes is a SPEED
knob you want turned UP**. Conflating them led me to treat a 2.9 GB working set as a problem to explain away instead of
a number to push higher.

On this box Mixtral is 26 GB against 7.2 GB usable, so r is roughly 11% — meaning most weight bytes may be re-read from
SSD every single position. If that is where the time goes, then no amount of gate/fold optimisation helps and the right
levers are locality and model choice. If it is CPU, the opposite. Nobody had measured which.

METHOD: time the SAME matmul twice — once with its bytes cold-ish, once immediately after (pages hot). A large hot/cold
ratio means disk-bound; a ratio near 1 means CPU-bound and the page cache is already doing its job.

  python host/pfc_iobound.py [model.gguf]
"""
import os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, "C:/llm/sdc_sandbox")
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import pfc_forward as F
from gguf_pp import row_bytes

MODEL = sys.argv[1] if len(sys.argv) > 1 else "C:/llm/models/mixtral-8x7b-instruct-v0.1.Q4_K_M.gguf"


def touch(mm, base, nbytes, step=4096):
    """Walk the byte range so the pages are resident, and report how long the pure READ took (no arithmetic)."""
    t0 = time.time(); s = 0
    for o in range(base, base + nbytes, step): s += mm[o]
    return time.time() - t0, s


def main():
    f = F.Forward(MODEL, substrate=True); f.tile = 2048
    print(f"=== CPU-BOUND or DISK-BOUND? — {os.path.basename(MODEL)} ===", flush=True)
    gb = os.path.getsize(MODEL) / 1e9
    try:
        import ctypes
        class MS(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        m = MS(); m.dwLength = ctypes.sizeof(MS); ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        print(f"    model {gb:.1f} GB · RAM {m.ullTotalPhys/1e9:.1f} GB total, {m.ullAvailPhys/1e9:.2f} GB free"
              f"  ->  best-case r <= {min(1.0, m.ullTotalPhys/1e9/gb):.0%}", flush=True)
    except Exception:
        print(f"    model {gb:.1f} GB", flush=True)

    # pick two same-shaped tensors from DIFFERENT layers so neither is warmed by the other
    names = [n for n in (f"blk.{i}.attn_q.weight" for i in range(0, 32)) if n in f.g.tensors][:2]
    if len(names) < 2:
        print("  need two attn_q tensors"); return 1
    t = f.g.tensors[names[0]]
    n_in = int(t["dims"][0]); n_out = int(t["dims"][1]); macs = n_in * n_out
    rb = row_bytes(int(t["type"]), n_in); span = n_out * rb
    x = [((i * 37 % 211) - 105) / 400.0 for i in range(n_in)]
    print(f"    each tensor: {span/1e6:.0f} MB of weight bytes, {macs:,} MACs", flush=True)

    # A) a tensor whose pages we have NOT touched this process
    nm = names[1]
    tb = f.g.tensors[nm]; base = f.g.data0 + int(tb["off"])
    t_read_cold, _ = touch(f.g.mm, base, span)
    t0 = time.time(); f.matmul(nm, x); t_cold = time.time() - t0

    # B) same tensor again — now its pages are hot
    t_read_hot, _ = touch(f.g.mm, base, span)
    t0 = time.time(); f.matmul(nm, x); t_hot = time.time() - t0

    print(f"\n  pure byte-read of {span/1e6:.0f} MB : cold {t_read_cold*1000:7.0f} ms   hot {t_read_hot*1000:7.0f} ms"
          f"   ({span/1e6/max(t_read_cold,1e-9):.0f} vs {span/1e6/max(t_read_hot,1e-9):.0f} MB/s)", flush=True)
    print(f"  full matmul               : 1st  {t_cold:7.2f} s    2nd {t_hot:7.2f} s", flush=True)
    ratio = t_cold / t_hot if t_hot else 0
    io_share = max(0.0, (t_cold - t_hot)) / t_cold if t_cold else 0
    print(f"  cold/hot ratio {ratio:.2f}  ->  at most {io_share:.0%} of the first pass was page-fault/IO", flush=True)
    print(f"  read time is {t_read_cold/max(t_cold,1e-9):.1%} of the matmul, so the matmul is "
          f"{'DISK-bound — locality and model choice are the levers' if io_share > 0.35 else 'CPU-bound — the fold/drive is the lever, and page cache is already doing its job'}",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
