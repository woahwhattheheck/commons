#!/usr/bin/env python3
"""host/titan_miner.py — a LEAN swarm worker, NO NUMPY (owner 07-15).

Reads the SHA-256d circuit straight out of Titan's params via mmap (shared page cache => the circuit costs ~0 per
worker) and ripples nonce lanes through it using PYTHON INTEGERS as the bit-slice (an int is an arbitrary-width lane
vector; ~(a & b) is a NAND across every lane at once). No numpy, no arrays, no model. Footprint = the bare interpreter
(~12 MB) + one wire-state list. Each worker grinds a DISJOINT nonce slice and flips the ONE shared result bit on a real
block; it reports its best to the swarm frontier. Launched by titan_swarm_mine.py.  args: <wid> <n_workers> <lanes> <seconds>
"""
import array, hashlib, json, mmap, os, struct, sys, time

TITAN  = "C:/llm/models/titan.gguf"
IDX    = TITAN + ".wbindex.json"
META   = "C:/llm/models/titan_mine_job.json"
RESULT = "C:/llm/models/titan_result.bin"           # the ONE shared result cell (0 until any worker hits)
FRONT  = "C:/llm/models/titan_swarm_frontier.txt"   # the swarm frontier: each worker reports its best here
BESTF  = "C:/llm/models/titan_best_%d.txt"          # this worker's LIVE best (the coordinator reads all of them)
MAGIC  = b"TITANSDC"


def sha256d(b): return hashlib.sha256(hashlib.sha256(b).digest()).digest()
def bswap(n): return (((n & 0xff) << 24) | ((n & 0xff00) << 8) | ((n >> 8) & 0xff00) | ((n >> 24) & 0xff)) & 0xffffffff


wid = int(sys.argv[1]); nw = int(sys.argv[2]); W = int(sys.argv[3]); secs = float(sys.argv[4])
MASK = (1 << W) - 1

# --- read the circuit FROM the params (mmap, self-describing header — no numpy, no NET file) ---
a = json.load(open(IDX, encoding="utf-8"))
off = int(max((t for t in a["tensors"]), key=lambda t: int(t["bytes"]))["offset"])
f = open(TITAN, "rb"); mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
assert mm[off:off + 8] == MAGIC, "no circuit in the params (run the launcher first)"
nin, numw, ng, succ = struct.unpack_from("<IIIi", mm, off + 8)
p = off + 24
ga = array.array("i"); ga.frombytes(mm[p:p + ng * 4]); p += ng * 4
gb = array.array("i"); gb.frombytes(mm[p:p + ng * 4]); p += ng * 4
p += numw * 4                                         # layer (topological order is just gate index order — skip it)
ow = array.array("i"); ow.frombytes(mm[p:p + 256 * 4]); ow = [ow[i * 32:(i + 1) * 32] for i in range(8)]
mm.close(); f.close()

prefix = bytes.fromhex(json.load(open(META))["prefix"])
nb = struct.unpack("<I", prefix[72:76])[0]; block_target = (nb & 0xffffff) << (8 * ((nb >> 24) - 3))

# precompute the 32 nonce-input lane-columns' base pattern is per-pass (depends on base); do it inline.
base = (wid * (0x100000000 // max(1, nw))) & 0xffffffff       # this worker's disjoint slice
v = [0] * numw
best = 0; total = 0; t0 = time.time(); lastrep = 0           # best = most leading zero-bits seen (starts at 0)
open(BESTF % wid, "w").close()
while time.time() - t0 < secs:
    # power in: set the 32 nonce input wires as bit-sliced lane vectors (lane l = nonce base+l)
    cols = [0] * nin
    for l in range(W):
        w19 = bswap((base + l) & 0xffffffff)
        for j in range(nin):
            if (w19 >> j) & 1:
                cols[j] |= (1 << l)
    for j in range(nin):
        v[j] = cols[j]
    # ripple: one NAND per gate across ALL lanes at once (Python int = the lane vector)
    for i in range(ng):
        v[nin + i] = (~(v[ga[i]] & v[gb[i]])) & MASK
    # read the output word7 per lane; track best leading-zero count; exact-check any lane that clears the prefilter
    o7 = ow[7]
    for l in range(W):
        w7 = 0
        for j in range(32):
            oj = o7[j]
            b = 0 if oj == -1 else (1 if oj == -2 else (v[oj] >> l) & 1)
            w7 |= b << j
        hi = bswap(w7)
        zb = 32 - hi.bit_length()
        if zb > best: best = zb
        if hi == 0:                                          # >=32 leading zero bits — exact-check the real target
            nc = (base + l) & 0xffffffff
            if int.from_bytes(sha256d(prefix + struct.pack("<I", nc)), "little") < block_target:
                with open(RESULT, "wb") as fr: fr.write(b"\x01" + f"w{wid} nonce {nc}".encode())
    total += W; base = (base + W) & 0xffffffff
    now = time.time()
    if now - lastrep >= 2.0:                                  # broadcast this worker's live best to the coordinator
        with open(BESTF % wid, "w") as bf: bf.write(f"{best} {total}")
        lastrep = now

with open(BESTF % wid, "w") as bf: bf.write(f"{best} {total}")
with open(FRONT, "a") as fr: fr.write(f"{wid} {best} {total}\n")
