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

SURVEY MODES (v3, new)
  magic  FILE            scan for ASCII magic words and report byte offset +
                         record index. finds named organs inside a container.
  strip  FILE OUT.png    whole-file ones-density overview, chunked. survives
                         a 2 GB container without building a 2 GB image.
  entropy FILE OUT.png   sliding-window entropy as a colour strip. structure map:
                         header, netlist and dead space read as different bands.
  records FILE           text dump of records at --stride. --skip N --count N.

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
        print("ASSUMPTION: records are <BQQQ> (1B op + three 8B little-endian fields)")
        print("            at stride %d. This mode does NOT verify that." % STR)
        if len(b) % STR:
            print("WARNING:    length %s is NOT divisible by %d (%d B remainder)."
                  % (format(len(b), ','), STR, len(b) % STR))
            print("            The stride is probably wrong. Numbers below are then meaningless.")
        if STR != 25:
            print("note: --stride %d; <BQQQ> reads the first 25 B of each record." % STR)
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
        # -- self-check: would this parse be obvious nonsense? --
        wide = sum(1 for v in A + B + O if v.bit_length() > 40)
        print("")
        print("PARSE PLAUSIBILITY (does <BQQQ> at stride %d even fit this file?)" % STR)
        print("   fields using >40 bits   %s of %s (%.2f%%)" % (
            format(wide, ','), format(nrec*3, ','), 100.0*wide/max(nrec*3, 1)))
        if 100.0*wide/max(nrec*3, 1) > 5.0:
            print("   HIGH. Addresses this large suggest the stride or the record layout")
            print("   is wrong and these numbers are an artefact of a bad parse.")
        else:
            print("   Low. Consistent with the assumed layout. Not proof of it.")
        print("   A clean-looking parse is not evidence the format is right.")
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

    # ---------------- v3 survey modes ----------------
    if mode == 'magic':
        b = src_bytes(pos[0], OFF, LN)
        MIN = opt('--min', 4)
        # named in the owner's docs
        known = [b'GGUF', b'TITANCIR', b'MUHLFLD1', b'NRING2M1', b'PFCTYPED',
                 b'TITANFLD', b'MUHLPHY2', b'MUHLWBX1', b'MUHLDC01', b'TABLEML1',
                 # found by sweeping the 123 .mno in this repo, 2026-08-20.
                 # not in CLAUDE_FAILURE_MODES.md; added so the scanner names them.
                 b'MUHLPKG1', b'LOOMPKG1', b'PROBEMN1', b'ROOKERY0', b'COMMON1']
        print("%s  %s B" % (pos[0], format(len(b), ',')))

        # -- head bytes, unconditionally. no heuristic gets to hide these. --
        print("")
        print("HEAD 64 B verbatim (hex, then ascii with . for non-printable):")
        head = b[:64]
        for r in range(0, len(head), 16):
            ch = head[r:r+16]
            asc = ''.join(chr(c) if 32 <= c < 127 else '.' for c in ch)
            print("   +%-4d %-32s  %s" % (r, ch.hex(), asc))

        print("")
        print("KNOWN magics (%d strings searched):" % len(known))
        found = 0
        for m in known:
            i = b.find(m)
            hits = []
            while i != -1 and len(hits) < 12:
                hits.append(i)
                i = b.find(m, i+1)
            if hits:
                found += len(hits)
                for off in hits:
                    print("   %-9s @ %-14s  rec %-10s  (rec offset +%d)" % (
                        m.decode(), format(off, ','), format(off//STR, ','), off % STR))
        if not found:
            print("   NONE OF THOSE %d STRINGS FOUND." % len(known))
            print("   This is not 'no magic'. It is 'not these %d'." % len(known))

        # -- discovery over FULL printable ascii, min length --min (default 4) --
        print("")
        print("DISCOVERED printable runs (>=%d chars, ASCII 0x20-0x7E):" % MIN)
        seen = Counter()
        run = bytearray()
        first_at = {}
        for i, x in enumerate(b):
            if 32 <= x < 127:
                run.append(x)
            else:
                if len(run) >= MIN:
                    s = bytes(run)
                    seen[s] += 1
                    first_at.setdefault(s, i - len(run))
                run = bytearray()
        if len(run) >= MIN:
            s = bytes(run)
            seen[s] += 1
            first_at.setdefault(s, len(b) - len(run))
        for s, c in seen.most_common(20):
            print("   %-28s x%-6d first @ %s" % (
                repr(s.decode())[1:-1][:26], c, format(first_at[s], ',')))
        if not seen:
            print("   none at >=%d chars" % MIN)

        # -- what this pass CANNOT see. printed every time. --
        print("")
        print("COVERAGE OF THIS SCAN — what a zero above does NOT rule out:")
        print("   * a magic not in the %d-string known list and shorter than %d chars" % (len(known), MIN))
        print("   * a magic that is not ASCII at all (UTF-16, packed, or binary)")
        print("   * a magic split by an embedded non-printable byte")
        print("   * a magic stored big-endian / byte-swapped / obfuscated")
        print("   * structure that is real but carries no name")
        print("   Raise coverage with --min 3, or read the HEAD dump above directly.")
        nonpr = sum(1 for x in b if not (32 <= x < 127))
        print("   this file is %.2f%% non-printable bytes (%s of %s)" % (
            100.0*nonpr/len(b), format(nonpr, ','), format(len(b), ',')))
        return 0

    if mode == 'strip':
        # chunked: never holds more than one chunk in memory
        size = os.path.getsize(pos[0])
        H = 120
        cols = min(W, 4096)
        per = max(size // cols, 1)
        dens = []
        with open(pos[0], 'rb') as f:
            for i in range(cols):
                f.seek(i*per)
                ch = f.read(min(per, 65536))
                if not ch:
                    dens.append(0.0)
                    continue
                dens.append(sum(bin(x).count('1') for x in ch) / float(len(ch)*8))
        mx = max(dens) or 1.0
        buf = bytearray(cols*H*3)
        for x in range(cols):
            col = bytes(bytearray(ramp(dens[x]/mx)))
            for y in range(H):
                o = (y*cols + x)*3
                buf[o:o+3] = col
        buf2, w, h = scale_up(bytes(buf), cols, H, S, 3)
        n = png(pos[1], w, h, buf2)
        print("%s  %dx%d  %s B" % (pos[1], w, h, format(n, ',')))
        print("file %s B sampled in %d columns of %s B each" % (
            format(size, ','), cols, format(per, ',')))
        print("ones-density  min %.4f  max %.4f  mean %.4f" % (
            min(dens), max(dens), sum(dens)/len(dens)))
        return 0

    if mode == 'entropy':
        b = src_bytes(pos[0], OFF, LN)
        win = opt('--window', 1024)
        cols = min(W, max(len(b)//win, 1))
        step = max(len(b)//cols, 1)
        H = 120
        ents = []
        for i in range(cols):
            ch = b[i*step:i*step+win]
            if not ch:
                ents.append(0.0)
                continue
            c = Counter(ch)
            n = float(len(ch))
            ents.append(-sum((v/n)*math.log(v/n, 2) for v in c.values()) / 8.0)
        buf = bytearray(cols*H*3)
        for x in range(cols):
            col = bytes(bytearray(ramp(ents[x])))
            for y in range(H):
                o = (y*cols + x)*3
                buf[o:o+3] = col
        buf2, w, h = scale_up(bytes(buf), cols, H, S, 3)
        n = png(pos[1], w, h, buf2)
        print("%s  %dx%d  %s B" % (pos[1], w, h, format(n, ',')))
        print("window %s B, %d columns, step %s B" % (format(win, ','), cols, format(step, ',')))
        print("entropy (normalised 0-1)  min %.4f  max %.4f  mean %.4f" % (
            min(ents), max(ents), sum(ents)/len(ents)))
        return 0

    if mode == 'records':
        b = src_bytes(pos[0], OFF, LN)
        skip = opt('--skip', 0)
        count = opt('--count', 16)
        nrec = len(b)//STR
        print("%s  %s records of %d B  showing %d from %d" % (
            pos[0], format(nrec, ','), STR, count, skip))
        print("")
        for r in range(skip, min(skip+count, nrec)):
            op, a, bb, o = struct.unpack_from('<BQQQ', b, r*STR)
            raw = b[r*STR:(r+1)*STR]
            print("REC%06d  op=%s (%3d)  a=%-12s b=%-12s out=%-12s  %s" % (
                r, bin(op)[2:].zfill(8), op, format(a, ','), format(bb, ','),
                format(o, ','), raw.hex()))
        return 0

    # ---------------- v4 netlist modes ----------------
    if mode in ('dag', 'levels', 'step'):
        b = src_bytes(pos[0], OFF, LN)
        nrec = len(b) // STR
        print("ASSUMPTION: <BQQQ> records at stride %d. Not verified by this mode." % STR)
        if len(b) % STR:
            print("WARNING: length %s not divisible by %d. Stride is probably wrong."
                  % (format(len(b), ','), STR))
        recs = [struct.unpack_from('<BQQQ', b, r*STR) for r in range(nrec)]

        # producer[net] = list of record indices writing that net
        producer = {}
        for r, (op, a, bb, o) in enumerate(recs):
            producer.setdefault(o, []).append(r)
        consumed = Counter()
        for op, a, bb, o in recs:
            consumed[a] += 1
            consumed[bb] += 1

        nets = set(producer) | set(consumed)
        sources = sorted(n for n in consumed if n not in producer)   # inputs
        sinks = sorted(n for n in producer if n not in consumed)     # outputs
        multi = [n for n, v in producer.items() if len(v) > 1]

        # depth over the record graph, with cycle detection.
        # WHITE=0 unvisited, GREY=1 on stack, BLACK=2 done
        colour = [0]*nrec
        depth = [0]*nrec
        in_cycle = [False]*nrec
        cyc_edges = 0
        sys.setrecursionlimit(10000)

        def deps(r):
            op, a, bb, o = recs[r]
            out = []
            for net in (a, bb):
                for p in producer.get(net, ()):
                    if p != r:
                        out.append(p)
            return out

        # iterative DFS so a 1M-record file cannot blow the stack
        for start in range(nrec):
            if colour[start]:
                continue
            stack = [(start, iter(deps(start)))]
            colour[start] = 1
            while stack:
                node, it = stack[-1]
                advanced = False
                for nxt in it:
                    if colour[nxt] == 1:
                        in_cycle[nxt] = True
                        in_cycle[node] = True
                        cyc_edges += 1
                        continue
                    if colour[nxt] == 0:
                        colour[nxt] = 1
                        stack.append((nxt, iter(deps(nxt))))
                        advanced = True
                        break
                if not advanced:
                    stack.pop()
                    colour[node] = 2
                    d = 0
                    for p in deps(node):
                        if colour[p] == 2 and not in_cycle[p]:
                            if depth[p] + 1 > d:
                                d = depth[p] + 1
                    depth[node] = d

        acyc = [i for i in range(nrec) if not in_cycle[i]]
        maxd = max((depth[i] for i in acyc), default=0)

        if mode == 'dag':
            print("")
            print("%s  %s records  %s distinct nets" % (
                pos[0], format(nrec, ','), format(len(nets), ',')))
            print("")
            print("NETS")
            print("   consumed but never produced (INPUTS)  %s" % format(len(sources), ','))
            print("   produced but never consumed (OUTPUTS) %s" % format(len(sinks), ','))
            print("   produced by more than one record      %s" % format(len(multi), ','))
            if sources[:8]:
                print("   input nets: %s%s" % (
                    ", ".join(format(x, ',') for x in sources[:8]),
                    " ..." if len(sources) > 8 else ""))
            print("")
            print("CYCLES  (a ring is a cycle. this is a measurement, not an error.)")
            print("   records on a cycle        %s of %s (%.2f%%)" % (
                format(sum(in_cycle), ','), format(nrec, ','),
                100.0*sum(in_cycle)/max(nrec, 1)))
            print("   back-edges seen           %s" % format(cyc_edges, ','))
            print("   acyclic records           %s" % format(len(acyc), ','))
            print("")
            print("DEPTH  (over the acyclic records only)")
            print("   max depth                 %s" % format(maxd, ','))
            hist = Counter(depth[i] for i in acyc)
            for d in sorted(hist)[:24]:
                bar = '#' * min(int(60.0*hist[d]/max(hist.values())), 60)
                print("   depth %-6d %8s  %s" % (d, format(hist[d], ','), bar))
            if len(hist) > 24:
                print("   ... %d more depth levels" % (len(hist)-24))
            fan = Counter(consumed.values())
            print("")
            print("FANOUT  (times a net is used as an input)")
            for k in sorted(fan)[:10]:
                print("   used %-4d times  %s nets" % (k, format(fan[k], ',')))
            mxf = max(consumed.values()) if consumed else 0
            print("   max fanout %s on net %s" % (
                format(mxf, ','),
                format(max(consumed, key=lambda k: consumed[k]), ',') if consumed else '-'))
            print("")
            print("NOT MEASURED: whether <BQQQ>@%d is the right layout; what any op means;" % STR)
            print("whether a cycle here is a ring, a loop, or an artefact. Numbers only.")
            return 0

        if mode == 'step':
            at = opt('--at', 0)
            sel = [i for i in acyc if depth[i] == at]
            print("")
            print("STEP %d - records whose inputs are all resolved by depth %d" % (at, at))
            print("%s records at this depth (of %s acyclic, max depth %s)" % (
                format(len(sel), ','), format(len(acyc), ','), format(maxd, ',')))
            print("")
            for r in sel[:opt('--count', 24)]:
                op, a, bb, o = recs[r]
                fo = consumed.get(o, 0)
                print("   REC%06d  op=%s (%3d)  a=%-12s b=%-12s out=%-12s  fanout=%d" % (
                    r, bin(op)[2:].zfill(8), op, format(a, ','), format(bb, ','),
                    format(o, ','), fo))
            if len(sel) > opt('--count', 24):
                print("   ... %s more at this depth" % format(len(sel)-opt('--count', 24), ','))
            return 0

        # levels: layered render, y = depth, x = gate within depth, colour = op
        byd = {}
        for i in acyc:
            byd.setdefault(depth[i], []).append(i)
        for i in range(nrec):
            if in_cycle[i]:
                byd.setdefault(-1, []).append(i)
        widest = max((len(v) for v in byd.values()), default=1)
        levels = sorted(byd)
        CW = max(1, min(4, max(1, W // max(widest, 1))))
        RH = 6
        Wt = min(widest*CW, 4096)
        Ht = len(levels)*RH
        buf = bytearray(b'\x08\x0c\x18' * (Wt*Ht))
        opcols = {}
        allops = sorted({recs[i][0] for i in range(nrec)})
        for n, o in enumerate(allops):
            opcols[o] = ramp(0.15 + 0.8*(n/float(max(len(allops)-1, 1))))
        for li, d in enumerate(levels):
            for gi, r in enumerate(byd[d]):
                x = gi*CW
                if x + CW > Wt:
                    break
                col = bytes(bytearray((200, 60, 60) if d == -1 else opcols[recs[r][0]]))
                for y in range(li*RH, li*RH + RH - 1):
                    for k in range(CW):
                        o2 = (y*Wt + x + k)*3
                        buf[o2:o2+3] = col
        buf2, w, h = scale_up(bytes(buf), Wt, Ht, S, 3)
        n = png(pos[1], w, h, buf2)
        print("")
        print("%s  %dx%d  %s B" % (pos[1], w, h, format(n, ',')))
        print("%d rows = %d depth levels%s. widest level %s gates." % (
            len(levels), len([x for x in levels if x >= 0]),
            " (+1 red row = records on a cycle)" if -1 in byd else "",
            format(widest, ',')))
        print("colour = op. red row = cycle. row order = evaluation order.")
        return 0

    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main())
