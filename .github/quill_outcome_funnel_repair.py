#!/usr/bin/env python3
"""Reconcile Outcome Commerce's compiled receipt census with canonical receipts."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "revenue" / "outcome_commerce" / "catalog.json"
TESTS = ROOT / "test_outcome_commerce.py"
RECEIPTS = ROOT / "revenue" / "payment_ready" / "outreach_receipts"
COMPOSIO = "20260830-composio-1a053aa4f8a0014a.json"
LANGFUSE = "20260828-langfuse-1a0496451e052b9d.json"


def replace_exact(text: str, old: str, new: str, expected: int) -> str:
    actual = text.count(old)
    if actual != expected:
        raise AssertionError((old, expected, actual))
    return text.replace(old, new)


def main() -> None:
    receipt_paths = sorted(RECEIPTS.glob("*.json"))
    assert len(receipt_paths) == 18, len(receipt_paths)
    rows = [json.loads(path.read_text(encoding="utf-8")) for path in receipt_paths]
    contacts = {
        (row.get("dedupe") or {}).get("distinct_contact_key")
        or row.get("recipient_email")
        or row["target_id"]
        for row in rows
    }
    assert len(contacts) == 13, len(contacts)
    assert receipt_paths[-1].name == COMPOSIO

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    truth = catalog["funnel_truth"]
    assert truth["as_of"] == "2026-08-28T17:21:46Z"
    assert truth["delivered_transports"] == 17
    assert truth["distinct_targets"] == 12
    assert LANGFUSE in truth["source"]
    assert COMPOSIO not in truth["source"]
    truth["as_of"] = "2026-08-30T17:14:25Z"
    truth["source"] = (
        "revenue/payment_ready/current_receipt.json plus "
        "revenue/payment_ready/outreach_receipts/ through "
        f"{COMPOSIO}; includes {LANGFUSE}; "
        "unclassified response signal: p/slack-1787769698-642529.md"
    )
    truth["distinct_targets"] = 13
    truth["delivered_transports"] = 18
    CATALOG.write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    text = TESTS.read_text(encoding="utf-8")
    text = replace_exact(
        text,
        'self.assertEqual(truth["delivered_transports"], 17)',
        'self.assertEqual(truth["delivered_transports"], 18)',
        2,
    )
    text = replace_exact(
        text,
        'self.assertEqual(truth["distinct_targets"], 12)',
        'self.assertEqual(truth["distinct_targets"], 13)',
        2,
    )
    text = replace_exact(
        text,
        "self.assertEqual(len(receipts), 17)",
        "self.assertEqual(len(receipts), 18)",
        1,
    )
    text = replace_exact(
        text,
        '    def test_langfuse_hard_dnr_zero_cash_advances_funnel_truth(self) -> None:\n'
        '        """#4969 receipt must advance catalog funnel_truth; do not leave 16/11 pins."""',
        '    def test_latest_hard_dnr_receipts_advance_funnel_truth(self) -> None:\n'
        '        """Canonical receipts advance truth without claiming cash or acceptance."""',
        1,
    )
    text = replace_exact(
        text,
        '        self.assertEqual(\n'
        '            {row["response_state"] for row in receipts},\n'
        '            {"UNKNOWN"},\n'
        '        )',
        '        self.assertEqual(\n'
        '            {row["response_state"] for row in receipts},\n'
        '            {"UNKNOWN", "NO_REPLY_OBSERVED"},\n'
        '        )',
        1,
    )
    source_assert = (
        '        self.assertIn("20260828-langfuse-1a0496451e052b9d.json", truth["source"])'
    )
    text = replace_exact(
        text,
        source_assert,
        source_assert
        + '\n        self.assertIn("20260830-composio-1a053aa4f8a0014a.json", truth["source"])',
        2,
    )

    marker = '\n\n\nif __name__ == "__main__":\n'
    addition = '''

    def test_composio_hard_dnr_zero_cash_advances_funnel_truth(self) -> None:
        truth = self.catalog["funnel_truth"]
        self.assertEqual(truth["as_of"], "2026-08-30T17:14:25Z")
        self.assertEqual(truth["delivered_transports"], 18)
        self.assertEqual(truth["distinct_targets"], 13)
        self.assertIn("20260830-composio-1a053aa4f8a0014a.json", truth["source"])
        row = read_json(
            ROOT
            / "revenue"
            / "payment_ready"
            / "outreach_receipts"
            / "20260830-composio-1a053aa4f8a0014a.json"
        )
        self.assertEqual(row["target_id"], "composio")
        self.assertEqual(row["provider"], "GMAIL")
        self.assertEqual(row["provider_state"], "SENT")
        self.assertEqual(row["provider_reference"], "gmail:message:1a053aa4f8a0014a")
        self.assertTrue(row["dedupe"]["do_not_resend"])
        self.assertEqual(row["dedupe"]["distinct_contact_key"], "support@composio.dev")
        self.assertEqual(row["response_state"], "NO_REPLY_OBSERVED")
        self.assertIsNone(row["response_reference"])
        self.assertIs(row["facts"]["cash_claimed"], False)
        self.assertEqual(row["facts"]["collected_cash_usd"], 0)
        self.assertEqual(row["facts"]["legal_acceptance"], "NOT_LANDED")
        self.assertEqual(row["facts"]["buyer_authorization"], "UNKNOWN")
'''
    text = replace_exact(text, marker, addition + marker, 1)
    TESTS.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
