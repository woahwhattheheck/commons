#!/usr/bin/env python3
"""One-shot: read named mouths as 1s/0s. Die. No mmap. No inject. No fire."""
import os
import sys

PATH = r"C:\Users\lucys\Desktop\MUHL_DATACENTER\muhlnickel_dc.mno"
OUT = r"C:\Users\lucys\Desktop\MUHL_GO\_dc_mouths_%s.txt"

MOUTHS = (
    (0, 224),
    (224, 48),
    (336, 1),
    (337, 1),
    (524288, 1),
    (26373783552, 32),
)


def b8(x):
    return format(x, "08b")


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "T"
    if not os.path.isfile(PATH):
        print("SKIP missing")
        return 2
    parts = []
    with open(PATH, "rb") as f:
        f.seek(0, os.SEEK_END)
        end = f.tell()
        parts.append("TAG %s" % tag)
        parts.append("SIZE %d" % end)
        for off, n in MOUTHS:
            if off < 0 or off >= end:
                parts.append("SKIP @%d" % off)
                continue
            take = n if off + n <= end else end - off
            if take <= 0:
                parts.append("SKIP @%d" % off)
                continue
            f.seek(off)
            blob = f.read(take)
            parts.append("@%d %s" % (off, " ".join(b8(x) for x in blob)))
    text = "\n".join(parts) + "\n"
    dest = OUT % tag
    with open(dest, "w", encoding="utf-8", newline="\n") as o:
        o.write(text)
    print(text, end="")
    print("WROTE", dest, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
