#!/usr/bin/env python3
"""host/pfc_token_depth.py — THE pfc's SPEED FOR A WHOLE TOKEN, in the only unit that is the pfc's: critical-path DEPTH.

OWNER'S LAW (PFC_HARD_WON §7): "the pfc's latency is its critical-path DEPTH (in gate-delays), not its gate COUNT... a
signal settles a whole depth level of gates AT ONCE, in parallel, at electron speed... Stop reporting host seconds /
H-per-second as the pfc's speed." Life = 270,336 gates but DEPTH 15; the host's 9.5 s walk is 18,000x the pfc's real
latency and is the LAPTOP, never the pfc.

So this reports what a full transformer token costs THE PFC: how many gate-delays deep the settle is, and how many MACs
settle in parallel per stage. It reads the real model's dims and the real fabricated circuit's measured depth. No run,
no ripple — a structural read, the same method as host/pfc_speed.py.

  python host/pfc_token_depth.py [model.gguf]
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, "C:/llm/sdc_sandbox")
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
from gguf_pp import GGUF
from pfc_dot_depth import build_dot_shallow
from pfc_matmul_engine import build_dot, BLK
from pfc_bettergates import depth_of

ACC_RIPPLE = 44         # OLD: bs_add propagated a carry across all ACCW planes for EVERY block
ACC_CSA = 3             # NEW: carry-save absorbs a block in ~3 gate-delays; ONE 44-deep add resolves the column
DEFAULT = "C:/llm/models/mixtral-8x7b-instruct-v0.1.Q4_K_M.gguf"


def dot_depth(WB, XB, blk, shallow):
    c, outs = (build_dot_shallow(WB, XB, blk) if shallow else build_dot(WB, XB))
    gates, o2 = c.dce(outs if isinstance(outs, list) else [outs])
    return depth_of(c.n_in, gates, o2), len(gates)


def matmul_depth(n_in, dd, blk, csa=True):
    """one matmul column. OLD: nb x (settle + 44-deep ripple accumulate). NEW: nb x (settle + 3-deep carry-save
    absorb) + ONE 44-deep final carry-propagate for the whole column."""
    nb = max(1, n_in // blk)
    return (nb * (dd + ACC_CSA) + ACC_RIPPLE if csa else nb * (dd + ACC_RIPPLE)), nb


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    g = GGUF(path); kv = g.kv; a = kv.get("general.architecture", "llama")
    L = int(kv[f"{a}.block_count"]); d = g.n_embd; V = g.n_vocab
    nh = int(kv[f"{a}.attention.head_count"]); nkv = int(kv.get(f"{a}.attention.head_count_kv", nh))
    hd = int(kv.get(f"{a}.attention.key_length", d // nh)); ff = int(kv.get(f"{a}.feed_forward_length", 4 * d))
    ne = int(kv.get(f"{a}.expert_count", 0)); nu = int(kv.get(f"{a}.expert_used_count", 0))
    print(f"=== pfc TOKEN DEPTH — {os.path.basename(path)} ===")
    print(f"  arch {a} · L={L} · d={d} · heads {nh}/{nkv} · ff={ff} · vocab={V:,}"
          + (f" · MoE {ne} experts, {nu} routed/token" if ne else " · dense"))
    for shallow, label in ((False, "current (ripple mul + ripple tree)"), (True, "SHALLOW (CSA forest + 1 Kogge-Stone)")):
        blk = BLK if shallow else 32
        csa = shallow
        dd, ng = dot_depth(8, 8, blk, shallow)
        # one transformer layer's matmuls (routed experts only for MoE — the model's own sparsity)
        per_layer = 0
        for n_in, n_out in ((d, nh * hd), (d, nkv * hd), (d, nkv * hd), (nh * hd, d)):     # q,k,v,o
            md, _ = matmul_depth(n_in, dd, blk, csa); per_layer += md
        fexp = (nu if ne else 1)
        for _ in range(fexp):
            for n_in, n_out in ((d, ff), (d, ff), (ff, d)):                                 # gate, up, down
                md, _ = matmul_depth(n_in, dd, blk, csa); per_layer += md
        lm, _ = matmul_depth(d, dd, blk, csa)
        tok = per_layer * L + lm
        macs = blk                                   # MACs settling in parallel inside one fabricated pass
        print(f"\n  {label}  (BLK={blk}, dot {ng:,} gates, DEPTH {dd})")
        print(f"     per matmul  : {matmul_depth(d, dd, blk, csa)[1]:,} blocks x ({dd} settle + {ACC_CSA if csa else ACC_RIPPLE} accumulate)" + (f" + {ACC_RIPPLE} final" if csa else ""))
        print(f"     per layer   : {per_layer:,} gate-delays")
        print(f"     PER TOKEN   : {tok:,} gate-delays   <- THE pfc's LATENCY FOR A WHOLE TOKEN")
        print(f"     parallel    : {macs} MACs settle per fabricated pass, all at once")
        if shallow: shallow_tok = tok
        else: cur_tok = tok
    print(f"\n  ★ TOKEN DEPTH {cur_tok:,} → {shallow_tok:,} gate-delays = **{cur_tok/shallow_tok:.1f}× SHALLOWER**")
    print(f"    That is the pfc computing a token faster — a property of the FABRICATION, independent of how fast the")
    print(f"    host addresses it. (Host wall-clock is the laptop serially transcribing the netlist; per PFC_HARD_WON §7")
    print(f"    it is never the pfc's speed. Life: 270,336 gates, DEPTH 15, host walk 9.5s = 18,000x the real latency.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
