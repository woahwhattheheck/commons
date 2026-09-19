#!/usr/bin/env python3
"""Run the fictional operator journey through real CLI subprocesses.

The output directory must not exist. Partial runs retain their command logs;
rehearsal.json is written only after every expected result has been observed.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys


HERE = Path(__file__).resolve().parent


class RehearsalError(ValueError):
    """The real CLI did not produce the specified fictional journey."""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _save(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def _require(condition: bool, detail: str) -> None:
    if not condition:
        raise RehearsalError(detail)


def _files(directory: Path) -> dict[str, str]:
    return {str(p.relative_to(directory)): _sha(p)
            for p in sorted(directory.rglob("*")) if p.is_file()}


def _issue_comparison(baseline: dict, revised: dict) -> list[dict]:
    """Issue IDs are local to each receipt; code and subject identify the comparison."""
    groups: dict[tuple[str, str], dict] = {}
    for label, receipt in (("baseline", baseline), ("revised", revised)):
        for issue in receipt["issues"]:
            key = (issue["code"], issue["subject"])
            if key not in groups:
                groups[key] = {"code": key[0], "subject": key[1],
                               "baseline_issue_ids": [], "revised_issue_ids": []}
            groups[key][f"{label}_issue_ids"].append(issue["issue_id"])
    return [groups[key] for key in sorted(groups)]


def rehearse(output_dir: Path) -> dict:
    output_dir = output_dir.absolute()
    output_dir.mkdir(parents=True, exist_ok=False)
    log_dir = output_dir / "commands"
    log_dir.mkdir()
    python = [sys.executable, "-B"] + (["-O"] if sys.flags.optimize else [])
    cli = HERE / "mortgage_case_reconcile.py"
    commands: list[dict] = []
    sources = {name: _sha(HERE / name) for name in
               ("mortgage_core.py", "mortgage_case_reconcile.py", "rehearse_mortgage.py",
                "sample_case.json", "revised_case.json")}

    def run(label: str, args: list[str], expected: int = 0,
            cwd: Path = HERE) -> None:
        index = len(commands) + 1
        command = python + args
        result = subprocess.run(command, cwd=cwd, capture_output=True, timeout=30)
        stem = f"{index:02d}-{label}"
        stdout = result.stdout.decode("utf-8", errors="replace")
        stderr = result.stderr.decode("utf-8", errors="replace")
        (log_dir / f"{stem}.stdout.txt").write_bytes(result.stdout)
        (log_dir / f"{stem}.stderr.txt").write_bytes(result.stderr)
        entry = {"label": label, "argv": command, "command": shlex.join(command),
                 "cwd": str(cwd), "exit_code": result.returncode,
                 "expected_exit_code": expected, "stdout": stdout, "stderr": stderr}
        _save(log_dir / f"{stem}.json", entry)
        commands.append(entry)
        _require(result.returncode == expected,
                 f"{label}: expected exit {expected}, observed {result.returncode}; see command logs")

    receipts: dict[str, dict] = {}
    for label, input_name in (("baseline", "sample_case.json"),
                              ("revised", "revised_case.json")):
        bundle = output_dir / label
        run(f"{label}-bundle", [str(cli), "bundle", str(HERE / input_name),
                                "--output-dir", str(bundle)])
        run(f"{label}-portable-verify",
            [str(bundle / "mortgage_case_reconcile.py"), "verify-bundle", "."], cwd=bundle)
        _require((bundle / "case.json").read_bytes() == (HERE / input_name).read_bytes(),
                 f"{label}: original input bytes were not retained")
        receipts[label] = json.loads((bundle / "receipt.json").read_text(encoding="utf-8"))

    baseline, revised = receipts["baseline"], receipts["revised"]
    expected_codes = Counter({"FIELD_CONFLICT": 1, "DOCUMENT_STATUS_CONFLICT": 1,
                              "DOCUMENT_REQUIREMENT_UNMET": 2, "MILESTONE_AMBIGUOUS": 1})
    _require(Counter(issue["code"] for issue in baseline["issues"]) == expected_codes,
             "baseline: expected exactly the five documented reconciliation issues")
    _require(baseline["reconciliation_status"] == "REVIEW_REQUIRED" and
             baseline["current_milestone"] is None and
             baseline["current_milestone_status"] == "AMBIGUOUS",
             "baseline: contradictory status evidence must remain ambiguous")
    _require(not revised["issues"] and revised["reconciliation_status"] == "NO_DECLARED_BLOCKERS"
             and revised["current_milestone"] == "REVIEW"
             and revised["current_milestone_status"] == "KNOWN",
             "revised: supplied corrections must reconcile without declared blockers")
    for label, receipt in receipts.items():
        authority_flags = [value for value in receipt["authority"].values()
                           if type(value) is bool]
        _require(bool(authority_flags) and not any(authority_flags),
                 f"{label}: all authority flags must remain false")

    # Exercise the original compile/verify interface as well as portable bundles.
    exports = output_dir / "separate-exports"
    exports.mkdir()
    run("separate-compile", [str(cli), "compile", str(HERE / "sample_case.json"),
                             "--json-out", str(exports / "receipt.json"),
                             "--csv-out", str(exports / "exceptions.csv"),
                             "--html-out", str(exports / "summary.html")])
    run("separate-verify", [str(cli), "verify", str(HERE / "sample_case.json"),
                            str(exports / "receipt.json")])
    for name in ("receipt.json", "exceptions.csv", "summary.html"):
        _require((exports / name).read_bytes() == (output_dir / "baseline" / name).read_bytes(),
                 f"{name}: separate compile and bundle disagree")

    # Deliberately edited receipt is a separate artifact; the original bundle remains intact.
    drifted = json.loads(json.dumps(baseline))
    drifted["current_milestone"] = "REVIEW"
    drift_path = output_dir / "deliberately-edited-receipt.json"
    _save(drift_path, drifted)
    run("edited-receipt-rejected", [str(cli), "verify", str(HERE / "sample_case.json"),
                                    str(drift_path)], expected=2)
    baseline_files_before = _files(output_dir / "baseline")
    run("existing-bundle-rejected", [str(cli), "bundle", str(HERE / "sample_case.json"),
                                     "--output-dir", str(output_dir / "baseline")], expected=2)
    _require(_files(output_dir / "baseline") == baseline_files_before,
             "existing bundle was changed during rejected overwrite")
    _require(all(_sha(HERE / name) == expected for name, expected in sources.items()),
             "source or fixture bytes changed during the rehearsal")

    comparison = _issue_comparison(baseline, revised)
    result = {
        "schema": "mortgage-operator-rehearsal/v1", "ok": True,
        "fixture_classification": "STRICTLY_FICTIONAL", "python_optimized": bool(sys.flags.optimize),
        "source_files_sha256": sources, "commands": commands,
        "baseline": {"receipt": "baseline/receipt.json", "source_digest": baseline["source_digest"],
                     "semantic_digest": baseline["semantic_digest"], "issues": baseline["issues"],
                     "reconciliation_status": baseline["reconciliation_status"],
                     "current_milestone": baseline["current_milestone"],
                     "current_milestone_status": baseline["current_milestone_status"],
                     "authority": baseline["authority"]},
        "revised": {"receipt": "revised/receipt.json", "source_digest": revised["source_digest"],
                    "semantic_digest": revised["semantic_digest"], "issues": revised["issues"],
                    "reconciliation_status": revised["reconciliation_status"],
                    "current_milestone": revised["current_milestone"],
                    "current_milestone_status": revised["current_milestone_status"],
                    "authority": revised["authority"]},
        "issue_comparison": comparison,
        "existing_bundle_unchanged": True,
        "correction_provenance": "The revised fictional input explicitly supplies corrections; the software does not infer or authorize them.",
        "browser_execution_performed": False,
    }
    lines = ["# Fictional mortgage reconciliation rehearsal", "",
             "The original and revised supplied snapshots remain separate. Reconciliation does not authorize lending.", "",
             "| Packet | Declared reconciliation | Current supplied status | Issues |",
             "|---|---|---|---|",
             f"| Baseline | {baseline['reconciliation_status']} | AMBIGUOUS | {len(baseline['issues'])} |",
             f"| Revised | {revised['reconciliation_status']} | REVIEW | {len(revised['issues'])} |", "",
             "The revised fixture supplies corrected source observations and a corrected status timestamp. No correction was inferred.", "",
             "| Issue code | Subject | Baseline issue IDs | Revised issue IDs |",
             "|---|---|---|---|"]
    for row in comparison:
        lines.append(f"| {row['code']} | {row['subject']} | {', '.join(row['baseline_issue_ids'])} | {', '.join(row['revised_issue_ids']) or 'None'} |")
    lines += ["", "Issue IDs belong to their own receipt. This table compares code and subject, not assumed cross-receipt ID identity.",
              "", "Open each packet's summary.html for its complete observations, timeline and exception queue. No browser execution is claimed.",
              "", "Literal commands, stdout, stderr and exit codes are retained under commands/ and in rehearsal.json. The intentionally edited receipt is outside both valid packets.", ""]
    (output_dir / "READOUT.md").write_text("\n".join(lines), encoding="utf-8")
    _save(output_dir / "rehearsal.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = rehearse(args.output_dir)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(f"rehearsal error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"ok": result["ok"], "commands": len(result["commands"]),
                      "python_optimized": result["python_optimized"],
                      "output_dir": str(args.output_dir.absolute())}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
