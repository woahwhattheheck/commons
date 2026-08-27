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
def train_PLACEHOLDER_NO
