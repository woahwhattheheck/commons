#!/usr/bin/env python3
"""SYNTHETIC fixture: a lane that really is reproducible.

Sorted traversal, no clock, no absolute paths in the output, no RNG.
"""
import json
import os

TOKENS = ["token-%02d" % n for n in range(64)]

def main():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "order.txt"), "w", encoding="utf-8") as handle:
        for token in sorted(set(TOKENS)):
            handle.write(token + "\n")
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as handle:
        json.dump({"tokens": len(TOKENS)}, handle, indent=2, sort_keys=True)
        handle.write("\n")

if __name__ == "__main__":
    main()
