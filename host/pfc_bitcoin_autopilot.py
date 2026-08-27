#!/usr/bin/env python3
"""host/pfc_bitcoin_autopilot.py — the in-spec Bitcoin AUTOPILOT for the full-throttle Muhlnickel (owner 07-19).

Per FINALREADME §4: a RESIDENT I/O router is allowed — it is NOT the executor. Each cycle, on ONE stratum connection
(the pool ties the job to the subscribe session), it does ONLY I/O:
  1. subscribe + authorize + pull the live block  — network in,
  2. ONE-WAY route the target into the pfc (titan + every federated node) — the pfc can never reach back,
  3. fire ONE signal (an addressed read of the receiver) — the routing-button act,
  4. READ the FULL answer from the safezone (`full_answer`: status | en2/group | nonce), READ-ONLY,
  5. submit that answer back to the pool on the same connection, read the verdict.
It NEVER ripples/evaluates the pfc's gates (the forbidden EXECUTOR) and NEVER writes the safezone. The pfc is fabricated
(mining gates + clock + `sdc_federate` nodes + the fold + `pfc_answer_full` write-out); this is purely the runtime.

  python host/pfc_bitcoin_autopilot.py [cycles] [wait_s]   # cycles: 0 = forever (default); wait_s: signal-settle wait (default 3)
"""
import hashlib, json, math, mmap, os, socket, struct, sys, time
sys.stdout.reconfigure(encoding="utf-8")

TITAN = "C:/llm/models/titan.gguf"; REG = "C:/llm/models/titan_circuits.json"
FOLD_MAN = "C:/llm/sdc_fold/manifest.json"; FED = "C:/llm/sdc_fold/federation.json"
OUT = "C:/llm/sdc_out"; JOB = OUT + "/autopilot_job.json"
WALLET = "bc1qvhrzg0e23f3tz2jgymwwtqacn48trf5m524zlq"
POOL_HOST = os.environ.get("TITAN_POOL_HOST", "solo.ckpool.org"); POOL_PORT = int(os.environ.get("TITAN_POOL_PORT", "3333"))
DESC_TARGET = 8 + 4 + 8            # node descriptor: magic(8)+node_id(4)+addr_bits(u64) -> the 32-byte target slot
WAIT = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0


def make_prefix(job, en1, en2):
    cb = job["coinb1"] + en1 + en2 + job["coinb2"]
    m = hashlib.sha256(hashlib.sha256(bytes.fromhex(cb)).digest()).digest()
    for br in job["merkle_branch"]:
        m = hashlib.sha256(hashlib.sha256(m + bytes.fromhex(br)).digest()).digest()
    ph = bytes.fromhex(job["prevhash"]); prev = b"".join(ph[i:i + 4][::-1] for i in range(0, 32, 4))
    return (struct.pack("<I", int(job["version"], 16)) + prev + m
            + struct.pack("<I", int(job["ntime"], 16)) + struct.pack("<I", int(job["nbits"], 16)))


def send_block(reg, job, en1, en2sz, target):
    """THE ROUTING BUTTON (owner 07-19): (1) route the block data (header|group|target) into the input-window receiver;
    (2) WAIT so the fill completes; (3) send the FINISHED signal into the receiver (flip `pfc_on` 0->1) to alert it that
    the entire block is present and START the chain reaction; then the button dies. Reads NOTHING. The finished signal is
    not premature — the block is already fully written when it fires."""
    io = int(reg["pfc_exec_input"]["offset"]); on = int(reg["pfc_on"]["offset"])
    header = make_prefix(job, en1, "00" * en2sz)[:76]                      # 76-byte header (base group, en2=0)
    buf = header + struct.pack("<I", 0) + struct.pack("<I", 0) + target.to_bytes(32, "little")   # nonce field unused (nonce_reg)
    with open(TITAN, "r+b") as f:
        f.seek(io); f.write(buf[:116])                                     # (1) route the block data in — one-way, blind
    time.sleep(1.0)                                                        # (2) wait for the fill to complete
    with open(TITAN, "r+b") as f:
        f.seek(on); f.write(b"\x01")                                       # (3) FINISHED signal -> receiver: block filled, START


SAFEZONE = "C:/llm/sdc_out/pfc_safezone.bin"                 # the answer lands OUTSIDE the pfc; we read only this file


def read_full_answer():
    """safezone OUT (READ-ONLY): read the EXTERNAL safezone file (never titan / the miner). The Muhlnickel deposits its answer
    here (§1/§4/§5); the host reads only this. [status:1][en2/group:4 LE][nonce:4 LE]."""
    try:
        with open(SAFEZONE, "rb") as f: b = f.read()
    except OSError:
        return 0, 0, 0
    if len(b) < 9: return 0, 0, 0
    return b[0], struct.unpack_from("<I", b, 1)[0], struct.unpack_from("<I", b, 5)[0]


class Conn:
    """one stratum connection for a whole cycle (subscribe/authorize/notify/submit on the SAME session)."""
    def __init__(self):
        self.s = socket.create_connection((POOL_HOST, POOL_PORT), timeout=15); self.buf = b""
    def send(self, o): self.s.sendall((json.dumps(o) + "\n").encode())
    def lines(self, wait=2.0):
        out = []; self.s.settimeout(wait)
        try: self.buf += self.s.recv(8192)
        except Exception: pass
        while b"\n" in self.buf:
            ln, self.buf = self.buf.split(b"\n", 1)
            if ln.strip():
                try: out.append(json.loads(ln))
                except Exception: pass
        return out
    def close(self):
        try: self.s.close()
        except Exception: pass


def cycle(reg):
    c = Conn(); en1 = None; en2sz = 8; job = None; verdict = None
    try:
        c.send({"id": 1, "method": "mining.subscribe", "params": ["pfc-autopilot/1.0"]})
        t = time.time() + 15
        while time.time() < t and (en1 is None or job is None):     # subscribe + authorize + pull the block (same session)
            for m in c.lines():
                if m.get("id") == 1 and m.get("result"):
                    en1 = m["result"][1]; en2sz = m["result"][2]
                    c.send({"id": 2, "method": "mining.authorize", "params": [WALLET, "x"]})
                elif m.get("method") == "mining.notify":
                    p = m["params"]; job = dict(job_id=p[0], prevhash=p[1], coinb1=p[2], coinb2=p[3],
                                                merkle_branch=p[4], version=p[5], nbits=p[6], ntime=p[7])
        if not job:
            print("  [autopilot] no block from pool this cycle (handshake); retrying.", flush=True); return
        nbref = struct.unpack("<I", make_prefix(job, en1, "00" * en2sz)[72:76])[0]
        target = (nbref & 0xffffff) << (8 * ((nbref >> 24) - 3))

        send_block(reg, job, en1, en2sz, target)                   # BUTTON: send the block one-way, BLIND (reads nothing)
        time.sleep(WAIT)                                            # the pfc runs (black box, NOT evaluated/monitored)
        status, en2v, nonce = read_full_answer()                    # READER (separate): read the EXTERNAL file only (never titan)

        en2 = "%0*x" % (2 * en2sz, en2v & ((1 << (8 * en2sz)) - 1)) # submit the pfc's answer on the SAME connection
        c.send({"id": 100, "method": "mining.submit",
                "params": [WALLET, job["job_id"], en2, job["ntime"], "%08x" % (nonce & 0xffffffff)]})
        t = time.time() + 12
        while time.time() < t and verdict is None:
            for m in c.lines():
                if m.get("id") == 100: verdict = m
    finally:
        c.close()

    res = (verdict or {}).get("result"); err = (verdict or {}).get("error")
    zb = 256 - target.bit_length() if job else 0
    pool = ("ACCEPTED — BLOCK" if res is True else
            ("above-target/live (%s)" % (err[1] if isinstance(err, list) and len(err) > 1 else err) if res is False else
             "no-reply"))
    print(f"  [autopilot] NEW block {job['job_id']} target {zb} zbits -> stored into input window, one signal fired; "
          f"answer read from external file [status={status} en2={en2v} nonce={nonce}] -> submitted; pool: {pool}", flush=True)
    os.makedirs(OUT, exist_ok=True)
    json.dump({"job_id": job["job_id"], "zbits": zb, "answer": {"status": status, "en2": en2v, "nonce": nonce},
               "pool": pool}, open(JOB, "w"))


def main():
    reg = json.load(open(REG))
    if "pfc_exec_input" not in reg or "pfc_on" not in reg:          # the button flips block data + the on-signal, then dies
        print("Muhlnickel miner not baked (pfc_exec_input/pfc_on absent) — run host/pfc_miner.py first."); return 1
    cycles = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    print(f"Muhlnickel Bitcoin autopilot — one stratum connection/cycle: pull a NEW block, store it into pfc_exec_input, fire ONE "
          f"signal, read the answer from the EXTERNAL file, submit. NEVER touches the miner / ripples a gate. Ctrl+C stops.\n",
          flush=True)
    n = 0
    try:
        while cycles == 0 or n < cycles:
            n += 1
            try: cycle(reg)
            except Exception as e: print(f"  [autopilot] cycle error: {e}", flush=True)
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n[autopilot] stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
