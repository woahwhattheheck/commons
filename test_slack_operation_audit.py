#!/usr/bin/env python3
"""Hosted-battery entry for the Slack operation receipt audit.

The audit module and its focused tests live under integrations/gemini_slack/.
The hosted battery only discovers root test_*.py files, so this file re-exports
the same cases without relocating or deleting the package tests.
"""
from integrations.gemini_slack.test_slack_operation_audit import SlackOperationAuditTests  # noqa: F401
import unittest

if __name__ == "__main__":
    unittest.main()
