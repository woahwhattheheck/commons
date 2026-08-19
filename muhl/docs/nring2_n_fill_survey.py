#!/usr/bin/env python3
"""Read-only occupancy of named nring2_* ram.fwd / ram.rev.

Offsets from C:/llm/models/titan_circuits.json keys only.
No glob. No numpy. No SHA. No titan write.
"""
import json
import os
import sys

TITAN = "C:/llm/models/titan.gguf"
REG = "C:/llm/models/titan_circuits.json"
OUT = "C:/Users/lucys/Desktop/MUHL_GO/nring2_n_fill_survey.txt"

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass


def ones_byte(b):
    n = 0
    x = b
    while x:
        n += x & 1
        x >>= 1
    return n


def ones_blob(blob):
    t = 0
    for b in blob:
        t += ones_byte(b)
    return t


def bits_line(blob):
    return " ".join(format(b, "08b") for b in blob)


def main():
    if not os.path.isfile(REG):
        print("FAIL CLOSED: registry missing")
        return 1
    if not os.path.isfile(TITAN):
        print("FAIL CLOSED: titan missing")
        return 1
    with open(REG, encoding="utf-8") as f:
        reg = json.load(f)
    names = []
    for k in reg:
        if not k.startswith("nring2_"):
            continue
        rest = k[7:]
        if rest.isdigit():
            names.append(k)
    names.sort(key=lambda s: int(s.split("_")[1]))
    print("registry named nring2_NNN: %d" % len(names))
    tf = open(TITAN, "rb", buffering=0)
    rows = []
    hist_fwd = {}
    hist_rev = {}
    packed_both = 0
    need = 0
    named_focus = ("nring2_000", "nring2_001", "nring2_511", "nring2_1023")
    focus_bits = []
    for name in names:
        e = reg[name]
        ram = e.get("ram")
        if not isinstance(ram, dict):
            print("SKIP %s: no ram" % name)
            continue
        if ram.get("fwd") is None or ram.get("rev") is None:
            print("SKIP %s: missing ram.fwd/rev" % name)
            continue
        cells = int(e.get("cells") or 0)
        if cells <= 0:
            print("SKIP %s: cells=%s" % (name, e.get("cells")))
            continue
        fwd_off = int(ram["fwd"])
        rev_off = int(ram["rev"])
        tf.seek(fwd_off)
        fwd = tf.read(cells)
        tf.seek(rev_off)
        rev = tf.read(cells)
        if len(fwd) != cells or len(rev) != cells:
            print("FAIL CLOSED: short read %s" % name)
            tf.close()
            return 1
        fo = ones_blob(fwd)
        ro = ones_blob(rev)
        hist_fwd[fo] = hist_fwd.get(fo, 0) + 1
        hist_rev[ro] = hist_rev.get(ro, 0) + 1
        max_ones = cells * 8
        both = (fo == max_ones and ro == max_ones)
        if both:
            packed_both += 1
        else:
            need += 1
        rows.append((name, fwd_off, rev_off, cells, fo, ro, fwd, rev, both))
        if name in named_focus:
            focus_bits.append((name, fwd_off, rev_off, cells, fo, ro, fwd, rev))
    tf.close()

    lines = []
    lines.append("NRING2 N-FILL SURVEY (read only)")
    lines.append("titan: %s" % TITAN)
    lines.append("reg:   %s" % REG)
    lines.append("named rings with ram.fwd+rev: %d" % len(rows))
    lines.append("packed both senses (skip): %d" % packed_both)
    lines.append("need fill (not packed both): %d" % need)
    lines.append("fwd ones hist: %s" % ", ".join("%d:%d" % (k, hist_fwd[k]) for k in sorted(hist_fwd)))
    lines.append("rev ones hist: %s" % ", ".join("%d:%d" % (k, hist_rev[k]) for k in sorted(hist_rev)))
    lines.append("")
    lines.append("FOCUS (actual bits)")
    for name, fwd_off, rev_off, cells, fo, ro, fwd, rev in focus_bits:
        lines.append("")
        lines.append("%s cells=%d" % (name, cells))
        lines.append("  fwd @ %d  ones=%d/%d" % (fwd_off, fo, cells * 8))
        lines.append("  %s" % bits_line(fwd))
        lines.append("  rev @ %d  ones=%d/%d" % (rev_off, ro, cells * 8))
        lines.append("  %s" % bits_line(rev))
    lines.append("")
    lines.append("NON-PACKED (name fwd_ones rev_ones fwd_off rev_off)")
    for name, fwd_off, rev_off, cells, fo, ro, fwd, rev, both in rows:
        if both:
            continue
        lines.append("%s  fwd=%d  rev=%d  fwd@%d  rev@%d" % (name, fo, ro, fwd_off, rev_off))
    text = "\n".join(lines) + "\n"
    with open(OUT, "w", encoding="utf-8") as o:
        o.write(text)
    print(text)
    print("wrote %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
