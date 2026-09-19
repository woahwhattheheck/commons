"""The findings store: the only thing a leadership statement is allowed to cite.

A finding here is not a sentence. It is a record with an identifier, an observed
fact, the evidence items behind it, the basis and confidence that evidence supports,
and an explicit SCOPE -- how many units it was established across, out of how many
were in scope. Scope is what makes "across the institution" checkable instead of
rhetorical.
"""

import json
from dataclasses import dataclass, field

from evidence import (
    BASIS,
    CONFIDENCE,
    EvidenceError,
    max_assertable_strength,
)

SEVERITY = ("INFORMATIONAL", "MINOR", "SIGNIFICANT", "CRITICAL")


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    kind: str          # e.g. "document", "interview", "observation", "artifact"
    locator: str       # where a reviewer goes to see it for themselves
    collected_on: str  # ISO date


@dataclass(frozen=True)
class Finding:
    finding_id: str
    area: str
    title: str
    observed: str                 # the fact, stated plainly, with no adjectives
    basis: str
    confidence: str               # may be "UNKNOWN"
    corroborating_sources: int
    severity: str
    units_established: object     # int, or "UNKNOWN"
    units_in_scope: object        # int, or "UNKNOWN"
    evidence: tuple = ()
    unresolved: tuple = ()

    @property
    def evidence_count(self):
        return len(self.evidence)

    @property
    def max_strength(self):
        return max_assertable_strength(self.basis, self.confidence,
                                       self.corroborating_sources,
                                       self.evidence_count)

    @property
    def scope_is_universal(self):
        """True only when the finding was established across EVERY unit in scope.

        UNKNOWN on either side returns False: an uncounted scope is not a universal
        scope, and treating it as one is exactly how 'across the institution' gets
        into a summary it has no right to be in.
        """
        if not isinstance(self.units_established, int):
            return False
        if not isinstance(self.units_in_scope, int) or self.units_in_scope <= 0:
            return False
        return self.units_established >= self.units_in_scope

    @property
    def scope_label(self):
        established = (self.units_established
                       if isinstance(self.units_established, int) else "UNKNOWN")
        in_scope = (self.units_in_scope
                    if isinstance(self.units_in_scope, int) else "UNKNOWN")
        return f"{established} of {in_scope} units"


class FindingsStore:

    def __init__(self, findings, source_label="(unlabelled)"):
        self._by_id = {}
        for finding in findings:
            if finding.finding_id in self._by_id:
                raise EvidenceError(f"duplicate finding_id {finding.finding_id!r}")
            self._by_id[finding.finding_id] = finding
        self.source_label = source_label

    def __len__(self):
        return len(self._by_id)

    def __contains__(self, finding_id):
        return finding_id in self._by_id

    def get(self, finding_id):
        return self._by_id.get(finding_id)

    def all(self):
        return [self._by_id[key] for key in sorted(self._by_id)]

    def ids(self):
        return sorted(self._by_id)


def _require(record, key, context):
    if key not in record:
        raise EvidenceError(f"{context}: missing required field {key!r}. A missing "
                            f"field is not a default; record it explicitly, using "
                            f"\"UNKNOWN\" where the value is not established.")
    return record[key]


def finding_from_dict(record):
    context = f"finding {record.get('finding_id', '(no id)')!r}"
    basis = _require(record, "basis", context)
    confidence = _require(record, "confidence", context)
    if basis not in BASIS:
        raise EvidenceError(f"{context}: basis {basis!r} not in {sorted(BASIS)}")
    if confidence not in CONFIDENCE:
        raise EvidenceError(f"{context}: confidence {confidence!r} not in "
                            f"{sorted(CONFIDENCE)}")
    severity = _require(record, "severity", context)
    if severity not in SEVERITY:
        raise EvidenceError(f"{context}: severity {severity!r} not in {list(SEVERITY)}")

    evidence = tuple(
        EvidenceItem(evidence_id=item["evidence_id"], kind=item["kind"],
                     locator=item["locator"], collected_on=item["collected_on"])
        for item in record.get("evidence", []))

    def scope_value(key):
        value = _require(record, key, context)
        if value == "UNKNOWN":
            return "UNKNOWN"
        if not isinstance(value, int) or value < 0:
            raise EvidenceError(f"{context}: {key} must be a non-negative integer or "
                                f'the string "UNKNOWN", got {value!r}')
        return value

    return Finding(
        finding_id=_require(record, "finding_id", context),
        area=_require(record, "area", context),
        title=_require(record, "title", context),
        observed=_require(record, "observed", context),
        basis=basis,
        confidence=confidence,
        corroborating_sources=_require(record, "corroborating_sources", context),
        severity=severity,
        units_established=scope_value("units_established"),
        units_in_scope=scope_value("units_in_scope"),
        evidence=evidence,
        unresolved=tuple(record.get("unresolved", [])),
    )


def load_findings(path):
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    findings, rejected = [], []
    for record in payload["findings"]:
        try:
            findings.append(finding_from_dict(record))
        except (EvidenceError, KeyError, TypeError) as exc:
            # Observable handling: a malformed finding is named and excluded. It is
            # NOT repaired with defaults, because a repaired finding would then be
            # citable by a leadership statement.
            rejected.append({"raw_id": record.get("finding_id", "(no id)"),
                             "error": str(exc)})
    return (FindingsStore(findings, payload.get("_source_label", "(unlabelled)")),
            rejected, payload)
