#!/usr/bin/env python3
"""host/pfc_miner_opt.py — calibrate the FAB TOOL for the leanest double-SHA miner circuit (owner 07-19).
Lever 1 = most-optimal circuit: minimal-gate ch/maj (fewer gates per round, CSE dedupes the shared xors) + iterated
DCE. Fewer gates = faster eval (gate-clock ÷ gates) AND trivial to compile. Byte-exact vs hashlib. Measures the drop
from the fab tool's default 213k-gate miner.
  python host/pfc_miner_opt.py
"""
import os, struct, sys, time
sys.path.insert(0, "C:/llm/sdc_sandbox")
import sdc_cc as CC


def sha_block_opt(g, Hin, in16):
    x32 = CC.xor32; add = CC.add32; rr = CC.rotr; sh = lambda X, n: CC.shr(g, X, n)
    W = list(in16)
    for i in range(16, 64):
        s0 = x32(g, x32(g, rr(W[i - 15], 7), rr(W[i - 15], 18)), sh(W[i - 15], 3))
        s1 = x32(g, x32(g, rr(W[i - 2], 17), rr(W[i - 2], 19)), sh(W[i - 2], 10))
        W.append(add(g, add(g, add(g, W[i - 16], s0), W[i - 7]), s1))
    a, b, c, d, e, f, gg, h = Hin
    for i in range(64):
        S1 = x32(g, x32(g, rr(e, 6), rr(e, 11)), rr(e, 25))
        ch = [g.XOR(gg[j], g.AND(e[j], g.XOR(f[j], gg[j]))) for j in range(32)]           # g ^ (e & (f^g))
        t1 = add(g, add(g, add(g, add(g, h, S1), ch), CC.cword(g, CC.K[i])), W[i])
        S0 = x32(g, x32(g, rr(a, 2), rr(a, 13)), rr(a, 22))
        mj = [g.OR(g.AND(a[j], b[j]), g.AND(c[j], g.XOR(a[j], b[j]))) for j in range(32)]  # (a&b) | (c & (a^b))
        t2 = add(g, S0, mj)
        h, gg, f, e, d, c, b, a = gg, f, e, add(g, d, t1), c, b, a, add(g, t1, t2)
    return [add(g, Hin[k], v) for k, v in enumerate((a, b, c, d, e, f, gg, h))]


def compile_miner_opt():
    g = CC.CircuitCompiler(32)
    ms = CC.numeric_midstate(CC.PREFIX[:64]); ms_w = [CC.cword(g, v) for v in ms]
    w16, w17, w18 = struct.unpack(">III", CC.PREFIX[64:76]); nonce = list(g.IN)
    blk2 = [CC.cword(g, w16), CC.cword(g, w17), CC.cword(g, w18), nonce, CC.cword(g, 0x80000000)] + [CC.cword(g, 0)] * 10 + [CC.cword(g, 640)]
    d1 = sha_block_opt(g, ms_w, blk2)
    blk3 = d1 + [CC.cword(g, 0x80000000)] + [CC.cword(g, 0)] * 6 + [CC.cword(g, 256)]
    d2 = sha_block_opt(g, [CC.cword(g, v) for v in CC.H0], blk3)
    return g, d2


def main():
    # baseline: the fab tool's default miner
    t = time.time(); gb, d2b = CC.compile_miner()
    gates_b, _ = gb.dce([w for word in d2b for w in word]); base_gates = len(gates_b)
    print(f"baseline miner (default fab): {base_gates:,} gates   (built {time.time()-t:.1f}s)", flush=True)

    # optimized
    t = time.time(); g, d2 = compile_miner_opt()
    gates, o2 = g.dce([w for word in d2 for w in word]); opt_gates = len(gates)
    n_wire = 2 + g.n_in + opt_gates; d2c = [o2[i * 32:(i + 1) * 32] for i in range(8)]
    print(f"OPTIMIZED miner (minimal ch/maj): {opt_gates:,} gates   (built {time.time()-t:.1f}s)", flush=True)

    run = g.compile_ripple(gates, n_wire)
    ok = all(CC.digest_from(run([(nb >> i) & 1 for i in range(32)], 1), d2c) == CC.ref(nb)
             for nb in (0, 1, 2, 0xcafebabe, 0x12345678, 0xffffffff))
    print(f"byte-exact vs hashlib: {ok}", flush=True)
    if ok:
        print(f"\n  gate reduction: {base_gates:,} -> {opt_gates:,}  = {base_gates-opt_gates:,} fewer "
              f"({100*(base_gates-opt_gates)/base_gates:.1f}%). eval speed scales as 1/gates, so ~{base_gates/opt_gates:.3f}x faster per lane.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
