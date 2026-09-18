#!/usr/bin/env python3
"""host/pfc_miner_fabopt.py — calibrate the FAB TOOL on the double-SHA miner: ALL 3 levers, MEASURED, byte-exact.
Owner 07-19: the lever to break past mining speed is the fabricator, not accepting the current speed. Do all 3.

  L1  DEEPER MINIMIZATION  — OptCompiler adds absorption/complement/double-not/xor-canon laws on top of the
                            existing fold+CSE+DCE, plus minimal-gate ch/maj. (fewer gates -> faster eval, wider slice)
  L2  CONSTANT-COLLAPSE    — report how much of block-2 the compiler already folds to constants (nonce-independent
                            rounds + schedule), i.e. how much dead compute the fold already deleted.
  L3  DEPTH                — carry-save (Wallace) trees for the multi-operand adds + Kogge-Stone final adder;
                            measure BOTH gate count and logic depth so the gate/depth tradeoff is on the table.

Reports gates + depth + byte-exact for every variant, then bit-slice H/s for baseline vs the leanest. Lets the
DATA say how far the fab lever goes — no feasibility guesses. Pure synthesis, no numpy, titan.gguf not opened.
  python host/pfc_miner_fabopt.py
"""
import os, random, struct, sys, time
sys.path.insert(0, "C:/llm/sdc_sandbox")
import sdc_cc as CC
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass


# ============================== L1: OptCompiler — extra Boolean laws on construction ==============================
class OptCompiler(CC.CircuitCompiler):
    """CircuitCompiler + structural simplification (absorption, complement, double-negation, xor canonicalization).
    Each rule is a logical identity, so the net stays byte-exact; they fire wherever the pattern occurs and CSE/DCE
    clean up after. Constant folds run first (correctness), then the structural rules, then _emit (with CSE)."""
    def _gate(self, w):
        base = 2 + self.n_in
        return self.gates[w - base] if w >= base else None

    def NOT(self, a):
        if a == self.C0: return self.C1
        if a == self.C1: return self.C0
        ga = self._gate(a)
        if ga is not None and ga[0] == "not": return ga[1]           # ¬¬x = x
        return self._emit("not", a, a)

    def AND(self, a, b):
        if a == self.C0 or b == self.C0: return self.C0
        if a == self.C1: return b
        if b == self.C1: return a
        if a == b: return a
        ga, gb = self._gate(a), self._gate(b)
        if gb is not None:
            if gb[0] == "or" and (gb[1] == a or gb[2] == a): return a  # a & (a|x) = a
            if gb[0] == "not" and gb[1] == a: return self.C0           # a & ¬a = 0
        if ga is not None:
            if ga[0] == "or" and (ga[1] == b or ga[2] == b): return b  # (b|x) & b = b
            if ga[0] == "not" and ga[1] == b: return self.C0
        return self._emit("and", a, b)

    def OR(self, a, b):
        if a == self.C1 or b == self.C1: return self.C1
        if a == self.C0: return b
        if b == self.C0: return a
        if a == b: return a
        ga, gb = self._gate(a), self._gate(b)
        if gb is not None:
            if gb[0] == "and" and (gb[1] == a or gb[2] == a): return a  # a | (a&x) = a
            if gb[0] == "not" and gb[1] == a: return self.C1            # a | ¬a = 1
        if ga is not None:
            if ga[0] == "and" and (ga[1] == b or ga[2] == b): return b  # (b&x) | b = b
            if ga[0] == "not" and ga[1] == b: return self.C1
        return self._emit("or", a, b)

    def XOR(self, a, b):
        if a == self.C0: return b
        if b == self.C0: return a
        if a == self.C1: return self.NOT(b)
        if b == self.C1: return self.NOT(a)
        if a == b: return self.C0
        ga, gb = self._gate(a), self._gate(b)
        an = ga is not None and ga[0] == "not"
        bn = gb is not None and gb[0] == "not"
        if an and bn: return self.XOR(ga[1], gb[1])                    # (¬x)^(¬y) = x^y
        if an: return self.NOT(self.XOR(ga[1], b))                    # (¬x)^y = ¬(x^y)   (canon -> CSE)
        if bn: return self.NOT(self.XOR(a, gb[1]))
        return self._emit("xor", a, b)


# ============================== L1: minimal-gate ch / maj ==============================
def ch_min(g, e, f, gg):  return [g.XOR(gg[j], g.AND(e[j], g.XOR(f[j], gg[j]))) for j in range(32)]   # g ^ (e&(f^g))
def maj_min(g, a, b, c):  return [g.OR(g.AND(a[j], b[j]), g.AND(c[j], g.XOR(a[j], b[j]))) for j in range(32)]  # (a&b)|(c&(a^b))


# ============================== L3: carry-save trees + Kogge-Stone final adder ==============================
def csa(g, x, y, z):
    """3:2 compressor -> (sum, carry<<1), mod 2^32. sum=x^y^z, carry=maj(x,y,z) shifted one position."""
    s = [g.XOR(g.XOR(x[j], y[j]), z[j]) for j in range(32)]
    cin = [g.OR(g.AND(x[j], y[j]), g.AND(z[j], g.XOR(x[j], y[j]))) for j in range(32)]   # x^y reused via CSE
    carry = [g.C0] + cin[:31]                                                            # <<1, drop bit-32 (≡0 mod 2^32)
    return s, carry


def add_ks(g, x, y):
    """Kogge-Stone parallel-prefix adder mod 2^32 — log2(32)=5 prefix levels (shallow), more gates than ripple."""
    P0 = [g.XOR(x[j], y[j]) for j in range(32)]      # propagate (also the pre-carry sum term)
    G = [g.AND(x[j], y[j]) for j in range(32)]       # generate
    P = list(P0); d = 1
    while d < 32:
        nG, nP = list(G), list(P)
        for j in range(d, 32):
            nG[j] = g.OR(G[j], g.AND(P[j], G[j - d]))
            nP[j] = g.AND(P[j], P[j - d])
        G, P, d = nG, nP, d * 2
    return [P0[0]] + [g.XOR(P0[j], G[j - 1]) for j in range(1, 32)]   # carry into bit j = G[j-1], c0=0


def make_adds(g, final_kind, use_csa):
    add2 = (lambda x, y: add_ks(g, x, y)) if final_kind == "ks" else (lambda x, y: CC.add32(g, x, y))
    def addN(ops):
        ops = list(ops)
        if not use_csa:
            acc = ops[0]
            for o in ops[1:]: acc = add2(acc, o)
            return acc
        while len(ops) > 2:                              # Wallace-style reduce to 2 via 3:2 compressors
            x, y, z = ops.pop(), ops.pop(), ops.pop()
            s, c = csa(g, x, y, z); ops.append(s); ops.append(c)
        return add2(ops[0], ops[1]) if len(ops) == 2 else ops[0]
    return add2, addN


# ============================== the miner, parameterized by the levers ==============================
def sha_block_v(g, Hin, in16, min_chmaj, add2, addN):
    x32 = CC.xor32; rr = CC.rotr; sh = lambda X, n: CC.shr(g, X, n)
    W = list(in16)
    for i in range(16, 64):
        s0 = x32(g, x32(g, rr(W[i - 15], 7), rr(W[i - 15], 18)), sh(W[i - 15], 3))
        s1 = x32(g, x32(g, rr(W[i - 2], 17), rr(W[i - 2], 19)), sh(W[i - 2], 10))
        W.append(addN([W[i - 16], s0, W[i - 7], s1]))
    a, b, c, d, e, f, gg, h = Hin
    for i in range(64):
        S1 = x32(g, x32(g, rr(e, 6), rr(e, 11)), rr(e, 25))
        ch = ch_min(g, e, f, gg) if min_chmaj else x32(g, CC.and32(g, e, f), CC.and32(g, CC.not32(g, e), gg))
        t1 = addN([h, S1, ch, CC.cword(g, CC.K[i]), W[i]])
        S0 = x32(g, x32(g, rr(a, 2), rr(a, 13)), rr(a, 22))
        mj = maj_min(g, a, b, c) if min_chmaj else x32(g, x32(g, CC.and32(g, a, b), CC.and32(g, a, c)), CC.and32(g, b, c))
        t2 = add2(S0, mj)
        h, gg, f, e, d, c, b, a = gg, f, e, add2(d, t1), c, b, a, add2(t1, t2)
    return [add2(Hin[k], v) for k, v in enumerate((a, b, c, d, e, f, gg, h))]


def build_miner(compiler_cls, min_chmaj, use_csa, final_kind):
    g = compiler_cls(32)
    add2, addN = make_adds(g, final_kind, use_csa)
    ms = CC.numeric_midstate(CC.PREFIX[:64]); ms_w = [CC.cword(g, v) for v in ms]
    w16, w17, w18 = struct.unpack(">III", CC.PREFIX[64:76]); nonce = list(g.IN)
    blk2 = [CC.cword(g, w16), CC.cword(g, w17), CC.cword(g, w18), nonce, CC.cword(g, 0x80000000)] + [CC.cword(g, 0)] * 10 + [CC.cword(g, 640)]
    d1 = sha_block_v(g, ms_w, blk2, min_chmaj, add2, addN)
    blk3 = d1 + [CC.cword(g, 0x80000000)] + [CC.cword(g, 0)] * 6 + [CC.cword(g, 256)]
    d2 = sha_block_v(g, [CC.cword(g, v) for v in CC.H0], blk3, min_chmaj, add2, addN)
    return g, d2


# ============================== measurement helpers ==============================
def circuit_depth(gates, n_in):
    base = 2 + n_in; dep = [0] * len(gates)
    dof = lambda w: dep[w - base] if w >= base else 0
    for k, (op, a, b) in enumerate(gates): dep[k] = 1 + max(dof(a), dof(b))
    return max(dep) if dep else 0


def const_report(min_chmaj):
    """L2: how much does the fold already delete? Count typed gates BEFORE dce vs the live cone AFTER dce."""
    g, d2 = build_miner(OptCompiler, min_chmaj, False, "ripple")
    before = g.n_gate()
    gates, _ = g.dce([w for word in d2 for w in word])
    return before, len(gates)


def measure(name, cls, min_chmaj, use_csa, final_kind, verify=True):
    t = time.time()
    g, d2 = build_miner(cls, min_chmaj, use_csa, final_kind)
    gates, o2 = g.dce([w for word in d2 for w in word])
    n_wire = 2 + g.n_in + len(gates); d2c = [o2[i * 32:(i + 1) * 32] for i in range(8)]
    depth = circuit_depth(gates, g.n_in)
    ok = "-"
    if verify:
        run = g.compile_ripple(gates, n_wire)
        ok = all(CC.digest_from(run([(nb >> i) & 1 for i in range(32)], 1), d2c) == CC.ref(nb)
                 for nb in (0, 1, 2, 0xcafebabe, 0x12345678, 0xffffffff, 0xdeadbeef))
    print(f"  {name:<34} {len(gates):>8,} gates   depth {depth:>4}   byte-exact {ok}   ({time.time()-t:.1f}s)", flush=True)
    return g, gates, n_wire, d2c, len(gates)


def bitslice_hs(g, gates, n_wire, d2c, label):
    run = g.compile_ripple(gates, n_wire)
    def rate(fn, secs):
        t0 = time.time(); n = 0
        while time.time() - t0 < secs: fn(); n += 1
        return n, time.time() - t0
    out = []
    for W in (2048, 8192):
        ones = (1 << W) - 1; lanes = [random.getrandbits(W) for _ in range(32)]
        n, s = rate(lambda: run(lanes, ones), 2.0); hs = n * W / s
        out.append((W, hs)); print(f"    {label:<20} bit-slice W={W:>5}: {hs:>12,.0f} H/s", flush=True)
    return max(h for _, h in out)


def main():
    print("FAB-TOOL CALIBRATION on double-SHA-256d miner — all 3 levers, measured, byte-exact\n", flush=True)

    # --- L2 first: how much dead compute did the fold already delete? ---
    before, after = const_report(False)
    print(f"  L2 constant-collapse: fold+CSE built {before:,} typed gates, DCE keeps {after:,} live "
          f"({before-after:,} folded/dead = {100*(before-after)/before:.0f}% deleted before we start)\n", flush=True)

    print("  VARIANTS (each = a fab-tool configuration):", flush=True)
    base = measure("baseline (default fab)",        CC.CircuitCompiler, False, False, "ripple")
    v1   = measure("L1 min ch/maj + opt laws",      OptCompiler,        True,  False, "ripple")
    v2   = measure("L1+L3 csa tree, ripple final",  OptCompiler,        True,  True,  "ripple")
    v3   = measure("L1+L3 csa tree, kogge-stone",   OptCompiler,        True,  True,  "ks")

    variants = [("baseline", base), ("L1", v1), ("L1+csa", v2), ("L1+csa+ks", v3)]
    lean = min(variants, key=lambda kv: kv[1][4])
    base_g = base[4]
    print(f"\n  gate summary (vs baseline {base_g:,}):", flush=True)
    for nm, r in variants:
        dg = base_g - r[4]
        print(f"    {nm:<14} {r[4]:>8,}   {'-' if dg==0 else ('%+d' % -dg)}   ({100*dg/base_g:+.1f}%)", flush=True)
    print(f"\n  leanest by gate count: {lean[0]} ({lean[1][4]:,} gates)", flush=True)

    print(f"\n  THROUGHPUT (Python compiled ripple, bit-sliced) — baseline vs leanest:", flush=True)
    hb = bitslice_hs(base[0], base[1], base[2], base[3], "baseline")
    hl = bitslice_hs(lean[1][0], lean[1][1], lean[1][2], lean[1][3], lean[0])
    print(f"\n  ================= baseline {hb:,.0f} H/s  ->  {lean[0]} {hl:,.0f} H/s  = {hl/hb:.3f}x =================", flush=True)
    print(f"  (gate ratio {base_g/lean[1][4]:.3f}x; H/s tracks 1/gates for the count-bound bit-slice engine)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
