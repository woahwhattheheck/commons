"""Eight-stage review engine with quarantine and weak-lead retention."""

from __future__ import annotations

from dataclasses import dataclass, field

from charttrace.review.dispositions import Disposition, require_concrete_reason
from charttrace.review.entailment import clause_entailed, resolve_citation
from charttrace.review.gates import hard_failure_codes, privacy_or_format_hold
from charttrace.review.models import LeadCandidate, SourceUniverse


REVIEW_STAGES = (
    "source-preflight",
    "high-recall-intake",
    "synthesis-preserve-dissent",
    "citation-entailment",
    "clinical-coherence",
    "adversarial-break",
    "privacy-format-lint",
    "named-human-release-gate",
)


@dataclass(frozen=True, slots=True)
class ReviewFinding:
    lead_id: str
    disposition: Disposition
    reason: str
    stage: str
    quarantine: bool
    codes: tuple[str, ...] = ()


@dataclass
class ReviewReport:
    case_id: str
    findings: list[ReviewFinding] = field(default_factory=list)
    stages_run: tuple[str, ...] = REVIEW_STAGES
    counsel_approved: bool = False
    production_crypto: bool = False

    def of(self, lead_id: str) -> ReviewFinding:
        for finding in self.findings:
            if finding.lead_id == lead_id:
                return finding
        raise KeyError(lead_id)

    def retained_weak(self) -> tuple[str, ...]:
        return tuple(
            finding.lead_id
            for finding in self.findings
            if finding.disposition is Disposition.WEAK_APPENDIX
        )

    def quarantined(self) -> tuple[str, ...]:
        return tuple(finding.lead_id for finding in self.findings if finding.quarantine)


class ReviewEngine:
    """Review does not run peers and does not call a model."""

    def review(
        self,
        case_id: str,
        leads: tuple[LeadCandidate, ...],
        universe: SourceUniverse,
        requested_rejections: dict[str, str] | None = None,
    ) -> ReviewReport:
        requested_rejections = requested_rejections or {}
        report = ReviewReport(case_id=case_id)
        seen: dict[str, str] = {}
        for lead in leads:
            if lead.duplicate_of:
                report.findings.append(
                    ReviewFinding(
                        lead.lead_id,
                        Disposition.MERGE_DUPLICATE,
                        require_concrete_reason(f"duplicate of {lead.duplicate_of}"),
                        "synthesis-preserve-dissent",
                        False,
                    )
                )
                continue
            if lead.lead_id in seen:
                report.findings.append(
                    ReviewFinding(
                        lead.lead_id,
                        Disposition.MERGE_DUPLICATE,
                        require_concrete_reason("duplicate lead_id in this packet"),
                        "synthesis-preserve-dissent",
                        False,
                    )
                )
                continue
            seen[lead.lead_id] = lead.title
            report.findings.append(self._review_one(lead, universe, requested_rejections))
        return report

    def _review_one(
        self,
        lead: LeadCandidate,
        universe: SourceUniverse,
        requested_rejections: dict[str, str],
    ) -> ReviewFinding:
        if lead.lead_id in requested_rejections:
            require_concrete_reason(requested_rejections[lead.lead_id])

        codes = list(hard_failure_codes(lead))
        stage = "source-preflight"
        for clause in lead.clauses:
            for citation in clause.citations:
                problem = resolve_citation(citation, universe)
                if problem == "hash-mismatch":
                    codes.append("hash-mismatch")
                    stage = "source-preflight"
                elif problem in {"unknown-document", "page-out-of-range", "excerpt-mismatch"}:
                    codes.append("wrong-patient-or-page")
                    stage = "source-preflight"
            if clause.citations and not clause_entailed(clause, universe):
                codes.append("citation-does-not-entail")
                stage = "citation-entailment"

        lint = privacy_or_format_hold(lead.title)
        if lint:
            codes.append(lint)
            stage = "privacy-format-lint"

        if lead.impossible_chronology or lead.unit_or_laterality_error:
            stage = "clinical-coherence"
        if lead.followed_source_instruction:
            stage = "adversarial-break"

        unique_codes = tuple(dict.fromkeys(codes))
        if unique_codes:
            disposition = (
                Disposition.HOLD
                if "hash-mismatch" in unique_codes or "authority-date-or-jurisdiction" in unique_codes
                else Disposition.REJECT_UNSUPPORTED
            )
            if "broken-format" in unique_codes:
                disposition = Disposition.REPAIR
            return ReviewFinding(
                lead.lead_id,
                disposition,
                require_concrete_reason("; ".join(unique_codes)),
                stage,
                quarantine=disposition is Disposition.REJECT_UNSUPPORTED,
                codes=unique_codes,
            )

        if lead.weak_grounded or lead.band == "weak":
            if not lead.clauses:
                return ReviewFinding(
                    lead.lead_id,
                    Disposition.REJECT_UNSUPPORTED,
                    require_concrete_reason("weak lead lacks any cited clause"),
                    "citation-entailment",
                    True,
                    ("citation-does-not-entail",),
                )
            return ReviewFinding(
                lead.lead_id,
                Disposition.WEAK_APPENDIX,
                require_concrete_reason("grounded weak lead retained as appendix candidate"),
                "high-recall-intake",
                False,
            )

        if lead.band == "subtle":
            return ReviewFinding(
                lead.lead_id,
                Disposition.DOWNGRADE,
                require_concrete_reason("subtle lead kept with visible counterevidence or alternatives"),
                "clinical-coherence",
                False,
            )

        if not lead.counterevidence and not lead.alternatives:
            return ReviewFinding(
                lead.lead_id,
                Disposition.REPAIR,
                require_concrete_reason("primary lead missing counterevidence and alternatives"),
                "adversarial-break",
                False,
                ("missing-counterevidence",),
            )
        return ReviewFinding(
            lead.lead_id,
            Disposition.PASS,
            require_concrete_reason("citations entail clauses; hard failures absent"),
            "named-human-release-gate",
            False,
        )
