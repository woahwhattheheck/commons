#!/usr/bin/env python3
"""host/titan_mine_worker.py — the GATED SANDBOX mining worker (owner 07-15; docs/WHITEBOX_SANDBOX.md).

The mining is SANDBOXED. This process is handed its work ONE-WAY (a nonce slice via argv + the live job file), reads the
SHA-256d circuit that lives IN titan.gguf's PARAMS by mmap (the circuit is ADDRESSED in storage, never copied out — the
~40 GB model costs ~0; only the ~8 MB netlist region is touched), and ripples a wide population of nonce-lanes through it
with power from the wall (bit-sliced: one uint64 op flips a gate across 64 lanes at once — speed of light, as many ops as
the burst allows; the PC is plugged in). Every couple seconds it FREEZES a complete static snapshot of its best result +
any real-target hit to --result (atomic write), and when its bounded window ends it freezes a final snapshot and EXITS.
A dead process draws zero compute. This worker NEVER touches the network — it cannot reach back into the PC. The
coordinator (titan_mine_demo.py) starts it, reads only the STATIC frozen snapshots, re-checks any hit, and submits any
block to the wallet. Reuses the proven, byte-exact ripple in titan_sdc.py (no logic reimplemented here).

  python titan_mine_worker.py --off <circuit_byte_offset> --base <nonce> --width <W> --seconds <s> --result <file>
"""
import hashlib, json, mmap, os, struct, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import titan_sdc as T

SNAP = 2.0                                                      # seconds between static snapshots


def sha256d(b): return hashlib.sha256(hashlib.sha256(b).digest()).digest()


def read_circuit_from_params(off):
    """address the circuit netlist in titan.gguf's params by offset (mmap) — sandboxed in storage, model cost ~0."""
    f = open(T.TITAN, "rb"); mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    try:
        assert mm[off:off + 8] == T.MAGIC, "no circuit at this offset in the params"
        nin, numw, ng, succ = struct.unpack_from("<IIIi", mm, off + 8)
        total = 24 + ng * 4 + ng * 4 + numw * 4 + 256 * 4
        return T.parse_circuit(bytes(mm[off:off + total]))     # parse the addressed region; nothing else is touched
    finally:
        mm.close(); f.close()


def freeze(result, out):
    """write a COMPLETE static snapshot atomically, so the coordinator only ever reads a finished frozen file."""
    if not result:
        return
    tmp = result + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f)
    os.replace(tmp, result)


def main():
    a = {}
    args = sys.argv[1:]
    for i in range(0, len(args) - 1, 2):
        if args[i].startswith("--"):
            a[args[i][2:]] = args[i + 1]
    off = int(a.get("off", "0")); base0 = int(a.get("base", "0"))
    W = max(1, int(a.get("width", "96"))); seconds = float(a.get("seconds", "60"))
    result = a.get("result")

    j = json.load(open(T.META)); prefix = bytes.fromhex(j["prefix"])
    nb = struct.unpack("<I", prefix[72:76])[0]; block_target = (nb & 0xffffff) << (8 * ((nb >> 24) - 3))

    C = read_circuit_from_params(off)
    groups = T.groups_of(C)                                     # build the layer-parallel ripple index once (amortized)
    v = np.empty((C["numw"], W), np.uint64)                    # the transient wire-state (the compute); dies with us

    base = base0 & 0xffffffff
    best_hi = 1 << 32; best_nonce = base0; lanes = 0; hits = []
    t0 = time.time(); snap_next = t0 + SNAP
    while time.time() - t0 < seconds:
        nn, B = T.ripple(C, groups, base, W, v)                # power in: ripple 64*W nonce-lanes through the circuit
        for lane in T.succ_lanes(C, v, B).tolist():            # any lane whose success gate fired -> exact-check locally
            nc = int(nn[lane])
            if int.from_bytes(sha256d(prefix + struct.pack("<I", nc)), "little") < block_target:
                hits.append(nc)
        w7 = T.word7(C, v, B); k = int(np.argmin(w7))          # track the frontier (fewest-nonzero => most leading zeros)
        if int(w7[k]) < best_hi:
            best_hi = int(w7[k]); best_nonce = int(nn[k])
        lanes += B; base = (base + B) & 0xffffffff
        if time.time() >= snap_next:
            freeze(result, {"best_hi": best_hi, "best_nonce": best_nonce, "best_zbits": T.zbits(best_hi),
                            "lanes": lanes, "hits": hits, "done": False})
            snap_next = time.time() + SNAP

    freeze(result, {"best_hi": best_hi, "best_nonce": best_nonce, "best_zbits": T.zbits(best_hi),
                    "lanes": lanes, "hits": hits, "done": True})   # final static snapshot, then EXIT (zero draw after)
    return 0


if __name__ == "__main__":
    sys.exit(main())
