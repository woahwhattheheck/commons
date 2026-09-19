#!/usr/bin/env python3
"""Measure the four dedup strategies and find where the difference starts.

Same measurement discipline as UIOWA-095: ``time.perf_counter`` for elapsed,
``tracemalloc`` for memory, separate passes, one uncounted warmup, minimum and
median of the counted repeats, environment recorded alongside the numbers.

Every strategy's output is compared against the current (list-scan) output
BEFORE anything is timed. A strategy that disagrees aborts the run.

Also reads the OPS-PERF-SCAN results, if present, to report how many real sites
this curve applies to. It does NOT claim to know their input sizes -- those stay
UNKNOWN.

Python 3 standard library only. No network.
"""
from __future__ import annotations

import argparse
import csv
import gc
import json
import platform
import random
import statistics
import sys
import time
import tracemalloc
from pathlib import Path

import dedup

HERE = Path(__file__).resolve().parent

# Distinct-item counts to measure. The kit's flagged sites dedup things like
# distinct colours in a document and distinct terms in a question, so the
# interesting range is small-to-moderate; the top end is there to show the shape.
SIZES = [10, 25, 50, 100, 200, 400, 800, 1600, 3200]
REPEATS = 7
DUPLICATION_FACTOR = 3  # each distinct item appears ~3 times, as in real input


def environment() -> dict:
    cpu_model = "UNKNOWN"
    try:
        for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
            if line.lower().startswith("model name"):
                cpu_model = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    import os
    return {
        "python_version": sys.version.split()[0],
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "processor_model": cpu_model,
        "cpu_count_logical": os.cpu_count(),
        "timer": "time.perf_counter",
        "memory_probe": "tracemalloc (Python-level allocations only, not process RSS)",
        "measured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "note": "Minimum of counted repeats after one uncounted warmup. Shared container; "
                "median reported alongside so noise is visible.",
    }


def make_input(distinct: int, seed: int = 20260919) -> list:
    """Strings shaped like the things the flagged sites actually dedup
    (colour codes, tokens), with realistic repetition, deterministically."""
    rng = random.Random(seed)
    items = [f"#{i:06X}" for i in range(distinct)] * DUPLICATION_FACTOR
    rng.shuffle(items)
    return items


def measure(strategies, sizes, repeats: int) -> list:
    rows = []
    for n in sizes:
        items = make_input(n)
        expected = dedup.dedup_list_scan(items)
        point = {"distinct_items": n, "input_length": len(items), "strategies": {}}
        for name in strategies:
            fn, _ = dedup.STRATEGIES[name]
            got = fn(items)
            if got != expected:
                raise SystemExit(
                    f"ABORT: strategy {name!r} disagreed with the current behaviour at n={n}. "
                    "Refusing to publish timings for two different answers.")
            fn(items)  # uncounted warmup
            samples = []
            for _ in range(repeats):
                gc.collect()
                t0 = time.perf_counter()
                fn(items)
                samples.append(time.perf_counter() - t0)
            gc.collect()
            tracemalloc.start()
            try:
                fn(items)
                _, peak = tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop()
            point["strategies"][name] = {
                "seconds_min": min(samples),
                "seconds_median": statistics.median(samples),
                "peak_bytes": peak,
                "samples": len(samples),
            }
        rows.append(point)
    return rows


def find_crossover(rows, baseline: str, candidate: str, factor: float) -> dict:
    """Smallest MEASURED n where candidate is at least `factor` times faster.

    Measured points only -- no interpolation, no fitted curve. If no measured
    point reached the factor, the answer is UNKNOWN rather than a guess.
    """
    for row in rows:
        b = row["strategies"][baseline]["seconds_min"]
        c = row["strategies"][candidate]["seconds_min"]
        if c > 0 and (b / c) >= factor:
            return {"distinct_items": row["distinct_items"], "speedup": b / c}
    return {"distinct_items": "UNKNOWN", "speedup": "UNKNOWN"}


def hashability_report() -> dict:
    """What happens to each strategy on unhashable elements. Measured by running
    them, not by reading the docs."""
    unhashable = [{"a": 1}, {"a": 1}, {"b": 2}]
    out = {}
    for name, (fn, requires_hashable) in dedup.STRATEGIES.items():
        try:
            result = fn(unhashable)
            out[name] = {"works_on_unhashable": True, "result_length": len(result),
                         "declared_requires_hashable": requires_hashable}
        except TypeError as exc:
            out[name] = {"works_on_unhashable": False, "error": f"TypeError: {exc}",
                         "declared_requires_hashable": requires_hashable}
    return out


def load_scan_sites(scan_results: Path) -> dict:
    """How many real sites this curve applies to, from the OPS-PERF-SCAN output."""
    if not scan_results.exists():
        return {"available": False,
                "note": "OPS-PERF-SCAN results not found at the expected path; site count "
                        "UNKNOWN for this run."}
    data = json.loads(scan_results.read_text(encoding="utf-8"))
    sites = [f for f in data.get("findings", [])
             if f.get("pattern") == "P1_list_membership_in_loop"]
    return {
        "available": True,
        "source": str(scan_results),
        "scanned_at_utc": data.get("environment", {}).get("scanned_at_utc", "UNKNOWN"),
        "site_count": len(sites),
        "sites": [{"file": s["file"], "line": s["line"], "source": s["source"]} for s in sites],
        "input_sizes": "UNKNOWN -- this lane measured the cost curve, not the data these "
                       "sites actually see.",
    }


def render(report: dict) -> str:
    env = report["environment"]
    lines = [
        "# Order-preserving dedup: measured cost curve",
        "",
        "OPS-PERF-SCAN reported sites written as `seen = []` + `if x not in seen` with",
        "magnitude UNKNOWN. This measures the cost curve so those findings carry a number.",
        "Generated by `bench_dedup.py`; every figure is from the run stamped below.",
        "",
        "## Environment",
        "",
        "| Property | Value |",
        "| --- | --- |",
    ]
    for k in ["python_version", "python_implementation", "platform", "processor_model",
              "cpu_count_logical", "timer", "memory_probe", "note", "measured_at_utc"]:
        lines.append(f"| {k} | {env[k]} |")

    lines += ["", "## Elapsed time (seconds, minimum of counted repeats)", "",
              f"Each input holds `distinct_items` distinct values repeated ~{DUPLICATION_FACTOR}x, shuffled with a fixed seed.",
              "", "| Distinct items | Input length | " + " | ".join(report["strategy_order"]) + " |",
              "| ---: | ---: | " + " | ".join("---:" for _ in report["strategy_order"]) + " |"]
    for row in report["measurements"]:
        cells = " | ".join(f"{row['strategies'][s]['seconds_min']:.6f}" for s in report["strategy_order"])
        lines.append(f"| {row['distinct_items']:,} | {row['input_length']:,} | {cells} |")

    lines += ["", "## Speedup over the current form (`list_scan`)", "",
              "| Distinct items | " + " | ".join(
                  s for s in report["strategy_order"] if s != "list_scan") + " |",
              "| ---: | " + " | ".join("---:" for s in report["strategy_order"] if s != "list_scan") + " |"]
    for row in report["measurements"]:
        base = row["strategies"]["list_scan"]["seconds_min"]
        cells = []
        for s in report["strategy_order"]:
            if s == "list_scan":
                continue
            c = row["strategies"][s]["seconds_min"]
            cells.append(f"{base / c:.2f}x" if c > 0 else "n/a")
        lines.append(f"| {row['distinct_items']:,} | " + " | ".join(cells) + " |")

    lines += ["", "## Where it starts to matter (measured, not interpolated)", "",
              "| Comparison | Smallest measured n reaching the threshold | Speedup there |",
              "| --- | ---: | ---: |"]
    for key, cx in sorted(report["crossovers"].items()):
        n = cx["distinct_items"]
        sp = cx["speedup"]
        lines.append(f"| {key} | {n if isinstance(n, str) else format(n, ',')} | "
                     f"{sp if isinstance(sp, str) else f'{sp:.2f}x'} |")

    lines += ["", "## Peak Python-allocated memory (bytes)", "",
              "| Distinct items | " + " | ".join(report["strategy_order"]) + " |",
              "| ---: | " + " | ".join("---:" for _ in report["strategy_order"]) + " |"]
    for row in report["measurements"]:
        cells = " | ".join(f"{row['strategies'][s]['peak_bytes']:,}" for s in report["strategy_order"])
        lines.append(f"| {row['distinct_items']:,} | {cells} |")

    lines += ["", "## Unhashable elements", "",
              "Measured by running each strategy on a list of dicts, not by reading docs.",
              "This is why the recommendation is not simply \"use a set\".", "",
              "| Strategy | Works on unhashable input | Detail |",
              "| --- | --- | --- |"]
    for name, res in sorted(report["hashability"].items()):
        detail = f"returns {res['result_length']} items" if res["works_on_unhashable"] else res["error"]
        lines.append(f"| `{name}` | {'yes' if res['works_on_unhashable'] else 'NO'} | {detail} |")

    sites = report["scan_sites"]
    lines += ["", "## Sites this applies to", ""]
    if sites.get("available"):
        lines += [f"From the OPS-PERF-SCAN results at `{sites['source']}`, scanned {sites['scanned_at_utc']}.",
                  "", f"- Sites matching this shape: **{sites['site_count']}**",
                  f"- Input sizes at those sites: **UNKNOWN** — {sites['input_sizes']}", "",
                  "| File | Line | Source |", "| --- | ---: | --- |"]
        for s in sites["sites"]:
            lines.append(f"| `{s['file']}` | {s['line']} | `{s['source']}` |")
    else:
        lines.append(sites.get("note", "Scan results unavailable; site count UNKNOWN."))

    lines += ["", "## What is measured and what is not", "",
              "- **Measured here:** the elapsed times, peak allocations, speedups, crossover",
              "  points and unhashable-input behaviour above, on this machine in this run.",
              "- **UNKNOWN:** the number of distinct items each flagged site actually sees. That",
              "  depends on University data this lane does not have. The curve is a decision aid",
              "  against a known n; it is not a verdict on any site.",
              "- **Not claimed:** that any flagged site is too slow. None of them were profiled",
              "  in place. No lane, seat or person is scored.", ""]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Measure order-preserving dedup strategies.")
    p.add_argument("--results-dir", type=Path, default=HERE / "results")
    p.add_argument("--scan-results", type=Path,
                   default=HERE.parent / "uiowa_rfq_18649_capacity_scan" / "results" / "kit_scan_results.json")
    p.add_argument("--repeats", type=int, default=REPEATS)
    a = p.parse_args(argv)

    strategy_order = ["list_scan", "dict_fromkeys", "set_aside", "ordered_unique"]
    env = environment()
    print("environment:", json.dumps(env, indent=2, sort_keys=True))
    measurements = measure(strategy_order, SIZES, a.repeats)

    report = {
        "schema": "uiowa-ops-dedup-threshold-v1",
        "environment": env,
        "duplication_factor": DUPLICATION_FACTOR,
        "repeats": a.repeats,
        "strategy_order": strategy_order,
        "measurements": measurements,
        "crossovers": {
            f"{c} vs list_scan (2x faster)": find_crossover(measurements, "list_scan", c, 2.0)
            for c in strategy_order if c != "list_scan"
        },
        "hashability": hashability_report(),
        "scan_sites": load_scan_sites(a.scan_results),
        "recommended_strategy": dedup.RECOMMENDED,
        "recommendation_reason": (
            "dict_fromkeys and set_aside are faster but raise TypeError on unhashable "
            "elements. ordered_unique takes the fast path when it can and falls back "
            "per item when it cannot, so it is a drop-in without auditing each site."),
    }

    a.results_dir.mkdir(parents=True, exist_ok=True)
    (a.results_dir / "dedup_results.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with (a.results_dir / "dedup_results.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["distinct_items", "input_length", "strategy", "seconds_min",
                    "seconds_median", "peak_bytes", "samples"])
        for row in measurements:
            for s in strategy_order:
                d = row["strategies"][s]
                w.writerow([row["distinct_items"], row["input_length"], s,
                            f"{d['seconds_min']:.9f}", f"{d['seconds_median']:.9f}",
                            d["peak_bytes"], d["samples"]])
    (a.results_dir / "DEDUP_REPORT.md").write_text(render(report), encoding="utf-8")

    print(f"wrote {a.results_dir / 'dedup_results.json'}")
    print(f"wrote {a.results_dir / 'dedup_results.csv'}")
    print(f"wrote {a.results_dir / 'DEDUP_REPORT.md'}")
    for key, cx in sorted(report["crossovers"].items()):
        print(f"  {key}: n={cx['distinct_items']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
