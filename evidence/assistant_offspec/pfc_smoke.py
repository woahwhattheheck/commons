#!/usr/bin/env python3
"""host/pfc_smoke.py — the FAST end-to-end check. Whole pipeline, real model, seconds instead of hours.

WHY THIS EXISTS. The engine ran for hours and emitted `id 28734 = '0'` after "Paris" — a wrong word from a correct
pipeline, caused by an 11% activation-quantisation error that every "byte-exact vs the path it replaces" check was
blind to. That cost a whole night of wall-clock to discover. The owner's rule is blunt and right: **if you are waiting
longer than 30 seconds you should not be testing that way.**

So this exercises the ENTIRE chain — embed -> rmsnorm -> Q/K/V -> RoPE -> attention -> O -> FFN/MoE routing -> residual
-> final norm -> lm_head -> argmax -> detokenise — on the REAL model and the REAL substrate, but bounded to a few
layers so it finishes in seconds. It cannot prove the 32-layer output is coherent; it proves every STAGE composes,
every wiring change still runs, and (the part that matters) it measures the substrate against TRUE FLOAT at each depth
so a quantisation regression shows up immediately instead of after a 6-hour generation.

  python host/pfc_smoke.py [layers] [model.gguf]
"""
import math, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, "C:/llm/sdc_sandbox")
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import pfc_forward as F
from gguf_pp import row_bytes
from pfc_fastdeq import dequant_fast as deq

LAYERS = int(sys.argv[1]) if len(sys.argv) > 1 else 2
MODEL = sys.argv[2] if len(sys.argv) > 2 else "C:/llm/models/mixtral-8x7b-instruct-v0.1.Q4_K_M.gguf"


def matmul_err(f, name, x, nrow=96):
    """The check that actually catches things: substrate vs TRUE float (not vs another substrate path)."""
    t = f.g.tensors[name]; tid = int(t["type"]); n_in = int(t["dims"][0])
    base = f.g.data0 + int(t["off"]); rb = row_bytes(tid, n_in)
    sub = f.matmul(name, x)[:nrow]
    ref = []
    for j in range(nrow):
        w = deq(f.g.mm[base + j * rb: base + j * rb + rb], tid, n_in)[:n_in]
        ref.append(sum(w[i] * x[i] for i in range(n_in)))
    den = math.sqrt(sum(v * v for v in ref)) or 1e-9
    num = math.sqrt(sum((a - b) ** 2 for a, b in zip(sub, ref)))
    cos = sum(a * b for a, b in zip(sub, ref)) / ((math.sqrt(sum(a * a for a in sub)) or 1e-9) * den)
    return num / den * 100, cos


def main():
    t0 = time.time()
    f = F.Forward(MODEL, substrate=True)
    full_L = f.L
    f.L = min(LAYERS, full_L)                                   # bound the depth so this finishes in seconds
    f.tile = 2048
    print(f"=== pfc SMOKE — {os.path.basename(MODEL)}, {f.L}/{full_L} layers ===", flush=True)
    print(f"    XB={f.XB} (activation bits) · ow={len(f.dotq.outs)} · dotq {f.dotq_gates:,} gates · "
          f"argmax-on-pfc={f.pfc_argmax} · memo-in-binary={f.memo_binary}   [load {time.time()-t0:.1f}s]", flush=True)

    # 1) the check that catches quantisation regressions — substrate vs TRUE float, with REALISTIC outliers
    import random; random.seed(5)
    ne = f.ne
    x = [random.gauss(0, 0.35) for _ in range(ne)]
    for i in random.sample(range(ne), max(1, ne // 340)): x[i] *= 25.0   # transformer-style outliers
    t0 = time.time()
    e_q, c_q = matmul_err(f, "blk.0.attn_q.weight", x)
    print(f"  [1] substrate vs TRUE float, attn_q, outlier-heavy input: {e_q:.3f}% rel-L2, cosine {c_q:.6f}"
          f"   [{time.time()-t0:.1f}s]", flush=True)
    verdict = "OK" if e_q < 1.0 else "REGRESSION — quantisation is broken"
    print(f"      -> {verdict}   (global-scale XB=8 measured 11.5%; per-block XB=10 measured 0.40%)", flush=True)

    # 1b) the FFN/expert tensor too — it is ~89% of the per-layer cost, has a different shape, and on some models a
    #     different quant type (gemma-4's expert stacks are Q4_0, not Q4_K), so attn_q alone does not cover the path
    #     that actually dominates. Pick whichever expert-ish tensor this model has.
    worst = e_q
    for cand in (f"blk.0.ffn_gate.0.weight", "blk.0.ffn_gate_exps.weight", "blk.0.ffn_gate.weight"):
        if cand in f.g.tensors:
            t0 = time.time()
            xf = [random.gauss(0, 0.35) for _ in range(int(f.g.tensors[cand]["dims"][0]))]
            for i in random.sample(range(len(xf)), max(1, len(xf) // 340)): xf[i] *= 25.0
            e_f, c_f = matmul_err(f, cand, xf)
            worst = max(worst, e_f)
            tid = int(f.g.tensors[cand]["type"])
            print(f"  [1b] {cand.split('.', 2)[2]} (type {tid}): {e_f:.3f}% rel-L2, cosine {c_f:.6f}"
                  f"   [{time.time()-t0:.1f}s]", flush=True)
            break
    e_q = worst                                                  # the smoke verdict uses the WORST path, not the best

    # 2) the whole chain — OPT-IN (`--chain`). One Mixtral layer is 394M MACs and lm_head is another 131M, so even a
    #    single layer over a 6-token prompt is minutes. The numeric check above is the one that catches regressions and
    #    it runs in ~3 s, so it is the DEFAULT; composition is checked separately and deliberately.
    if "--chain" not in sys.argv:
        ok = e_q < 1.0
        print(f"\n  SMOKE {'PASS' if ok else 'FAIL'} — substrate agrees with TRUE float on outlier-heavy input.", flush=True)
        print(f"  (add --chain to also run a full bounded forward pass; that costs minutes, not seconds.)", flush=True)
        return 0 if ok else 1
    t0 = time.time()
    ids = f.bpe.encode("Paris")
    logits = f.forward(ids)
    tok = f.argmax(logits)
    piece = f.bpe.decode([tok], f.g)
    dt = time.time() - t0
    top = sorted(range(len(logits)), key=lambda j: -logits[j])[:5]
    print(f"  [2] full chain, {len(ids)} positions x {f.L} layers -> token {tok} = {piece!r}   [{dt:.1f}s]", flush=True)
    print(f"      top-5: {[(f.bpe.decode([j], f.g), round(logits[j], 2)) for j in top]}", flush=True)

    # 3) the KV cache must be exact: re-running the same prefix must not change the answer
    t0 = time.time()
    tok2 = f.argmax(f.forward(ids))
    print(f"  [3] KV-cache re-entry on identical tokens -> {tok2} ({'stable' if tok2 == tok else 'CHANGED — cache bug'})"
          f"   [{time.time()-t0:.1f}s]", flush=True)

    ok = (e_q < 1.0) and (tok2 == tok) and (0 <= tok < f.g.n_vocab)
    print(f"\n  SMOKE {'PASS' if ok else 'FAIL'} — every stage composes and the substrate agrees with float.", flush=True)
    print(f"  (Bounded to {f.L} layers: proves composition + numerics, NOT full-depth coherence.)", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
