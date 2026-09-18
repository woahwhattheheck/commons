#!/usr/bin/env python3
"""One-shot: read named mouths + many fixed spans as 1s and 0s. Two passes. Die.

No titan. No packer. No inject. No SHA. No hex. Host does not search primes.
Does not slurp a growing 100e9. Samples enough spans that "none" cannot hide.
"""
import os, struct, time, sys

PATH = r"C:\Users\lucys\Desktop\MUHL_DATACENTER\muhlnickel_dc.mno"
OUT = r"C:\Users\lucys\Desktop\MUHL_GO\_dc_use_bits.txt"
PLANT0 = 2147548550
PLANT_NEED = 102925
SLEEP_S = 8
SPAN = 256 * 1024
N_SPANS = 96

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError, ValueError):
        pass


def b8(x):
    return format(x, "08b")


def lines(blob, cap=None):
    if cap is not None:
        blob = blob[:cap]
    return "\n".join(b8(x) for x in blob)


def ones(blob):
    return sum(bin(x).count("1") for x in blob)


def rd(f, off, n):
    if off < 0:
        return b""
    f.seek(off)
    return f.read(n)


def named(f, end):
    fold = rd(f, 224, 48)
    n_rings = stride = fact_wire = net = 0
    if len(fold) >= 48:
        n_rings, stride = struct.unpack_from("<QQ", fold, 16)
        fact_wire, net = struct.unpack_from("<QQ", fold, 32)
    hdr = rd(f, 0, 224)
    fwd = rev = carry = pub = 0
    if len(hdr) >= 168:
        fwd, rev = struct.unpack_from("<QQ", hdr, 136)
        carry, pub = struct.unpack_from("<QQ", hdr, 152)
    w = []

    def add(name, off, n):
        if off < 0 or n <= 0 or off >= end:
            return
        take = n if off + n <= end else end - off
        w.append((name, off, take, rd(f, off, take)))

    add("HEADER", 0, 224)
    add("FOLD", 224, 48)
    add("CTRL_FWD", fwd, 32)
    add("CTRL_REV", rev, 32)
    add("CARRY", carry, 1)
    add("PUB", pub, 1)
    add("OPND", 338, 16)
    add("SEL", 354, 2)
    add("CTRL_G0", 356, 25)
    add("CTRL_LAST", 1981, 25)
    add("WIRE97", 97, 1)
    add("DIGEST0", 192, 32)
    idxs = [0, 1, 2, 7, 16, 32, 64, 100, 256, 1000, 4096, 10000, 32768, 65536, 100000]
    if n_rings > 2:
        idxs.extend([n_rings - 2, n_rings - 1, n_rings // 2, n_rings // 4, n_rings // 8])
    seen = set()
    for i in idxs:
        if i < 0 or (n_rings and i >= n_rings) or i in seen:
            continue
        seen.add(i)
        base = fact_wire + i * 66
        add("FACT_%d_FWD" % i, base, 32)
        add("FACT_%d_REV" % i, base + 32, 32)
        add("FACT_%d_CARRY" % i, base + 64, 1)
        add("FACT_%d_PUB" % i, base + 65, 1)
    add("FACT_GATES_HEAD", net, 125)
    add("PLANT_HEAD", PLANT0, 200)
    add("PLANT_187", PLANT0 + 187 * 25, 125)
    add("PLANT_LAST", PLANT0 + PLANT_NEED - 25, 25)
    add("PLANT_WHOLE", PLANT0, PLANT_NEED)
    add("AF_OUT", 8388791, 1)
    add("APERTURE", 8388608, 64)
    add("OFF_524288", 524288, 32)
    add("EOF_LAST25", end - 25, 25)
    return w, {
        "end": end,
        "n_rings": n_rings,
        "stride": stride,
        "fact_wire": fact_wire,
        "net": net,
        "fwd": fwd,
        "rev": rev,
        "carry": carry,
        "pub": pub,
    }


def spans(f, end):
    out = []
    if end <= 0:
        return out
    step = max(end // N_SPANS, SPAN)
    off = 0
    i = 0
    while off < end and i < N_SPANS:
        take = SPAN if off + SPAN <= end else end - off
        blob = rd(f, off, take)
        out.append((off, take, ones(blob), blob[:32]))
        off += step
        i += 1
    # last span always
    if end >= 32:
        last_off = end - min(SPAN, end)
        blob = rd(f, last_off, min(SPAN, end - last_off))
        out.append((last_off, len(blob), ones(blob), blob[:32]))
    return out


def flips(a, b, off):
    out = []
    lim = min(len(a), len(b))
    for i in range(lim):
        if a[i] == b[i]:
            continue
        xa, xb = a[i], b[i]
        for bit in range(8):
            mask = 1 << (7 - bit)
            if (xa & mask) != (xb & mask):
                out.append("%d bit%d  %d -> %d" % (off + i, bit, 1 if xa & mask else 0, 1 if xb & mask else 0))
    if len(a) != len(b):
        out.append("len %d -> %d" % (len(a), len(b)))
    return out


def dump(parts, name, off, blob, cap=None):
    parts.append("## %s @%d ones=%d bytes=%d" % (name, off, ones(blob), len(blob)))
    parts.append(lines(blob, cap))
    parts.append("")


def main():
    if not os.path.isfile(PATH):
        print("REFUSING: missing")
        return 2
    parts = []

    def P(s=""):
        parts.append(s)
        print(s, flush=True)

    with open(PATH, "rb") as f:
        magic = rd(f, 0, 8)
        if magic != b"MUHLDC01":
            print("REFUSING: magic not MUHLDC01")
            return 2
        f.seek(0, os.SEEK_END)
        end1 = f.tell()
        w1, meta1 = named(f, end1)
        s1 = spans(f, end1)

    P("DC_USE READ T1")
    P("titan not opened")
    P("packer not this file")
    P("no SHA")
    P("magic:")
    P(lines(magic))
    P("header named QWORDs: fwd=%d rev=%d carry=%d pub=%d" % (
        meta1["fwd"], meta1["rev"], meta1["carry"], meta1["pub"]))
    P("fold: n_rings=%d fact_wire=%d net=%d stride=%d" % (
        meta1["n_rings"], meta1["fact_wire"], meta1["net"], meta1["stride"]))
    P("T1 end address %d" % end1)
    named_vals = (meta1["fwd"], meta1["rev"], meta1["carry"], meta1["pub"],
                  meta1["fact_wire"], meta1["net"])
    P("524288 in header named QWORDs? %s" % ("YES" if 524288 in named_vals else "NO"))

    p1 = {n: (o, nlen, b) for n, o, nlen, b in w1}
    for name in ("CTRL_FWD", "CTRL_REV", "CARRY", "PUB", "CTRL_G0", "CTRL_LAST",
                 "FOLD", "WIRE97", "FACT_0_FWD", "FACT_0_CARRY", "FACT_0_PUB",
                 "PLANT_HEAD", "PLANT_187", "PLANT_LAST", "AF_OUT", "OFF_524288"):
        if name in p1:
            o, nlen, b = p1[name]
            cap = 32 if name in ("PLANT_HEAD", "PLANT_187") else None
            dump(parts, "T1 " + name, o, b, cap)
            print("## T1 %s @%d ones=%d" % (name, o, ones(b)), flush=True)
            print(lines(b, cap), flush=True)

    time.sleep(SLEEP_S)

    with open(PATH, "rb") as f:
        f.seek(0, os.SEEK_END)
        end2 = f.tell()
        w2, meta2 = named(f, end2)
        s2 = spans(f, end2)

    p2 = {n: (o, nlen, b) for n, o, nlen, b in w2}
    moved = []
    for n in p1:
        if n not in p2 or p1[n][2] != p2[n][2]:
            moved.append(n)

    P("T2 end address %d" % end2)
    P("NAMED_MOVED %s" % (",".join(moved) if moved else "none"))

    span_moved = 0
    for a in s1:
        match = None
        for b in s2:
            if b[0] == a[0]:
                match = b
                break
        if match is None:
            span_moved += 1
            continue
        if a[2] != match[2] or a[3] != match[3]:
            span_moved += 1
            P("SPAN_MOVED @%d T1_ones=%d T2_ones=%d" % (a[0], a[2], match[2]))
            P("T1 first32:")
            P(lines(a[3]))
            P("T2 first32:")
            P(lines(match[3]))
    P("spans sampled T1=%d T2=%d ones_or_head_moved=%d" % (len(s1), len(s2), span_moved))

    P("=== T2 named bits that moved ===")
    for name in moved:
        if name not in p1:
            continue
        o, nlen, b = p1[name]
        bb = p2[name][2] if name in p2 else b""
        cap = 64 if name in ("HEADER", "FOLD", "PLANT_HEAD", "PLANT_187") else None
        if name == "PLANT_WHOLE":
            P("## PLANT_WHOLE T1_ones=%d T2_ones=%d" % (ones(b), ones(bb)))
            continue
        P("## T1 %s @%d ones=%d" % (name, o, ones(b)))
        P(lines(b, cap))
        P("## T2 %s ones=%d" % (name, ones(bb)))
        P(lines(bb, cap))
        for fl in flips(b, bb, o)[:80]:
            P(fl)

    P("=== factory windows with ones (T1) ===")
    lit = 0
    for n, o, nlen, b in w1:
        if not n.startswith("FACT_"):
            continue
        c = ones(b)
        if c:
            lit += 1
            P("%s @%d ones=%d" % (n, o, c))
            P(lines(b, 32))
    if not lit:
        P("sampled factory fwd/rev/carry/pub: all zeros")

    if "PLANT_WHOLE" in p1:
        P("PLANT_WHOLE @%d ones=%d bytes=%d T2=%s" % (
            p1["PLANT_WHOLE"][0], ones(p1["PLANT_WHOLE"][2]), len(p1["PLANT_WHOLE"][2]),
            "SAME" if "PLANT_WHOLE" not in moved else "MOVED"))

    P("=== T2 still bits (named mouths) ===")
    for name in ("CTRL_FWD", "CTRL_REV", "CARRY", "PUB", "CTRL_LAST",
                 "FACT_0_CARRY", "FACT_0_PUB", "OFF_524288", "AF_OUT"):
        if name in p2:
            o, nlen, b = p2[name]
            P("## T2 %s @%d ones=%d" % (name, o, ones(b)))
            P(lines(b))

    with open(OUT, "w", encoding="utf-8", newline="\n") as o:
        o.write("\n".join(parts) + "\n")
    print("WROTE", OUT, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
