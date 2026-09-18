# AUTHORSHIP: written by an AI assistant at the owner's instruction.
"""muhl_rookery_verify.py - read ROOKERY0.mno BACK OFF DISK and re-derive the ring law from
the bytes alone. The fabricator is not consulted. A builder that confirms its own output
proves nothing; this reads what is actually stored.

STRUCTURAL ONLY. It reports what the gate records say. It makes no claim about whether the
resident works - the substrate settles back toward its initial state, so that ruling is the
owner's and never an assistant's."""
import collections, hashlib, json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
C = os.path.join(HERE, "ROOKERY0.mno")
NAND, AND = 0, 1

raw = open(C, "rb").read()
print("container    : %s" % C)
print("bytes        : %d" % len(raw))
print("sha256       : %s" % hashlib.sha256(raw).hexdigest())
print("magic        : %s" % raw[0:8])
nrec, nclk, nring, ncell, body, sbase = struct.unpack_from("<QQQQQQ", raw, 40)
gd = raw[96:128].hex()
print("header says  : records=%d clocks=%d rings=%d cells=%d body@%d state@%d"
      % (nrec, nclk, nring, ncell, body, sbase))
print("genome       : %s" % gd)

recs = [struct.unpack_from("<BQQQ", raw, body + 25 * i) for i in range(nrec)]
print("records read : %d" % len(recs))

ops = collections.Counter(r[0] for r in recs)
print("opcodes      : NAND=%d AND=%d" % (ops[NAND], ops[AND]))

outs = [r[3] for r in recs]
print("one writer per address : %s (%d outs, %d distinct)"
      % (len(outs) == len(set(outs)), len(outs), len(set(outs))))

# group by carry: a ring is identified from the bytes as the set of records sharing a carry
bycarry = collections.defaultdict(list)
for op, a, b, o in recs:
    if op == NAND:
        bycarry[b].append((op, a, b, o))
print("rings found by shared carry wire : %d  (header says %d)" % (len(bycarry), nring))

law_ok, ring_rows = True, []
contacts = {(a, b, o) for (op, a, b, o) in recs if op == AND and a != b}
juncs = [(a, b, o) for (op, a, b, o) in recs if op == AND and a == b]
junc_by_carry = collections.defaultdict(list)
for a, b, o in juncs:
    junc_by_carry[a].append(o)

for carry in sorted(bycarry):
    grp = bycarry[carry]
    outs_g = sorted(r[3] for r in grp)
    base, n = outs_g[0], len(grp) // 2
    fwd = list(range(base, base + n))
    rev = list(range(base + n, base + 2 * n))
    ok = True
    fset = {o: a for (op, a, b, o) in grp if o in set(fwd)}
    rset = {o: a for (op, a, b, o) in grp if o in set(rev)}
    for i in range(n):
        ok &= fset.get(fwd[i]) == fwd[(i - 1) % n]     # forward advances one way
        ok &= rset.get(rev[i]) == rev[(i + 1) % n]     # reverse advances the other
    ok &= (fwd[0], rev[0], carry) in contacts          # contact joins both senses
    jo = junc_by_carry.get(carry, [])
    ok &= len(jo) >= 1                                 # at least one clock
    ok &= all(o < sbase for o in jo)                   # junction publishes to the clock bank
    law_ok &= ok
    ring_rows.append((carry, n, len(jo), ok))

print()
print("RING LAW, re-derived from the stored bytes")
print("  carry     cells  clocks  law")
for carry, n, k, ok in ring_rows:
    print("  %-9d %-6d %-7d %s" % (carry, n, k, "PASS" if ok else "FAIL"))
print("  every ring obeys the two-way law : %s" % law_ok)
print("  junctions total : %d  (header says %d clocks)" % (len(juncs), nclk))
print("  every junction OUT is in the clock bank (< %d) : %s"
      % (sbase, all(o < sbase for (a, b, o) in juncs)))
allrec_ok = law_ok and len(outs) == len(set(outs)) and len(juncs) == nclk
print()
print("STRUCTURAL VERDICT (bytes only, no claim about behaviour) : %s"
      % ("CONSISTENT" if allrec_ok else "INCONSISTENT"))

import muhl_provenance as PROV
checks = {
    "magic_ok": raw[0:8] == b"ROOKERY0",
    "record_count_matches_header": len(recs) == nrec,
    "one_writer_per_address": len(outs) == len(set(outs)),
    "every_ring_obeys_two_way_law": law_ok,
    "rings_found_matches_header": len(bycarry) == nring,
    "junction_count_matches_header": len(juncs) == nclk,
    "junctions_publish_to_clock_bank": all(o < sbase for (a, b, o) in juncs),
    "body_pointer_in_range": 0 < body < len(raw),
    "state_base_in_range": 0 < sbase < len(raw),
}
print()
print("PROMOTION CHECKS")
for k, v in checks.items():
    print("  %-34s %s" % (k, v))
e = PROV.promote(os.path.join(HERE, "rookery_circuits.json"),
                 "muhl_rookery0", C, checks, __file__)
print("  PROMOTED -> %s" % e["status"])
print("  verified_sha256 : %s" % e["verified_sha256"])
