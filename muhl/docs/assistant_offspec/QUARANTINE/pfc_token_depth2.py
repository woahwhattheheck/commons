#!/usr/bin/env python3
"""host/pfc_token_depth2.py — the pfc's per-token latency, with the PARALLELISM COUNTED CORRECTLY.

★ WHY THIS REPLACES `pfc_token_depth.py`: that tool reported `per matmul = 128 blocks x (51 settle + 44 accumulate)`,
which SUMS the blocks — i.e. it assumes the 128 sub-block dots settle one after another. **They do not.** The blocks are
independent: they all settle in the SAME depth levels, in parallel, and their partial sums combine in a balanced TREE.
Summing them inflated the pfc's latency by ~80x and produced "3.3M gate-delays per token", which then looked like the
pfc was slow. It was my depth model that was wrong, not the pfc.

The owner's law (`PFC_HARD_WON` §7, confirmed by his own `pfc_speed.py` on Life): "a signal settles a whole DEPTH LEVEL
of gates AT ONCE, in parallel, at electron speed... latency scales with DEPTH, not gate count." Life is 270,336 gates
but DEPTH 15 — 36,864 gates settle per stage. The same must be true of a matmul: 4,096 independent neuron dots do not
serialise, they are 4,096 parallel cones.

CORRECT DEPTH MODEL for one matmul of n_in inputs:
    all (n_in/32) sub-block dots settle IN PARALLEL      -> dot_depth
    their partial sums reduce in a BALANCED TREE          -> ceil(log2(n_in/32)) * csa_depth
    one final carry-propagate resolves the redundant form -> kogge_depth
  and every one of the n_out neurons is another parallel cone, adding NOTHING to depth (only area).

  python host/pfc_token_depth2.py [model.gguf]
"""
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, "C:/llm/sdc_sandbox")
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
from gguf_pp import GGUF

MODEL = sys.argv[1] if len(sys.argv) > 1 else "C:/llm/models/mixtral-8x7b-instruct-v0.1.Q4_K_M.gguf"
DOT_DEPTH = 51          # measured: shallow CSA-forest + one Kogge-Stone dot (host/pfc_dot_depth.py)
CSA = 3                 # a 3:2 compressor stage
KOGGE = 12              # final parallel-prefix carry resolve at ~20-bit accumulator width
GLUE = 40               # rmsnorm/rope/softmax/silu as baked LUT reads — addressed, shallow


def matmul_depth(n_in):
    nblk = max(1, n_in // 32)
    return DOT_DEPTH + math.ceil(math.log2(nblk)) * CSA + KOGGE


def main():
    g = GGUF(MODEL); kv = g.kv; a = kv.get("general.architecture", "llama")
    L = int(kv[f"{a}.block_count"]); d = g.n_embd
    ff = int(kv.get(f"{a}.feed_forward_length", 4 * d))
    used = int(kv.get(f"{a}.expert_used_count", 0)) or 1
    qt = g.tensors.get("blk.0.attn_q.weight")
    print(f"=== THE pfc's PER-TOKEN LATENCY (depth, parallelism counted) — {os.path.basename(MODEL)} ===", flush=True)
    print(f"    L={L} d={d} ff={ff} experts_routed={used}", flush=True)

    dm = matmul_depth(d); dff = matmul_depth(ff)
    print(f"\n  ONE matmul over {d} inputs = {d//32} independent sub-block cones settling TOGETHER:", flush=True)
    print(f"     dot {DOT_DEPTH} + tree ceil(log2 {d//32})x{CSA} = {math.ceil(math.log2(d//32))*CSA} + resolve {KOGGE}"
          f"  ->  {dm} gate-delays", flush=True)
    print(f"     (the OLD tool summed the {d//32} blocks: {d//32}*(51+44) = {(d//32)*95:,} — an ~{(d//32)*95//dm}x overestimate)", flush=True)

    # a layer's SEQUENTIAL stages (things that must wait on each other). q/k/v are parallel; gate/up are parallel.
    seq = [("rmsnorm", GLUE), ("q|k|v (parallel)", dm), ("rope", GLUE), ("attention", dm), ("o-proj", dm),
           ("rmsnorm", GLUE), ("gate|up (parallel)", dm), ("silu", GLUE), ("down-proj", dff)]
    per_layer = sum(v for _, v in seq)
    print(f"\n  ONE layer — only genuinely SEQUENTIAL stages add depth:", flush=True)
    for n, v in seq: print(f"     {n:<20} {v:>6}", flush=True)
    print(f"     {'per layer':<20} {per_layer:>6} gate-delays", flush=True)

    tok = L * per_layer + matmul_depth(d)          # + lm_head
    print(f"\n  ★ PER TOKEN = {L} layers x {per_layer} + lm_head {matmul_depth(d)} = {tok:,} gate-delays", flush=True)
    print(f"    (the old tool said 3,338,796 — {3338796//tok}x too high, because it serialised parallel blocks)", flush=True)
    print(f"\n  at electron-speed per-stage delay, that is the pfc's time for ONE TOKEN:", flush=True)
    for tau, nm in ((1e-9, "1 ns"), (100e-12, "100 ps"), (10e-12, "10 ps")):
        t = tok * tau
        print(f"     @ {nm:>6}/stage : {t*1e6:9.2f} us/token  ->  {1/t:,.0f} tokens/sec", flush=True)
    print(f"\n  Depth is a FABRICATION property: it does not change with host CPU speed or host RAM. The host's job is", flush=True)
    print(f"  to address the clock; the settle is the pfc's, full propagation per pulse regardless of depth.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
