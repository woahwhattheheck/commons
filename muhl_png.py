#!/usr/bin/env python3
"""
muhl_png.py  v2 - surface bytes as PNG and as numbers. Read, emit, die.

Pure stdlib: zlib + struct + math. NO numpy. NO Pillow. NO third-party anything.
Nothing is ever mutated. Sources are opened 'rb' and never written.
ADDITIVE: every v1 mode still behaves exactly as it did. v2 only adds.

WHY THIS WORKS
  A PNG is four chunks and a zlib stream:
    magic  89 50 4E 47 0D 0A 1A 0A
    IHDR   width, height, bitdepth=8, colortype (0=gray, 2=RGB), 0,0,0
    IDAT   zlib.compress( each row prefixed with one filter byte 0x00 )
    IEND   empty
  Chunk = >I length | 4-byte tag | data | >I crc32(tag+data).
  That is the entire format. No library is required to write one.

RENDER MODES (v1, unchanged)
  bits   FILE OUT.png    one pixel per BIT.  white=1 black=0.
  bytes  FILE OUT.png    one pixel per BYTE. grayscale, value IS the grey.
  rgb    FILE OUT.png    three bytes per pixel, raw triples.
  ppm    IN.ppm OUT.png  P6 netpbm -> png.
  sheet  DIR  OUT.png    all *.ppm in DIR as a contact sheet.
  delta  DIR             frame-to-frame pixel delta report.

MEASURE MODES (v2, new)
  stats  FILE            ones%, entropy, byte histogram summary, run lengths.
  cols   FILE            per-bit-column occupancy at --stride. which bits are ever live.
  fields FILE            unpack <BQQQ> records: op census, field ranges,
                         and out->a/b collision count.
  diff   A B OUT.png     XOR two files. renders ONLY the bits that differ.
                         this is the instrument for a file that changes under you.
  heat   FILE OUT.png    ones-density per record as a colour ramp.
  hist   FILE OUT.png    byte-value histogram as an image.

COMMON FLAGS
  --width N    pixels per row (default 256). 200 = one 25-byte record per row.
  --scale N    nearest-neighbour magnify (default 1). no resampling, ever.
  --offset N   start byte. --len N  byte count. window a huge file cheaply.
  --stride N   record size in bytes (default 25).
  --cols N     contact-sheet columns (default 4).  --gutter N (default 4).
"""
import zlib, struct, sys, os, glob, math
from collections import Counter

# ---------------- the entire PNG writer ----------------
def png(path, w, h, data, gray=False):
    stride = w * (1 if gray else 3)
    raw = b''.join(b'\x00' + data[y*stride:(y+1)*stride] for y in range(h))
    def chunk(tag, payload):
        return (struct.pack('>I', len(payload)) + tag + payload
                + struct.pack('>I', zlib.crc32(tag + payload) & 0xffffffff))
    out = (b'\x89PNG\r\n\x1a\n'
           + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 0 if gray else 2, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(raw, 9))
           + chunk(b'IEND', b''))
    with open(path, 'wb') as f:
        f.write(out)
    return len(out)
# -------------------------------------------------------


def scale_up(data, w, h, s, chans):
    if s == 1:
        return data, w, h
    W, H = w * s, h * s
    buf = bytearray(W * H * chans)
    for y in range(h):
        row = data[y*w*chans:(y+1)*w*chans]
        big = bytearray()
        for x in range(w):
            big += row[x*chans:(x+1)*chans] * s
        for dy in range(s):
            o = ((y*s+dy) * W) * chans
            buf[o:o+W*chans] = big
    return bytes(buf), W, H


def read_ppm(path):
    d = open(path, 'rb').read()
    if d[:2] != b'P6':
        raise SystemExit(path + ": not P6 binary ppm")
    tok, i = [], 2
    while len(tok) < 3:
        while i < len(d) and d[i:i+1].isspace():
            i += 1
        if d[i:i+1] == b'#':
            while d[i:i+1] not in (b'\n', b''):
                i += 1
            continue
        s = i
        while i < len(d) and not d[i:i+1].isspace():
            i += 1
        tok.append(int(d[s:i]))
    i += 1
    w, h, _ = tok
    return w, h, d[i:i+w*h*3]


def src_bytes(path, off, ln):
    b = open(path, 'rb').read()
    return b[off:] if ln is None else b[off:off+ln]


def ramp(t):
    """0..1 -> (r,g,b). dark -> teal -> amber -> white. readable on black."""
    t = 0.0 if t < 0 else (1.0 if t > 1 else t)
    stops = [(0.00, (8, 12, 24)), (0.25, (16, 78, 92)), (0.50, (28, 160, 140)),
             (0.75, (226, 168, 58)), (1.00, (255, 255, 255))]
    for i in range(len(stops)-1):
        a, ca = stops[i]
        b, cb = stops[i+1]
        if a <= t <= b:
            f = 0 if b == a else (t-a)/(b-a)
            return tuple(int(ca[j] + (cb[j]-ca[j])*f) for j in range(3))
    return stops[-1][1]


def bits_to_gray(b, W):
    total = len(b) * 8
    h = (total + W - 1) // W
    buf = bytearray(W * h)
    for i in range(total):
        if (b[i >> 3] >> (7 - (i & 7))) & 1:
            buf[i] = 255
    return bytes(buf), W, h


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    mode = sys.argv[1]
    pos = [a for a in sys.argv[2:] if not a.startswith('--')]

    def opt(name, default=None, cast=int):
        return cast(sys.argv[sys.argv.index(name)+1]) if name in sys.argv else default

    W = opt('--width', 256)
    S = opt('--scale', 1)
    OFF = opt('--offset', 0)
    LN = opt('--len', None)
    STR = opt('--stride', 25)
    COLS = opt('--cols', 4)
    GUT = opt('--gutter', 4)

    # ---------------- v1 render modes ----------------
    if mode == 'delta':
        prev = None
        for f in sorted(glob.glob(os.path.join(pos[0], '*.ppm'))):
            w, h, px = read_ppm(f)
            name = os.path.basename(f)
            if prev is None:
                print("%-26s %9s          %dx%d" % (name, 'base', w, h))
            else:
                d = sum(1 for j in range(0, len(px), 3) if px[j:j+3] != prev[j:j+3])
                print("%-26s %9d px changed  %6.2f%%" % (name, d, 100.0*d/(w*h)))
            prev = px
        return 0

    if mode == 'sheet':
        fs = sorted(glob.glob(os.path.join(pos[0], '*.ppm')))
        if not fs:
            raise SystemExit("no *.ppm in " + pos[0])
        fr = [read_ppm(f) for f in fs]
        fw, fh = fr[0][0], fr[0][1]
        rows = (len(fr) + COLS - 1) // COLS
        Wt = COLS*fw + (COLS+1)*GUT
        Ht = rows*fh + (rows+1)*GUT
        sheet = bytearray(b'\x00\x00\x00' * (Wt*Ht))
        for i, (a, b, p) in enumerate(fr):
            ox = GUT + (i % COLS)*(fw+GUT)
            oy = GUT + (i // COLS)*(fh+GUT)
            for y in range(fh):
                o = ((oy+y)*Wt + ox) * 3
                sheet[o:o+fw*3] = p[y*fw*3:(y+1)*fw*3]
        n = png(pos[1], Wt, Ht, bytes(sheet))
        print("%s  %dx%d  %s B  (%d frames of %dx%d)" % (pos[1], Wt, Ht, format(n, ','), len(fr), fw, fh))
        return 0

    if mode == 'ppm':
        w, h, px = read_ppm(pos[0])
        px, w, h = scale_up(px, w, h, S, 3)
        n = png(pos[1], w, h, px)
        print("%s  %dx%d  %s B" % (pos[1], w, h, format(n, ',')))
        return 0

    if mode in ('bits', 'bytes', 'rgb'):
        b = src_bytes(pos[0], OFF, LN)
        if mode == 'bits':
            buf, w, h = bits_to_gray(b, W)
            buf, w, h = scale_up(buf, w, h, S, 1)
            n = png(pos[1], w, h, buf, gray=True)
            ones = sum(bin(x).count('1') for x in b)
            print("%s  %dx%d  %s B   bits=%s  ones=%s (%.2f%%)" % (
                pos[1], w, h, format(n, ','), format(len(b)*8, ','), format(ones, ','),
                100.0*ones/(len(b)*8)))
        elif mode == 'bytes':
            h = (len(b) + W - 1) // W
            buf = bytes(bytearray(b) + bytes(W*h - len(b)))
            buf, w, h = scale_up(buf, W, h, S, 1)
            n = png(pos[1], w, h, buf, gray=True)
            print("%s  %dx%d  %s B   bytes=%s" % (pos[1], w, h, format(n, ','), format(len(b), ',')))
        else:
            h = len(b) // (W*3)
            buf, w, h = scale_up(b[:W*h*3], W, h, S, 3)
            n = png(pos[1], w, h, buf)
            print("%s  %dx%d  %s B" % (pos[1], w, h, format(n, ',')))
        return 0

    # ---------------- v2 measure modes ----------------
    if mode == 'stats':
        b = src_bytes(pos[0], OFF, LN)
        n = len(b)
        bits = n * 8
        ones = sum(bin(x).count('1') for x in b)
        c = Counter(b)
        ent = -sum((v/n)*math.log(v/n, 2) for v in c.values())
        zero_runs = []
        run = 0
        for x in b:
            if x == 0:
                run += 1
            elif run:
                zero_runs.append(run)
                run = 0
        if run:
            zero_runs.append(run)
        print("file            %s" % pos[0])
        print("bytes           %s" % format(n, ','))
        print("bits            %s" % format(bits, ','))
        print("ones            %s  (%.4f%%)" % (format(ones, ','), 100.0*ones/bits))
        print("zeros           %s  (%.4f%%)" % (format(bits-ones, ','), 100.0*(bits-ones)/bits))
        print("distinct bytes  %d of 256" % len(c))
        print("entropy         %.4f bits/byte  (max 8.0)" % ent)
        print("zlib ratio      %.4f" % (len(zlib.compress(b, 9))/float(n)))
        print("0x00 bytes      %s  (%.2f%%)" % (format(c.get(0, 0), ','), 100.0*c.get(0, 0)/n))
        print("0xFF bytes      %s  (%.2f%%)" % (format(c.get(255, 0), ','), 100.0*c.get(255, 0)/n))
        if zero_runs:
            print("zero runs       %s  longest %s B  mean %.1f B" % (
                format(len(zero_runs), ','), format(max(zero_runs), ','),
                sum(zero_runs)/float(len(zero_runs))))
        print("top bytes       " + "  ".join("0x%02X:%s" % (k, format(v, ',')) for k, v in c.most_common(8)))
        if n % STR == 0:
            print("stride %-3d      divides evenly -> %s records" % (STR, format(n//STR, ',')))
        else:
            print("stride %-3d      does NOT divide evenly (%d B remainder)" % (STR, n % STR))
        return 0

    if mode == 'cols':
        b = src_bytes(pos[0], OFF, LN)
        nrec = len(b) // STR
        cols = [0]*(STR*8)
        for r in range(nrec):
            rec = b[r*STR:(r+1)*STR]
            for i in range(STR*8):
                if (rec[i >> 3] >> (7 - (i & 7))) & 1:
                    cols[i] += 1
        live = [i for i, v in enumerate(cols) if v]
        print("%s  %s records of %d B  -> %d bit columns" % (
            pos[0], format(nrec, ','), STR, STR*8))
        print("columns ever set : %d of %d" % (len(live), STR*8))
        print("columns always 0 : %d" % (STR*8 - len(live)))
        print("")
        print("col  byte.bit   set      %      bar")
        for i in range(STR*8):
            pct = 100.0*cols[i]/nrec if nrec else 0.0
            bar = '#' * int(pct/2.5)
            flag = '' if cols[i] else '   <- never set'
            print("%3d  %2d.%d    %7d %6.2f  %s%s" % (i, i//8, i % 8, cols[i], pct, bar, flag))
        return 0

    if mode == 'fields':
        b = src_bytes(pos[0], OFF, LN)
        nrec = len(b) // STR
        if STR != 25:
            print("note: --stride %d; <BQQQ> assumes 25. reading first 25 B of each record." % STR)
        ops = Counter()
        A, B, O = [], [], []
        for r in range(nrec):
            op, a, bb, o = struct.unpack_from('<BQQQ', b, r*STR)
            ops[op] += 1
            A.append(a)
            B.append(bb)
            O.append(o)
        outs = set(O)
        ins = set(A) | set(B)
        collide = outs & ins
        hits = sum(1 for a in A if a in outs) + sum(1 for x in B if x in outs)
        print("%s  %s B  /%d = %s records  <BQQQ>" % (
            pos[0], format(len(b), ','), STR, format(nrec, ',')))
        print("")
        print("op census:")
        for k, v in ops.most_common():
            print("   op=%08d (%3d)  %7d  %6.2f%%" % (int(bin(k)[2:]), k, v, 100.0*v/nrec))
        for nm, vals in (('a', A), ('b', B), ('out', O)):
            mx = max(vals)
            mn = min(vals)
            print("")
            print("%-4s min=%s  max=%s  distinct=%s  bits_used=%d of 64" % (
                nm, format(mn, ','), format(mx, ','), format(len(set(vals)), ','), mx.bit_length()))
        print("")
        print("COLLISION (an out address that is also an input address):")
        print("   distinct out addresses        %s" % format(len(outs), ','))
        print("   distinct input addresses      %s" % format(len(ins), ','))
        print("   addresses that are both       %s" % format(len(collide), ','))
        print("   input slots landing on an out %s of %s (%.2f%%)" % (
            format(hits, ','), format(nrec*2, ','), 100.0*hits/(nrec*2)))
        seq = 0
        for r in range(nrec-1):
            o = struct.unpack_from('<BQQQ', b, r*STR)[3]
            nxt = struct.unpack_from('<BQQQ', b, (r+1)*STR)
            if o == nxt[1] or o == nxt[2]:
                seq += 1
        print("   REC n out == REC n+1 a or b   %s of %s (%.2f%%)" % (
            format(seq, ','), format(nrec-1, ','), 100.0*seq/max(nrec-1, 1)))
        return 0

    if mode == 'diff':
        a = src_bytes(pos[0], OFF, LN)
        c = src_bytes(pos[1], OFF, LN)
        n = min(len(a), len(c))
        x = bytes(bytearray(a[i] ^ c[i] for i in range(n)))
        changed = sum(bin(v).count('1') for v in x)
        bdiff = sum(1 for v in x if v)
        buf, w, h = bits_to_gray(x, W)
        buf, w, h = scale_up(buf, w, h, S, 1)
        px = png(pos[2], w, h, buf, gray=True)
        print("A  %s  %s B" % (pos[0], format(len(a), ',')))
        print("B  %s  %s B" % (pos[1], format(len(c), ',')))
        print("compared        %s B  (%s bits)" % (format(n, ','), format(n*8, ',')))
        print("bits differing  %s  (%.4f%%)" % (format(changed, ','), 100.0*changed/(n*8)))
        print("bytes differing %s  (%.4f%%)" % (format(bdiff, ','), 100.0*bdiff/n))
        if len(a) != len(c):
            print("SIZE DELTA      %+d B  (compared the common prefix only)" % (len(c)-len(a)))
        print("%s  %dx%d  %s B   white pixel = that bit changed" % (pos[2], w, h, format(px, ',')))
        return 0

    if mode == 'heat':
        b = src_bytes(pos[0], OFF, LN)
        nrec = len(b) // STR
        rowpx = 3
        buf = bytearray(nrec*rowpx*W*3)
        for r in range(nrec):
            rec = b[r*STR:(r+1)*STR]
            d = sum(bin(x).count('1') for x in rec) / float(STR*8)
            col = bytes(bytearray(ramp(d))) * W
            for k in range(rowpx):
                o = ((r*rowpx+k)*W)*3
                buf[o:o+W*3] = col
        buf2, w, h = scale_up(bytes(buf), W, nrec*rowpx, S, 3)
        n = png(pos[1], w, h, buf2)
        print("%s  %dx%d  %s B   %s records, ones-density per record" % (
            pos[1], w, h, format(n, ','), format(nrec, ',')))
        return 0

    if mode == 'hist':
        b = src_bytes(pos[0], OFF, LN)
        c = Counter(b)
        mx = max(c.values())
        Wt, Ht, BW = 256*3, 320, 3
        buf = bytearray(b'\x08\x0c\x18' * (Wt*Ht))
        for v in range(256):
            hgt = int((c.get(v, 0)/float(mx)) * (Ht-20))
            col = bytes(bytearray(ramp(c.get(v, 0)/float(mx))))
            for y in range(Ht-hgt, Ht):
                for k in range(BW):
                    o = (y*Wt + v*BW + k)*3
                    buf[o:o+3] = col
        n = png(pos[1], Wt, Ht, bytes(buf))
        peak = max(c, key=lambda k: c[k])
        print("%s  %dx%d  %s B   peak byte 0x%02X = %s" % (
            pos[1], Wt, Ht, format(n, ','), peak, format(mx, ',')))
        return 0

    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main())
