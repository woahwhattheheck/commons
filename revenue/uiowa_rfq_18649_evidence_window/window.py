"""Does a claim's stated time window agree with the dates of its evidence?

The failure: a finding says "over the last 90 days, 3 of 14 deployments were
rolled back", and the records cited all fall inside a single week in the middle
of that period. The count is right, the citation resolves, the arithmetic is
sound, and the sentence still describes ninety days of behaviour on the strength
of seven. Nothing else in a report-checking kit looks at this, because every
other check is about identity or magnitude rather than about *when*.

Related but different work: normalising timestamps to a common instant, and
tracking whether a source document changed between versions. This does neither.
It takes dates that are already normalised and asks whether they cover the
period the claim is about.

Determinism: the assessment date is declared in the input as `as_of`. The system
clock is never consulted, so a run today and a run next month over the same input
produce identical output.
"""
from __future__ import annotations

import dataclasses
import datetime
import json
from typing import Any

ERROR = "error"
WARN = "warning"
INFO = "info"

# A claim in the present tense ("services are monitored") rests on evidence
# being current. This is the default horizon past which it no longer is.
DEFAULT_FRESHNESS_DAYS = 180

# Below this share of the stated window covered by evidence dates, the claim is
# describing a period it did not observe.
DEFAULT_MIN_COVERAGE = 0.60

TENSES = ("PRESENT", "PAST")


class WindowError(ValueError):
    """Input that cannot be checked at all, as distinct from input that fails."""


@dataclasses.dataclass
class Finding:
    code: str
    severity: str
    claim_id: str
    message: str
    restatement: str = ""
    detail: dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    def sort_key(self):
        return ({ERROR: 0, WARN: 1, INFO: 2}.get(self.severity, 9),
                self.claim_id, self.code)


@dataclasses.dataclass
class Evidence:
    id: str
    date: datetime.date | None     # None means UNDATED, never "assume in window"
    label: str = ""


@dataclasses.dataclass
class Claim:
    id: str
    text: str
    tense: str
    window_start: datetime.date | None
    window_end: datetime.date | None
    evidence_ids: list[str]


def _date(value: Any, where: str) -> datetime.date | None:
    if value is None:
        return None
    try:
        return datetime.date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise WindowError(f"{where}: {value!r} is not an ISO date ({exc})")


def load(path: str) -> tuple[datetime.date, dict[str, Evidence], list[Claim], dict]:
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    if not raw.get("synthetic"):
        raise WindowError("the input must be explicitly marked synthetic:true")

    as_of = _date(raw.get("as_of"), "as_of")
    if as_of is None:
        raise WindowError(
            "as_of is required: staleness is judged against a declared assessment "
            "date, never against the clock, so that runs are reproducible")

    evidence: dict[str, Evidence] = {}
    for item in raw.get("evidence", []):
        eid = item["id"]
        if eid in evidence:
            raise WindowError(f"duplicate evidence id {eid!r}")
        evidence[eid] = Evidence(id=eid, date=_date(item.get("date"), f"evidence {eid}"),
                                 label=item.get("label", ""))

    claims: list[Claim] = []
    for item in raw.get("claims", []):
        cid = item["id"]
        tense = item.get("tense", "PAST")
        if tense not in TENSES:
            raise WindowError(f"claim {cid!r} has unknown tense {tense!r}")
        claims.append(Claim(
            id=cid, text=item["text"], tense=tense,
            window_start=_date(item.get("window_start"), f"claim {cid} window_start"),
            window_end=_date(item.get("window_end"), f"claim {cid} window_end"),
            evidence_ids=list(item.get("evidence_ids", []))))

    settings = {
        "freshness_days": int(raw.get("freshness_days", DEFAULT_FRESHNESS_DAYS)),
        "min_coverage": float(raw.get("min_coverage", DEFAULT_MIN_COVERAGE)),
    }
    return as_of, evidence, sorted(claims, key=lambda c: c.id), settings


def check(as_of: datetime.date, evidence: dict[str, Evidence],
          claims: list[Claim], settings: dict) -> list[Finding]:
    out: list[Finding] = []
    freshness = settings["freshness_days"]
    min_coverage = settings["min_coverage"]

    for claim in claims:
        dated: list[datetime.date] = []
        undated: list[str] = []
        missing: list[str] = []

        for eid in claim.evidence_ids:
            record = evidence.get(eid)
            if record is None:
                missing.append(eid)
                continue
            if record.date is None:
                undated.append(eid)
            else:
                dated.append(record.date)

        for eid in sorted(missing):
            out.append(Finding(
                "EVIDENCE_NOT_FOUND", ERROR, claim.id,
                f"{eid} is cited by this claim but is not in the evidence set"))

        if undated:
            out.append(Finding(
                "UNDATED_EVIDENCE", ERROR, claim.id,
                f"{', '.join(sorted(undated))} carries no date, so it cannot be "
                "placed inside or outside this claim's window; it is not assumed "
                "to be in window",
                restatement="record the date, or drop the time bound from the claim",
                detail={"undated": sorted(undated)}))

        if not claim.evidence_ids:
            out.append(Finding(
                "NO_EVIDENCE_CITED", ERROR, claim.id,
                "a time-bounded claim with no evidence cited at all"))
            continue

        # -- window sanity before anything is measured against it
        if claim.window_start and claim.window_end:
            if claim.window_end < claim.window_start:
                out.append(Finding(
                    "WINDOW_INVERTED", ERROR, claim.id,
                    f"the stated window ends {claim.window_end.isoformat()} before "
                    f"it starts {claim.window_start.isoformat()}"))
                continue
            if claim.window_end > as_of:
                out.append(Finding(
                    "WINDOW_ENDS_AFTER_ASOF", ERROR, claim.id,
                    f"the window runs to {claim.window_end.isoformat()}, past the "
                    f"assessment date {as_of.isoformat()}; part of it had not "
                    "happened when the evidence was collected"))

        for date in sorted(set(d for d in dated if d > as_of)):
            out.append(Finding(
                "EVIDENCE_AFTER_ASOF", ERROR, claim.id,
                f"evidence dated {date.isoformat()} is later than the assessment "
                f"date {as_of.isoformat()}",
                detail={"evidence_date": date.isoformat()}))

        # A record dated after the assessment could not have been observed, so
        # it is withdrawn from the window analysis rather than also being
        # reported as out-of-window and as a single-date support. One bad record
        # is one finding; three findings for one defect makes the count useless.
        dated = [d for d in dated if d <= as_of]
        if not dated:
            continue

        first, last = min(dated), max(dated)

        if claim.window_start and claim.window_end:
            outside = sorted(set(d for d in dated
                                 if d < claim.window_start or d > claim.window_end))
            if outside:
                out.append(Finding(
                    "EVIDENCE_OUTSIDE_WINDOW", ERROR, claim.id,
                    f"{len(outside)} cited record(s) fall outside the stated window "
                    f"{claim.window_start.isoformat()}..{claim.window_end.isoformat()}"
                    f" (earliest outside: {outside[0].isoformat()})",
                    restatement="widen the stated window to match the evidence, or "
                                "drop the out-of-window records from the claim",
                    detail={"outside": [d.isoformat() for d in outside]}))

            window_days = (claim.window_end - claim.window_start).days + 1
            covered_days = (min(last, claim.window_end)
                            - max(first, claim.window_start)).days + 1
            covered_days = max(0, covered_days)
            coverage = covered_days / window_days if window_days else 0.0

            if len(set(dated)) == 1:
                out.append(Finding(
                    "SINGLE_DATE_SUPPORTS_A_PERIOD", ERROR, claim.id,
                    f"every cited record is dated {first.isoformat()}, but the claim "
                    f"describes {window_days} days",
                    restatement=f"state what was observed on {first.isoformat()}",
                    detail={"window_days": window_days}))
            elif coverage < min_coverage:
                out.append(Finding(
                    "WINDOW_NOT_COVERED", ERROR, claim.id,
                    f"the claim describes {window_days} days but its evidence spans "
                    f"{covered_days} ({coverage:.0%} of the window), "
                    f"{first.isoformat()}..{last.isoformat()}",
                    restatement=(f"state the period actually observed: "
                                 f"{first.isoformat()} to {last.isoformat()}"),
                    detail={"window_days": window_days, "covered_days": covered_days,
                            "coverage": round(coverage, 3)}))
        elif claim.window_start or claim.window_end:
            out.append(Finding(
                "PARTIAL_WINDOW", ERROR, claim.id,
                "only one end of the window is stated, so the period being "
                "described is not defined",
                restatement="state both ends, or remove the time bound"))

        if claim.tense == "PRESENT":
            age = (as_of - last).days
            if age > freshness:
                out.append(Finding(
                    "STALE_EVIDENCE_FOR_PRESENT_TENSE", ERROR, claim.id,
                    f"this is written in the present tense but its most recent "
                    f"evidence is {age} days old at the assessment date, past the "
                    f"{freshness}-day freshness horizon",
                    restatement=(f"write it in the past tense and name the date: "
                                 f"as of {last.isoformat()}, ..."),
                    detail={"newest_evidence": last.isoformat(), "age_days": age}))

    return sorted(out, key=lambda f: f.sort_key())


def render_text(as_of: datetime.date, claims: list[Claim],
                findings: list[Finding], settings: dict) -> str:
    errors = [f for f in findings if f.severity == ERROR]
    warns = [f for f in findings if f.severity == WARN]
    lines = [
        "evidence window agreement",
        "=" * 72,
        f"assessment date (as_of) : {as_of.isoformat()}",
        f"claims checked          : {len(claims)}",
        f"freshness horizon       : {settings['freshness_days']} days",
        f"minimum window coverage : {settings['min_coverage']:.0%}",
        f"result                  : {'FAIL' if errors else 'PASS'}"
        f"  ({len(errors)} error, {len(warns)} warning)",
        "",
    ]
    for f in findings:
        lines.append(f"  [{f.severity}] {f.code}  {f.claim_id}")
        lines.append(f"      {f.message}")
        if f.restatement:
            lines.append(f"      say instead: {f.restatement}")
    if not findings:
        lines.append("  Every claim's evidence is dated, falls inside the period the")
        lines.append("  claim describes, covers enough of it, and is current enough")
        lines.append("  for the tense it is written in.")
    lines.append("")
    return "\n".join(lines)
