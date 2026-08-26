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
