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

# ── gate helpers (shared with muhl_neural) ────────────────────────────────────────
