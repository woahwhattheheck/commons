"""Root CI bridge for the enterprise security-questionnaire evidence-pack battery."""
from __future__ import annotations

import importlib.util
from pathlib import Path

TEST_FILE = Path(__file__).resolve().parent / "tests" / "test_security_questionnaire_evidence_pack.py"
SPEC = importlib.util.spec_from_file_location("security_questionnaire_evidence_pack_tests", TEST_FILE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"unable to load {TEST_FILE}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

TestSecurityQuestionnaireEvidencePack = MODULE.SecurityQuestionnaireEvidencePackTests
