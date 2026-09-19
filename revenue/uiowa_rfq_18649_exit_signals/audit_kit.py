"""Audit a tree of kit tools for whether they can signal a finding.

Run:  python3 audit_kit.py <root>         (default: this lane's fixtures/)

Obeys its own contract, which is the point: a tool that audits exit signals and
cannot itself signal would be the defect it is reporting.
  0 CLEAN          every entrypoint can signal
  1 FINDINGS       at least one HIGH/MEDIUM finding
  2 INPUT_ERROR    the root does not exist
  3 INDETERMINATE  only INFO findings plus at least one unresolvable entrypoint
"""

import argparse
import json
import os
import sys

import contract
import report
import scan

OUT = "out"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default="fixtures",
                        help="directory to scan (read-only)")
    parser.add_argument("--out", default=OUT, help="output directory")
    parser.add_argument("--snapshot-note", default="",
                        help="provenance line recorded in the rendered report")
    parser.add_argument("--lane-prefix", default="",
                        help="restrict to top-level lane dirs with this name prefix")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    if not os.path.isdir(args.root):
        print(f"root not found: {args.root}", file=sys.stderr)
        print(contract.status_line(contract.INPUT_ERROR, "audit_kit",
                                   note=f"root not found: {args.root}"))
        return contract.INPUT_ERROR

    result = scan.scan_tree(args.root, lane_prefix=args.lane_prefix or None)
    stats = report.summarize(result)

    os.makedirs(args.out, exist_ok=True)
    written = []
    for name, text in (
            ("exit_signal_audit.md", report.render_markdown(result, args.snapshot_note)),
            ("exit_signal_audit.csv", report.render_csv(result))):
        path = os.path.join(args.out, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        written.append((path, len(text)))
    path = os.path.join(args.out, "exit_signal_audit.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({"summary": stats, "snapshot_note": args.snapshot_note,
                   "entrypoints": result["entrypoints"]},
                  handle, indent=2, sort_keys=True)
        handle.write("\n")
    written.append((path, os.path.getsize(path)))

    if not args.quiet:
        print(f"Scanned {stats['root']}")
        for out_path, size in written:
            print(f"  {out_path:<36} {size:>7} bytes")
        print(f"\n  lanes={stats['lanes']} entrypoints={stats['entrypoints']}")
        print(f"  GATE={stats['gate_count']}  "
              f"REPORT_ONLY={stats['report_only_count']}  "
              f"INDETERMINATE={stats['indeterminate_count']}")
        for code in sorted(stats["finding_counts"],
                           key=lambda c: (-stats["finding_counts"][c], c)):
            print(f"  {code:<18} {stats['finding_counts'][code]}")

    actionable = sum(count for code, count in stats["finding_counts"].items()
                     if code in ("FALSE_CLEAN", "NO_SIGNAL_PATH", "DEAD_GATE",
                                 "UNPARSEABLE", "UNREADABLE"))
    # A tool that declares its status at runtime is not unresolved to a runner,
    # so only genuinely unreadable exits count toward INDETERMINATE.
    unresolved = stats["finding_counts"].get("UNRESOLVED_EXIT", 0) + \
        stats["finding_counts"].get("UNPARSEABLE", 0)
    code = contract.emit("audit_kit", findings=actionable, indeterminate=unresolved,
                         note=f"{stats['report_only_count']} of "
                              f"{stats['entrypoints']} entrypoints cannot signal")
    return code


if __name__ == "__main__":
    sys.exit(main())
