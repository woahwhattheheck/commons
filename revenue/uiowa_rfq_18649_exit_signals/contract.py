"""The kit runner contract: how a delivery-kit tool signals what it found.

Measured gap this exists to close: across the landed UIOWA delivery kit, most tool
entrypoints cannot return a non-zero exit code under any input. An operator running
the kit gets exit 0 from a tool that found a serious problem and exit 0 from a tool
that found nothing. The finding lives in stdout, which makes it real only if a human
reads every line of every tool -- precisely the assumption this engagement's
discipline exists to remove.

The contract is four codes and one optional status line.

    0  CLEAN          ran to completion, nothing requiring attention
    1  FINDINGS       ran to completion, found something an operator must look at
    2  INPUT_ERROR    could not run: bad arguments, missing or malformed input
    3  INDETERMINATE  ran, but could not determine whether there are findings

Code 3 is the one that makes this contract belong to THIS engagement. The standing
rule is that missing evidence stays UNKNOWN -- it never becomes a pass. A tool that
could not reach its inputs, or could not evaluate part of what it was asked about,
must not exit 0, because 0 means "I checked and it is clean". Collapsing "clean" and
"could not tell" into one code is the same error as scoring an un-inventoried system
as zero.

A crash is not a signal. An uncaught exception also produces a non-zero code, but it
carries no statement about the subject -- it says the tool broke, not that the kit
has findings. scan.py classifies those separately for that reason.
"""

import sys

CLEAN = 0
FINDINGS = 1
INPUT_ERROR = 2
INDETERMINATE = 3

CODE_NAME = {
    CLEAN: "CLEAN",
    FINDINGS: "FINDINGS",
    INPUT_ERROR: "INPUT_ERROR",
    INDETERMINATE: "INDETERMINATE",
}

CODE_MEANING = {
    CLEAN: "ran to completion; nothing requiring operator attention",
    FINDINGS: "ran to completion; found something an operator must look at",
    INPUT_ERROR: "could not run: bad arguments, or missing/malformed input",
    INDETERMINATE: "ran, but could not determine whether there are findings",
}

STATUS_PREFIX = "KIT-STATUS:"


def status_line(code, tool, findings=0, indeterminate=0, note=""):
    """One machine-readable line a runner can grep for without parsing prose.

    Deliberately a single flat line rather than JSON on stdout: it has to survive
    being mixed into human-readable output, and a runner has to be able to find it
    with a grep in a shell pipeline.
    """
    if code not in CODE_NAME:
        raise ValueError(f"exit code {code!r} is not part of the contract "
                         f"{sorted(CODE_NAME)}")
    fields = [f"code={code}", f"status={CODE_NAME[code]}", f"tool={tool}",
              f"findings={findings}", f"indeterminate={indeterminate}"]
    if note:
        fields.append(f"note={note.replace(chr(10), ' ')[:160]}")
    return STATUS_PREFIX + " " + " ".join(fields)


def decide(findings, indeterminate, input_error=False):
    """The contract's precedence order, in one place so it cannot drift.

    INPUT_ERROR first (the run did not happen), then FINDINGS, then INDETERMINATE,
    then CLEAN. FINDINGS outranks INDETERMINATE because a known problem is more
    actionable than an unmeasured area; but INDETERMINATE outranks CLEAN, always.
    """
    if input_error:
        return INPUT_ERROR
    if findings > 0:
        return FINDINGS
    if indeterminate > 0:
        return INDETERMINATE
    return CLEAN


def emit(tool, findings=0, indeterminate=0, input_error=False, note="",
         stream=None):
    """Print the status line and return the exit code. Does not call sys.exit()
    itself, so a caller can still run cleanup."""
    code = decide(findings, indeterminate, input_error)
    print(status_line(code, tool, findings, indeterminate, note),
          file=stream or sys.stdout)
    return code


def parse_status_line(text):
    """Read a status line back out of captured output. Returns None if absent.

    Used by wrap.py to tell a contract-aware tool from one that needs a fallback
    rule applied to it.
    """
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line.startswith(STATUS_PREFIX):
            continue
        parsed = {}
        for token in line[len(STATUS_PREFIX):].strip().split(" "):
            if "=" in token:
                key, _, value = token.partition("=")
                parsed[key] = value
        if "code" not in parsed:
            return None
        try:
            parsed["code"] = int(parsed["code"])
        except ValueError:
            return None
        if parsed["code"] not in CODE_NAME:
            return None
        return parsed
    return None
