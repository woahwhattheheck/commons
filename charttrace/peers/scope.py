"""Single global scope statement (not timid boilerplate on every lead)."""

GLOBAL_SCOPE_STATEMENT = (
    "ChartTrace is an investigative research aid. It separates record-supported "
    "observations, external authority, hypotheses, counterevidence, and "
    "professional review questions. Licensed counsel determines legal "
    "significance; qualified clinicians determine clinical significance."
)


def attach_global_scope(payload: dict) -> dict:
    """Attach scope once at result root — never duplicate under each lead."""
    out = dict(payload)
    out["global_scope_statement"] = GLOBAL_SCOPE_STATEMENT
    return out
