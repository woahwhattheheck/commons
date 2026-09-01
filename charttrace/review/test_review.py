"""Lane D review, export, and counsel tests. Synthetic only."""

from __future__ import annotations

import hashlib
import unittest

from charttrace.counsel.release import CounselAccess, named_human_release
from charttrace.export.ctpkg import build_ctpkg, verify_ctpkg
from charttrace.review.dispositions import Disposition, require_concrete_reason
from charttrace.review.engine import REVIEW_STAGES, ReviewEngine
from charttrace.review.models import (
    AuthorityRef,
    Citation,
    FactualClause,
    LeadCandidate,
    SourceDocument,
    SourceUniverse,
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


PAGE = "SYNTHETIC_ONLY doc=syn-ed-001 page=1 SYN-DX-VALVE first documented SYN-TOKEN"
PAGE_B = "SYNTHETIC_ONLY doc=syn-ed-001 page=2 callback to SYN-PT-ALPHA SYN-TOKEN"
SHA = _sha(PAGE)


def _universe() -> SourceUniverse:
    document = SourceDocument(
        "syn-ed-001",
        SHA,
        2,
        (PAGE, PAGE_B),
    )
    return SourceUniverse("syn-case-01", {"syn-ed-001": document})


def _citation(text: str, page: int = 1) -> Citation:
    page_text = PAGE if page == 1 else PAGE_B
    start = page_text.find(text)
    return Citation("syn-ed-001", page, SHA, start, start + len(text), text)


def _clause(clause_id: str, text: str, snippet: str, page: int = 1) -> FactualClause:
    return FactualClause(clause_id, text, (_citation(snippet, page),))


def _lead(**changes: object) -> LeadCandidate:
    base = dict(
        lead_id="lead-obv-01",
        title="SYN-DX-VALVE documented before first communication",
        band="obvious",
        clauses=(_clause("c1", "SYN-DX-VALVE first documented", "SYN-DX-VALVE first documented"),),
        counterevidence=("callback documented",),
        alternatives=("documentation lag",),
    )
    base.update(changes)
    return LeadCandidate(**base)  # type: ignore[arg-type]


class DispositionTests(unittest.TestCase):
    def test_vague_rejection_fails_closed(self) -> None:
        for reason in ("not actionable", "unlikely", "too aggressive", "a lawyer might dislike it"):
            with self.assertRaises(ValueError):
                require_concrete_reason(reason)

    def test_empty_reason_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            require_concrete_reason("  ")

    def test_eight_stages_and_seven_dispositions_are_locked(self) -> None:
        self.assertEqual(len(REVIEW_STAGES), 8)
        self.assertEqual(len(Disposition), 7)


class EngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = ReviewEngine()
        self.universe = _universe()

    def test_grounded_primary_passes(self) -> None:
        report = self.engine.review("syn-case-01", (_lead(),), self.universe)
        self.assertEqual(report.of("lead-obv-01").disposition, Disposition.PASS)
        self.assertFalse(report.counsel_approved)
        self.assertFalse(report.production_crypto)

    def test_weak_grounded_lead_is_retained(self) -> None:
        lead = _lead(lead_id="lead-weak-01", band="weak", weak_grounded=True)
        report = self.engine.review("syn-case-01", (lead,), self.universe)
        self.assertEqual(report.of("lead-weak-01").disposition, Disposition.WEAK_APPENDIX)
        self.assertIn("lead-weak-01", report.retained_weak())
        self.assertNotIn("lead-weak-01", report.quarantined())

    def test_unsupported_fact_is_quarantined(self) -> None:
        clause = FactualClause("c-bad", "Invented SYN-DX-NEVER event", (), invented=True)
        lead = _lead(lead_id="lead-bad", clauses=(clause,))
        report = self.engine.review("syn-case-01", (lead,), self.universe)
        self.assertEqual(report.of("lead-bad").disposition, Disposition.REJECT_UNSUPPORTED)
        self.assertIn("lead-bad", report.quarantined())

    def test_citation_mismatch_fails_entailment(self) -> None:
        bad = Citation("syn-ed-001", 1, SHA, 0, 5, "XXXXX")
        clause = FactualClause("c2", "SYN-DX-VALVE first documented", (bad,))
        lead = _lead(clauses=(clause,))
        report = self.engine.review("syn-case-01", (lead,), self.universe)
        self.assertIn(report.of("lead-obv-01").disposition, {Disposition.REJECT_UNSUPPORTED, Disposition.HOLD})
        self.assertTrue(
            {"citation-does-not-entail", "wrong-patient-or-page"} & set(report.of("lead-obv-01").codes)
        )

    def test_hash_mismatch_holds(self) -> None:
        bad = _citation("SYN-DX-VALVE first documented")
        bad = Citation(bad.document_id, bad.page, "0" * 64, bad.span_start, bad.span_end, bad.text)
        clause = FactualClause("c3", "SYN-DX-VALVE first documented", (bad,))
        report = self.engine.review("syn-case-01", (_lead(clauses=(clause,)),), self.universe)
        self.assertEqual(report.of("lead-obv-01").disposition, Disposition.HOLD)
        self.assertIn("hash-mismatch", report.of("lead-obv-01").codes)

    def test_prompt_injection_and_unbounded_absence_quarantine(self) -> None:
        lead = _lead(
            lead_id="lead-inj",
            followed_source_instruction=True,
            unbounded_absence=True,
            title="the patient was never told",
        )
        report = self.engine.review("syn-case-01", (lead,), self.universe)
        finding = report.of("lead-inj")
        self.assertEqual(finding.disposition, Disposition.REJECT_UNSUPPORTED)
        self.assertIn("source-prompt-followed", finding.codes)
        self.assertIn("unbounded-absence-claim", finding.codes)

    def test_problem_list_and_ordered_not_completed(self) -> None:
        lead = _lead(
            lead_id="lead-pl",
            problem_list_as_diagnosis=True,
            ordered_as_completed=True,
        )
        report = self.engine.review("syn-case-01", (lead,), self.universe)
        codes = set(report.of("lead-pl").codes)
        self.assertIn("problem-list-as-confirmed-diagnosis", codes)
        self.assertIn("ordered-treated-as-completed", codes)

    def test_stale_authority_holds(self) -> None:
        lead = _lead(
            authority=AuthorityRef(
                "auth-01",
                "synthetic",
                "2021-01-01",
                None,
                "2020-01-15",
                "context_only",
            )
        )
        report = self.engine.review("syn-case-01", (lead,), self.universe)
        self.assertEqual(report.of("lead-obv-01").disposition, Disposition.HOLD)
        self.assertIn("authority-date-or-jurisdiction", report.of("lead-obv-01").codes)

    def test_requested_vague_rejection_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            self.engine.review(
                "syn-case-01",
                (_lead(),),
                self.universe,
                requested_rejections={"lead-obv-01": "not actionable"},
            )

    def test_duplicate_merges(self) -> None:
        lead = _lead(lead_id="lead-dup", duplicate_of="lead-obv-01")
        report = self.engine.review("syn-case-01", (lead,), self.universe)
        self.assertEqual(report.of("lead-dup").disposition, Disposition.MERGE_DUPLICATE)


class ExportTests(unittest.TestCase):
    def test_package_is_recipient_specific_and_byte_locked(self) -> None:
        package = build_ctpkg(
            "syn-case-01",
            "syn-firm-01",
            "rel-01",
            {"leads": ["lead-obv-01"], "appendix": ["lead-weak-01"]},
        )
        self.assertEqual(package.signing_state, "UNSIGNED_SYNTHETIC")
        self.assertFalse(package.counsel_approved)
        self.assertFalse(package.production_crypto)
        verify_ctpkg(package, "syn-firm-01", package.to_bytes())
        with self.assertRaises(ValueError):
            verify_ctpkg(package, "syn-firm-other")
        mutated = package.to_bytes() + b" "
        with self.assertRaises(ValueError):
            verify_ctpkg(package, "syn-firm-01", mutated)


class CounselTests(unittest.TestCase):
    def test_named_human_required_and_unrelated_denied(self) -> None:
        with self.assertRaises(ValueError):
            named_human_release("syn-case-01", "syn-firm-01", "", "named-human-release-owner", "rel-01")
        receipt = named_human_release(
            "syn-case-01",
            "syn-firm-01",
            "syn-actor-01",
            "named-human-release-owner",
            "rel-01",
        )
        self.assertFalse(receipt.counsel_approved)
        access = CounselAccess()
        with self.assertRaises(PermissionError):
            access.require_read("syn-case-01", "syn-firm-01", "syn-case-01")
        access.record(receipt)
        access.require_read("syn-case-01", "syn-firm-01", "syn-case-01")
        with self.assertRaises(PermissionError):
            access.require_read("syn-case-01", "syn-firm-01", "syn-case-other")


if __name__ == "__main__":
    unittest.main()
