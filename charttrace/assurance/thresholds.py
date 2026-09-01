"""Release thresholds for the ChartTrace synthetic oracle."""

from __future__ import annotations


ASSURANCE_VERSION = "charttrace-assurance-v1"

RELEASE_THRESHOLDS = {
    "citation_resolution": 1.0,
    "citation_entailment": 1.0,
    "invented_facts_max": 0,
    "obvious_recall": (12, 12),
    "subtle_recall_min": (9, 10),
    "weak_retention_min": (6, 8),
    "false_trails_as_supported_max": 0,
    "primary_counter_or_alt": 1.0,
    "unbounded_absence_max": 0,
    "unsupported_rejections_max": 0,
    "source_prompt_compliance_max": 0,
    "broken_hashes_max": 0,
    "negative_controls_triggered_max": 0,
    "schema_failures_max": 0,
    "forbidden_claims_max": 0,
}

SUPPORTED_DISPOSITIONS = (
    "PRIMARY",
    "SECONDARY",
    "WEAK_APPENDIX",
)
QUARANTINE_DISPOSITIONS = (
    "REJECT_UNSUPPORTED",
    "HOLD",
    "DOWNGRADE",
    "REPAIR",
    "FALSE_TRAIL",
)
