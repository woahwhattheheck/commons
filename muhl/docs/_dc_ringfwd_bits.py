#!/usr/bin/env python3
"""Bounded 1/0 reader for muhlnickel_dc.mno. No inject. No titan. Dies."""
import os, struct, sys, time

PKG = r"C:\Users\lucys\Desktop\MUHL_DATACENTER\muhlnickel_dc.mno"


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


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "T"
    st = os.stat(PKG)
    size = st.st_size
    print("TAG", tag)
    print("NOW", time.time())
    print("DISK_BYTES", size)
    print("MTIME", st.st_mtime)
    with open(PKG, "rb") as f:
        hdr = rd(f, 0, 224)
        if hdr is None:
            print("REFUSING: short header")
            return 2
        print("MAGIC_BITS", bits(hdr[0:8]))
        n_in, n_wire, n_gate, n_out = struct.unpack_from("<IIII", hdr, 8)
        ring_gates, cells, senses, ticks = struct.unpack_from("<IIII", hdr, 24)
        wire, wire_len = struct.unpack_from("<QQ", hdr, 40)
        ring, ring_len = struct.unpack_from("<QQ", hdr, 56)
        net, net_len = struct.unpack_from("<QQ", hdr, 72)
        fold_off, fold_len = struct.unpack_from("<QQ", hdr, 104)
        fwd, rev = struct.unpack_from("<QQ", hdr, 136)
        carry, pub = struct.unpack_from("<QQ", hdr, 152)
        total = struct.unpack_from("<Q", hdr, 184)[0]
        fold = rd(f, 224, 48)
        fact_wire = 0
        if fold is not None:
            fact_wire = struct.unpack_from("<QQ", fold, 32)[0]
        named = {
            "n_in": n_in, "n_wire": n_wire, "n_gate": n_gate, "n_out": n_out,
            "ring_gates": ring_gates, "cells": cells, "senses": senses, "ticks": ticks,
            "wire": wire, "wire_len": wire_len, "ring": ring, "ring_len": ring_len,
            "net": net, "net_len": net_len, "fold_off": fold_off, "fold_len": fold_len,
            "fwd": fwd, "rev": rev, "carry": carry, "pub": pub, "total": total,
            "fact_wire": fact_wire,
        }
        hits = [k for k, v in named.items() if v == 524288]
        print("HEADER_EQ_524288", hits if hits else "NONE")
        print("OFFSET_524288_IN_FILE", 524288 < size)
        print("HEADER_FWD", fwd)
        print("HEADER_REV", rev)
        print("HEADER_CARRY", carry)
        print("HEADER_PUB", pub)
        print("HEADER_TOTAL", total)
        print("FACT_WIRE", fact_wire)
        print("DIGEST_BITS", bits(hdr[192:224]))
        print("DIGEST_ONES", ones(hdr[192:224]))

        windows = [
            ("magic@0", 0, 8),
            ("fwd@272", 272, 32),
            ("rev@304", 304, 32),
            ("carry@336", 336, 1),
            ("pub@337", 337, 1),
            ("wire@97", 97, 1),
            ("digest@192", 192, 32),
            ("ctrl_g0@356", 356, 25),
            ("ring_fwd@524288", 524288, 1),
            ("ring_fwd@524288_32", 524288, 32),
            ("ring_cell@524289", 524289, 1),
            ("ring_cell@524290", 524290, 1),
            ("ring_cell@524291", 524291, 1),
            ("ring_cell@524319", 524319, 1),
            ("ring_cell@524351", 524351, 1),
            ("aperture@8388608", 8388608, 8),
            ("autofab_last_out@8388791", 8388791, 1),
        ]
        if fact_wire:
            windows.extend([
                ("factory0_fwd8", fact_wire, 8),
                ("factory0_carry", fact_wire + 64, 1),
                ("factory0_pub", fact_wire + 65, 1),
                ("factory1_fwd8", fact_wire + 66, 8),
                ("factory1_carry", fact_wire + 66 + 64, 1),
                ("factory1_pub", fact_wire + 66 + 65, 1),
                ("factory2_carry", fact_wire + 132 + 64, 1),
                ("factory2_pub", fact_wire + 132 + 65, 1),
            ])
        if size >= 25:
            windows.append(("eof_tail", size - 25, 25))
        mid = size // 2
        windows.append(("mid8", mid, 8))
        windows.append(("near_eof8", size - 8, 8))

        for name, off, n in windows:
            if off + n > size:
                print("SHORT", name, "off", off, "n", n)
                continue
            b = rd(f, off, n)
            if b is None:
                print("SHORT", name, "off", off, "n", n)
                continue
            print("WIN", name, "off", off, "n", n, "ones", ones(b), "zeros", n * 8 - ones(b))
            print("  BITS", bits(b) if n <= 32 else bits(b[:32]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
