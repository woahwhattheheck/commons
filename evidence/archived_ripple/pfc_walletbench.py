#!/usr/bin/env python3
"""host/pfc_walletbench.py — REAL-BLOCK WALLET BENCHMARK (owner 07-19). TWO mechanisms, "try both":

  ripple  (default) — the PROVEN mechanism (same as sdc_run / the 4D-shape playground): POWER the fabricated gates by
                      rippling the stored `gen_miner` netlist, bit-sliced (W nonce lanes/ripple), and read the frontier
                      off the output bus. This is how every working result was produced (4D shapes, the 11->22 frontier).
                      The best nonce (the ANSWER) is written to the memory address `latch_reg`, then read back by a
                      HIGH-IMPEDANCE probe — the owner's "answer at a memory address, probes rest on it" read-out. Submits
                      the best share to the wallet. Reports HOW MANY HASHES + the frontier.

  clock   — the AUTONOMOUS clock the owner was building (resident bounded bit-toggle energy on clk_bit): route the block,
            toggle the clock, probe latch_reg/nonce_reg. This is the piece being FIXED (it did not advance the state in
            the last run). Kept here so we can try both side by side.

Containment: ripple is BOUNDED (W lanes, RSS flat — the sdc_run mechanism, proven ~0-spike); probes/clock are bounded
seek/read/write (no mmap whole-file ripple). Network is I/O only (pull block + submit + never-stale poll). Never-stale.
  python host/pfc_walletbench.py [ripple|clock] [max_seconds]
"""
import hashlib, json, mmap, os, struct, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, "C:/llm/sdc_sandbox")
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import sdc_cc as CC
from pfc_bitcoin_autopilot import make_prefix, Conn, WALLET, POOL_HOST, POOL_PORT

TITAN = "C:/llm/models/titan.gguf"; REG = "C:/llm/models/titan_circuits.json"
OPS = {0: "nand", 1: "and", 2: "or", 3: "xor", 4: "not"}; GEN_MAGIC = b"TITANGEN"
W = 4096; LOGW = 12                                    # 4096 nonce lanes/ripple (sdc_run's proven bounded width, RSS flat)


def load_gen(off):                                    # read the fabricated generic miner netlist out of the params (read-only)
    f = open(TITAN, "rb"); mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    assert mm[off:off + 8] == GEN_MAGIC, "gen_miner magic mismatch"
    n_in, n_wire, n_gate, _ = struct.unpack_from("<IIII", mm, off + 8); p = off + 24
    gates = [None] * n_gate
    for i in range(n_gate):
        op, a, b = struct.unpack_from("<Bii", mm, p); p += 9; gates[i] = (OPS[op], a, b)
    d2c = [[struct.unpack_from("<i", mm, p + (wi * 32 + j) * 4)[0] for j in range(32)] for wi in range(8)]
    mm.close(); f.close()
    return n_in, n_wire, gates, d2c


def get_job(c):
    en1 = None; job = None; en2sz = 8; t = time.time() + 15
    c.send({"id": 1, "method": "mining.subscribe", "params": ["pfc-walletbench/1.0"]})
    while time.time() < t and (en1 is None or job is None):
        for m in c.lines():
            if m.get("id") == 1 and m.get("result"):
                en1 = m["result"][1]; en2sz = m["result"][2]
                c.send({"id": 2, "method": "mining.authorize", "params": [WALLET, "x"]})
            elif m.get("method") == "mining.notify":
                p = m["params"]; job = dict(job_id=p[0], prevhash=p[1], coinb1=p[2], coinb2=p[3],
                                            merkle_branch=p[4], version=p[5], nbits=p[6], ntime=p[7])
    return en1, en2sz, job


def poll_stale(c, prevhash):
    for m in c.lines(wait=0.05):
        if m.get("method") == "mining.notify" and m["params"][1] != prevhash: return True
    return False


def ripple_bench(reg, c, en1, en2sz, job, header76, target, max_s):
    lo = int(reg["latch_reg"]["offset"]) if "latch_reg" in reg else None
    n_in, n_wire, gates, d2c = load_gen(int(reg["gen_miner"]["offset"]))
    run = CC.CircuitCompiler(n_in).compile_ripple(gates, n_wire)   # POWER: the gate rippler (the pfc's fabricated gates)
    words = [struct.unpack_from(">I", header76, i * 4)[0] for i in range(19)]
    ones = (1 << W) - 1
    blkbits = [ones if (words[wi] >> j) & 1 else 0 for wi in range(19) for j in range(32)]
    low = []
    for j in range(LOGW):
        half = 1 << j; period = 1 << (j + 1); mask = 0
        for c0 in range(0, W, period):
            for cc in range(c0 + half, c0 + period): mask |= 1 << cc
        low.append(mask)

    def frontier(v):                                              # best leading-zero count across the W lanes (output bus)
        cand = ones; z = 0
        for j in range(31, -1, -1):
            w = d2c[7][j]; vec = (0 if w == 0 else (ones if w == 1 else v[w]))
            zero = cand & ~vec & ones
            if zero: cand = zero; z += 1
            else: break
        return z, ((cand & -cand).bit_length() - 1 if cand else 0)

    base = 0; swept = 0; best_z = 0; best_nonce = 0; t0 = time.time(); last = 0.0
    print(f"  RIPPLE mechanism (the proven one): powering {len(gates):,} fabricated gates, {W} nonce lanes/ripple…\n", flush=True)
    while time.time() - t0 < max_s and base <= 0xffffffff:
        inp = [blkbits[i] if i < 608 else (low[i - 608] if (i - 608) < LOGW else (ones if (base >> (i - 608)) & 1 else 0)) for i in range(640)]
        v = run(inp, ones)                                        # the pfc computes W real double-SHA-256d hashes
        z, lane = frontier(v)
        if z > best_z:
            best_z = z; best_nonce = (base + lane) & 0xffffffff
            if lo is not None:                                    # write the ANSWER to the memory address latch_reg…
                with open(TITAN, "r+b") as f: f.seek(lo); f.write(struct.pack("<I", best_nonce))
        base = (base + W) & 0xffffffff; swept += W
        now = time.time()
        if now - last >= 3.0:
            probe = ""
            if lo is not None:                                    # …and READ it back with a high-impedance probe
                with open(TITAN, "rb") as f: f.seek(lo); probe = f" latch_reg(probe)={struct.unpack('<I', f.read(4))[0]:#010x}"
            print(f"    +{int(now-t0):3d}s  hashes={swept:,}  frontier={best_z} zero-bits  best_nonce={best_nonce:#010x}{probe}", flush=True)
            last = now
            if poll_stale(c, job["prevhash"]): print("    tip moved — never-stale stop."); break
    return swept, best_z, best_nonce


def clock_bench(reg, c, header76, target, max_s):
    iw = int(reg["input_window"]["offset"]); no = int(reg["nonce_reg"]["offset"])
    lo = int(reg["latch_reg"]["offset"]); cb = int(reg["clk_bit"]["offset"])
    with open(TITAN, "r+b") as f:
        f.seek(iw); f.write((header76 + target.to_bytes(32, "little"))[:108])
        f.seek(no); f.write(b"\x00\x00\x00\x00"); f.seek(lo); f.write(b"\x00\x00\x00\x00")
    t0 = time.time(); ticks = 0; f = open(TITAN, "r+b")
    while time.time() - t0 < max_s:
        for _ in range(200_000): f.seek(cb); f.write(b"\x01"); f.seek(cb); f.write(b"\x00")
        ticks += 200_000
        f.seek(no); nonce = struct.unpack("<I", f.read(4))[0]; f.seek(lo); latch = struct.unpack("<I", f.read(4))[0]
        print(f"    ticks={ticks:,}  nonce_reg(probe)={nonce}  latch_reg(answer)={latch:#010x}", flush=True)
        if latch or nonce: break
    f.close()
    return ticks, 0, 0


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("ripple", "clock") else "ripple"
    max_s = float(sys.argv[2]) if len(sys.argv) > 2 else (60.0 if mode == "ripple" else 30.0)
    reg = json.load(open(REG))
    need = ["gen_miner"] if mode == "ripple" else ["pfc_mine", "input_window", "nonce_reg", "latch_reg", "clk_bit"]
    for k in need:
        if k not in reg: print(f"{k} absent."); return 1

    print(f"pfc WALLET BENCHMARK — mode={mode}  ·  wallet {WALLET}  ·  pool {POOL_HOST}:{POOL_PORT}\n", flush=True)
    c = Conn(); en1, en2sz, job = get_job(c)
    if not job: print("  no block from the pool."); c.close(); return 1
    header76 = make_prefix(job, en1, "00" * en2sz)[:76]
    nbref = struct.unpack("<I", make_prefix(job, en1, "00" * en2sz)[72:76])[0]
    target = (nbref & 0xffffff) << (8 * ((nbref >> 24) - 3)); zb = 256 - target.bit_length()
    print(f"  REAL block {job['job_id']}  prevhash {job['prevhash'][:16]}…  target {zb} zero-bits\n", flush=True)

    if mode == "ripple":
        swept, best_z, best_nonce = ripple_bench(reg, c, en1, en2sz, job, header76, target, max_s)
    else:
        swept, best_z, best_nonce = clock_bench(reg, c, header76, target, max_s)

    print(f"\n  === RESULT ({mode}) ===", flush=True)
    print(f"  HASHES (double-SHA-256d) computed : {swept:,}", flush=True)
    print(f"  frontier reached                  : {best_z} leading zero-bits   (target is {zb})", flush=True)
    print(f"  best nonce (answer @ latch_reg)   : {best_nonce:#010x}", flush=True)
    if best_nonce and mode == "ripple":
        d = hashlib.sha256(hashlib.sha256(header76 + struct.pack("<I", best_nonce)).digest()).digest()
        below = int.from_bytes(d, "little") < target
        c.send({"id": 100, "method": "mining.submit",
                "params": [WALLET, job["job_id"], "00" * en2sz, job["ntime"], "%08x" % best_nonce]})
        verdict = None; t = time.time() + 10
        while time.time() < t and verdict is None:
            for m in c.lines():
                if m.get("id") == 100: verdict = m
        print(f"  submitted best share to wallet    : {'BELOW target — BLOCK!' if below else 'above-target/live share'} · pool: {verdict}", flush=True)
    c.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
