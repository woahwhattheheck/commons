#!/usr/bin/env python3
"""host/pfc_layerbench.py — the FAST ITERATION LOOP for the lever stack (owner: "implement and experiment so your FIRST
test isn't slow — if it's slow keep building").

A full Mixtral token is ~398M block-dots; waiting ~16 min per lever trial is not an experiment loop, it's a stall. So
this runs ONE real transformer layer on the real model with the real engine, reports the per-layer cost + how much each
COUNT lever actually removes, and extrapolates the whole token. Tune levers here in ~a minute, then run the real thing.

Reports, per config: block-dots actually FOLDED (after sparse-cone + threshold-prune), blocks PRUNED, wall-seconds for
the layer, extrapolated s/token, and the routed-expert accounting. Resident RAM printed so the flat-RAM property is
visible while tuning.

  python host/pfc_layerbench.py [model.gguf] [xprune=2] [tile=8192] [WB=8]
"""
import os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, "C:/llm/sdc_sandbox")
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
from pfc_forward import Forward, Meter, resident_mb

DEFAULT = "C:/llm/models/mixtral-8x7b-instruct-v0.1.Q4_K_M.gguf"


def one_layer(f, tokens, li=0):
    """run exactly transformer block `li` on the real model, timed, with the meter reset — the unit of the lever loop."""
    xs = [f.g.deq_row(t) for t in tokens]
    Meter.reset(); t0 = time.time()
    anw = f.normw(f"blk.{li}.attn_norm.weight")
    hs = [f.rmsnorm(x, anw) for x in xs]
    f.matmul_batch(f"blk.{li}.attn_q.weight", hs, "q")
    f.matmul_batch(f"blk.{li}.attn_k.weight", hs, "k")
    f.matmul_batch(f"blk.{li}.attn_v.weight", hs, "v")
    f.matmul_batch(f"blk.{li}.attn_output.weight", hs, "o")
    fnw = f.normw(f"blk.{li}.ffn_norm.weight")
    h2s = [f.rmsnorm(x, fnw) for x in xs]
    if f.n_expert > 0:                                        # MoE: only the ROUTED experts ripple (the α lever)
        logits = f.matmul(f"blk.{li}.ffn_gate_inp.weight", h2s[-1], "router")
        order = sorted(range(len(logits)), key=lambda j: -logits[j])[:max(1, f.n_expert_used)]
        for j in order:
            gt = f.matmul(f"blk.{li}.ffn_gate.{j}.weight", h2s[-1], "e_gate")
            up = f.matmul(f"blk.{li}.ffn_up.{j}.weight", h2s[-1], "e_up")
            act = [f.glue.silu(gt[i]) * up[i] for i in range(len(gt))]
            f.matmul(f"blk.{li}.ffn_down.{j}.weight", act, "e_down")
    else:
        gts = f.matmul_batch(f"blk.{li}.ffn_gate.weight", h2s, "gate")
        ups = f.matmul_batch(f"blk.{li}.ffn_up.weight", h2s, "up")
        acts = [[f.glue.silu(gts[p][i]) * ups[p][i] for i in range(len(gts[p]))] for p in range(len(h2s))]
        f.matmul_batch(f"blk.{li}.ffn_down.weight", acts, "down")
    return time.time() - t0, (order if f.n_expert > 0 else None)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    xprune = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    tile = int(sys.argv[3]) if len(sys.argv) > 3 else 8192
    WB = int(sys.argv[4]) if len(sys.argv) > 4 else 8
    print(f"=== LAYER BENCH — {os.path.basename(path)}  (WB={WB} tile={tile} xprune={xprune}) ===", flush=True)
    f = Forward(path, WB=WB, XB=8, tile=tile, memo=False, substrate=True, sharedx=True, xprune=xprune)
    print(f"  arch={f.arch} L={f.L} d={f.ne} experts={f.n_expert}/{f.n_expert_used} vocab={f.g.n_vocab} "
          f"dot={f.gates_per_sweep:,} gates", flush=True)
    print(f"  resident baseline {resident_mb():.1f} MB (model {os.path.getsize(path)/1e9:.1f} GB, never loaded)\n", flush=True)
    ids = f.bpe.encode("The capital of France is")
    dt, order = one_layer(f, ids, 0)
    folded = Meter.ripple // max(1, f.gates_per_sweep)          # gate-sweeps = folded block-dot groups
    tot_blocks = folded + Meter.pruned
    prune_pct = 100.0 * Meter.pruned / max(1, tot_blocks)
    print(f"  LAYER 0: {dt:.1f}s  routed experts {order}", flush=True)
    print(f"    folded block-groups {folded:,} | PRUNED {Meter.pruned:,} ({prune_pct:.1f}% of {tot_blocks:,}) "
          f"= ripple never spent", flush=True)
    print(f"    {Meter.line()}", flush=True)
    print(f"    resident now {resident_mb():.1f} MB", flush=True)
    # extrapolate: L layers + the lm_head projection
    lm_bd = f.g.n_vocab * (f.ne // 32)
    rate = (folded * f.gates_per_sweep) / max(1e-9, dt) / f.gates_per_sweep  # block-groups/s
    est = dt * f.L + (lm_bd / max(1.0, rate * 1.0)) * 0.0
    print(f"\n  ⇒ EXTRAPOLATED: {dt:.1f}s x {f.L} layers = {dt*f.L/60:.1f} min/token (+ lm_head {lm_bd/1e6:.1f}M bd)", flush=True)
    print(f"    prune is the free COUNT lever here; raise xprune until the emitted token changes, then back off one.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
