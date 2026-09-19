#!/usr/bin/env python3
"""Peak memory per delivered lane.

OPS-RUN-SWEEP records whether each lane's suite runs and how long it takes.
This records how much memory it needs, which is the other half of "can an
operator run this kit on the machine they have".

One fresh subprocess per lane (see mem_probe.py for why). Read-only with
respect to other seats' lanes: it executes their test suites, which is what
those suites are for, and writes nothing into them.

Honesty rules enforced here:
  * A lane with no test suite is UNKNOWN, never 0.
  * A suite that fails, errors, or times out keeps its status and its memory
    figure is marked unusable rather than being reported as a low number.
  * The interpreter baseline is measured in the same run and reported
    alongside, not silently subtracted.

Python 3 standard library only. No network.
"""
from __future__ import annotations

import argparse
import csv
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE / "mem_probe.py"
DEFAULT_TIMEOUT = 300

# Statuses whose memory figure describes a complete run of the suite. Anything
# else gets its number withheld, because a peak measured up to the point a suite
# exploded is not that lane's cost.
USABLE_STATUSES = {"OK", "TESTS_FAILED"}


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
        "probe": "resource.getrusage(RUSAGE_SELF).ru_maxrss, read inside a fresh "
                 "subprocess per lane",
        "unit_note": "ru_maxrss is KiB on Linux and bytes on macOS; normalised to bytes "
                     "in mem_probe.py",
        "scope_note": "Peak RSS includes the Python interpreter baseline, which is measured "
                      "separately in the same run and reported rather than subtracted.",
        "measured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def measure_baseline(python: str = sys.executable) -> dict:
    proc = subprocess.run([python, str(PROBE), "--baseline"],
                          capture_output=True, text=True, timeout=60)
    return json.loads(proc.stdout.strip())


def measure_lane(lane: Path, python: str = sys.executable, timeout: int = DEFAULT_TIMEOUT) -> dict:
    started = time.perf_counter()
    try:
        proc = subprocess.run([python, str(PROBE), str(lane)],
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"lane": lane.name, "status": "TIMEOUT", "tests_run": "UNKNOWN",
                "peak_rss_bytes": "UNKNOWN",
                "note": f"Suite exceeded {timeout}s. Memory UNKNOWN -- a partial run's peak "
                        "is not this lane's cost.",
                "wall_seconds": time.perf_counter() - started}
    out = proc.stdout.strip()
    if not out:
        return {"lane": lane.name, "status": "NO_OUTPUT", "tests_run": "UNKNOWN",
                "peak_rss_bytes": "UNKNOWN",
                "note": "Probe produced no parseable output.",
                "stderr_tail": proc.stderr.strip()[-400:],
                "wall_seconds": time.perf_counter() - started}
    try:
        record = json.loads(out.splitlines()[-1])
    except json.JSONDecodeError as exc:
        return {"lane": lane.name, "status": "UNPARSEABLE", "tests_run": "UNKNOWN",
                "peak_rss_bytes": "UNKNOWN", "note": f"{type(exc).__name__}: {exc}",
                "stdout_tail": out[-400:],
                "wall_seconds": time.perf_counter() - started}

    record.setdefault("lane", lane.name)
    record["wall_seconds"] = time.perf_counter() - started
    if record.get("status") not in USABLE_STATUSES:
        # Keep what was observed, but do not let it be read as the lane's cost.
        record["peak_rss_bytes_observed"] = record.get("peak_rss_bytes", "UNKNOWN")
        record["peak_rss_bytes"] = "UNKNOWN"
    return record


def measure_all(revenue_root: Path, lane_glob: str, timeout: int) -> dict:
    revenue_root = Path(revenue_root).resolve()
    lanes = sorted(p for p in revenue_root.glob(lane_glob) if p.is_dir())
    baseline = measure_baseline()
    records = [measure_lane(lane, timeout=timeout) for lane in lanes]

    measured = [r for r in records if isinstance(r.get("peak_rss_bytes"), int)]
    by_status = {}
    for r in records:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1

    summary = {
        "lanes_found": len(lanes),
        "lanes_with_a_usable_figure": len(measured),
        "lanes_without_a_usable_figure": len(records) - len(measured),
        "by_status": by_status,
        "baseline_peak_rss_bytes": baseline["peak_rss_bytes"],
    }
    if measured:
        peaks = sorted(measured, key=lambda r: r["peak_rss_bytes"])
        summary.update({
            "lowest_peak_rss_bytes": peaks[0]["peak_rss_bytes"],
            "lowest_peak_lane": peaks[0]["lane"],
            "highest_peak_rss_bytes": peaks[-1]["peak_rss_bytes"],
            "highest_peak_lane": peaks[-1]["lane"],
            "median_peak_rss_bytes": peaks[len(peaks) // 2]["peak_rss_bytes"],
        })
    else:
        summary.update({"lowest_peak_rss_bytes": "UNKNOWN", "highest_peak_rss_bytes": "UNKNOWN",
                        "median_peak_rss_bytes": "UNKNOWN"})

    return {
        "schema": "uiowa-ops-memory-ceiling-v1",
        "revenue_root": str(revenue_root),
        "lane_glob": lane_glob,
        "timeout_seconds": timeout,
        "environment": environment(),
        "baseline": baseline,
        "summary": summary,
        "lanes": records,
    }


def render(report: dict) -> str:
    env = report["environment"]
    s = report["summary"]
    base = s["baseline_peak_rss_bytes"]

    def mib(v):
        return f"{v / (1024 * 1024):.1f}" if isinstance(v, int) else "UNKNOWN"

    lines = [
        "# Peak memory per delivered lane",
        "",
        "How much memory each lane's own test suite needs. Companion to OPS-RUN-SWEEP,",
        "which records whether suites run and how long they take; this records what they",
        "cost in memory. Generated by `measure_memory.py`.",
        "",
        "Each lane runs in a fresh subprocess and reports",
        "`resource.getrusage(RUSAGE_SELF).ru_maxrss` from inside itself, so the figure",
        "belongs to that lane rather than being a running maximum across lanes.",
        "",
        "## Environment",
        "",
        "| Property | Value |",
        "| --- | --- |",
    ]
    for k in ["python_version", "python_implementation", "platform", "processor_model",
              "cpu_count_logical", "probe", "unit_note", "scope_note", "measured_at_utc"]:
        lines.append(f"| {k} | {env[k]} |")

    lines += [
        "",
        "## Summary",
        "",
        f"- Lanes found: **{s['lanes_found']}**",
        f"- Lanes with a usable figure: **{s['lanes_with_a_usable_figure']}**",
        f"- Lanes without one (UNKNOWN, not zero): **{s['lanes_without_a_usable_figure']}**",
        f"- Bare-interpreter baseline: **{mib(base)} MiB** — every figure below includes this.",
        f"- Lowest peak: **{mib(s['lowest_peak_rss_bytes'])} MiB** (`{s.get('lowest_peak_lane', 'UNKNOWN')}`)",
        f"- Median peak: **{mib(s['median_peak_rss_bytes'])} MiB**",
        f"- Highest peak: **{mib(s['highest_peak_rss_bytes'])} MiB** (`{s.get('highest_peak_lane', 'UNKNOWN')}`)",
        "",
        "Statuses observed:",
        "",
        "| Status | Lanes |",
        "| --- | ---: |",
    ]
    for status, count in sorted(s["by_status"].items()):
        lines.append(f"| `{status}` | {count} |")

    lines += ["", "## Per lane", "",
              "Sorted by peak memory. `UNKNOWN` means the suite did not complete, so no",
              "figure describes it — it does not mean the lane is free.",
              "",
              "| Lane | Status | Tests run | Peak RSS (MiB) | Above baseline (MiB) | Suite seconds |",
              "| --- | --- | ---: | ---: | ---: | ---: |"]

    def sort_key(r):
        v = r.get("peak_rss_bytes")
        return (0, -v) if isinstance(v, int) else (1, 0)

    for r in sorted(report["lanes"], key=sort_key):
        peak = r.get("peak_rss_bytes")
        over = f"{(peak - base) / (1024 * 1024):.1f}" if isinstance(peak, int) and isinstance(base, int) else "UNKNOWN"
        secs = r.get("elapsed_seconds")
        secs_s = f"{secs:.2f}" if isinstance(secs, (int, float)) else "UNKNOWN"
        lines.append(f"| `{r['lane']}` | {r['status']} | {r.get('tests_run', 'UNKNOWN')} "
                     f"| {mib(peak)} | {over} | {secs_s} |")

    notes = [r for r in report["lanes"] if r.get("note") or r.get("error")]
    if notes:
        lines += ["", "## Lanes with no usable figure", "",
                  "| Lane | Status | Why |", "| --- | --- | --- |"]
        for r in notes:
            why = (r.get("error") or r.get("note") or "").replace("|", "\\|")
            lines.append(f"| `{r['lane']}` | {r['status']} | {why} |")

    lines += [
        "",
        "## What is measured and what is not",
        "",
        "- **Measured:** peak RSS and suite duration for each lane's own test suite, on this",
        "  machine in this run, plus the interpreter baseline.",
        "- **Includes the interpreter baseline.** It is reported rather than subtracted, so",
        "  the numbers stay comparable to what an operator would actually see.",
        "- **UNKNOWN:** memory under the University's real data volumes. Test suites run on",
        "  small synthetic fixtures; these figures are not a prediction of production memory",
        "  and are not extrapolated into one.",
        "- **UNKNOWN:** any lane whose suite did not complete, and any lane with no suite.",
        "  Absence of a measurement is recorded as absence, never as zero.",
        "- **Not a score.** Lanes are sorted by memory so an operator can see the ceiling.",
        "  A higher figure is not a defect and no lane, seat or person is being ranked.",
        "",
    ]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Measure peak memory per delivered lane.")
    p.add_argument("--revenue", type=Path, required=True)
    p.add_argument("--lane-glob", default="uiowa_rfq_18649_*")
    p.add_argument("--out", type=Path, default=HERE / "results")
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    a = p.parse_args(argv)

    if not a.revenue.is_dir():
        print(f"not a directory: {a.revenue}", file=sys.stderr)
        return 2

    report = measure_all(a.revenue, a.lane_glob, a.timeout)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "memory_results.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with (a.out / "memory_results.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["lane", "status", "tests_run", "peak_rss_bytes", "elapsed_seconds"])
        for r in report["lanes"]:
            w.writerow([r["lane"], r["status"], r.get("tests_run", "UNKNOWN"),
                        r.get("peak_rss_bytes", "UNKNOWN"), r.get("elapsed_seconds", "UNKNOWN")])
    (a.out / "MEMORY_REPORT.md").write_text(render(report), encoding="utf-8")

    s = report["summary"]
    print(f"lanes={s['lanes_found']} usable={s['lanes_with_a_usable_figure']} "
          f"unknown={s['lanes_without_a_usable_figure']}")
    print(f"baseline={s['baseline_peak_rss_bytes']} bytes")
    print(f"highest={s['highest_peak_rss_bytes']} ({s.get('highest_peak_lane')})")
    for status, count in sorted(s["by_status"].items()):
        print(f"  {status}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
