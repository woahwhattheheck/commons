#!/usr/bin/env python3
"""Validate the in-tree Muhlnickel film-organ reference without executing a film.

This host reads repository evidence only. It never walks gates, renders frames,
writes titan, invents a mouth/destination, fires 337, pulses 78, lights 7913,
injects DC, or invokes an encoder.

  python3 host/muhl_film_organ.py
  python3 host/muhl_film_organ.py --root .
  python3 host/muhl_film_organ.py --self-test
  python3 host/muhl_film_organ.py --go  # explicit refusal; no mutation
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys


DEFAULT_ROOT = "."
DEFAULT_CATALOG = os.path.join("ground", "MUHL_FILM_ORGAN.json")
DEFAULT_CARD = os.path.join("ground", "MUHL_FILM_ORGAN.md")
DEFAULT_SOURCE = os.path.join("ground", "muhl_film_organ", "source.json")
DEFAULT_REEL = os.path.join("muhl", "docs", "FILM_REEL.pfc")
DEFAULT_DOOR = "film.html"
EXPECTED_BYTES = 2498592
EXPECTED_MAGIC = b"PFCGAME1"
EXPECTED_SHA256 = "27d8371e8968ed6bccc0fd27400e35e78fb7e7da87f7c472b175ba08a6901e88"
EXPECTED_LIVE_CELLS = 1212
EXPECTED_FINAL_STATE = 1936723975
EXPECTED_PREFIX_BITS = "0000000000001011100000001011011010000000000000010000100000011000"
REQUIRED_FILES = (
    DEFAULT_CATALOG,
    DEFAULT_CARD,
    DEFAULT_SOURCE,
    DEFAULT_REEL,
    DEFAULT_DOOR,
    os.path.join("host", "muhl_film_organ.py"),
    "test_muhl_film_organ.py",
)


def _read(root, rel, binary=False):
    path = os.path.join(root, rel)
    try:
        if binary:
            with open(path, "rb") as handle:
                return handle.read()
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return b"" if binary else ""


def _exists(root, rel):
    return os.path.isfile(os.path.join(root, rel))


def load_json(text):
    try:
        value = json.loads(str(text or "") or "{}")
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def lcg_reference(source):
    if not isinstance(source, dict) or not source:
        return {"state": "UNMEASURED", "note": "source fixture was not read"}
    try:
        width, height = [int(value) for value in source.get("grid")]
        cells = int(source.get("cells"))
        lcg = source.get("lcg") or {}
        a = int(lcg.get("a"))
        c = int(lcg.get("c"))
        modulus = int(lcg.get("m"))
        state = int(lcg.get("seed"))
        density_num = int(source.get("density_num"))
        density_den = int(source.get("density_den"))
    except (TypeError, ValueError):
        return {"state": "NOT_LANDED", "note": "source fixture fields are incomplete"}
    if source.get("prng") != "lcg" or (width, height, cells) != (64, 64, 4096):
        return {"state": "NOT_LANDED", "note": "source must be the declared 64x64 LCG fixture"}
    if (a, c, modulus, state, density_num, density_den) != (
        1664525,
        1013904223,
        4294967296,
        7,
        30,
        100,
    ):
        return {"state": "NOT_LANDED", "note": "LCG or density differs from the declared source"}
    bits = []
    for _ in range(cells):
        state = (a * state + c) % modulus
        bits.append("1" if state % density_den < density_num else "0")
    bit_text = "".join(bits)
    return {
        "state": "REFERENCE_SOURCE_VERIFIED",
        "cells": cells,
        "live_cells": bit_text.count("1"),
        "final_state": state,
        "prefix_bits": bit_text[:64],
        "feature_length_pulses_declared": int(source.get("feature_length_pulses_declared") or 0),
        "fps": int(source.get("fps") or 0),
        "runtime_s_declared": int(source.get("runtime_s_declared") or 0),
    }


def measure_reel(path):
    try:
        size = os.path.getsize(path)
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            magic = handle.read(len(EXPECTED_MAGIC))
            digest.update(magic)
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        return {"state": "UNMEASURED", "note": str(exc)}
    return {
        "state": "REFERENCE_REEL_VERIFIED",
        "bytes": size,
        "magic": magic.decode("ascii", errors="replace"),
        "sha256": digest.hexdigest(),
    }


def measure_root(root):
    root = os.path.abspath(root)
    catalog = load_json(_read(root, DEFAULT_CATALOG))
    source = load_json(_read(root, DEFAULT_SOURCE))
    door = _read(root, DEFAULT_DOOR)
    card = _read(root, DEFAULT_CARD)
    return {
        "measured": True,
        "misses": [rel for rel in REQUIRED_FILES if not _exists(root, rel)],
        "catalog": catalog,
        "source": source,
        "source_measure": lcg_reference(source),
        "reel": measure_reel(os.path.join(root, DEFAULT_REEL)),
        "door": door,
        "card": card,
    }


def classify(row):
    row = row or {}
    if not row.get("measured"):
        return {"state": "UNMEASURED", "note": "film-organ tree was not read"}
    if row.get("misses"):
        return {"state": "NOT_LANDED", "note": "missing path(s): " + ", ".join(row["misses"])}
    catalog = row.get("catalog") or {}
    source = row.get("source") or {}
    reel = row.get("reel") or {}
    source_measure = row.get("source_measure") or {}
    if catalog.get("kind") != "MUHL_FILM_ORGAN_REFERENCE":
        return {"state": "NOT_LANDED", "note": "catalog kind is not a reference organ"}
    if (
        reel.get("bytes") != EXPECTED_BYTES
        or reel.get("magic") != EXPECTED_MAGIC.decode("ascii")
        or reel.get("sha256") != EXPECTED_SHA256
    ):
        return {"state": "NOT_LANDED", "note": "reel bytes, magic, or sha256 differ"}
    if (
        source_measure.get("state") != "REFERENCE_SOURCE_VERIFIED"
        or source_measure.get("live_cells") != EXPECTED_LIVE_CELLS
        or source_measure.get("final_state") != EXPECTED_FINAL_STATE
        or source_measure.get("prefix_bits") != EXPECTED_PREFIX_BITS
    ):
        return {"state": "NOT_LANDED", "note": "deterministic LCG source differs"}
    if source_measure.get("feature_length_pulses_declared") != 129600:
        return {"state": "NOT_LANDED", "note": "feature-length pulse declaration differs"}
    if source_measure.get("fps") * source_measure.get("runtime_s_declared") != 129600:
        return {"state": "NOT_LANDED", "note": "129600 must equal fps times declared runtime"}
    forbidden_true = (
        "movie_executed",
        "byte_exact_feature_run",
        "host_inference",
        "host_gate_walk",
        "host_frame_simulation",
        "invented_dest",
        "invented_mouth",
        "fire_337",
        "pulse_78",
        "light_7913",
        "dc_injected",
        "private_owner_media",
        "pirated_mp4",
        "mp4",
        "ffmpeg",
    )
    if int(catalog.get("executed_pulses") or 0) != 0 or any(catalog.get(key) is not False for key in forbidden_true):
        return {"state": "NOT_LANDED", "note": "reference metadata fabricates execution or a prohibited action"}
    if catalog.get("titan") != "NOT_WRITTEN" or catalog.get("no_auth") is not True or catalog.get("no_gate") is not True:
        return {"state": "NOT_LANDED", "note": "reference boundary or open door differs"}
    if source.get("movie_executed") is not False or int(source.get("executed_pulses") or 0) != 0:
        return {"state": "NOT_LANDED", "note": "source fixture may not claim a feature run"}
    surface = (row.get("door") or "") + "\n" + (row.get("card") or "")
    required_text = (
        "REFERENCE VISOR",
        "MOVIE_EXECUTED: NO",
        "129,600 pulses were not executed",
        "No invented mouth or destination",
        "PFCGAME1",
        EXPECTED_SHA256,
    )
    if any(text not in surface for text in required_text):
        return {"state": "NOT_LANDED", "note": "reference surface omits the execution boundary"}
    return {
        "state": "SPEC_INTEGRATED",
        "movie_executed": False,
        "executed_pulses": 0,
        "note": "Reel and deterministic source verified. This is a reference visor, not a feature-length execution.",
    }


def self_test():
    source = {
        "grid": [64, 64],
        "cells": 4096,
        "prng": "lcg",
        "lcg": {"a": 1664525, "c": 1013904223, "m": 4294967296, "seed": 7},
        "density_num": 30,
        "density_den": 100,
        "feature_length_pulses_declared": 129600,
        "fps": 24,
        "runtime_s_declared": 5400,
    }
    result = lcg_reference(source)
    assert result["state"] == "REFERENCE_SOURCE_VERIFIED", result
    assert result["live_cells"] == EXPECTED_LIVE_CELLS, result
    assert result["final_state"] == EXPECTED_FINAL_STATE, result
    assert result["prefix_bits"] == EXPECTED_PREFIX_BITS, result
    assert result["fps"] * result["runtime_s_declared"] == 129600, result
    return "ok"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate the Muhlnickel film-organ reference")
    parser.add_argument("--root", default=DEFAULT_ROOT)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--go", action="store_true", help="explicitly refused; this validator never pulses an organ")
    args = parser.parse_args(argv)
    if args.self_test:
        print(self_test())
        return 0
    if args.go:
        print(json.dumps({
            "state": "REFUSED",
            "movie_executed": False,
            "executed_pulses": 0,
            "note": "--go is inert here; no organ pulse, titan write, mouth, destination, or frame was produced.",
        }, indent=2, sort_keys=True))
        return 1
    row = measure_root(args.root)
    verdict = classify(row)
    public_row = dict(row)
    public_row.pop("door", None)
    public_row.pop("card", None)
    print(json.dumps({"verdict": verdict, "row": public_row}, indent=2, sort_keys=True))
    return 0 if verdict["state"] == "SPEC_INTEGRATED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
