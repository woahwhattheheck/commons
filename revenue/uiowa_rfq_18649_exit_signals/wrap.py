"""Run an existing kit tool and re-emit a contract-conformant exit code.

This is the remediation path that respects lane ownership. Every tool in the
delivery kit belongs to the seat that built it. Rather than editing 51 lanes to add
an exit code, a runner wraps a tool from outside: run it as a subprocess, read its
output, and translate whatever it did into the contract.

Two rules hold this honest.

  1. The DEFAULT fallback is INDETERMINATE, not CLEAN. A tool that emits no status
     line and has no declared rule has told the runner nothing about its subject.
     Recording that as a pass is the same error as scoring an un-inventoried system
     as zero.
  2. A crash is translated to INPUT_ERROR, never FINDINGS. An uncaught exception
     exits non-zero, which looks identical to a gate from the outside -- see the
     t_crash_only fixture, which exits 1 exactly like t_gate. The difference is
     visible only in whether the process left a traceback, so that is what is
     checked. A crash says the tool broke; it makes no statement about the kit.
"""

import argparse
import os
import subprocess
import sys

import contract

RULE_STATUS_ONLY = "status_only"      # default: no status line -> INDETERMINATE
RULE_EXIT_CODE = "exit_code"          # trust the tool's own exit code
RULE_STDOUT_MARKERS = "stdout_markers"  # declared words on stdout mean FINDINGS

RULES = (RULE_STATUS_ONLY, RULE_EXIT_CODE, RULE_STDOUT_MARKERS)

_TRACEBACK = "Traceback (most recent call last)"


def run_tool(command, rule=RULE_STATUS_ONLY, markers=(), timeout=120, cwd=None):
    """Run `command` (a list) and return a contract decision with its reasoning."""
    if rule not in RULES:
        raise ValueError(f"unknown fallback rule {rule!r}; expected one of {RULES}")
    try:
        completed = subprocess.run(command, capture_output=True, text=True,
                                   timeout=timeout, cwd=cwd, check=False)
    except FileNotFoundError as exc:
        return {"code": contract.INPUT_ERROR, "basis": "tool_not_found",
                "detail": str(exc), "returncode": None, "stdout": "", "stderr": ""}
    except subprocess.TimeoutExpired:
        return {"code": contract.INDETERMINATE, "basis": "timeout",
                "detail": f"tool did not finish within {timeout}s, so whether it has "
                          f"findings is unknown",
                "returncode": None, "stdout": "", "stderr": ""}

    stdout, stderr = completed.stdout, completed.stderr
    status = contract.parse_status_line(stdout) or contract.parse_status_line(stderr)

    if status is not None:
        return {"code": status["code"], "basis": "contract_status_line",
                "detail": f"tool declared {contract.CODE_NAME[status['code']]}",
                "returncode": completed.returncode, "stdout": stdout, "stderr": stderr,
                "status": status}

    crashed = _TRACEBACK in stderr
    if crashed:
        return {"code": contract.INPUT_ERROR, "basis": "uncaught_exception",
                "detail": "the tool exited via an uncaught exception; a crash is not "
                          "a statement about the subject, so this is INPUT_ERROR and "
                          "not FINDINGS",
                "returncode": completed.returncode, "stdout": stdout, "stderr": stderr}

    if rule == RULE_EXIT_CODE:
        code = contract.CLEAN if completed.returncode == 0 else contract.FINDINGS
        return {"code": code, "basis": "declared_rule:exit_code",
                "detail": f"no status line; operator declared that this tool's exit "
                          f"code is meaningful (got {completed.returncode})",
                "returncode": completed.returncode, "stdout": stdout, "stderr": stderr}

    if rule == RULE_STDOUT_MARKERS:
        if not markers:
            return {"code": contract.INPUT_ERROR, "basis": "declared_rule:no_markers",
                    "detail": "stdout_markers rule selected but no markers given",
                    "returncode": completed.returncode, "stdout": stdout,
                    "stderr": stderr}
        hits = [marker for marker in markers if marker.lower() in stdout.lower()]
        code = contract.FINDINGS if hits else contract.CLEAN
        return {"code": code, "basis": "declared_rule:stdout_markers",
                "detail": (f"markers present on stdout: {', '.join(hits)}" if hits
                           else "none of the declared markers appeared on stdout"),
                "returncode": completed.returncode, "stdout": stdout, "stderr": stderr,
                "markers_hit": hits}

    return {"code": contract.INDETERMINATE, "basis": "no_status_no_rule",
            "detail": "the tool emitted no status line and no fallback rule was "
                      "declared, so whether it has findings is unknown. Not recorded "
                      "as clean.",
            "returncode": completed.returncode, "stdout": stdout, "stderr": stderr}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Run a kit tool and re-emit a contract-conformant exit code.")
    parser.add_argument("--rule", choices=RULES, default=RULE_STATUS_ONLY)
    parser.add_argument("--marker", action="append", default=[],
                        help="stdout marker meaning FINDINGS (repeatable)")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--quiet", action="store_true",
                        help="suppress the wrapped tool's own output")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    command = [part for part in args.command if part != "--"]
    if not command:
        print("usage: python3 wrap.py [--rule RULE] [--marker WORD] -- <command>",
              file=sys.stderr)
        print(contract.status_line(contract.INPUT_ERROR, "wrap", note="no command"))
        return contract.INPUT_ERROR

    result = run_tool(command, rule=args.rule, markers=tuple(args.marker),
                      timeout=args.timeout)
    if not args.quiet:
        sys.stdout.write(result.get("stdout", ""))
        sys.stderr.write(result.get("stderr", ""))
    print(contract.status_line(result["code"], os.path.basename(command[-1]),
                               findings=1 if result["code"] == contract.FINDINGS else 0,
                               indeterminate=1 if result["code"] == contract.INDETERMINATE
                               else 0,
                               note=f"{result['basis']}: {result['detail']}"))
    return result["code"]


if __name__ == "__main__":
    sys.exit(main())
