#!/usr/bin/env python3
"""SYNTHETIC fixture: three real reproducibility defects, on purpose.

  stamp.txt  a wall-clock timestamp
  where.txt  the absolute path the run happened in
  order.txt  set iteration order, which depends on PYTHONHASHSEED

The third is the one a same-process double-run can never catch.
"""
import datetime
import os

TOKENS = {"token-%02d" % n for n in range(64)}

def main():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "stamp.txt"), "w", encoding="utf-8") as handle:
        handle.write("generated at %s\n"
                     % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"))
    with open(os.path.join(out, "where.txt"), "w", encoding="utf-8") as handle:
        handle.write("generated in %s\n" % os.getcwd())
    with open(os.path.join(out, "order.txt"), "w", encoding="utf-8") as handle:
        for token in TOKENS:
            handle.write(token + "\n")

if __name__ == "__main__":
    main()
