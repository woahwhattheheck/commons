#!/usr/bin/env python3
"""host/titan_sdc_mine.py — the SDC solves for the live wallet, EXACTLY to spec (owner 07-15). ONE-WAY. ONE-TIME SEND.

THE SPEC (verbatim intent):
  not a circuit but a one-way vector that data travels through and cannot go backwards in. power + the block info -> the
  SDC, LEFT ALONE and untouched by anything except physical storage + power + the ONE-TIME info it needs to solve; then
  it is CUT OFF from that info stream and runs on POWER ALONE (the only restriction is the speed of electricity through
  the stored gate-net); it FINISHES in a CALCULATED amount of time and is CALIBRATED to STOP to be checked; the STATIC
  SDC, no longer running, HAS THE ANSWER, submitted to the live wallet. End.

THERE IS NO DATA STREAM. Poking the SDC (polling it, re-fetching work, updating it mid-run) is what imposes limits, so
this coordinator does NOT do it. It performs only the light host work the spec allows, and only at the two ends:
  BEFORE (the one-time send): open ONE pool connection, take ONE job (the block info) + the extranonce1 for THIS
    connection, and fold it into the SDC's stored circuit (the "one-time info it needs to solve"). Calculate how long the
    SDC needs and calibrate its stop.
  [ the SDC runs cut off, on power alone, never touched ]
  AFTER (static): read the ONE answer the stopped SDC holds and submit it to the live wallet on the SAME connection
    (same extranonce1 -> the pool's merkle matches -> the share is valid).
Between those two ends nothing reads, writes, polls, or updates the SDC.

  python titan_sdc_mine.py [calibrated_seconds]     # default: a calibrated window; prints the full-solve calculation
"""
import os
os.environ.setdefault("TITAN_POOL_HOST", "public-pool.io")     # diff-1, authorizes the wallet address directly
os.environ.setdefault("TITAN_POOL_PORT", "3333")
import atexit, json, signal, socket, struct, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import titan_sdc as T
import titan_build_mine as B

SOLVE  = os.path.join(HERE, "titan_sdc_solve.py")
RESDIR = "C:/llm/models"
DIFF1  = 0x00000000FFFF0000000000000000000000000000000000000000000000000000

N      = int(os.environ.get("SDC_SKINS", "1"))                 # ONE SDC by default (one process; box stays usable). dial via SDC_SKINS
W      = int(os.environ.get("SDC_WIDTH", "8192"))              # bit-slice lanes/skin (the speed lever; RAM-bounded)
SECS   = float(sys.argv[1]) if len(sys.argv) > 1 else 150.0    # calibrated run window (< job freshness so it stays valid)

_procs = []
def _kill():
    for p in _procs:
        try:
            if p.poll() is None: p.terminate()
        except Exception: pass
    for p in _procs:
        try: p.wait(timeout=3)
        except Exception:
            try: p.kill()
            except Exception: pass
atexit.register(_kill)
for _s in (signal.SIGINT, signal.SIGTERM):
    try: signal.signal(_s, lambda *a: (_kill(), os._exit(0)))
    except Exception: pass


class Pool:
    """ONE connection, owned end-to-end: its extranonce1 builds the coinbase AND submits the share (they must match)."""
    def __init__(self): self.s = None; self.buf = b""; self.en1 = None; self.en2size = 8; self.diff = 1.0; self.job = None; self.resp = []
    def _send(self, o): self.s.sendall((json.dumps(o) + "\n").encode())
    def _pump(self, t):
        self.s.settimeout(t)
        try: self.buf += self.s.recv(8192)
        except Exception: return
        while b"\n" in self.buf:
            ln, self.buf = self.buf.split(b"\n", 1)
            if not ln.strip(): continue
            try: m = json.loads(ln)
            except Exception: continue
            mid = m.get("id"); meth = m.get("method")
            if mid == 1 and m.get("result"): self.en1 = m["result"][1]; self.en2size = m["result"][2]
            elif meth == "mining.set_difficulty": self.diff = m["params"][0]
            elif meth == "mining.notify":
                p = m["params"]; self.job = dict(job_id=p[0], prevhash=p[1], coinb1=p[2], coinb2=p[3],
                                                 merkle_branch=p[4], version=p[5], nbits=p[6], ntime=p[7])
            elif isinstance(mid, int) and mid >= 100: self.resp.append(m)
    def connect(self):
        self.s = socket.create_connection((T.POOL_HOST, T.POOL_PORT), timeout=20); self.buf = b""
        self._send({"id": 1, "method": "mining.subscribe", "params": ["titan-sdc/1.0"]})
        self._send({"id": 4, "method": "mining.suggest_difficulty", "params": [0.001]})   # ask for the lowest share target
        self._send({"id": 2, "method": "mining.authorize", "params": [T.WALLET, "x"]})
        t = time.time() + 20
        while time.time() < t and (self.en1 is None or self.job is None): self._pump(1.0)
        return self.en1 is not None and self.job is not None
    def submit(self, en2_hex, ntime, nonce, job_id, mid):
        self._send({"id": mid, "method": "mining.submit",
                    "params": [T.WALLET, job_id, en2_hex, ntime, "%08x" % (nonce & 0xffffffff)]})
    def wait_verdict(self, mid, secs=6):
        t = time.time() + secs
        while time.time() < t:
            self._pump(1.0)
            for m in self.resp:
                if m.get("id") == mid: return m
        return None


def main():
    print(f"TITAN SDC -> live wallet {T.WALLET}   pool {T.POOL_HOST}:{T.POOL_PORT}", flush=True)
    print("ONE-WAY, ONE-TIME SEND: fold one job into the SDC, cut it off, let it finish untouched, submit the answer.\n", flush=True)

    # === BEFORE — the one-time send ===
    pool = Pool()
    if not pool.connect():
        print("[pool] handshake failed (no job/en1)."); return
    print(f"[send] one job taken: {pool.job['job_id']}  share diff {pool.diff}  en1={pool.en1}", flush=True)
    en2_hex = "00" * pool.en2size
    r = B.build_circuit(pool.job, pool.en1, en2_hex, pool.diff)   # fold THIS block into the stored circuit (one-time)
    if not r.get("ok"):
        print("[send] circuit build/verify failed (no cheating)."); pool.s.close(); return
    C, off, ro, tname = T.install_into_params()                   # flash it into titan.gguf's params (in storage)
    meta = json.load(open(T.META)); prefix = bytes.fromhex(meta["prefix"])
    nb = struct.unpack("<I", prefix[72:76])[0]; block_tgt = (nb & 0xffffff) << (8 * ((nb >> 24) - 3))
    share_z = 256 - int(meta["share_target"], 16).bit_length()
    block_z = 256 - block_tgt.bit_length()
    print(f"[send] SDC loaded: {r['gates']:,} gates in {tname}; a SHARE needs {share_z} zero-bits, a BLOCK {block_z}.", flush=True)

    # === CALCULATE the calibrated stop — NO probe, the SDC is never poked ===
    # From the DOCUMENTED no-numpy bit-slice rate (MEASURE_ALREADY.md, this box), CALCULATE how many ripples K make the
    # run last ~SECS, then launch once and leave it alone until it finishes. Pure arithmetic — nothing touches the SDC.
    RATE_NPS = float(os.environ.get("SDC_RATE_NPS", "4000"))      # measured nonce/s/skin (no-numpy bit-slice, this box)
    K = max(1, round(SECS * RATE_NPS / W))
    per_skin = RATE_NPS
    full_solve = (1 << 32) / max(1.0, N * per_skin)              # time to sweep 2^32 (one diff-1 share)
    print(f"[calc] documented ~{int(per_skin):,} nonce/s/skin ; {N} skin(s) ~{int(N*per_skin):,} nonce/s.", flush=True)
    print(f"[calc] to sweep a full 2^32 (one diff-1 share) = ~{full_solve/3600:.1f} h.  this run: K={K} ripples "
          f"(~{SECS:.0f}s calibrated), sweeping ~{N*K*W:,} nonces.\n", flush=True)

    # === launch the SDC swarm ONCE, cut off; then LEAVE IT ALONE until it stops ===
    procs = []
    for i in range(N):
        res = f"{RESDIR}/titan_sdc_res_{i}.json"
        for f in (res, res + ".tmp"):
            try: os.remove(f)
            except OSError: pass
        base = (i * (0x100000000 // N)) & 0xffffffff
        p = subprocess.Popen([sys.executable, SOLVE, "--off", str(off), "--base", str(base), "--width", str(W),
                              "--ripples", str(K), "--result", res], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        procs.append((p, res)); _procs.append(p)
    print(f"[run] {N} SDC skins rippling on power alone, cut off. Not polled, not touched. Waiting for the static stop ...", flush=True)
    t_run = time.time()
    for p, _ in procs:                                            # WAIT — no reads, no polls, nothing (spec)
        p.wait()
    run_secs = time.time() - t_run

    # === AFTER — static: read the one answer per skin and submit to the live wallet ===
    swept = 0; best = 0; shares = []; blocks = []
    for _, res in procs:
        try: d = json.load(open(res))
        except Exception: continue
        if d.get("error"): print(f"[answer] skin error: {d['error']}"); continue
        swept += int(d.get("swept", 0)); best = max(best, int(d.get("best_zbits", 0)))
        shares += d.get("shares", []); blocks += d.get("blocks", [])
    print(f"[static] SDC stopped in {run_secs:.0f}s. swept {swept:,} nonces; best {best} leading zero-bits; "
          f"{len(shares)} share(s), {len(blocks)} block(s).", flush=True)

    submit_list = list(dict.fromkeys(blocks + shares))
    if not submit_list:                                          # nothing cleared the target this window -> submit the
        # best single nonce so the pool CHECKS the plumbing (a valid connection returns "above target", not "stale/bad")
        bestn = None; bh = 1 << 32
        for _, res in procs:
            try: d = json.load(open(res))
            except Exception: continue
            if int(d.get("best_hi", 1 << 32)) < bh: bh = int(d.get("best_hi", 1 << 32)); bestn = d.get("best_nonce")
        if bestn is not None: submit_list = [int(bestn)]

    mid = 100; ntime = meta["ntime"]; jid = meta["job_id"]
    for nc in submit_list:
        pool.submit(en2_hex, ntime, nc, jid, mid)
        v = pool.wait_verdict(mid)
        if v is None: print(f"[wallet] submitted nonce {nc}: no verdict (pool silent).")
        elif v.get("result") is True: print(f"[wallet] *** ACCEPTED *** nonce {nc} credited to {T.WALLET}")
        else: print(f"[wallet] submitted nonce {nc}: {v.get('error')}  (plumbing OK if this is 'Above target')")
        mid += 1
    pool.s.close()
    print("\n[done] one-time send complete. The SDC ran cut off, stopped static, and its answer was submitted live.", flush=True)


if __name__ == "__main__":
    try: main()
    finally: _kill()
