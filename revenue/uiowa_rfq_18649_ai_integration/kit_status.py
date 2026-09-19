"""Emit a KIT-STATUS line so a runner can read this lane's result without parsing prose.

Conforms to the contract defined in revenue/uiowa_rfq_18649_exit_signals/contract.py.
It does NOT import it, deliberately: lanes in this kit are independently runnable, and
a cross-lane import would make this one fail to run on its own. The LINE FORMAT is the
interface; six lines of duplication is the correct price for lane independence.

    0 CLEAN          ran to completion; nothing requiring operator attention
    1 FINDINGS       ran to completion; found something an operator must look at
    2 INPUT_ERROR    could not run: bad arguments, missing or malformed input
    3 INDETERMINATE  ran, but could not determine whether there are findings
"""

CLEAN, FINDINGS, INPUT_ERROR, INDETERMINATE = 0, 1, 2, 3
_NAME = {CLEAN: "CLEAN", FINDINGS: "FINDINGS", INPUT_ERROR: "INPUT_ERROR",
         INDETERMINATE: "INDETERMINATE"}


def decide(findings, indeterminate, input_error=False):
    """INPUT_ERROR > FINDINGS > INDETERMINATE > CLEAN.

    INDETERMINATE always outranks CLEAN: 0 means "checked and clean", and a tool that
    could not evaluate part of its subject has not checked it.
    """
    if input_error:
        return INPUT_ERROR
    if findings > 0:
        return FINDINGS
    if indeterminate > 0:
        return INDETERMINATE
    return CLEAN


def emit(tool, findings=0, indeterminate=0, input_error=False, note=""):
    code = decide(findings, indeterminate, input_error)
    fields = [f"code={code}", f"status={_NAME[code]}", f"tool={tool}",
              f"findings={findings}", f"indeterminate={indeterminate}"]
    if note:
        fields.append("note=" + note.replace("\n", " ")[:160])
    print("KIT-STATUS: " + " ".join(fields))
    return code
