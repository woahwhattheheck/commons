#!/usr/bin/env python3
"""host/pfc_walletbench_max.py — the LEVERED wallet fire (owner 07-20: "the one we just came up with").

Same wallet plumbing as pfc_walletbench.py (pull ONE live block, ripple the fabricated gates, submit the best share,
never-stale, exit), but with the ceiling-math levers STACKED instead of the 4,096-lane baseline:

  L0  CONSTANT-SPECIALIZE to the LIVE block  — fold this block's header in as CONSTANTS (build_miner_hdr), so the
      nonce-independent rounds/schedule collapse. The 640-input generic miner becomes a 32-input (nonce-only) net =
      the biggest area+depth collapse (handoff §5 constant-specialization / §L2 constant-collapse).
  L1  LEANER FAB   — OptCompiler (absorption/complement/¬¬/xor-canon) + minimal-gate ch/maj.
  L3  SHALLOWER    — Wallace (carry-save) trees for the multi-operand adds + Kogge-Stone final adder.
  W   WIDER SLICE  — the leaner/shallower net has a smaller wire vector, so a much wider bit-slice stays cache-resident:
                     crank W from 4,096 toward the cache cliff (default 32,768 = 8x baseline; arg to sweep it).

Containment (identical to walletbench): ripple is BOUNDED (W lanes, RSS flat — the proven sdc_run mechanism); network is
I/O only (pull block + submit + never-stale poll); the answer is written to latch_reg and read back by a probe. Fab-time
byte-exact verify vs hashlib is the ONE sanctioned host eval — if it fails, we DO NOT fire (never submit a wrong circuit).

  python host/pfc_walletbench_max.py [max_seconds] [W]
"""
import hashlib, json, os, struct, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, "C:/llm/sdc_sandbox")
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import sdc_cc as CC
import pfc_miner_fabopt as FO
import pfc_walletbench as WB
from pfc_bitcoin_autopilot import make_prefix, Conn, WALLET, POOL_HOST, POOL_PORT

TITAN = "C:/llm/models/titan.gguf"; REG = "C:/llm/models/titan_circuits.json"


def build_miner_hdr(cls, header76, min_chmaj, use_csa, final_kind):
    """FO.build_miner, but specialized to a LIVE header76 (its 76 bytes fold in as constants; nonce is the only input)."""
    g = cls(32)
    add2, addN = FO.make_adds(g, final_kind, use_csa)
    ms = CC.numeric_midstate(header76[:64]); ms_w = [CC.cword(g, v) for v in ms]
    w16, w17, w18 = struct.unpack(">III", header76[64:76]); nonce = list(g.IN)
    blk2 = [CC.cword(g, w16), CC.cword(g, w17), CC.cword(g, w18), nonce, CC.cword(g, 0x80000000)] + \
           [CC.cword(g, 0)] * 10 + [CC.cword(g, 640)]
    d1 = FO.sha_block_v(g, ms_w, blk2, min_chmaj, add2, addN)
    blk3 = d1 + [CC.cword(g, 0x80000000)] + [CC.cword(g, 0)] * 6 + [CC.cword(g, 256)]
    d2 = FO.sha_block_v(g, [CC.cword(g, v) for v in CC.H0], blk3, min_chmaj, add2, addN)
    return g, d2


def main():
    max_s = float(sys.argv[1]) if len(sys.argv) > 1 else 600.0
    W = int(sys.argv[2]) if len(sys.argv) > 2 else 32768
    LOGW = W.bit_length() - 1
    assert (1 << LOGW) == W, "W must be a power of two"
    reg = json.load(open(REG)) if os.path.exists(REG) else {}
    lo = int(reg["latch_reg"]["offset"]) if "latch_reg" in reg else None

    print(f"pfc WALLET FIRE (LEVERED) — wallet {WALLET} · pool {POOL_HOST}:{POOL_PORT} · W={W:,} lanes/ripple\n", flush=True)
    c = Conn(); en1, en2sz, job = WB.get_job(c)
    if not job: print("  no block from the pool."); c.close(); return 1
    header76 = make_prefix(job, en1, "00" * en2sz)[:76]
    nbref = struct.unpack("<I", header76[72:76])[0]
    target = (nbref & 0xffffff) << (8 * ((nbref >> 24) - 3)); zb = 256 - target.bit_length()
    print(f"  REAL block {job['job_id']}  prevhash {job['prevhash'][:16]}…  target {zb} zero-bits", flush=True)

    # --- FAB: constant-specialize to THIS block + MIN-AREA lean, then byte-exact verify (sanctioned fab-time eval) ---
    # Host ripple throughput ∝ W / n_gates, so on THIS substrate the lever is fewest GATES (area), not depth:
    # OptCompiler + minimal ch/maj + RIPPLE adders (no CSA/KS — those trade more gates for depth, which only pays on
    # parallel silicon). Constant-folding this block's header in drops the whole block-1 + nonce-independent block-2 cone.
    tb = time.time()
    g, d2 = build_miner_hdr(FO.OptCompiler, header76, True, False, "ripple")
    gates, o2 = g.dce([w for word in d2 for w in word])
    n_wire = 2 + g.n_in + len(gates); d2c = [o2[i * 32:(i + 1) * 32] for i in range(8)]
    depth = FO.circuit_depth(gates, g.n_in)
    run = g.compile_ripple(gates, n_wire)
    ref = lambda nb: hashlib.sha256(hashlib.sha256(header76 + struct.pack(">I", nb)).digest()).digest()
    ok = all(CC.digest_from(run([(nb >> i) & 1 for i in range(32)], 1), d2c) == ref(nb)
             for nb in (0, 1, 2, 0xcafebabe, 0x12345678, 0xffffffff, 0xdeadbeef, 0x0badc0de))
    print(f"  FAB: {len(gates):,} gates · depth {depth} · byte-exact {ok} · ({time.time()-tb:.1f}s)  "
          f"[vs 213k-gate baseline]", flush=True)
    if not ok:
        print("  byte-exact FAILED — refusing to fire (never submit a wrong circuit)."); c.close(); return 2

    # --- FIRE: bit-sliced ripple sweep of the nonce space (the proven POWER mechanism), never-stale ---
    ones = (1 << W) - 1
    low = []
    for j in range(LOGW):
        half = 1 << j; period = 1 << (j + 1); mask = 0
        for c0 in range(0, W, period):
            for cc in range(c0 + half, c0 + period): mask |= 1 << cc
        low.append(mask)

    def frontier(v):
        cand = ones; z = 0
        for j in range(31, -1, -1):
            w = d2c[7][j]; vec = (0 if w == 0 else (ones if w == 1 else v[w]))
            zero = cand & ~vec & ones
            if zero: cand = zero; z += 1
            else: break
        return z, ((cand & -cand).bit_length() - 1 if cand else 0)

    base = 0; swept = 0; best_z = 0; best_nonce = 0; t0 = time.time(); last = 0.0
    print(f"\n  POWER: rippling {len(gates):,} specialized gates, {W:,} nonce lanes/ripple…\n", flush=True)
    while time.time() - t0 < max_s and base <= 0xffffffff:
        nlanes = [(low[j] if j < LOGW else (ones if (base >> j) & 1 else 0)) for j in range(32)]
        v = run(nlanes, ones)
        z, lane = frontier(v)
        if z > best_z:
            best_z = z; best_nonce = (base + lane) & 0xffffffff
            if lo is not None:
                with open(TITAN, "r+b") as f: f.seek(lo); f.write(struct.pack("<I", best_nonce))
        base = (base + W) & 0xffffffff; swept += W
        now = time.time()
        if now - last >= 3.0:
            hs = swept / (now - t0); probe = ""
            if lo is not None:
                with open(TITAN, "rb") as f: f.seek(lo); probe = f" latch(probe)={struct.unpack('<I', f.read(4))[0]:#010x}"
            print(f"    +{int(now-t0):3d}s  hashes={swept:,}  {hs:,.0f} H/s  frontier={best_z} zero-bits  "
                  f"best={best_nonce:#010x}{probe}", flush=True)
            last = now
            if WB.poll_stale(c, job["prevhash"]): print("    tip moved — never-stale stop."); break

    print(f"\n  === RESULT (levered) ===", flush=True)
    print(f"  HASHES computed  : {swept:,}   ({swept/max(1e-9,time.time()-t0):,.0f} H/s)", flush=True)
    print(f"  frontier         : {best_z} leading zero-bits   (target is {zb})", flush=True)
    print(f"  best nonce       : {best_nonce:#010x}", flush=True)
    if best_nonce:
        d = hashlib.sha256(hashlib.sha256(header76 + struct.pack(">I", best_nonce)).digest()).digest()
        below = int.from_bytes(d, "little") < target
        c.send({"id": 100, "method": "mining.submit",
                "params": [WALLET, job["job_id"], "00" * en2sz, job["ntime"], "%08x" % best_nonce]})
        verdict = None; t = time.time() + 10
        while time.time() < t and verdict is None:
            for m in c.lines():
                if m.get("id") == 100: verdict = m
        print(f"  submitted to wallet : {'BELOW target — BLOCK!' if below else 'live share'} · pool: {verdict}", flush=True)
    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
