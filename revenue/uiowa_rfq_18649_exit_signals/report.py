"""Render the scan: Markdown, CSV, JSON."""

import csv
import io

import scan

SEVERITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "INFO": 3}


def summarize(result):
    entrypoints = result["entrypoints"]
    by_class = {}
    for entry in entrypoints:
        by_class[entry["classification"]] = by_class.get(entry["classification"], 0) + 1
    finding_counts = {}
    for entry in entrypoints:
        for finding in entry["findings"]:
            finding_counts[finding["code"]] = finding_counts.get(finding["code"], 0) + 1
    lanes = sorted({entry.get("lane", "(root)") for entry in entrypoints})
    return {
        "root": result["root"],
        "lanes": len(lanes),
        "entrypoints": len(entrypoints),
        "non_entrypoint_files_skipped": result["non_entrypoint_files_skipped"],
        "by_classification": by_class,
        "finding_counts": finding_counts,
        "gate_count": by_class.get(scan.GATE, 0),
        "report_only_count": by_class.get(scan.REPORT_ONLY, 0),
        "indeterminate_count": by_class.get(scan.INDETERMINATE, 0),
        "false_clean_count": finding_counts.get("FALSE_CLEAN", 0),
        "dead_gate_count": finding_counts.get("DEAD_GATE", 0),
    }


def render_markdown(result, snapshot_note=""):
    stats = summarize(result)
    out = ["# Kit exit-signal audit", ""]
    if snapshot_note:
        out += [f"> {snapshot_note}", ""]
    out += [f"Scanned `{stats['root']}` - {stats['lanes']} lane(s), "
            f"{stats['entrypoints']} entrypoint(s) with a `__main__` guard "
            f"({stats['non_entrypoint_files_skipped']} non-entrypoint files skipped).",
            "",
            "| Classification | Count | Meaning |", "|---|---|---|",
            f"| `GATE` | {stats['gate_count']} | a non-zero exit is reachable |",
            f"| `REPORT_ONLY` | {stats['report_only_count']} | always exits 0 |",
            f"| `INDETERMINATE` | {stats['indeterminate_count']} | exit value not "
            f"statically resolvable; not assumed either way |", "",
            "| Finding | Count |", "|---|---|"]
    for code in sorted(stats["finding_counts"],
                       key=lambda c: (-stats["finding_counts"][c], c)):
        out.append(f"| `{code}` | {stats['finding_counts'][code]} |")
    out.append("")

    high = [(entry, finding) for entry in result["entrypoints"]
            for finding in entry["findings"]
            if finding.get("severity") == "HIGH"]
    if high:
        out += ["## HIGH-severity findings", ""]
        for entry, finding in sorted(high, key=lambda pair: pair[0]["tool"]):
            out += [f"### `{entry['tool']}` - `{finding['code']}`", "",
                    f"{finding['detail']}", "",
                    f"*Remedy:* {finding['remedy']}", ""]

    out += ["## Every entrypoint", "",
            "| Tool | Class | Contract line | Dead non-zero exits | Findings |",
            "|---|---|---|---|---|"]
    for entry in sorted(result["entrypoints"], key=lambda e: e["tool"]):
        codes = ", ".join(f"`{f['code']}`" for f in entry["findings"]) or "none"
        out.append(f"| `{entry['tool']}` | `{entry['classification']}` | "
                   f"{'yes' if entry['emits_contract_status'] else 'no'} | "
                   f"{entry['dead_nonzero_exits']} | {codes} |")
    return "\n".join(out).rstrip() + "\n"


def render_csv(result):
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["tool", "lane", "classification", "emits_contract_status",
                     "dead_nonzero_exits", "unresolved_exits", "raises_uncaught",
                     "finding_code", "severity", "detail"])
    for entry in sorted(result["entrypoints"], key=lambda e: e["tool"]):
        rows = entry["findings"] or [{"code": "", "severity": "", "detail": ""}]
        for finding in rows:
            writer.writerow([entry["tool"], entry.get("lane", ""),
                             entry["classification"],
                             entry["emits_contract_status"],
                             entry["dead_nonzero_exits"], entry["unresolved_exits"],
                             entry["raises_uncaught"], finding.get("code", ""),
                             finding.get("severity", ""), finding.get("detail", "")])
    return buffer.getvalue()
