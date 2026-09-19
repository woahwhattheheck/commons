"""Vocabularies, diagnostic reason codes and cell-state rules for the UIOWA-092 rehearsal.

Why this module is separate from the pipeline: a second operator reviewing the rehearsal
needs to read the RULES without reading the plumbing. Everything that decides what a cell
says lives here; rehearse_intake.py only moves data through it.

Python 3 standard library only. No network. No clock: every date used by a rule is read
from the collection's declared `as_of`, so two operators get identical output.
"""

SYNTHETIC_BANNER = (
    "SYNTHETIC REHEARSAL OUTPUT - every organization, document, number and quotation "
    "below is fictional, authored for the UIOWA-092 integration rehearsal. Nothing here "
    "is a University of Iowa record, measurement, or finding."
)

# The three fictional groups and the RFQ's four assessment areas -> the twelve cells.
GROUPS = ("ESS", "RIS", "IAM")
AREAS = ("SD", "SEC", "DEP", "AI")
AREA_LABELS = {
    "SD": "Software development",
    "SEC": "Security",
    "DEP": "Deployment and operations",
    "AI": "AI readiness",
}
GROUP_LABELS = {
    "ESS": "ESS (fictional enterprise student systems group)",
    "RIS": "RIS (fictional research information systems group)",
    "IAM": "IAM (fictional identity and access management group)",
}

SOURCE_TYPES = (
    "configuration_export", "change_record", "system_log", "system_export",
    "scan_report", "policy", "document",
)
DIRECTIONS = ("STRENGTH", "GAP", "NEUTRAL")
ESTABLISHES = ("practice_claim", "availability_only")

# Cell states. These are CATEGORIES, deliberately not a scale and never averaged:
# there is no maturity number anywhere in this package, and UNKNOWN is a distinct
# outcome that must never collapse into a gap, a zero, or a pass.
CELL_STATES = (
    "DEMONSTRATED_STRENGTH",  # direct artifact evidence, corroborated across source types
    "OBSERVED_GAP",           # direct artifact evidence of a shortfall
    "MIXED",                  # direct evidence of both a strength and a gap in one cell
    "CONFLICT",               # sources disagree about the same claim; disagreement retained
    "PARTIAL",                # something is evidenced, but not enough to demonstrate practice
    "UNKNOWN",                # insufficient evidence. NOT a gap and NOT a pass.
)

REJECT, DEGRADE, NOTE = "REJECT", "DEGRADE", "NOTE"

# Every way this rehearsal can be handed a bad input, and what observably happens.
# REJECT  = record excluded from the matrix, retained in diagnostics with its locator.
# DEGRADE = record retained, but its evidentiary capability is reduced (and that
#           reduction is what later stops a cell from claiming more than it can).
# NOTE    = nothing is wrong; the operator is told something that affects reading.
REASON_CODES = {
    "SRC_MISSING":            (DEGRADE, "Declared source file is not present at its path."),
    "SRC_UNREADABLE":         (DEGRADE, "Declared source file exists but could not be read."),
    "SRC_DIGEST_MISMATCH":    (DEGRADE, "File bytes do not match the digest declared in the register."),
    "SRC_PATH_ESCAPE":        (REJECT,  "Source path resolves outside the collection root."),
    "SRC_DUPLICATE_ID":       (REJECT,  "source_id appears more than once in the register."),
    "SRC_MISSING_FIELD":      (REJECT,  "Source entry is missing a required field."),
    "SRC_UNKNOWN_GROUP":      (REJECT,  "Source declares a group outside the three in scope."),
    "SRC_UNKNOWN_TYPE":       (DEGRADE, "Source declares a source_type outside the vocabulary."),
    "OBS_MISSING_FIELD":      (REJECT,  "Observation is missing a required field."),
    "OBS_DUPLICATE_ID":       (REJECT,  "observation_id appears more than once."),
    "OBS_UNKNOWN_GROUP":      (REJECT,  "Observation declares a group outside the three in scope."),
    "OBS_UNKNOWN_AREA":       (REJECT,  "Observation declares an area outside the four in scope."),
    "OBS_UNKNOWN_DIRECTION":  (REJECT,  "Observation declares a direction outside the vocabulary."),
    "OBS_DANGLING_SOURCE":    (DEGRADE, "Observation cites a source_id absent from the register."),
    "OBS_UNRESOLVED_SOURCE":  (DEGRADE, "Observation cites a source that did not resolve to readable bytes."),
    "OBS_ARITHMETIC_INCONSISTENT": (DEGRADE, "Count assertion is not internally consistent."),
    "INT_MISSING_FIELD":      (REJECT,  "Interview excerpt is missing a required field."),
    "INT_DUPLICATE_ID":       (REJECT,  "interview_id appears more than once."),
    "INT_DANGLING_OBSERVATION": (DEGRADE, "Excerpt is attached to an observation_id that does not exist."),
    "INT_NO_CLAIM":           (NOTE,    "Excerpt establishes availability only and contributes no support."),
    "INT_UNKNOWN_ESTABLISHES": (DEGRADE, "Excerpt declares an 'establishes' value outside the vocabulary."),
    "COLLECTION_UNAVAILABLE": (NOTE,    "An external collection was requested but no manifest was found."),
    "COLLECTION_UNREADABLE":  (DEGRADE, "External collection manifest was found but could not be parsed."),
    "COLLECTION_SHAPE_UNRECOGNIZED": (DEGRADE, "External collection manifest parsed but carries none of the keys this adapter reads."),
    "MANIFEST_UNPARSEABLE":   (REJECT,  "An input manifest is not valid JSON."),
}

REQUIRED_SOURCE_FIELDS = ("source_id", "group", "source_type", "path", "version")
REQUIRED_OBS_FIELDS = ("observation_id", "group", "area", "direction", "claim", "scope_limit")
REQUIRED_INT_FIELDS = ("interview_id", "supports_observation", "establishes", "excerpt")


def severity_of(code):
    return REASON_CODES[code][0]


def check_count_assertion(assertion):
    """Return a list of human-readable inconsistencies in a declared count assertion.

    This is how 'internal facts are consistent' becomes executable instead of asserted:
    a fixture that claims 'three of two releases' or parts that do not sum to the whole
    is caught here and degrades the observation, rather than quietly reaching the matrix.
    """
    problems = []
    if not isinstance(assertion, dict):
        return ["count_assertion is not an object"]
    num = assertion.get("numerator")
    den = assertion.get("denominator")
    whole = assertion.get("whole")
    parts = assertion.get("parts")
    for name, val in (("numerator", num), ("denominator", den), ("whole", whole)):
        if val is not None and (not isinstance(val, int) or isinstance(val, bool) or val < 0):
            problems.append(f"{name} is not a non-negative integer: {val!r}")
    if isinstance(num, int) and isinstance(den, int) and not isinstance(num, bool) and num > den:
        problems.append(f"numerator {num} exceeds denominator {den}")
    if isinstance(den, int) and isinstance(whole, int) and not isinstance(den, bool) and den > whole:
        problems.append(f"denominator {den} exceeds whole {whole}")
    if parts is not None:
        if not isinstance(parts, list) or not all(
            isinstance(p, int) and not isinstance(p, bool) and p >= 0 for p in parts
        ):
            problems.append(f"parts is not a list of non-negative integers: {parts!r}")
        elif isinstance(whole, int) and sum(parts) != whole:
            problems.append(f"parts sum to {sum(parts)} but whole is {whole}")
    return problems


def derive_cell_state(cell_observations):
    """Decide one (group, area) cell from its observations. Returns (state, basis).

    Rules are evaluated in order and the first match wins. The basis string is exported
    with the cell so a reader can see WHY, not just what. No rule produces a score, and
    no rule lets an absence of evidence become an assertion about practice.
    """
    if not cell_observations:
        return "UNKNOWN", "No evidence was supplied for this cell."

    direct = [o for o in cell_observations if o["support"]["directness"] == "DIRECT"]
    indirect = [o for o in cell_observations if o["support"]["directness"] == "INDIRECT"]
    unevidenced = [o for o in cell_observations if o["support"]["directness"] == "NONE"]

    # Rule 2: observations exist, but nothing behind them resolved. An evidence request
    # that went unanswered is still an unanswered question, not a finding.
    if not direct and not indirect:
        ids = ", ".join(o["observation_id"] for o in unevidenced)
        return "UNKNOWN", (
            "Evidence was identified but none of it resolved to readable material "
            f"({ids}). Nothing is established about this area in either direction."
        )

    # Rule 3: an explicit conflict group with observations pointing different ways.
    groups_seen = {}
    for o in cell_observations:
        cg = o.get("conflict_group")
        if cg:
            groups_seen.setdefault(cg, set()).add(o["direction"])
    for cg, dirs in sorted(groups_seen.items()):
        if len({d for d in dirs if d in ("STRENGTH", "GAP")}) > 1:
            return "CONFLICT", (
                f"Sources disagree about the same claim (conflict group {cg}). "
                "The disagreement is retained rather than resolved by the tool."
            )

    directions = {o["direction"] for o in direct}

    # Rule 4: direct evidence of both a strength and a shortfall in the same cell.
    if "STRENGTH" in directions and "GAP" in directions:
        return "MIXED", (
            "Direct evidence supports both a strength and a shortfall in this area; "
            "both are reported rather than netted against each other."
        )

    # Rule 5: only statements, no artifacts. Stated is not demonstrated.
    if not direct:
        ids = ", ".join(o["observation_id"] for o in indirect)
        return "PARTIAL", (
            f"Support is interview statement only ({ids}). The practice is stated, "
            "not demonstrated; no artifact was produced."
        )

    # Rule 6: a strength is only 'demonstrated' when more than one kind of source agrees.
    if directions == {"STRENGTH"}:
        corroborated = [o for o in direct if o["support"]["corroboration"] == "MULTI_TYPE"]
        if corroborated:
            return "DEMONSTRATED_STRENGTH", (
                "Direct artifact evidence, corroborated across more than one source type "
                f"({', '.join(o['observation_id'] for o in corroborated)})."
            )
        # Several single-source observations of different types still corroborate.
        types = set()
        for o in direct:
            types.update(o["support"]["source_types"])
        if len(types) >= 2:
            return "DEMONSTRATED_STRENGTH", (
                "Direct artifact evidence from independent observations across source "
                f"types {', '.join(sorted(types))}."
            )
        return "PARTIAL", (
            "Direct artifact evidence from a single source type only; a strength is not "
            "called demonstrated on one kind of record."
        )

    # Rule 7: direct evidence of a shortfall.
    if "GAP" in directions:
        return "OBSERVED_GAP", (
            "Direct artifact evidence of a shortfall against a stated expectation "
            f"({', '.join(o['observation_id'] for o in direct if o['direction'] == 'GAP')})."
        )

    # Rule 8: direct evidence that establishes context but no practice claim either way.
    return "PARTIAL", (
        "Direct evidence establishes context or intent but does not demonstrate a "
        "practice in operation."
    )
