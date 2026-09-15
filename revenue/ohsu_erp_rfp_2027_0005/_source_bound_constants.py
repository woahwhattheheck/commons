from __future__ import annotations

import datetime as _dt

SCHEMA_FACTS = "ohsu-erp-source-bound-facts/v1"
SCHEMA_PACKET = "ohsu-erp-source-bound-owner-review/v2"
SCHEMA_INPUT = "ohsu-erp-source-bound-compile-input/v1"
SCHEMA_VERIFY_INPUT = "ohsu-erp-source-bound-verify-input/v1"
OPPORTUNITY_ID = "RFP-2027-0005"
MAX_STDIN_BYTES = 1_048_576

CONTROLLING_PACK_SHA256 = "4d4c634ac5f7846dac54692c8d7d2c57a6512f8c2f6984be1c36f2a8dc99f90e"
SUPPLIER_QA_SHA256 = "40815c4a57d9d82cf07e4db6b2b6f1dfc6512c7fa4cf996af6ec364608722cf0"
INTENT_DEADLINE = _dt.datetime.fromisoformat("2026-09-16T17:00:00-07:00")
PROPOSAL_DEADLINE = _dt.datetime.fromisoformat("2026-09-25T17:00:00-07:00")
RESPONDENT_REF = "token-junkie-labs"


REQUIREMENT_IDS = (
    "MBR_1_01_RECENT_COMPARABLE_ERP_ASSESSMENTS",
    "MBR_1_02_ORACLE_EBS_AND_MAJOR_ERP_EVALUATION",
    "MBR_1_03_CROSS_FUNCTIONAL_ERP_EXPERTISE",
    "MBR_1_04_VENDOR_NEUTRALITY_AND_AFFILIATION_DISCLOSURE",
    "MBR_1_05_REGULATED_ENVIRONMENT_TEAM_PM_QA",
    "MBR_1_06_COMPARABLE_REFERENCES_AND_WORK_SAMPLES",
    "MBR_1_07_DATA_AND_DELIVERABLE_RIGHTS",
)
_REQUIRED_SET = frozenset(REQUIREMENT_IDS)
_SHA256_CHARS = frozenset("0123456789abcdef")


class ContractError(ValueError):
    pass
