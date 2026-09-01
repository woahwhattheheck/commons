"""Comprehensive tests for ChartTrace Lane E (Pricing, Affiliates, Commercial Guards)."""

import unittest
from typing import Dict, Any

from charttrace.pricing import (
    ProductTier,
    ReviewPriorityScore,
    ReviewWorkScore,
    WorkloadMetrics,
    calculate_review_priority,
    calculate_review_work_score,
    assert_clean_workload_inputs,
    EconomicIsolationViolation,
    FORBIDDEN_ECONOMIC_SIGNAL_KEYS,
)
from charttrace.pricing.ledgers import PAGE_BANDS
from charttrace.affiliates import (
    ReviewerQATier,
    ReviewerAuditProfile,
    calculate_affiliate_review_fee,
    evaluate_rolling_qa_tier,
    AffiliateConflictError,
    ReviewerIncentiveViolation,
    PAGE_BAND_RATES_CENTS,
    QA_TIER_MULTIPLIERS,
)
from charttrace.commercial import (
    PolicyState,
    RoutingEngine,
    RoutingRequest,
    FirmCandidate,
    RoutingPolicyViolation,
    OpaqueOrderContract,
    SensitiveDataExposureError,
    CommercialFeatureFlags,
    assert_live_operations_disabled,
    LivePaymentOperationBlockedError,
)


class TestSeparatedLedgers(unittest.TestCase):
    """Tests for REVIEW_PRIORITY and REVIEW_WORK_SCORE separated ledgers."""

    def test_review_priority_ordering_not_price_or_probability(self):
        priority = calculate_review_priority(
            "item_001",
            evidence_support=0.9,
            materiality_if_confirmed=0.85,
            temporal_linkage=0.7,
            novelty=0.6,
            counterevidence=0.4,
            completeness=0.8,
            deadline_urgency=0.95,
            notes="Statute of limitations approaching for missed diagnostic lead.",
        )
        self.assertIsInstance(priority, ReviewPriorityScore)
        self.assertGreaterEqual(priority.composite_priority, 0.0)
        self.assertLessEqual(priority.composite_priority, 100.0)
        self.assertEqual(priority.priority_band, "URGENT")
        data = priority.to_dict()
        # Verify no price, probability, or case value fields exist
        for forbidden in ("price", "case_value", "probability", "damages", "recovery"):
            self.assertNotIn(forbidden, data)

    def test_forbidden_economic_signals_in_priority_calc(self):
        with self.assertRaises(EconomicIsolationViolation):
            calculate_review_priority(
                "item_002",
                evidence_support=0.8,
                materiality_if_confirmed=0.8,
                temporal_linkage=0.5,
                novelty=0.5,
                counterevidence=0.2,
                completeness=0.9,
                deadline_urgency=0.5,
                extra_metadata={"damages_amount": 5000000},
            )

    def test_review_work_score_priced_strictly_by_disclosed_workload(self):
        metrics_small = WorkloadMetrics(
            unique_pages=45,
            file_count=3,
            ocr_repair_page_count=2,
            source_provider_count=1,
            date_span_days=30,
            specialties_count=1,
            language_count=1,
            duplicate_conflict_pairs=0,
            jurisdiction_pack_count=1,
            turnaround_hours=72,
            estimated_human_qa_minutes=20,
        )
        work_score_indexed = calculate_review_work_score("pkt_001", ProductTier.INDEXED, metrics_small)
        work_score_investigative = calculate_review_work_score("pkt_001", ProductTier.INVESTIGATIVE, metrics_small)
        work_score_counsel = calculate_review_work_score("pkt_001", ProductTier.COUNSEL_READY, metrics_small)

        self.assertEqual(work_score_indexed.page_band, "1-50")
        self.assertGreater(work_score_counsel.calculated_price_cents, work_score_investigative.calculated_price_cents)
        self.assertGreater(work_score_investigative.calculated_price_cents, work_score_indexed.calculated_price_cents)

    def test_pricing_invariant_case_merits_do_not_alter_price(self):
        """Case merits/damages/recovery/severity MUST NOT change price."""
        metrics = WorkloadMetrics(
            unique_pages=150,
            file_count=5,
            ocr_repair_page_count=10,
            source_provider_count=2,
            turnaround_hours=48,
        )
        score1 = calculate_review_work_score("pkt_002", ProductTier.INVESTIGATIVE, metrics)

        # Attempting to pass forbidden inputs must fail
        with self.assertRaises(EconomicIsolationViolation):
            calculate_review_work_score(
                "pkt_002",
                ProductTier.INVESTIGATIVE,
                metrics,
                extra_metadata={"expected_recovery": 10000000, "win_probability": 0.95},
            )

        # A second identical workload with no illegal input generates identical price
        score2 = calculate_review_work_score("pkt_003", ProductTier.INVESTIGATIVE, metrics)
        self.assertEqual(score1.calculated_price_cents, score2.calculated_price_cents)
        self.assertEqual(score1.page_band, score2.page_band)

    def test_legal_fees_and_named_signals_cannot_change_price_or_priority(self):
        """Hard-block price/priority from legal fees, success, destination, recovery."""
        metrics = WorkloadMetrics(unique_pages=80, file_count=2)
        for key in ("legal_fees", "legal_fee", "success", "destination", "recovery"):
            with self.assertRaises(EconomicIsolationViolation):
                calculate_review_work_score(
                    "pkt_blocked",
                    ProductTier.INDEXED,
                    metrics,
                    extra_metadata={key: 1},
                )
            with self.assertRaises(EconomicIsolationViolation):
                calculate_review_priority(
                    "item_blocked",
                    evidence_support=0.5,
                    materiality_if_confirmed=0.5,
                    temporal_linkage=0.5,
                    novelty=0.5,
                    counterevidence=0.5,
                    completeness=0.5,
                    deadline_urgency=0.5,
                    extra_metadata={key: 1},
                )


class TestAffiliateReviewers(unittest.TestCase):
    """Tests for affiliate reviewer rolling QA tiers, fee formula, and conflict guards."""

    def test_rolling_qa_tier_evaluation(self):
        tier_prov = evaluate_rolling_qa_tier(5, 0.85, 0.85, 0.80)
        self.assertEqual(tier_prov, ReviewerQATier.PROVISIONAL)

        tier_est = evaluate_rolling_qa_tier(15, 0.92, 0.90, 0.85)
        self.assertEqual(tier_est, ReviewerQATier.ESTABLISHED)

        tier_sr = evaluate_rolling_qa_tier(50, 0.96, 0.96, 0.90)
        self.assertEqual(tier_sr, ReviewerQATier.SENIOR_AUDITED)

        tier_master = evaluate_rolling_qa_tier(120, 0.99, 0.99, 0.96)
        self.assertEqual(tier_master, ReviewerQATier.MASTER_AUDITED)

    def test_affiliate_review_fee_formula(self):
        """review_fee = page_band_rate × established_QA_tier × approved_SLA_multiplier"""
        profile = ReviewerAuditProfile(
            reviewer_id="rev_101",
            reviewer_firm_id="firm_alpha",
            total_audited_reviews=60,
            accuracy_rate=0.97,
            citation_precision=0.96,
            disposition_concordance=0.92,
            current_qa_tier=ReviewerQATier.SENIOR_AUDITED,  # 1.30x
        )

        statement = calculate_affiliate_review_fee(
            matter_id="mat_888",
            reviewer_profile=profile,
            recipient_firm_id="firm_beta",
            page_band="51-200",  # $75.00 (7500 cents)
            turnaround_hours=24,  # 1.25x SLA
        )
        # 7500 * 1.30 * 1.25 = 12187.5 -> 12188 cents
        self.assertEqual(statement.page_band_rate_cents, 7500)
        self.assertEqual(statement.qa_tier_multiplier, 1.30)
        self.assertEqual(statement.approved_sla_multiplier, 1.25)
        self.assertEqual(statement.review_fee_cents, 12188)

    def test_reviewer_firm_conflict_separation(self):
        """Reviewer firm != recipient firm on one matter."""
        profile = ReviewerAuditProfile(
            reviewer_id="rev_102",
            reviewer_firm_id="firm_shared",
            total_audited_reviews=20,
            accuracy_rate=0.94,
            citation_precision=0.94,
            disposition_concordance=0.90,
            current_qa_tier=ReviewerQATier.ESTABLISHED,
        )

        with self.assertRaises(AffiliateConflictError):
            calculate_affiliate_review_fee(
                matter_id="mat_889",
                reviewer_profile=profile,
                recipient_firm_id="firm_shared",  # Same firm!
                page_band="1-50",
                turnaround_hours=72,
            )

    def test_reviewer_never_earns_more_for_outcomes_or_severity(self):
        """Reviewer fee must reject contingency, retainer, or severity bonuses."""
        profile = ReviewerAuditProfile(
            reviewer_id="rev_103",
            reviewer_firm_id="firm_independent",
            total_audited_reviews=30,
            accuracy_rate=0.95,
            citation_precision=0.95,
            disposition_concordance=0.90,
            current_qa_tier=ReviewerQATier.ESTABLISHED,
        )

        with self.assertRaises(ReviewerIncentiveViolation):
            calculate_affiliate_review_fee(
                matter_id="mat_890",
                reviewer_profile=profile,
                recipient_firm_id="firm_recipient",
                page_band="201-500",
                turnaround_hours=48,
                forbidden_incentive_check={"case_acceptance_bonus": 500},
            )

        with self.assertRaises(ReviewerIncentiveViolation):
            calculate_affiliate_review_fee(
                matter_id="mat_891",
                reviewer_profile=profile,
                recipient_firm_id="firm_recipient",
                page_band="201-500",
                turnaround_hours=48,
                forbidden_incentive_check={"bad_conduct_multiplier": 1.5},
            )

        with self.assertRaises(ReviewerIncentiveViolation):
            calculate_affiliate_review_fee(
                matter_id="mat_892",
                reviewer_profile=profile,
                recipient_firm_id="firm_recipient",
                page_band="201-500",
                turnaround_hours=48,
                forbidden_incentive_check={"legal_fees": 40000},
            )


class TestCommercialAndRoutingPolicies(unittest.TestCase):
    """Tests for routing policies, policy states, and Stripe order contracts."""

    def setUp(self):
        self.candidates = [
            FirmCandidate(
                firm_id="firm_01",
                firm_name="Alpha Legal LLC",
                jurisdictions=["CA", "WA"],
                practice_categories=["medmal", "personal_injury"],
                languages=["en", "es"],
                declared_capacity=5,
                is_conflict_cleared=True,
            ),
            FirmCandidate(
                firm_id="firm_02",
                firm_name="Beta Law Group",
                jurisdictions=["CA", "NY"],
                practice_categories=["medmal"],
                languages=["en"],
                declared_capacity=2,
                is_conflict_cleared=True,
            ),
            FirmCandidate(
                firm_id="firm_03",
                firm_name="Gamma Partners",
                jurisdictions=["CA"],
                practice_categories=["medmal"],
                languages=["en"],
                declared_capacity=0,  # No capacity
                is_conflict_cleared=True,
            ),
        ]

    def test_routing_engine_policy_states(self):
        # 1. Default OFF
        engine_off = RoutingEngine(policy_state=PolicyState.OFF)
        req = RoutingRequest(jurisdiction="CA", practice_category="medmal")
        dec_off = engine_off.route_matter(req, self.candidates)
        self.assertEqual(dec_off.policy_state, PolicyState.OFF)
        self.assertIsNone(dec_off.routed_firm_id)
        self.assertEqual(dec_off.routing_method, "NONE")

        engine_ad = RoutingEngine(policy_state=PolicyState.ADVERTISING_ONLY)
        dec_ad = engine_ad.route_matter(req, self.candidates)
        self.assertEqual(dec_ad.policy_state, PolicyState.ADVERTISING_ONLY)
        self.assertIsNone(dec_ad.routed_firm_id)
        self.assertEqual(dec_ad.routing_method, "NONE")

    def test_routing_engine_user_selection(self):
        engine = RoutingEngine(policy_state=PolicyState.QUALIFYING_PROVIDER_APPROVED)
        req = RoutingRequest(
            jurisdiction="CA",
            practice_category="medmal",
            user_selected_firm_id="firm_02",
        )
        dec = engine.route_matter(req, self.candidates)
        self.assertEqual(dec.routed_firm_id, "firm_02")
        self.assertEqual(dec.routing_method, "USER_SELECTED")

    def test_forbidden_routing_inputs_raise(self):
        with self.assertRaises(RoutingPolicyViolation):
            RoutingRequest(
                jurisdiction="CA",
                practice_category="medmal",
                metadata={"juice": "high", "damages_amount": 1000000},
            )
        for key in ("legal_fees", "destination", "firm_interest", "success", "recovery"):
            with self.assertRaises(RoutingPolicyViolation):
                RoutingRequest(
                    jurisdiction="CA",
                    practice_category="medmal",
                    metadata={key: 1},
                )

    def test_paid_lead_generation_jurisdiction_disabled_by_default(self):
        # Default engine has no paid lead gen jurisdictions enabled
        engine = RoutingEngine(policy_state=PolicyState.ADVERTISING_ONLY)
        # If jurisdiction is not enabled for paid lead gen, standard routing proceeds
        req = RoutingRequest(jurisdiction="CA", practice_category="medmal")
        dec = engine.route_matter(req, self.candidates)
        self.assertFalse(dec.is_paid_lead_generation)

        # Attempting paid lead generation without qualified policy state raises
        engine_paid_attempt = RoutingEngine(
            policy_state=PolicyState.ADVERTISING_ONLY,
            paid_lead_generation_enabled_jurisdictions={"CA"},
        )
        with self.assertRaises(RoutingPolicyViolation):
            engine_paid_attempt.route_matter(req, self.candidates)

    def test_opaque_stripe_order_contract_clean(self):
        metrics = WorkloadMetrics(unique_pages=150, file_count=5, turnaround_hours=48)
        work_score = calculate_review_work_score("pkt_ord", ProductTier.INVESTIGATIVE, metrics)
        contract = OpaqueOrderContract(
            order_id="ct_ord_9901",
            customer_id="ct_cus_1102",
            product_tier=ProductTier.INVESTIGATIVE,
            page_band=work_score.page_band,
            turnaround_hours=48,
            amount_cents=work_score.calculated_price_cents,
            currency="usd",
            metadata={"source_system": "charttrace_local"},
            work_score=work_score,
        )
        payload = contract.to_stripe_checkout_payload()
        self.assertEqual(payload["client_reference_id"], "ct_ord_9901")
        self.assertEqual(payload["customer"], "ct_cus_1102")
        self.assertEqual(payload["metadata"]["tier"], "INVESTIGATIVE")
        self.assertEqual(payload["metadata"]["page_band"], "51-200")

    def test_opaque_stripe_contract_forbids_phi_and_case_merits(self):
        # Forbidden keys
        metrics = WorkloadMetrics(unique_pages=250, file_count=4, turnaround_hours=24)
        work_score = calculate_review_work_score("pkt_blocked", ProductTier.COUNSEL_READY, metrics)
        with self.assertRaises(SensitiveDataExposureError):
            OpaqueOrderContract(
                order_id="ct_ord_9902",
                customer_id="ct_cus_1102",
                product_tier=ProductTier.COUNSEL_READY,
                page_band=work_score.page_band,
                turnaround_hours=24,
                amount_cents=work_score.calculated_price_cents,
                metadata={"patient_name": "John Doe"},
                work_score=work_score,
            )

        with self.assertRaises(SensitiveDataExposureError):
            OpaqueOrderContract(
                order_id="ct_ord_9903",
                customer_id="ct_cus_1102",
                product_tier=ProductTier.COUNSEL_READY,
                page_band=work_score.page_band,
                turnaround_hours=24,
                amount_cents=work_score.calculated_price_cents,
                metadata={"source_system": "hospital malpractice injury"},
                work_score=work_score,
            )

    def test_live_operations_disabled_invariants(self):
        default_flags = CommercialFeatureFlags()
        self.assertFalse(default_flags.live_routing_enabled)
        self.assertEqual(default_flags.connect_status, "HOLD_LEGAL_AND_PAYMENT_DESIGN")
        self.assertFalse(default_flags.charges_enabled)
        self.assertFalse(default_flags.products_enabled)
        self.assertFalse(default_flags.subscriptions_enabled)
        self.assertFalse(default_flags.transfers_enabled)
        self.assertFalse(default_flags.payouts_enabled)
        self.assertFalse(default_flags.tax_automation_enabled)
        self.assertFalse(default_flags.external_spend_enabled)
        self.assertFalse(default_flags.stripe_account_mutation_allowed)

        # Should pass with defaults
        assert_live_operations_disabled(default_flags)

        # Violation if live charges enabled
        bad_flags = CommercialFeatureFlags(charges_enabled=True)
        with self.assertRaises(LivePaymentOperationBlockedError):
            assert_live_operations_disabled(bad_flags)

        for kwargs in (
            {"live_routing_enabled": True},
            {"products_enabled": True},
            {"subscriptions_enabled": True},
            {"payouts_enabled": True},
            {"tax_automation_enabled": True},
            {"percentage_fee_enabled": True},
            {"transfers_enabled": True},
            {"external_spend_enabled": True},
            {"stripe_account_mutation_allowed": True},
        ):
            with self.assertRaises(LivePaymentOperationBlockedError):
                assert_live_operations_disabled(CommercialFeatureFlags(**kwargs))


class TestAdversarialBypasses(unittest.TestCase):
    def test_negative_qa_minutes_cannot_create_negative_price(self):
        with self.assertRaises(ValueError):
            WorkloadMetrics(
                unique_pages=10,
                file_count=1,
                estimated_human_qa_minutes=-40,
            )

    def test_caller_master_audited_with_zero_history_is_rejected(self):
        with self.assertRaises(AffiliateConflictError):
            ReviewerAuditProfile(
                reviewer_id="",
                reviewer_firm_id="firm_alpha",
                total_audited_reviews=0,
                accuracy_rate=1.0,
                citation_precision=1.0,
                disposition_concordance=1.0,
                current_qa_tier=ReviewerQATier.MASTER_AUDITED,
            )
        with self.assertRaises(ReviewerIncentiveViolation):
            ReviewerAuditProfile(
                reviewer_id="rev_zero",
                reviewer_firm_id="firm_alpha",
                total_audited_reviews=0,
                accuracy_rate=1.0,
                citation_precision=1.0,
                disposition_concordance=1.0,
                current_qa_tier=ReviewerQATier.MASTER_AUDITED,
            )
        self.assertEqual(evaluate_rolling_qa_tier(0, 1.0, 1.0, 1.0), ReviewerQATier.PROVISIONAL)

    def test_blank_reviewer_and_recipient_ids_fail_separation(self):
        with self.assertRaises(AffiliateConflictError):
            ReviewerAuditProfile(
                reviewer_id="   ",
                reviewer_firm_id="firm_alpha",
                total_audited_reviews=12,
                accuracy_rate=0.91,
                citation_precision=0.91,
                disposition_concordance=0.9,
                current_qa_tier=ReviewerQATier.ESTABLISHED,
            )
        profile = ReviewerAuditProfile(
            reviewer_id="rev_blank",
            reviewer_firm_id="firm_alpha",
            total_audited_reviews=12,
            accuracy_rate=0.91,
            citation_precision=0.91,
            disposition_concordance=0.9,
            current_qa_tier=ReviewerQATier.ESTABLISHED,
        )
        with self.assertRaises(AffiliateConflictError):
            calculate_affiliate_review_fee(
                matter_id="mat_blank",
                reviewer_profile=profile,
                recipient_firm_id="",
                page_band="1-50",
                turnaround_hours=72,
            )

    def test_advertising_only_and_caller_seed_cannot_choose_recipient(self):
        candidates = [
            FirmCandidate(
                firm_id="firm_01",
                firm_name="Alpha Legal LLC",
                jurisdictions=["CA"],
                practice_categories=["medmal"],
                languages=["en"],
                declared_capacity=5,
            ),
            FirmCandidate(
                firm_id="firm_02",
                firm_name="Beta Law Group",
                jurisdictions=["CA"],
                practice_categories=["medmal"],
                languages=["en"],
                declared_capacity=2,
            ),
        ]
        ad = RoutingEngine(policy_state=PolicyState.ADVERTISING_ONLY)
        dec = ad.route_matter(
            RoutingRequest(
                jurisdiction="CA",
                practice_category="medmal",
                neutral_rotation_seed=1,
            ),
            candidates,
        )
        self.assertIsNone(dec.routed_firm_id)
        approved = RoutingEngine(policy_state=PolicyState.QUALIFYING_PROVIDER_APPROVED)
        first = approved.route_matter(
            RoutingRequest(
                jurisdiction="CA",
                practice_category="medmal",
                neutral_rotation_seed=99,
            ),
            candidates,
        )
        second = approved.route_matter(
            RoutingRequest(
                jurisdiction="CA",
                practice_category="medmal",
                neutral_rotation_seed=99,
            ),
            candidates,
        )
        self.assertEqual(first.routed_firm_id, "firm_01")
        self.assertEqual(second.routed_firm_id, "firm_02")
        self.assertNotEqual(first.routed_firm_id, second.routed_firm_id)

    def test_patient_data_cannot_enter_ids_page_band_or_metadata(self):
        metrics = WorkloadMetrics(unique_pages=20, file_count=1)
        work_score = calculate_review_work_score("pkt_id", ProductTier.INDEXED, metrics)
        with self.assertRaises(ValueError):
            OpaqueOrderContract(
                order_id="ct_ord_patientjohn",
                customer_id="ct_cus_1102",
                product_tier=ProductTier.INDEXED,
                page_band=work_score.page_band,
                turnaround_hours=72,
                amount_cents=work_score.calculated_price_cents,
                work_score=work_score,
            )
        with self.assertRaises(ValueError):
            OpaqueOrderContract(
                order_id="ct_ord_9901",
                customer_id="ct_cus_1102",
                product_tier=ProductTier.INDEXED,
                page_band="patient-20",
                turnaround_hours=72,
                amount_cents=work_score.calculated_price_cents,
                work_score=work_score,
            )
        with self.assertRaises(SensitiveDataExposureError):
            OpaqueOrderContract(
                order_id="ct_ord_9901",
                customer_id="ct_cus_1102",
                product_tier=ProductTier.INDEXED,
                page_band=work_score.page_band,
                turnaround_hours=72,
                amount_cents=work_score.calculated_price_cents,
                metadata={"note": "patient record"},
                work_score=work_score,
            )

    def test_nested_aliased_suffixed_prohibited_fields_are_rejected(self):
        metrics = WorkloadMetrics(unique_pages=20, file_count=1)
        for payload in (
            {"legal_fee_cents": 1},
            {"nested": {"damages": 9}},
            {"expected_recovery_alias": 1},
            {"destination_firm_id_x": "x"},
        ):
            with self.assertRaises(EconomicIsolationViolation):
                calculate_review_work_score(
                    "pkt_alias",
                    ProductTier.INDEXED,
                    metrics,
                    extra_metadata=payload,
                )

    def test_percentage_fee_flag_fails_live_ops_assertion(self):
        with self.assertRaises(LivePaymentOperationBlockedError):
            assert_live_operations_disabled(
                CommercialFeatureFlags(percentage_fee_enabled=True)
            )

    def test_checkout_emission_enforces_live_ops_disabled(self):
        metrics = WorkloadMetrics(unique_pages=20, file_count=1, turnaround_hours=72)
        work_score = calculate_review_work_score("pkt_chk", ProductTier.INDEXED, metrics)
        contract = OpaqueOrderContract(
            order_id="ct_ord_chk01",
            customer_id="ct_cus_chk01",
            product_tier=ProductTier.INDEXED,
            page_band=work_score.page_band,
            turnaround_hours=72,
            amount_cents=work_score.calculated_price_cents,
            work_score=work_score,
        )
        # Default flags (all OFF) succeeds
        payload = contract.to_stripe_checkout_payload()
        self.assertEqual(payload["client_reference_id"], "ct_ord_chk01")

        # Live charges enabled fails closed
        with self.assertRaises(LivePaymentOperationBlockedError):
            contract.to_stripe_checkout_payload(flags=CommercialFeatureFlags(charges_enabled=True))

        # Live percentage fee enabled fails closed
        with self.assertRaises(LivePaymentOperationBlockedError):
            contract.to_stripe_checkout_payload(flags=CommercialFeatureFlags(percentage_fee_enabled=True))

    def test_parameterized_prohibited_signals(self):
        metrics = WorkloadMetrics(unique_pages=20, file_count=1)
        for key in sorted(FORBIDDEN_ECONOMIC_SIGNAL_KEYS):
            with self.subTest(key=key):
                with self.assertRaises(EconomicIsolationViolation):
                    calculate_review_work_score(
                        "pkt_sig",
                        ProductTier.INDEXED,
                        metrics,
                        extra_metadata={key: 1},
                    )
        self.assertEqual(PAGE_BANDS, ("1-50", "51-200", "201-500", "501-1000", "1000+"))

    def test_zero_pages_and_unknown_metadata_are_rejected(self):
        with self.assertRaises(ValueError):
            WorkloadMetrics(unique_pages=0, file_count=1)
        with self.assertRaises(ValueError):
            WorkloadMetrics(unique_pages=10, file_count=0)
        with self.assertRaises(ValueError):
            WorkloadMetrics(unique_pages=10, file_count=1, turnaround_hours=36)
        metrics = WorkloadMetrics(unique_pages=10, file_count=1)
        with self.assertRaises(EconomicIsolationViolation):
            calculate_review_work_score(
                "pkt_meta",
                ProductTier.INDEXED,
                metrics,
                extra_metadata={"foo": "bar"},
            )
        with self.assertRaises(EconomicIsolationViolation):
            calculate_review_work_score(
                "patient-john-doe-mrn-999",
                ProductTier.INDEXED,
                metrics,
            )
        score = calculate_review_work_score("pkt_ok", ProductTier.INDEXED, metrics)
        self.assertGreater(score.calculated_price_cents, 0)
        self.assertEqual(score.page_band, "1-50")

    def test_named_and_mrn_order_ids_are_rejected(self):
        metrics = WorkloadMetrics(unique_pages=20, file_count=1, turnaround_hours=72)
        work_score = calculate_review_work_score("pkt_id", ProductTier.INDEXED, metrics)
        with self.assertRaises(ValueError):
            OpaqueOrderContract(
                order_id="ct_ord_johnsmith",
                customer_id="ct_cus_1102",
                product_tier=ProductTier.INDEXED,
                page_band=work_score.page_band,
                turnaround_hours=72,
                amount_cents=work_score.calculated_price_cents,
                work_score=work_score,
            )
        with self.assertRaises(ValueError):
            OpaqueOrderContract(
                order_id="ct_ord_9901",
                customer_id="ct_cus_mrn9999",
                product_tier=ProductTier.INDEXED,
                page_band=work_score.page_band,
                turnaround_hours=72,
                amount_cents=work_score.calculated_price_cents,
                work_score=work_score,
            )
        with self.assertRaises(SensitiveDataExposureError):
            OpaqueOrderContract(
                order_id="ct_ord_9901",
                customer_id="ct_cus_1102",
                product_tier=ProductTier.INDEXED,
                page_band=work_score.page_band,
                turnaround_hours=72,
                amount_cents=work_score.calculated_price_cents,
                metadata={"packet_id": "dx-sepsis-note"},
                work_score=work_score,
            )
        with self.assertRaises(ValueError):
            OpaqueOrderContract(
                order_id="ct_ord_9901",
                customer_id="ct_cus_1102",
                product_tier=ProductTier.INDEXED,
                page_band=work_score.page_band,
                turnaround_hours=72,
                amount_cents=work_score.calculated_price_cents + 1,
                work_score=work_score,
            )

    def test_jurisdiction_cannot_carry_prohibited_tokens(self):
        with self.assertRaises(RoutingPolicyViolation):
            RoutingRequest(jurisdiction="damages", practice_category="medmal")
        with self.assertRaises(RoutingPolicyViolation):
            RoutingRequest(jurisdiction="CA", practice_category="patient_mrn")

    def test_every_live_ops_flag_including_connect_is_off(self):
        assert_live_operations_disabled(CommercialFeatureFlags())
        with self.assertRaises(LivePaymentOperationBlockedError):
            assert_live_operations_disabled(
                CommercialFeatureFlags(connect_status="ACTIVE")
            )
        with self.assertRaises(LivePaymentOperationBlockedError):
            assert_live_operations_disabled(
                CommercialFeatureFlags(connect_status="LIVE")
            )

    def test_parameterized_routing_and_stripe_aliases(self):
        from charttrace.commercial import FORBIDDEN_ROUTING_KEYS, FORBIDDEN_STRIPE_PAYLOAD_KEYS

        metrics = WorkloadMetrics(unique_pages=20, file_count=1)
        work_score = calculate_review_work_score("pkt_pay", ProductTier.INDEXED, metrics)
        for key in sorted(FORBIDDEN_ROUTING_KEYS):
            with self.subTest(routing=key):
                with self.assertRaises(RoutingPolicyViolation):
                    RoutingRequest(
                        jurisdiction="CA",
                        practice_category="medmal",
                        metadata={key: 1},
                    )
                with self.assertRaises(RoutingPolicyViolation):
                    RoutingRequest(
                        jurisdiction="CA",
                        practice_category="medmal",
                        metadata={"nested": {f"{key}_alias": 1}},
                    )
        for key in sorted(FORBIDDEN_STRIPE_PAYLOAD_KEYS):
            with self.subTest(stripe=key):
                with self.assertRaises(SensitiveDataExposureError):
                    OpaqueOrderContract(
                        order_id="ct_ord_9901",
                        customer_id="ct_cus_1102",
                        product_tier=ProductTier.INDEXED,
                        page_band=work_score.page_band,
                        turnaround_hours=72,
                        amount_cents=work_score.calculated_price_cents,
                        metadata={key: "x"},
                        work_score=work_score,
                    )


if __name__ == "__main__":
    unittest.main()
