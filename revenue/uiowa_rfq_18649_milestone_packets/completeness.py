"""The automated completeness report.

"Complete" here means one narrow thing: the packet can be handed to a reviewer
as a draft without containing an unverifiable citation or an unmade decision.
It explicitly does NOT mean the milestone is approved, billable, or accepted --
this tool has no authority over any of those and says so in every output.

Severity is two-valued on purpose. ERROR means the packet is not ready to go out
and names exactly what to fix. WARN means a real condition a human must read
(an overdue dependency, an undated open item) that is not itself a defect in the
packet. Nothing is silently dropped into a third "probably fine" bucket.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import schedule
from schema import UNKNOWN, AcceptanceRecord, Money

ERROR = "ERROR"
WARN = "WARN"
INFO = "INFO"

REQUIRED_CONTRACT_TOTAL = Money(2_400_000)   # $24,000.00, in cents


@dataclass
class Finding:
    code: str
    severity: str
    message: str
    milestone_id: Any = UNKNOWN
    item_id: Any = UNKNOWN

    def to_json(self) -> dict:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "milestone_id": None if self.milestone_id is UNKNOWN else self.milestone_id,
            "item_id": None if self.item_id is UNKNOWN else self.item_id,
        }


@dataclass
class MilestoneResult:
    milestone_id: str
    name: str
    kind: str
    amount_display: str
    submission_state: str
    acceptance_state: str
    billing_state: str
    findings: list = field(default_factory=list)

    @property
    def errors(self) -> list:
        return [f for f in self.findings if f.severity == ERROR]

    @property
    def warnings(self) -> list:
        return [f for f in self.findings if f.severity == WARN]

    @property
    def status(self) -> str:
        # Deliberately not "COMPLETE" or "APPROVED": the strongest thing this
        # tool is entitled to say is that the draft is ready to be sent.
        return "READY_TO_SUBMIT_AS_DRAFT" if not self.errors else "NOT_READY"


@dataclass
class Report:
    engagement_id: str
    as_of: str
    milestone_results: list = field(default_factory=list)
    engagement_findings: list = field(default_factory=list)

    @property
    def all_findings(self) -> list:
        out = list(self.engagement_findings)
        for mr in self.milestone_results:
            out.extend(mr.findings)
        return out

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.all_findings if f.severity == ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.all_findings if f.severity == WARN)

    @property
    def passed(self) -> bool:
        return self.error_count == 0

    def to_json(self) -> dict:
        return {
            "engagement_id": self.engagement_id,
            "as_of": self.as_of,
            "passed": self.passed,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "milestones": [
                {
                    "milestone_id": mr.milestone_id,
                    "name": mr.name,
                    "kind": mr.kind,
                    "amount": mr.amount_display,
                    "submission_state": mr.submission_state,
                    "acceptance_state": mr.acceptance_state,
                    "billing_state": mr.billing_state,
                    "status": mr.status,
                    "findings": [f.to_json() for f in mr.findings],
                }
                for mr in self.milestone_results
            ],
            "engagement_findings": [f.to_json() for f in self.engagement_findings],
        }


def check(engagement, resolutions: dict, as_of: str) -> Report:
    rpt = Report(engagement_id=engagement.engagement_id, as_of=as_of)
    _check_amounts(engagement, rpt)
    _check_milestone_kinds(engagement, rpt)
    for ms in engagement.milestones:
        rpt.milestone_results.append(_check_milestone(ms, resolutions, as_of))
    return rpt


def _check_amounts(engagement, rpt: Report) -> None:
    """Integer-cent arithmetic. Two separate facts, checked separately."""
    total = engagement.milestone_total()
    if total.cents != engagement.contract_total.cents:
        rpt.engagement_findings.append(
            Finding(
                "E_AMOUNTS_DO_NOT_SUM", ERROR,
                f"milestone amounts total {total.dollars()} but the contract total "
                f"is {engagement.contract_total.dollars()} "
                f"({total.cents} vs {engagement.contract_total.cents} cents)",
            )
        )
    if engagement.contract_total.cents != REQUIRED_CONTRACT_TOTAL.cents:
        rpt.engagement_findings.append(
            Finding(
                "E_CONTRACT_TOTAL_MISMATCH", ERROR,
                f"contract total is {engagement.contract_total.dollars()}; the "
                f"proposed subcontract total is "
                f"{REQUIRED_CONTRACT_TOTAL.dollars()}",
            )
        )
    if total.cents == REQUIRED_CONTRACT_TOTAL.cents:
        rpt.engagement_findings.append(
            Finding(
                "I_AMOUNTS_CONFIRMED", INFO,
                f"milestone amounts sum to {total.dollars()} exactly "
                f"({total.cents} cents), checked in integer cents",
            )
        )


def _check_milestone_kinds(engagement, rpt: Report) -> None:
    """Draft delivery and final acceptance must be distinct milestones.

    The failure this prevents is a packet set where "draft" and "final" are the
    same artifact wearing two labels -- which makes an acceptance record for the
    final look like it also covers the draft review.
    """
    kinds = [m.kind for m in engagement.milestones]
    for required in ("KICKOFF", "DRAFT_DELIVERY", "FINAL_ACCEPTANCE"):
        if kinds.count(required) == 0:
            rpt.engagement_findings.append(
                Finding("E_MISSING_MILESTONE_KIND", ERROR,
                        f"no milestone of kind {required}")
            )
        elif kinds.count(required) > 1:
            rpt.engagement_findings.append(
                Finding("E_DUPLICATE_MILESTONE_KIND", ERROR,
                        f"{kinds.count(required)} milestones claim kind {required}; "
                        "draft delivery and final acceptance must be distinct")
            )


def _check_milestone(ms, resolutions: dict, as_of: str) -> MilestoneResult:
    mr = MilestoneResult(
        milestone_id=ms.milestone_id,
        name=ms.name,
        kind=ms.kind,
        amount_display=ms.amount.dollars(),
        submission_state=ms.submission_state,
        acceptance_state=ms.acceptance_state,
        billing_state=ms.billing_state,
    )
    f = mr.findings
    defined_criteria = {c.criterion_id for c in ms.criteria}
    item_ids = {i.item_id for i in ms.index_items}

    if not ms.index_items:
        f.append(Finding("E_EMPTY_INDEX", ERROR,
                         "milestone has no delivered-file index rows",
                         ms.milestone_id))

    for item in ms.index_items:
        res = resolutions.get(item.item_id)

        # "every cited artifact opens"
        if res is None:
            f.append(Finding("E_UNRESOLVED_ARTIFACT", ERROR,
                             "cited artifact was never resolved",
                             ms.milestone_id, item.item_id))
        elif not res.opens:
            f.append(Finding("E_ARTIFACT_DOES_NOT_OPEN", ERROR,
                             f"{item.path}: {res.state} - {res.detail}",
                             ms.milestone_id, item.item_id))
        elif not res.version_identifiable:
            # It opened, so we have a digest; what is missing is the label that
            # ties the digest to a delivered version.
            f.append(Finding("E_VERSION_NOT_IDENTIFIABLE", ERROR,
                             f"{item.path}: opened (sha256 {res.sha256[:12]}...) but "
                             "declared_version is UNKNOWN, so the delivered version "
                             "cannot be named",
                             ms.milestone_id, item.item_id))

        # custody + disposition: the four fields every inventoried item carries
        for fieldname, code in (
            ("source", "E_MISSING_SOURCE"),
            ("custodian", "E_MISSING_CUSTODIAN"),
            ("storage_location", "E_MISSING_STORAGE_LOCATION"),
        ):
            if getattr(item, fieldname) is UNKNOWN:
                f.append(Finding(code, ERROR,
                                 f"{item.item_id}: {fieldname} is UNKNOWN",
                                 ms.milestone_id, item.item_id))
        if item.disposition is UNKNOWN:
            # The briefed rule: an item without a disposition decision fails the
            # check. It is NOT given a default -- an unmade decision is reported
            # as unmade so somebody makes it.
            f.append(Finding("E_MISSING_DISPOSITION", ERROR,
                             f"{item.item_id}: no disposition decision recorded. "
                             "The item is not assigned a default; a person must "
                             "decide retain / return / destroy / client-system.",
                             ms.milestone_id, item.item_id))

        for cid in item.criteria_ids:
            if cid not in defined_criteria:
                f.append(Finding("E_DANGLING_CRITERION_REF", ERROR,
                                 f"{item.item_id} cites criterion {cid}, which this "
                                 "milestone does not define",
                                 ms.milestone_id, item.item_id))

    for crit in ms.criteria:
        if not crit.evidence_item_ids:
            f.append(Finding("W_CRITERION_WITHOUT_EVIDENCE", WARN,
                             f"{crit.criterion_id} cites no index item; presence of "
                             "evidence for it is UNKNOWN",
                             ms.milestone_id))
        for eid in crit.evidence_item_ids:
            if eid not in item_ids:
                f.append(Finding("E_CRITERION_CITES_MISSING_ITEM", ERROR,
                                 f"{crit.criterion_id} cites index item {eid}, which "
                                 "is not in this milestone's index",
                                 ms.milestone_id))

    for dep in ms.dependencies:
        status = schedule.classify_due(dep.needed_by, as_of, closed=dep.state == "CLOSED")
        if status.state == schedule.OVERDUE:
            f.append(Finding("W_DEPENDENCY_OVERDUE", WARN,
                             f"{dep.dependency_id}: {dep.description} - {status.note} "
                             f"(needed by {dep.needed_by}, as of {as_of})",
                             ms.milestone_id))
        elif status.state == schedule.DUE_UNKNOWN:
            f.append(Finding("W_DEPENDENCY_UNDATED", WARN,
                             f"{dep.dependency_id}: {dep.description} - open with no "
                             "agreed date; it cannot be called on time or late",
                             ms.milestone_id))

    # Acceptance is reported, never inferred.
    if isinstance(ms.acceptance, AcceptanceRecord):
        f.append(Finding("I_ACCEPTANCE_ON_RECORD", INFO,
                         f"acceptance recorded {ms.acceptance.recorded_on} by "
                         f"{ms.acceptance.recorded_by} (ref {ms.acceptance.reference})",
                         ms.milestone_id))
    elif ms.submission_state == "DELIVERED":
        f.append(Finding("I_ACCEPTANCE_PENDING", INFO,
                         "delivered; no acceptance record supplied, so acceptance "
                         "is PENDING. Delivery is not acceptance.",
                         ms.milestone_id))
    return mr
