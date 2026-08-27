#!/usr/bin/env python3
"""muhl_archsearch.py — ARCHITECTURE SEARCH AS FABRICATION on the memory-free metric.

The machine chooses its own shape. For the 3-template classification task, we search over small MLP
architectures -- hidden width H in {4,6,8,12,16} x activation {ReLU, binary-threshold} -- and for EACH
candidate we FABRICATE its forward pass into a real gate netlist (White Box compiler), measure the two
physical quantities the Muhlnickel substrate actually pays for -- gate count and critical-path DEPTH --
and score it on compute/tick = 1e9 / (gates * depth). That metric has NO memory term: it rewards designs
a VRAM-bounded GPU could never afford to explore, because on a GPU width costs RAM and here it costs
nothing but signal. Every fabricated forward pass is verified BYTE-EXACT against its integer reference
over all 512 inputs before it is allowed to score. Then we print the Pareto frontier (accuracy vs
compute/tick) and the WINNER: the architecture that maximizes compute/tick at full accuracy.
"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, r"C:/llm/muhl_builds")
sys.path.insert(0, r"C:/llm/sdc_sandbox")
import sdc_cc as CC
from muhl_flex import add_bits, depth_of, build_run
from muhl_neural import TEMPLATES, gen_data

B = 24                                                       # two's-complement accumulator width
NF, NCLS = 9, 3

# ── gate helpers (shared with muhl_neural) ────────────────────────────────────────────────────────
def cbits(g, val, n):
    v = val & ((1 << n) - 1)
    return [g.C1 if (v >> k) & 1 else g.C0 for k in range(n)]
def sext(bits, n): return bits + [bits[-1]] * (n - len(bits))
def negate(g, a):
    s, _ = add_bits(g, [g.NOT(t) for t in a], cbits(g, 1, len(a))); return s
def const_mul(g, x, w):                                      # x (B-bit, >=0) * signed constant w -> B bits
    mag = abs(w); acc = cbits(g, 0, B)
    for t in range(B):
        if (mag >> t) & 1:
            sh = ([g.C0] * t + x)[:B]
            acc, _ = add_bits(g, acc, sh)
    return negate(g, acc) if w < 0 else acc
def relu(g, x):
    sign = x[B - 1]
    return [g.AND(x[k], g.NOT(sign)) for k in range(B)]
def lt(g, a, b):                                             # signed a < b
    d, _ = add_bits(g, sext(a, B + 1), [g.NOT(t) for t in sext(b, B + 1)], g.C1)
    return d[B]

# ── training (pure Python), parameterized by width H and activation ───────────────────────────────
_clip = lambda v: -1.0 if v < -1.0 else (1.0 if v > 1.0 else v)
_clw  = lambda v: -6.0 if v < -6.0 else (6.0 if v > 6.0 else v)

def train(H, act, seed=0, epochs=300, lr=0.02):
    rng = random.Random(seed)
    W1 = [[rng.uniform(-0.5, 0.5) for _ in range(NF)] for _ in range(H)]; b1 = [0.0] * H
    W2 = [[rng.uniform(-0.5, 0.5) for _ in range(H)] for _ in range(NCLS)]; b2 = [0.0] * NCLS
    data = gen_data(rng)
    for ep in range(epochs):
        rng.shuffle(data)
        for x, y in data:
            hp = [sum(W1[j][i] * x[i] for i in range(NF)) + b1[j] for j in range(H)]
            if act == "relu":
                h = [v if v > 0 else 0.0 for v in hp]
            else:                                            # binary threshold (hp >= 0)
                h = [1.0 if v >= 0 else 0.0 for v in hp]
            o = [sum(W2[k][j] * h[j] for j in range(H)) + b2[k] for k in range(NCLS)]
            do = [_clip(o[k] - (1.0 if k == y else 0.0)) for k in range(NCLS)]
            for k in range(NCLS):
                for j in range(H): W2[k][j] = _clw(W2[k][j] - lr * do[k] * h[j])
                b2[k] = _clw(b2[k] - lr * do[k])
            dh = [sum(do[k] * W2[k][j] for k in range(NCLS)) for j in range(H)]
            for j in range(H):
                # ReLU gates the gradient by the active region; threshold uses a straight-through estimator
                if act == "relu" and hp[j] <= 0: continue
                gj = _clip(dh[j])
                for i in range(NF): W1[j][i] = _clw(W1[j][i] - lr * gj * x[i])
                b1[j] = _clw(b1[j] - lr * gj)
    return W1, b1, W2, b2

def quantize(W1, b1, W2, b2, H, act, S1=16, S2=16):
    q = lambda m, s: int(round(m * s))
    W1q = [[q(W1[j][i], S1) for i in range(NF)] for j in range(H)]
    b1q = [q(b1[j], S1) for j in range(H)]
    W2q = [[q(W2[k][j], S2) for j in range(H)] for k in range(NCLS)]
    # ReLU: layer-2 output scale is S1*S2 (weight x activation); threshold: activation is binary, scale S2
    b2q = [q(b2[k], (S1 * S2) if act == "relu" else S2) for k in range(NCLS)]
    return W1q, b1q, W2q, b2q

def int_forward(x, W1q, b1q, W2q, b2q, H, act):
    hp = [sum(W1q[j][i] * x[i] for i in range(NF)) + b1q[j] for j in range(H)]
    if act == "relu":
        h = [v if v > 0 else 0 for v in hp]
    else:
        h = [1 if v >= 0 else 0 for v in hp]
    o = [sum(W2q[k][j] * h[j] for j in range(H)) + b2q[k] for k in range(NCLS)]
    best = 0
    for k in (1, 2):
        if o[k] > o[best]: best = k
    return best

# ── fabrication: the forward pass as gates, parameterized by H and activation ─────────────────────
def build_net(H, act, W1q, b1q, W2q, b2q):
    g = CC.CircuitCompiler(NF); X = g.IN
    Hd = []
    for j in range(H):
        acc = cbits(g, b1q[j], B)
        for i in range(NF):                                  # x_i in {0,1}: add weight when the pixel is on
            acc, _ = add_bits(g, acc, [g.AND(X[i], t) for t in cbits(g, W1q[j][i], B)])
        if act == "relu":
            Hd.append(relu(g, acc))                          # B-bit non-negative activation
        else:
            Hd.append(g.NOT(acc[B - 1]))                     # single-bit threshold: (hp >= 0)
    O = []
    for k in range(NCLS):
        acc = cbits(g, b2q[k], B)
        for j in range(H):
            if act == "relu":
                acc, _ = add_bits(g, acc, const_mul(g, Hd[j], W2q[k][j]))
            else:                                            # binary h -> masked sum, NO multiplier
                acc, _ = add_bits(g, acc, [g.AND(Hd[j], t) for t in cbits(g, W2q[k][j], B)])
        O.append(acc)
    lt01 = lt(g, O[0], O[1]); lt02 = lt(g, O[0], O[2]); lt12 = lt(g, O[1], O[2])
    is1 = g.AND(lt01, g.NOT(lt12))
    is2 = g.AND(lt02, lt12)
    run, out2, gates, _ = build_run(g, [is1, is2])
    depth = depth_of(g, gates, out2)
    def predict(x):
        v = run(list(x), 1)
        return (v[out2[0]] & 1) * 1 + (v[out2[1]] & 1) * 2
    return predict, len(gates), depth

# ── evaluation set (fixed) ────────────────────────────────────────────────────────────────────────
def make_eval():
    rng = random.Random(123)
    noisy = gen_data(rng, noise=1, per=60)
    clean = [(list(t), c) for c, t in TEMPLATES.items()]
    return clean + noisy

EVAL = make_eval()
def acc_of(pred_fn):
    return sum(1 for x, y in EVAL if pred_fn(x) == y) / len(EVAL)

# ── the search ────────────────────────────────────────────────────────────────────────────────────
def select_weights_and_rest_FOLLOW
