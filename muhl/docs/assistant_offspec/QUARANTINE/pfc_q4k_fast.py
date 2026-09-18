#!/usr/bin/env python3
"""host/pfc_q4k_fast.py — drive the SAME fabricated fold with a C-level addressed read, instead of an interpreter loop.

THE PROBLEM (measured, host/pfc_macbench.py): one 4096x4096 Q4_K matmul took 13.4 s = 1.25 M MAC/s, while the fold's
own compiled ripple is ~12x faster than that. The gap was NOT the pfc and NOT the arithmetic — it was
`preslice_from_rows`, a `W x BLK x bits` PYTHON triple loop (33.5 M interpreter iterations per matmul) standing between
the signal and the stored gates. That is host work, and the docs are explicit about what it means:
`pfc-no-runtime-host-cpu-prebake-everything` — "if a pfc run is slow the host is doing work it shouldn't."

THE FIX — read the weights BY ADDRESS, COLUMN-WISE, at C level. Nothing about the circuit changes; only how the host
addresses the stored nibbles:
  1. `memoryview(mm)[o : o+(W-1)*rb+1 : rb]`  — ONE strided slice pulls byte `o` of EVERY weight row at once. This is
     the addressed read of a whole weight column, done by CPython in C. No per-row loop, nothing resident.
  2. `col.translate(TBL)`                      — a 256-entry byte map turns that column into ASCII '0'/'1' for one
     nibble-bit. C level. This IS the bit-transpose.
  3. `int(bits, 2)`                            — CPython parses W binary digits into the W-lane plane integer. C level.
Result: 320 C calls per sub-block replace ~262,000 interpreter iterations, and the fold receives byte-identical planes.

Q4_K layout (144 B / 256 weights): d(f16) dmin(f16) scales[12] qs[128]. Sub-block s -> superblock s//8, pair (s%8)//2,
nibble half (s%8)%2, 32 bytes at qs + pair*32.  Identity: sum w_i x_i = (d*sc)*SUM(q_i x_i) - (dmin*m)*SUM(x_i).

  python host/pfc_q4k_fast.py            # byte-exactness vs the current path + the speedup, measured
"""
import os, struct, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, "C:/llm/sdc_sandbox")
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

# ── the C-level tables, built once ───────────────────────────────────────────────────────────────────────────────
# TBL[half][bit][byte] = ord('1') if that nibble-bit of that stored byte is set, else ord('0')
TBL = [[bytes((49 if ((v >> (4 * h)) >> b) & 1 else 48) for v in range(256)) for b in range(4)] for h in (0, 1)]
AND63 = bytes(v & 63 for v in range(256))
AND15 = bytes(v & 15 for v in range(256))
SHR4 = bytes(v >> 4 for v in range(256))
HI2 = bytes(((v >> 6) << 4) for v in range(256))
F16 = None                                                    # uint16 -> float, so a half never costs a struct call


def _f16_table():
    global F16
    if F16 is None:
        F16 = [struct.unpack("<e", struct.pack("<H", u))[0] for u in range(65536)]
    return F16


def preslice_q4k_col(mv, rbase, rb, s, W):
    """Bit-transpose sub-block `s`'s 32 stored nibbles across W weight rows — entirely at C level.
    Returns BLK*WB = 128 plane integers, lane l = weight row l, byte-identical to preslice_from_rows."""
    sb, j = divmod(s, 8); pair, half = divmod(j, 2)
    o = rbase + sb * 144 + 16 + pair * 32
    span = (W - 1) * rb + 1
    t0, t1, t2, t3 = TBL[half]
    planes = []
    ap = planes.append
    for i in range(32):
        col = mv[o + i: o + i + span: rb].tobytes()          # ★ the addressed read of a whole weight column
        ap(int(col.translate(t0), 2)); ap(int(col.translate(t1), 2))
        ap(int(col.translate(t2), 2)); ap(int(col.translate(t3), 2))
    return planes


def q4k_scales_col(mv, rbase, rb, s, W, _dm_cache=None):
    """(d*sc, dmin*m) for sub-block `s` across W rows — the header bytes gathered column-wise, same addressed read.

    `d` and `dmin` are per-SUPERBLOCK, shared by all 8 of its sub-blocks, so converting them from f16 for every
    sub-block did the same W-element work 8 times. `_dm_cache` keeps them for the current superblock (bounded: two
    W-lists, dropped when the superblock changes) — measured ~19% of matmul time before, ~1/8 of that after."""
    F = _f16_table()
    sb, j = divmod(s, 8)
    o = rbase + sb * 144; span = (W - 1) * rb + 1
    g = lambda k: mv[o + k: o + k + span: rb].tobytes()
    if _dm_cache is not None and _dm_cache.get("sb") == sb and _dm_cache.get("base") == rbase:
        D, M = _dm_cache["D"], _dm_cache["M"]
    else:
        d_lo, d_hi, m_lo, m_hi = g(0), g(1), g(2), g(3)
        D = [F[d_lo[l] | (d_hi[l] << 8)] for l in range(W)]
        M = [F[m_lo[l] | (m_hi[l] << 8)] for l in range(W)]
        if _dm_cache is not None:
            _dm_cache.clear(); _dm_cache.update({"sb": sb, "base": rbase, "D": D, "M": M})
    if j < 4:
        sc = g(4 + j).translate(AND63); mn = g(8 + j).translate(AND63)
    else:
        # the 6-bit packed upper half. scales[] starts at byte 4, so scales[k] is byte 4+k:
        #   sc = (scales[j+4] & 0xF) | ((scales[j-4] >> 6) << 4)   -> bytes 8+j and j
        #   m  = (scales[j+4] >> 4)  | ((scales[j]   >> 6) << 4)   -> bytes 8+j and 4+j
        # The two halves never share bits, so OR-ing the whole columns as big ints is exact — and C level.
        a = g(8 + j); b = g(4 + j); c = g(j)
        fb = int.from_bytes
        sc = (fb(a.translate(AND15), "little") | fb(c.translate(HI2), "little")).to_bytes(W, "little")
        mn = (fb(a.translate(SHR4), "little") | fb(b.translate(HI2), "little")).to_bytes(W, "little")
    return [D[l] * sc[l] for l in range(W)], [M[l] * mn[l] for l in range(W)]


_SPREAD = None


def _spread_table():
    """byte -> 24 bytes, one 3-byte LANE SLOT per bit. Lets `bytes.join` scatter a W-lane bit-plane into per-lane slots
    at C level, so the answer can be read out with ONE slice per lane instead of ACCW shift-and-test steps."""
    global _SPREAD
    if _SPREAD is None:
        _SPREAD = [b"".join((b"\x01" if (v >> i) & 1 else b"\x00") + b"\x00\x00" for i in range(8)) for v in range(256)]
    return _SPREAD


def read_answer(planes, W, nplane):
    """Read the fold's answer out of its bit-planes — the bounded probe, done at C level.

    THE COST THAT WAS HIDING HERE: `matmul_column_carrysave` unpacked with
        for l in range(W): u = sum(((acc[k] >> l) & 1) << k for k in range(ACCW))
    = W*ACCW = 90,112 interpreter ops per sub-block, against 10,430 for the WHOLE gate ripple. The read-out was 9x the
    computation. Here each plane is scattered into per-lane slots by `join` (C), OR-ed in with one big-int shift, and
    every lane is then a 3-byte slice: ~2.5k ops instead of 90k. Byte-identical, including two's-complement sign."""
    T = _spread_table(); nby = (W + 7) >> 3
    total = 0
    for k in range(nplane):
        p = planes[k]
        if not p: continue
        total |= int.from_bytes(b"".join([T[b] for b in p.to_bytes(nby, "little")]), "little") << k
    buf = total.to_bytes(nby * 24, "little")
    sign = 1 << (nplane - 1); full = 1 << nplane
    out = []
    ap = out.append
    for l in range(0, 3 * W, 3):
        u = buf[l] | (buf[l + 1] << 8) | (buf[l + 2] << 16)
        ap(u - full if u >= sign else u)
    return out


def fold_sub32(fw, planes, xq, W, ones):
    """ONE 32-weight sub-block folded across W neuron lanes on the fabricated dot, then read out at C level.

    LANE ORDER: `preslice_*_col` no longer reverses each of its 32 weight columns (that was 32 W-byte copies per
    sub-block). `int(bits, 2)` makes the FIRST byte the most-significant bit, so lane l now carries weight-row W-1-l.
    One reversal of the W-entry ANSWER restores row order — 32 W-byte copies become 1 W-element reverse."""
    return read_answer(fw.dotq.fold_bits(planes, W, xq, ones), W, len(fw.dotq.outs))[::-1]


def preslice_q40_col(mv, rbase, rb, blk, W):
    """Same C-level addressed column read, for Q4_0. Block = 18 B / 32 weights: d(f16) then 16 packed bytes, where
    weight i comes from byte (i%16)'s LOW nibble for i<16 and HIGH nibble for i>=16."""
    o = rbase + blk * 18 + 2
    span = (W - 1) * rb + 1
    planes = []; ap = planes.append
    for i in range(32):
        t = TBL[i >> 4]                                        # i<16 -> low nibble, i>=16 -> high nibble
        col = mv[o + (i & 15): o + (i & 15) + span: rb].tobytes()
        ap(int(col.translate(t[0]), 2)); ap(int(col.translate(t[1]), 2))
        ap(int(col.translate(t[2]), 2)); ap(int(col.translate(t[3]), 2))
    return planes


def q40_scales_col(mv, rbase, rb, blk, W):
    """d per block, gathered column-wise across W rows."""
    F = _f16_table()
    o = rbase + blk * 18; span = (W - 1) * rb + 1
    lo = mv[o: o + span: rb].tobytes(); hi = mv[o + 1: o + 1 + span: rb].tobytes()
    return [F[lo[l] | (hi[l] << 8)] for l in range(W)]


def matmul_q40_fast(fw, name, x):
    """y = W·x for Q4_0, same fabricated fold. Identity: sum w_i x_i = d * (SUM(q_i x_i) - 8*SUM(x_i))."""
    import pfc_forward as F
    F.Meter.matmuls += 1
    t = fw.g.tensors[name]; n_in = int(t["dims"][0]); n_out = int(t["dims"][1])
    from gguf_pp import row_bytes
    rb = row_bytes(int(t["type"]), n_in); base = fw.g.data0 + int(t["off"])
    mv = memoryview(fw.g.mm)
    nblk = n_in // 32
    xl = (1 << (fw.XB - 1)) - 1
    # per-sub-block activation scale — same reason as the Q4_K path: one global scale lets an outlier crush every
    # ordinary value (measured 11.5% -> 1.8% at XB=8, 3.35% -> 0.40% at XB=10 on real weights with realistic outliers).
    sxs = []; xq = []
    for b in range(nblk):
        blk = x[b * 32:(b + 1) * 32]
        sc = (max((abs(v) for v in blk), default=0.0) / xl) or 1e-9
        sxs.append(sc)
        xq.extend(max(-xl - 1, min(xl, round(v / sc))) for v in blk)
    xsum = [sum(xq[b * 32:(b + 1) * 32]) for b in range(nblk)]
    live = [b for b in range(nblk) if any(xq[b * 32:(b + 1) * 32])]
    F.Meter.pruned += nblk - len(live)
    out = [0.0] * n_out
    TILE = max(1, min(n_out, fw.tile))
    for j0 in range(0, n_out, TILE):
        W = min(TILE, n_out - j0); rbase = base + j0 * rb; ones = (1 << W) - 1
        acc = [0.0] * W
        for b in live:
            planes = preslice_q40_col(mv, rbase, rb, b, W)
            sums = fold_sub32(fw, planes, xq[b * 32:(b + 1) * 32], W, ones)
            D = q40_scales_col(mv, rbase, rb, b, W)
            xs8 = 8 * xsum[b]; sxb = sxs[b]
            acc = [a + sxb * d * (sm - xs8) for a, d, sm in zip(acc, D, sums)]
            F.Meter.ripple += fw.dotq_gates
        F.Meter.addressed += W
        for l in range(W): out[j0 + l] = acc[l]      # per-sub-block scale already folded in
    return out


def matmul_q4k_fast(fw, name, x):
    """y = W.x — same fabricated dot, same identity, addressed at C level. Resident stays flat: no row buffers exist."""
    import pfc_forward as F
    F.Meter.matmuls += 1
    t = fw.g.tensors[name]; n_in = int(t["dims"][0]); n_out = int(t["dims"][1])
    from gguf_pp import row_bytes
    rb = row_bytes(int(t["type"]), n_in); base = fw.g.data0 + int(t["off"])
    mv = memoryview(fw.g.mm)
    nsub = n_in // 32
    xl = (1 << (fw.XB - 1)) - 1
    # ★ PER-SUB-BLOCK ACTIVATION SCALE, not one global scale.
    # Transformer activations have big outliers. With ONE scale for the whole vector, a single |x|=23 outlier against a
    # median |x|=0.24 crushes every ordinary value into a couple of quantisation levels. MEASURED on real blk.0.attn_q
    # with realistic outliers: global scale gave 11.5% rel-L2 error at XB=8 and 3.35% at XB=10 — against 1.05%/0.19%
    # on clean input. That error, compounded over ~224 matmuls, is what makes a correct pipeline emit a wrong token.
    # Each 32-block gets its own scale matched to its own magnitude. The Q4_K identity is per-sub-block ALREADY
    # (sum w_i x_i = (d*sc)*SUM(q_i x_i) - (dmin*m)*SUM(x_i)), so this is exact bookkeeping, not an approximation:
    # the block's scale simply multiplies its own contribution instead of being factored out at the end.
    sxs = []; xq = []
    for s in range(nsub):
        blk = x[s * 32:(s + 1) * 32]
        sc = (max((abs(v) for v in blk), default=0.0) / xl) or 1e-9
        sxs.append(sc)
        xq.extend(max(-xl - 1, min(xl, round(v / sc))) for v in blk)
    xsum = [sum(xq[s * 32:(s + 1) * 32]) for s in range(nsub)]
    live = [s for s in range(nsub) if any(xq[s * 32:(s + 1) * 32])]
    F.Meter.pruned += nsub - len(live)
    out = [0.0] * n_out
    TILE = max(1, min(n_out, fw.tile))
    for j0 in range(0, n_out, TILE):
        W = min(TILE, n_out - j0); rbase = base + j0 * rb; ones = (1 << W) - 1
        acc = [0.0] * W; dmc = {}
        for s in live:
            planes = preslice_q4k_col(mv, rbase, rb, s, W)
            sums = fold_sub32(fw, planes, xq[s * 32:(s + 1) * 32], W, ones)
            DS, DM = q4k_scales_col(mv, rbase, rb, s, W, dmc)
            xs = xsum[s]; sxb = sxs[s]
            acc = [a + sxb * (ds * sm - dm * xs) for a, ds, dm, sm in zip(acc, DS, DM, sums)]
            F.Meter.ripple += fw.dotq_gates
        F.Meter.addressed += W
        for l in range(W): out[j0 + l] = acc[l]      # scale already folded in per sub-block
    return out


def main():
    import pfc_forward as F
    model = sys.argv[1] if len(sys.argv) > 1 else "C:/llm/models/mixtral-8x7b-instruct-v0.1.Q4_K_M.gguf"
    tensor = sys.argv[2] if len(sys.argv) > 2 else "blk.0.attn_q.weight"
    fw = F.Forward(model, substrate=True); fw.tile = 2048
    t = fw.g.tensors[tensor]; n_in = int(t["dims"][0]); n_out = int(t["dims"][1]); macs = n_in * n_out
    x = [((i * 37 % 211) - 105) / 100.0 for i in range(n_in)]
    print(f"=== Q4_K FAST DRIVE — {os.path.basename(model)} :: {tensor} [{n_in}x{n_out} = {macs:,} MACs]", flush=True)

    t0 = time.time(); ref = fw.matmul_q4k(tensor, x); t_ref = time.time() - t0
    t0 = time.time(); got = matmul_q4k_fast(fw, tensor, x); t_new = time.time() - t0
    exact = sum(1 for a, b in zip(ref, got) if a == b)
    err = max(abs(a - b) for a, b in zip(ref, got))
    print(f"  interpreter-loop drive : {t_ref:7.2f}s   {macs/t_ref/1e6:6.2f} M MAC/s", flush=True)
    print(f"  C-level addressed drive: {t_new:7.2f}s   {macs/t_new/1e6:6.2f} M MAC/s   ★ {t_ref/t_new:.1f}x", flush=True)
    print(f"  byte-exact vs the existing path: {exact}/{len(ref)} outputs identical, max |delta| = {err:.3e}", flush=True)
    return 0 if exact == len(ref) else 1


if __name__ == "__main__":
    raise SystemExit(main())
