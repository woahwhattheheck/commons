#!/usr/bin/env python3
"""host/titan_swarm_mine.py — THE LIVE SWARM at the wallet (owner 07-15).

⚠ SUPERSEDED (07-15) by host/titan_mine_demo.py + titan_mine_worker.py (launch: TitanBitcoin.cmd). This version launched
2×cores pure-Python (no-numpy, slow) workers that oversubscribed the 8-thread box and THROTTLED hard — the "disappointing"
failure. The fix: gated SANDBOX workers (numpy bit-slice ripple, pinned to physical cores, below-normal priority, ending
processes) + a host coordinator that only starts them + checks answers + submits. Kept for reference; do not run this one.


Many lean (no-numpy, ~19 MB each, Titan itself ~0.86 MB) workers over ONE shared stored circuit, CONNECTED:
  - DISJOINT nonce slices  => N workers cover N x the space as a single machine (not the same space N times).
  - ONE shared result bit  => any worker's real block alerts the whole swarm.
  - a live frontier        => each worker broadcasts its best; the coordinator shows the swarm's collective best.
The coordinator holds ONE authorized pool connection and SUBMITS any real block to the wallet. Each cycle it refreshes to
current chain-tip work and re-flashes the circuit, so work never goes stale (time is not a factor). Bounded worker cycles
=> nothing orphans. Real target only => no fake attempts. RAM is not the limit (storage is free); CPU + electricity is.

  python host/titan_swarm_mine.py [n_workers] [lanes] [seconds_forever(0=until killed)]
"""
import glob, json, os, socket, struct, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import titan_sdc as T

HERE    = os.path.dirname(os.path.abspath(__file__))
RESULT  = "C:/llm/models/titan_result.bin"
BESTGLOB = "C:/llm/models/titan_best_*.txt"
REFRESH = 240

N     = int(sys.argv[1]) if len(sys.argv) > 1 else (os.cpu_count() or 8) * 2
LANES = int(sys.argv[2]) if len(sys.argv) > 2 else 64
TOTAL = float(sys.argv[3]) if len(sys.argv) > 3 else 0


def swarm_best():
    best = 0; tot = 0
    for fp in glob.glob(BESTGLOB):
        try:
            b, t = open(fp).read().split()
            best = max(best, int(b)); tot += int(t)
        except Exception:
            pass
    return best, tot


def submit(s, meta, nc):
    s.sendall((json.dumps({"id": 300, "method": "mining.submit",
               "params": [T.WALLET, meta["job_id"], meta["en2"], meta["ntime"], "%08x" % (nc & 0xffffffff)]}) + "\n").encode())


if __name__ == "__main__":
    print(f"LIVE SWARM -> {T.WALLET}   ({N} lean workers x {LANES} lanes, connected, real target only)\n", flush=True)
    t_start = time.time(); cycle = 0
    procs = []
    try:
        while TOTAL == 0 or time.time() - t_start < TOTAL:
            cycle += 1
            print(f"[cycle {cycle}] refreshing to current chain-tip work + re-flashing the circuit ...", flush=True)
            ok, _ = T.refresh_work()
            if not ok:
                print("  work fetch failed; retry in 10s."); time.sleep(10); continue
            C, off, ro, tname = T.install_into_params()
            meta = json.load(open(T.META)); prefix = bytes.fromhex(meta["prefix"])
            nb = struct.unpack("<I", prefix[72:76])[0]; block_target = (nb & 0xffffff) << (8 * ((nb >> 24) - 3))
            for fp in glob.glob(BESTGLOB):
                try: os.remove(fp)
                except Exception: pass
            with open(RESULT, "wb") as fr: fr.write(b"\x00")
            s = T.connect()
            procs = [subprocess.Popen([sys.executable, os.path.join(HERE, "titan_miner.py"),
                                       str(w), str(N), str(LANES), str(REFRESH)]) for w in range(N)]
            print(f"  {N} workers up over {len(C['ga']):,} gates; real target {256 - block_target.bit_length()} zero-bits. "
                  f"pool connected. mining -> wallet.", flush=True)
            c_t0 = time.time(); last = 0
            while time.time() - c_t0 < REFRESH and any(p.poll() is None for p in procs):
                # a worker flipped the shared bit => a real block => submit it to the wallet
                try:
                    r = open(RESULT, "rb").read()
                    if r and r[0] == 1:
                        try: nc = int(r.split(b"nonce")[1].strip())
                        except Exception: nc = None
                        if nc is not None:
                            submit(s, meta, nc)
                            print(f"  [BLOCK] a worker cleared the real target! nonce {nc} -> SUBMITTED to {T.WALLET}", flush=True)
                        with open(RESULT, "wb") as fr: fr.write(b"\x00")
                except Exception: pass
                try:                                        # drain pool responses (accept/reject)
                    s.setblocking(False); data = s.recv(8192)
                    for ln in data.split(b"\n"):
                        if b'"result"' in ln and b"300" in ln:
                            print(f"  [pool] {ln.decode('utf-8','replace')[:120]}", flush=True)
                except Exception: pass
                now = time.time()
                if now - last >= 5:
                    b, tot = swarm_best()
                    print(f"  +{int(now-c_t0):3d}s  swarm best {b:2d} zero-bits   {tot:,} lanes covered this cycle", flush=True)
                    last = now
                time.sleep(0.5)
            for p in procs:
                try: p.wait(timeout=3)
                except Exception: p.terminate()
            s.close()
    except KeyboardInterrupt:
        print("\n[stop] tearing down workers ...", flush=True)
        for p in procs:
            try: p.terminate()
            except Exception: pass
    print("[done]", flush=True)
