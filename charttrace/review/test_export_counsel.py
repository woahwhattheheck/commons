"""Tests for export packet assembly, .ctpkg immutability, and counsel access."""

from __future__ import annotations

import unittest

from charttrace.counsel.access import CounselAccessError, CounselSession
from charttrace.counsel.mode import CounselReviewMode
from charttrace.export.ctpkg import (
    CtpkgBuildError,
    build_ctpkg,
    mutate_payload_bytes,
    verify_ctpkg,
)
from charttrace.export.packet import assemble_export_packet
from charttrace.review.fixtures_synth import base_packet, clean_lead, weak_grounded_lead
from charttrace.review.pipeline import ReviewPipeline


def _releasable_review():
    packet = base_packet()
    return packet, ReviewPipeline().run(packet)


class ExportCounselTests(unittest.TestCase):
    def test_assemble_ordered_packet_and_ctpkg(self) -> None:
        packet, review = _releasable_review()
        self.assertFalse(review.release_blocked)
        export = assemble_export_packet(
            review,
            sources=packet["sources"],
            recipient_id="firm-synth-001",
            release_version="r1.0.0",
            citation_index=packet["citation_index"],
            peer_manifest={
                "release_state": "RELEASED_TO_NAMED_RECIPIENT",
                "reviewer": "Reviewer-Synthetic-A",
            },
            reviewed_pdf_meta={"pages": 20, "label": "reviewed_synthetic.pdf"},
        )
        self.assertEqual(export.recipient_id, "firm-synth-001")
        self.assertEqual(list(export.section_order())[0], "strongest_grounded_patterns")
        self.assertTrue(export.weak_appendix or export.json_rows)

        pkg = build_ctpkg(export, signature_state="UNSIGNED_SYNTHETIC")
        self.assertEqual(pkg.signature_state, "UNSIGNED_SYNTHETIC")
        self.assertEqual(len(pkg.package_hash), 64)
        self.assertNotIn("quarantine_internal", pkg.payload)
        verify_ctpkg(pkg, expected_recipient_id="firm-synth-001")

    def test_changed_bytes_fail_closed(self) -> None:
        packet, review = _releasable_review()
        export = assemble_export_packet(
            review,
            sources=packet["sources"],
            recipient_id="firm-synth-001",
            release_version="r1.0.0",
            peer_manifest={"release_state": "RELEASED_TO_NAMED_RECIPIENT"},
        )
        pkg = build_ctpkg(export)
        tampered = mutate_payload_bytes(pkg, "release_version", "r9.9.9")
        with self.assertRaises(CtpkgBuildError):
            verify_ctpkg(tampered, expected_recipient_id="firm-synth-001")

    def test_wrong_recipient_fail_closed(self) -> None:
        packet, review = _releasable_review()
        export = assemble_export_packet(
            review,
            sources=packet["sources"],
            recipient_id="firm-synth-001",
            release_version="r1.0.0",
            peer_manifest={"release_state": "RELEASED_TO_NAMED_RECIPIENT"},
        )
        pkg = build_ctpkg(export)
        with self.assertRaises(CtpkgBuildError):
            verify_ctpkg(pkg, expected_recipient_id="firm-OTHER")

    def test_blocked_review_cannot_export(self) -> None:
        packet = base_packet()
        packet["release"]["named_human_reviewer"] = None
        review = ReviewPipeline().run(packet)
        self.assertTrue(review.release_blocked)
        with self.assertRaises(ValueError):
            assemble_export_packet(
                review,
                sources=packet["sources"],
                recipient_id="firm-synth-001",
                release_version="r1.0.0",
            )

    def test_counsel_cannot_read_unrelated_or_unreleased(self) -> None:
        packet, review = _releasable_review()
        export = assemble_export_packet(
            review,
            sources=packet["sources"],
            recipient_id="firm-synth-001",
            release_version="r1.0.0",
            peer_manifest={"release_state": "RELEASED_TO_NAMED_RECIPIENT"},
        )
        pkg = build_ctpkg(export)

        session = CounselSession(
            counsel_id="counsel-1",
            recipient_id="firm-synth-001",
            allowed_case_ids={"SYN-CASE-001"},
        )
        mode = CounselReviewMode(session)
        opened = mode.import_package(case_id="SYN-CASE-001", package=pkg)
        self.assertEqual(opened["package_hash"], pkg.package_hash)

        with self.assertRaises(CounselAccessError):
            mode.import_package(case_id="SYN-CASE-OTHER", package=pkg)

        other = CounselSession(
            counsel_id="counsel-2",
            recipient_id="firm-OTHER",
            allowed_case_ids={"SYN-CASE-001"},
        )
        with self.assertRaises(CounselAccessError):
            CounselReviewMode(other).import_package(
                case_id="SYN-CASE-001", package=pkg
            )

        export2 = assemble_export_packet(
            review,
            sources=packet["sources"],
            recipient_id="firm-synth-001",
            release_version="r1.0.1",
            peer_manifest={"release_state": "INTERNAL_QA"},
        )
        pkg2 = build_ctpkg(export2)
        with self.assertRaises(CounselAccessError):
            mode.import_package(case_id="SYN-CASE-001", package=pkg2)

    def test_only_counsel_fills_legal_fields(self) -> None:
        packet, review = _releasable_review()
        export = assemble_export_packet(
            review,
            sources=packet["sources"],
            recipient_id="firm-synth-001",
            release_version="r1.0.0",
            peer_manifest={"release_state": "RELEASED_TO_NAMED_RECIPIENT"},
        )
        pkg = build_ctpkg(export)
        session = CounselSession(
            counsel_id="counsel-1",
            recipient_id="firm-synth-001",
            allowed_case_ids={"SYN-CASE-001"},
        )
        mode = CounselReviewMode(session)
        mode.import_package(case_id="SYN-CASE-001", package=pkg)
        filled = mode.set_legal_assessment(
            case_id="SYN-CASE-001",
            lead_id="L-clean-1",
            legal_relevance="counsel assessment only",
        )
        self.assertTrue(filled["counsel_filled"])

        dirty = clean_lead(legal_relevance="auto junk", counsel_filled=False)
        packet2 = base_packet(leads=[dirty, weak_grounded_lead()])
        review2 = ReviewPipeline().run(packet2)
        release = next(s for s in review2.stages if s.name == "named_human_release")
        self.assertFalse(release.ok)


if __name__ == "__main__":
    unittest.main()
