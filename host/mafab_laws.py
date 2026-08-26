#!/usr/bin/env python3
"""host/mafab_laws.py — THE MEASURED LAWS, EXECUTABLE. The fabricator's decisions, derived from the
docs rather than from my judgement.

`pfc_preflight.py` did this for the SPEC: it turned the owner's rules into code that refuses to fire.
This does it for the MEASUREMENTS: every rule below cites the section that measured it, carries that
section's numbers, and is re-measurable by `--verify`. Nothing here is a preference. If a law does
not reproduce, the fabricator says so instead of quietly acting on it.

WHY THIS EXISTS, from the docs themselves:
  §25  "host/titan_circuit.py has no optimisation passes at all... The fabricator's only adder is the
       deepest adder that exists, hardcoded, unconditional. That is the origin of the thin serial
       tail found in every circuit profiled in §15 and §22."
  §33B "6th consecutive session in which my prediction lost to the measurement. The measurement table
       has been wrong ZERO times. The operational form of this is not 'be humble' — it is STOP
       PREDICTING AND START ENUMERATING."
  §33C "The search space here is 6 hand-written candidates. It should be GENERATED, not listed."
So the fabricator must (a) act on measured laws, not defaults, and (b) enumerate rather than choose.

  python host/mafab_laws.py --verify     # re-measure every law; report which reproduce
  python host/mafab_laws.py --laws       # print the law table with citations
"""
import os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, "C:/llm/sdc_sandbox")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import titan_circuit as TC


class Shim:
    """the g.AND/OR/XOR/NOT interface the circuit library expects, over a TC.Circuit"""
    def __init__(s, c): s.c = c; s.C0 = c.cvec(0, 1)[0]; s.C1 = c.cvec(1, 1)[0]
    def AND(s, a, b): return s.c.and_(a, b)
    def OR(s, a, b):  return s.c.or_(a, b)
    def XOR(s, a, b): return s.c.xor(a, b)
    def NOT(s, a):    return s.c.not_(a)


def depth_of(c, outs):
    base = 2 + c.n_in; G = len(c.ga)
    d = [0] * (base + G)
    for k in range(G): d[base + k] = 1 + max(d[c.ga[k]], d[c.gb[k]])
    return max(d[o] if o >= 2 else 0 for o in outs)


# ══════════════════════════════════════════════════════════════════════════════════
# LAW 1 — THE ADDER IS CHOSEN BY OPERAND COUNT, NEVER BY DEFAULT.   §25C
#
# MEASURED (§25C, sum of N sixteen-bit values, identical function, byte-exact both ways):
#     ripple: entry 66, then +6, +6, +6, +6   — expensive to enter, nearly free to extend
#     kogge : entry 20, then +18, +18, +14, +16 — cheap to enter, ~2.8x more expensive to extend
#     N=2 kogge 3.30x better · N=4 1.89x · N=8 1.39x · N=16 1.20x · N=32 1.05x  <- crossover
# §25C states the consequence verbatim: "THE RULE THE FABRICATOR NEEDS: c.add must switch on operand
# count — prefix below ~32 operands, ripple at or above. It is unconditionally ripple today, which
# costs 3.3x DEPTH on every single isolated add in the library."
# §24 licenses the area cost: kogge is ~2.1x the gates, and "area is not slowness".
# ⛔ THE RULE IS STRIPPED. §31A retires it in terms: "§25's adder table stops being a rule to
# hardcode and becomes ONE ENTRY IN A SPACE TO BE SEARCHED... a hardcoded rule is FAR TOO TIMID."
# The foundry then measured it: `always-kogge` — what this rule selects below 32 operands — scored
# 35% off optimal across 8 problems and lost to plain ripple. So there is no crossover constant and
# no chooser. A caller supplies the adder, and the caller gets it from a SEARCH.
def choose_adder(c, n_operands=None, adder=None):
    """No policy here. Pass the adder the search selected; there is no default to fall back on,
    because a default IS the hardcoded rule §31A removed."""
    if adder is None:
        raise ValueError("no adder supplied — §31A: the adder is searched, never defaulted. "
                         "Pass the winner from mafab_adders.family(), or call the search.")
    return adder
