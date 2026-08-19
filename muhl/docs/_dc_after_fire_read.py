#!/usr/bin/env python3
"""Bounded bit reader for muhlnickel_dc.mno. No inject. No titan. Dies."""
import os, struct, sys, time

PKG = r"C:\Users\lucys\Desktop\MUHL_DATACENTER\muhlnickel_dc.mno"
G = struct.Struct("<BQQQ")


def bits(b):
    return " ".join(format(x, "08b") for x in b)


def ones(b):
    return sum(bin(x).count("1") for x in b)


def rd(f, off, n):
    f.seek(off)
    b = f.read(n)
    if len(b) != n:
        return None
    return b


def rec(b):
    if b is None or len(b) != 25:
        return None
    return G.unpack(b)


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "T"
    st = os.stat(PKG)
    size = st.st_size
    mtime = st.st_mtime
    print("TAG", tag)
    print("NOW", time.time())
    print("SIZE", size)
    print("MTIME", mtime)
    with open(PKG, "rb") as f:
        hdr = rd(f, 0, 224)
        fold = rd(f, 224, 48)
        if hdr is None or fold is None:
            print("REFUSING: short header")
            return 2
        print("MAGIC", hdr[0:8])
        print("MAGIC_BITS", bits(hdr[0:8]))
        n_in, n_wire, n_gate, n_out = struct.unpack_from("<IIII", hdr, 8)
        ring_gates, cells, senses, ticks = struct.unpack_from("<IIII", hdr, 24)
        wire, wire_len = struct.unpack_from("<QQ", hdr, 40)
        ring, ring_len = struct.unpack_from("<QQ", hdr, 56)
        net, net_len = struct.unpack_from("<QQ", hdr, 72)
        netwire, netwire_len = struct.unpack_from("<QQ", hdr, 88)
        fold_off, fold_len = struct.unpack_from("<QQ", hdr, 104)
        lanes, outs_off = struct.unpack_from("<QQ", hdr, 120)
        fwd, rev = struct.unpack_from("<QQ", hdr, 136)
        carry, pub = struct.unpack_from("<QQ", hdr, 152)
        opnd, sel = struct.unpack_from("<QQ", hdr, 168)
        total = struct.unpack_from("<Q", hdr, 184)[0]
        digest = hdr[192:224]
        addr_bits, winner_only, stored, fold_senses = struct.unpack_from("<IIII", fold, 0)
        n_rings, stride = struct.unpack_from("<QQ", fold, 16)
        fact_wire, fact_net = struct.unpack_from("<QQ", fold, 32)
        named = {
            "n_in": n_in, "n_wire": n_wire, "n_gate": n_gate, "n_out": n_out,
            "ring_gates": ring_gates, "cells": cells, "senses": senses, "ticks": ticks,
            "wire": wire, "wire_len": wire_len, "ring": ring, "ring_len": ring_len,
            "net": net, "net_len": net_len, "netwire": netwire, "netwire_len": netwire_len,
            "fold_off": fold_off, "fold_len": fold_len, "lanes": lanes, "outs_off": outs_off,
            "fwd": fwd, "rev": rev, "carry": carry, "pub": pub, "opnd": opnd, "sel": sel,
            "total": total, "addr_bits": addr_bits, "winner_only": winner_only,
            "stored": stored, "fold_senses": fold_senses, "n_rings": n_rings,
            "stride": stride, "fact_wire": fact_wire, "fact_net": fact_net,
        }
        print("HEADER_NAMED", named)
        hits_524288 = [k for k, v in named.items() if v == 524288]
        print("HEADER_EQ_524288", hits_524288 if hits_524288 else "NONE")
        print("OFFSET_524288_IN_FILE", 524288 < size)
        print("DIGEST_HEX", digest.hex())
        print("DIGEST_ONES", ones(digest))

        windows = [
            ("fwd@hdr", fwd, 32),
            ("rev@hdr", rev, 32),
            ("carry@hdr", carry, 1),
            ("pub@hdr", pub, 1),
            ("ctrl_wire@272", 272, 84),
            ("ring_fwd_off_524288", 524288, 32),
            ("factory0_wire", fact_wire, 66),
            ("factory1_wire", fact_wire + 66, 66),
            ("factory2_wire", fact_wire + 132, 66),
            ("factory0_fwd8", fact_wire, 8),
            ("factory0_carry", fact_wire + 64, 1),
            ("factory0_pub", fact_wire + 65, 1),
            ("factory1_carry", fact_wire + 66 + 64, 1),
            ("factory1_pub", fact_wire + 66 + 65, 1),
            ("factory2_carry", fact_wire + 132 + 64, 1),
            ("factory2_pub", fact_wire + 132 + 65, 1),
            ("ctrl_g0@356", 356, 25),
            ("ctrl_glast", 356 + 65 * 25, 25),
        ]
        if size >= 25:
            windows.append(("autofab0_tail", size - 25, 25))
        plant0 = 2147548550
        if size >= plant0 + 25:
            windows.append(("autofab0_rec0", plant0, 25))
        # factory ring whose wire start is nearest 524288
        if fact_wire and 524288 >= fact_wire:
            idx = (524288 - fact_wire) // 66
            base = fact_wire + idx * 66
            windows.append(("factory_near524288_idx", idx, 0))
            windows.append(("factory_near524288_wire", base, 66))

        samples = {}
        for name, off, n in windows:
            if n == 0:
                print("NOTE", name, off)
                continue
            if off + n > size:
                print("SHORT", name, "off", off, "n", n, "size", size)
                continue
            b = rd(f, off, n)
            samples[name] = (off, b)
            print("WIN", name, "off", off, "n", n, "ones", ones(b), "zeros", n * 8 - ones(b))
            print("  BIN", bits(b) if n <= 84 else bits(b[:32]) + " ...")
            print("  HEX", b.hex() if n <= 84 else b[:32].hex() + "...")

        g0 = rec(samples.get("ctrl_g0@356", (0, None))[1])
        gl = rec(samples.get("ctrl_glast", (0, None))[1])
        print("CTRL_G0", g0, "out==in", (g0[3] == g0[1] or g0[3] == g0[2]) if g0 else None)
        print("CTRL_GLAST", gl, "out==in", (gl[3] == gl[1] or gl[3] == gl[2]) if gl else None)
        tail = rec(samples.get("autofab0_tail", (0, None))[1])
        rec0 = rec(samples.get("autofab0_rec0", (0, None))[1])
        print("AUTOFAB0_TAIL", tail, "out==in", (tail[3] == tail[1] or tail[3] == tail[2]) if tail else None)
        print("AUTOFAB0_REC0", rec0, "out==in", (rec0[3] == rec0[1] or rec0[3] == rec0[2]) if rec0 else None)

        # planted AUTOFAB0: scan 4117 records for out==in and 336/337
        if size >= plant0 + 102925:
            f.seek(plant0)
            blob = f.read(102925)
            nrec = len(blob) // 25
            self_clock = []
            hit_336_337 = []
            ring_524288 = []
            for i in range(nrec):
                op, a, b, o = G.unpack(blob[i * 25:(i + 1) * 25])
                if o == a or o == b:
                    if len(self_clock) < 12:
                        self_clock.append((i, op, a, b, o))
                    elif self_clock[-1][0] != i:
                        pass
                if 336 in (a, b, o) or 337 in (a, b, o):
                    hit_336_337.append((i, op, a, b, o))
                if 524288 in (a, b, o) or (524288 <= a <= 524543) or (524288 <= b <= 524543) or (524288 <= o <= 524543):
                    if len(ring_524288) < 8:
                        ring_524288.append((i, op, a, b, o))
            n_self = sum(1 for i in range(nrec) if (lambda t: t[3] == t[1] or t[3] == t[2])(G.unpack(blob[i * 25:(i + 1) * 25])))
            print("PLANTED_NREC", nrec)
            print("PLANTED_ONES", ones(blob), "ZEROS", nrec * 25 * 8 - ones(blob))
            print("PLANTED_SELF_CLOCK_COUNT", n_self)
            print("PLANTED_SELF_CLOCK_FIRST", self_clock)
            print("PLANTED_336_337", hit_336_337)
            print("PLANTED_RING_524288_FIRST", ring_524288)
        else:
            print("PLANTED_ABSENT_OR_SHORT", size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
