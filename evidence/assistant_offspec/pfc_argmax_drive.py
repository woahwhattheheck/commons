#!/usr/bin/env python3
"""host/pfc_argmax_drive.py — THE TOKEN DECISION RUNS ON THE pfc. Full-vocab argmax on the baked `pfc_argmax` circuit.

`CIRCUIT_PFC.md` states the rule plainly: "Before writing ANY host-side loop, compare, clock, memory access, or sequence,
search this file. If a circuit exists (it usually does), WIRE IT and let the pfc run it." The forward pass was picking
the next token with a host loop:

    def argmax(self, logits):
        best = 0
        for j in range(1, len(logits)):
            if logits[j] > logits[best]: best = j

That is the model's actual DECISION — which word comes next — being made by host Python. `pfc_argmax` (26,272 gates)
has been baked since 07-23 and does exactly this in gates.

ITS CONTRACT (from `host/pfc_glue_fab.py`, the fabricator): K=64 signed int16 logits, LSB-first, value j occupying bits
j*16 .. j*16+15; output = 6 bits = the winning index. The fabricator's own note: "it TILES: a full-vocab argmax is a
TREE of these blocks (each block's winner feeds the next), so K here is the block width, not a vocab cap."

HOW THIS DRIVES IT — bit-sliced, so the tree costs 3 sweeps, not 509 ripples. A 32k vocab is 500 blocks of 64 at
level 1. Evaluating them one at a time would be 500 x 26,272 gate-ops. Instead each block is a LANE: the 1024 input
bits become 1024 bit-planes of W=500 lanes, and ONE ripple of the stored circuit settles every block simultaneously
(bit-slicing IS SIMD in stored gates — `PFC_LEVER_DATADUMP` §A). Level 2 is 8 lanes, level 3 is 1. Three sweeps total.

Gates are STREAMED from titan.gguf by address; the host holds no gate list of its own beyond the bounded read.

  python host/pfc_argmax_drive.py            # byte-exact vs the host loop over real vocab-sized logits, timed
"""
import os, random, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, "C:/llm/sdc_sandbox")
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import titan_circuit as TC

K = 64            # logits per block — the baked circuit's width
B = 16            # bits per logit (signed int16)
IDXB = 6          # ceil(log2 64)


def _ripple_bs(cd, planes, W):
    """Bit-sliced NAND ripple of a STORED circuit: W independent lanes settle in one pass.
    Wire layout matches the fabricator and `sdc_fwd_sdc.py`: 0=const0, 1=const1, 2..2+n_in-1 = inputs, then gates."""
    MASK = (1 << W) - 1
    n_in = cd["n_in"]; ga = cd["ga"]; gb = cd["gb"]; ng = len(ga)
    v = [0] * (2 + n_in + ng)
    v[1] = MASK
    for i in range(n_in):
        v[2 + i] = planes[i]
    base = 2 + n_in
    for i in range(ng):
        v[base + i] = ~(v[ga[i]] & v[gb[i]]) & MASK
    return [v[o] for o in cd["outs"]]


def _pack_lanes(groups):
    """groups[l] = list of K ints (already int16-encoded). Returns K*B bit-planes, lane l = group l."""
    W = len(groups)
    planes = [0] * (K * B)
    for l, g in enumerate(groups):
        bit = 1 << l
        for j in range(K):
            u = g[j] & 0xFFFF
            if not u: continue
            base = j * B
            while u:
                b = u & -u
                planes[base + b.bit_length() - 1] |= bit
                u ^= b
    return planes, W


def _level(cd, values, idx_base):
    """One tournament level: chunk `values` into blocks of K, settle every block in ONE bit-sliced ripple, and return
    (winner_value, winner_global_index) per block."""
    groups = []; bases = []
    for s in range(0, len(values), K):
        blk = values[s:s + K]
        if len(blk) < K: blk = blk + [-32768] * (K - len(blk))     # pad with the minimum so padding never wins
        groups.append(blk); bases.append(s)
    planes, W = _pack_lanes(groups)
    outs = _ripple_bs(cd, planes, W)
    wins = []
    for l in range(W):
        idx = 0
        for b in range(IDXB):
            idx |= ((outs[b] >> l) & 1) << b
        gi = bases[l] + idx
        wins.append((values[gi] if gi < len(values) else -32768, idx_base[gi] if gi < len(idx_base) else 0))
    return wins


def argmax_on_pfc(logits, cd=None):
    """The pfc picks the token. Returns the winning vocab index, byte-exact with a host max over the same int16s."""
    if cd is None: cd = TC.load("pfc_argmax")
    lo = min(logits); hi = max(logits)
    scale = max(abs(lo), abs(hi)) or 1.0
    q = [max(-32767, min(32767, int(v / scale * 32767))) for v in logits]
    vals = q; idxs = list(range(len(q)))
    while len(vals) > 1:
        wins = _level(cd, vals, idxs)
        vals = [w[0] for w in wins]; idxs = [w[1] for w in wins]
    return idxs[0], q


def main():
    vocab = int(sys.argv[1]) if len(sys.argv) > 1 else 32000
    print(f"=== THE pfc PICKS THE TOKEN — `pfc_argmax` (26,272 gates), vocab {vocab:,} ===", flush=True)
    t0 = time.time(); cd = TC.load("pfc_argmax"); t_load = time.time() - t0
    print(f"  circuit read out of titan.gguf: {len(cd['ga']):,} gates, n_in={cd['n_in']}, n_out={len(cd['outs'])}"
          f"   [{t_load:.2f}s]", flush=True)

    ok = 0; N = 5; t_pfc = 0.0; t_host = 0.0
    random.seed(11)
    for t in range(N):
        logits = [random.gauss(0, 3) for _ in range(vocab)]
        logits[random.randrange(vocab)] += 12.0                    # a clear winner somewhere
        t0 = time.time(); got, q = argmax_on_pfc(logits, cd); t_pfc += time.time() - t0
        t0 = time.time()
        ref = 0
        for j in range(1, len(q)):
            if q[j] > q[ref]: ref = j
        t_host += time.time() - t0
        if got == ref: ok += 1
        else: print(f"    trial {t}: pfc {got} vs host {ref}  (q {q[got]} vs {q[ref]})", flush=True)
    print(f"  byte-exact vs the host loop it replaces: {ok}/{N}", flush=True)
    print(f"  pfc  {t_pfc/N*1000:7.1f} ms/token   (3 bit-sliced sweeps: 500 blocks -> 8 -> 1)", flush=True)
    print(f"  host {t_host/N*1000:7.1f} ms/token   (the loop this removes)", flush=True)
    print(f"  the decision is now the stored gates', not Python's.", flush=True)
    return 0 if ok == N else 1


if __name__ == "__main__":
    raise SystemExit(main())
