#!/usr/bin/env python3
"""Fixed-offset 1/0 extras. No inject. Dies."""
import os, struct, sys

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
    size = os.path.getsize(PKG)
    print("DISK_BYTES", size)
    with open(PKG, "rb") as f:
        print("TOTAL@184_BITS", bits(rd(f, 184, 8)))
        plant0 = 2147548550
        if size >= plant0 + 25:
            b = rd(f, plant0, 25)
            print("AUTOFAB0_REC0_BITS", bits(b), "ones", ones(b))
            op, a, bb, o = struct.unpack("<BQQQ", b)
            print("AUTOFAB0_REC0_DEC", op, a, bb, o)
        # planted recs that touch 336/337 sit at plant0 + rec*25
        for rec, name in ((187, "rec187_out336"), (188, "rec188_a336"), (189, "rec189_out337"), (191, "rec191_b337")):
            off = plant0 + rec * 25
            if size >= off + 25:
                b = rd(f, off, 25)
                op, a, bb, o = struct.unpack("<BQQQ", b)
                print(name, "op", op, "a", a, "b", bb, "o", o)
                print(" ", bits(b))
        # same mid as BEFORE (fixed), not size//2
        fixed_mids = (8511985609, 8810706889, 9037383625)
        for off in fixed_mids:
            if off + 8 <= size:
                b = rd(f, off, 8)
                print("FIXED8", off, bits(b), "ones", ones(b))
            else:
                print("FIXED8", off, "SHORT")
        # old sealed EOF neighborhood (seed 2147548550 area already planted)
        old_eof = 2147651475
        if old_eof + 8 <= size:
            print("PAST_OLD_EOF8", bits(rd(f, old_eof, 8)))
        # factory ring near old 2GiB end vs a later replica
        for name, off in (("fact_at_2g_ish", 2147548550 - 66), ("fact_at_8g", 8000000000), ("fact_at_16g", 16000000000)):
            if off + 8 <= size:
                print(name, bits(rd(f, off, 8)), "ones", ones(rd(f, off, 8)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
