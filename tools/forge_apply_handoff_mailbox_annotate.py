#!/usr/bin/env python3
"""Apply optional --mailbox-verify annotate on CRM6 handoff.

CLAIM ledger-crm6-handoff-mailbox-verify-annotate-20260906-01
Self-deleted by oneshot after commit.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT / "host" / "lm_gtm_relationship_handoff.py"
README = ROOT / "revenue" / "lm_gtm_index" / "README.md"
REGISTRY = ROOT / "revenue" / "lm_gtm_index" / "mailbox_buyer_reply_registry.json"
TEST = ROOT / "tests" / "test_ledger_crm6_handoff_mailbox_verify_annotate.py"
RECEIPT = ROOT / "p" / "ledger-crm6-handoff-mailbox-verify-annotate-20260906-01.md"

REGISTRY_BODY = """{
  "schema_version": "commons-lm-gtm-index/v1",
  "kind": "LM_GTM_MAILBOX_BUYER_REPLY_REGISTRY",
  "cash_usd": 0,
  "transport": "NONE",
  "landed": [
    {
      "claim_id": "ledger-crm6-mailbox-buyer-reply-verify-20260905-01",
      "slack_ts": "1788653647.048429",
      "pr": 9237,
      "merge_sha": "515d8c3ff6d3f55f0cd04f457cdcd8b373fd7e06",
      "mechanism": "python3 host/lm_gtm_mailbox_buyer_reply_verify.py SUBJECT",
      "statuses": ["NO_BUYER_REPLY", "BUYER_REPLY_OBSERVED"],
      "verified_human_yes": false
    }
  ],
  "annotate_claim_id": "ledger-crm6-handoff-mailbox-verify-annotate-20260906-01",
  "handoff_flag": "--mailbox-verify"
}
"""

IMPORT_NEEDLE = '''HOST = ROOT / "host" / "lm_gtm_index.py"

import importlib.util

_SPEC = importlib.util.spec_from_file_location("lm_gtm_index", HOST)
assert _SPEC and _SPEC.loader
idx = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(idx)
'''

IMPORT_INSERT = '''HOST = ROOT / "host" / "lm_gtm_index.py"
MAILBOX_HOST = ROOT / "host" / "lm_gtm_mailbox_buyer_reply_verify.py"

import importlib.util

_SPEC = importlib.util.spec_from_file_location("lm_gtm_index", HOST)
assert _SPEC and _SPEC.loader
idx = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(idx)

_MAILBOX_SPEC = importlib.util.spec_from_file_location(
    "lm_gtm_mailbox_buyer_reply_verify", MAILBOX_HOST
)
assert _MAILBOX_SPEC and _MAILBOX_SPEC.loader
mailbox_verify = importlib.util.module_from_spec(_MAILBOX_SPEC)
_MAILBOX_SPEC.loader.exec_module(mailbox_verify)
'''

SIG_NEEDLE = '''def relationship_handoff(
    subject_id: str,
    paths: dict[str, Path] | None = None,
    *,
    include_index_freshness: bool = False,
    as_of: dt.datetime | None = None,
) -> dict[str, Any]:
'''

SIG_INSERT = '''def relationship_handoff(
    subject_id: str,
    paths: dict[str, Path] | None = None,
    *,
    include_index_freshness: bool = False,
    include_mailbox_verify: bool = False,
    as_of: dt.datetime | None = None,
) -> dict[str, Any]:
'''

FRESH_NEEDLE = '''    if include_index_freshness:
        try:
            packet["index_freshness"] = idx.composed_at_freshness(paths, now=as_of)
        except idx.IndexError_:
            packet["index_freshness"] = {
                "status": "UNKNOWN",
                "reason": "Saved INDEX timestamp is unavailable or invalid at as_of.",
            }
    blob = json.dumps(packet, sort_keys=True, ensure_ascii=False)
'''

FRESH_INSERT = '''    if include_index_freshness:
        try:
            packet["index_freshness"] = idx.composed_at_freshness(paths, now=as_of)
        except idx.IndexError_:
            packet["index_freshness"] = {
                "status": "UNKNOWN",
                "reason": "Saved INDEX timestamp is unavailable or invalid at as_of.",
            }
    if include_mailbox_verify:
        try:
            result = mailbox_verify.verify_mailbox_buyer_reply(subject_id, paths)
            if result.get("verified_human_yes") is True:
                raise idx.IndexError_("mailbox verify invent VERIFIED_HUMAN_YES refused")
            result = dict(result)
            result["verified_human_yes"] = False
            packet["mailbox_verify"] = result
        except idx.IndexError_:
            packet["mailbox_verify"] = {
                "status": "UNKNOWN",
                "verified_human_yes": False,
                "mode": "HERMETIC",
                "reason": "Hermetic mailbox fixture unavailable or invalid.",
                "cash_usd": 0,
            }
    blob = json.dumps(packet, sort_keys=True, ensure_ascii=False)
'''

BRIEF_NEEDLE = '''    freshness = packet.get("index_freshness")
    if isinstance(freshness, dict):
        lines.append("index_freshness " + json.dumps(freshness, sort_keys=True))
    for name in FIELD_ORDER:
'''

BRIEF_INSERT = '''    freshness = packet.get("index_freshness")
    if isinstance(freshness, dict):
        lines.append("index_freshness " + json.dumps(freshness, sort_keys=True))
    mailbox = packet.get("mailbox_verify")
    if isinstance(mailbox, dict):
        lines.append("mailbox_verify " + json.dumps(mailbox, sort_keys=True))
    for name in FIELD_ORDER:
'''

PARSER_NEEDLE = '''    parser.add_argument("--index-freshness", action="store_true", help="include saved INDEX age metadata")
    parser.add_argument("--as-of", help="timezone-aware time for optional INDEX freshness")
    return parser
'''

PARSER_INSERT = '''    parser.add_argument("--index-freshness", action="store_true", help="include saved INDEX age metadata")
    parser.add_argument(
        "--mailbox-verify",
        action="store_true",
        help="include hermetic mailbox buyer-reply verify (never invents VERIFIED_HUMAN_YES)",
    )
    parser.add_argument("--as-of", help="timezone-aware time for optional INDEX freshness")
    return parser
'''

MAIN_NEEDLE = '''        packet = relationship_handoff(
            args.subject,
            include_index_freshness=args.index_freshness,
            as_of=idx.parse_time(args.as_of) if args.as_of else None,
        )
'''

MAIN_INSERT = '''        packet = relationship_handoff(
            args.subject,
            include_index_freshness=args.index_freshness,
            include_mailbox_verify=args.mailbox_verify,
            as_of=idx.parse_time(args.as_of) if args.as_of else None,
        )
'''

DOC_NEEDLE = '''  python3 host/lm_gtm_relationship_handoff.py SUBJECT --brief
"""
'''

DOC_INSERT = '''  python3 host/lm_gtm_relationship_handoff.py SUBJECT --brief
  python3 host/lm_gtm_relationship_handoff.py SUBJECT --mailbox-verify
"""
'''

TEST_BODY = r'''#!/usr/bin/env python3
"""Hermetic: optional --mailbox-verify annotate on CRM6 handoff.

CLAIM ledger-crm6-handoff-mailbox-verify-annotate-20260906-01
Never invents VERIFIED_HUMAN_YES. Hands off #8802.
"""
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
HANDOFF_PATH = ROOT / "host" / "lm_gtm_relationship_handoff.py"
REGISTRY = ROOT / "revenue" / "lm_gtm_index" / "mailbox_buyer_reply_registry.json"
RECEIPT = ROOT / "p" / "ledger-crm6-handoff-mailbox-verify-annotate-20260906-01.md"
BILLINGS = "city-of-billings-bid-1421"


def _load_handoff():
    spec = importlib.util.spec_from_file_location("lm_gtm_relationship_handoff_annotate", HANDOFF_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestHandoffMailboxVerifyAnnotate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.handoff = _load_handoff()

    def test_default_handoff_omits_mailbox_verify(self):
        packet = self.handoff.relationship_handoff(BILLINGS)
        self.assertNotIn("mailbox_verify", packet)

    def test_billings_mailbox_verify_is_no_buyer_reply(self):
        packet = self.handoff.relationship_handoff(BILLINGS, include_mailbox_verify=True)
        mv = packet["mailbox_verify"]
        self.assertEqual(mv["status"], "NO_BUYER_REPLY")
        self.assertIs(mv["verified_human_yes"], False)
        self.assertEqual(mv["cash_usd"], 0)
        brief = self.handoff.successor_brief(packet)
        self.assertIn("mailbox_verify", brief)
        self.assertIn("NO_BUYER_REPLY", brief)

    def test_unknown_when_fixture_missing(self):
        with patch.object(
            self.handoff.mailbox_verify,
            "verify_mailbox_buyer_reply",
            side_effect=self.handoff.idx.IndexError_("missing"),
        ):
            packet = self.handoff.relationship_handoff(
                BILLINGS, include_mailbox_verify=True
            )
        self.assertEqual(packet["mailbox_verify"]["status"], "UNKNOWN")
        self.assertIs(packet["mailbox_verify"]["verified_human_yes"], False)
        self.assertIsNotNone(self.handoff.successor_reads_next_action(packet))

    def test_refuses_invented_verified_human_yes(self):
        bad = {
            "status": "BUYER_REPLY_OBSERVED",
            "verified_human_yes": True,
            "cash_usd": 0,
        }
        with patch.object(
            self.handoff.mailbox_verify,
            "verify_mailbox_buyer_reply",
            return_value=bad,
        ):
            packet = self.handoff.relationship_handoff(
                BILLINGS, include_mailbox_verify=True
            )
        # fail-closed to UNKNOWN rather than invent YES
        self.assertEqual(packet["mailbox_verify"]["status"], "UNKNOWN")
        self.assertIs(packet["mailbox_verify"]["verified_human_yes"], False)

    def test_registry_and_receipt(self):
        self.assertTrue(REGISTRY.is_file(), REGISTRY)
        reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(reg["kind"], "LM_GTM_MAILBOX_BUYER_REPLY_REGISTRY")
        self.assertEqual(reg["landed"][0]["claim_id"], "ledger-crm6-mailbox-buyer-reply-verify-20260905-01")
        self.assertEqual(reg["landed"][0]["pr"], 9237)
        self.assertFalse(reg["landed"][0]["verified_human_yes"])
        self.assertTrue(RECEIPT.is_file(), RECEIPT)
        body = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("ledger-crm6-handoff-mailbox-verify-annotate-20260906-01", body)
        self.assertIn("--mailbox-verify", body)
        self.assertIn("#8802", body)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
'''

RECEIPT_BODY = '''# ledger-crm6-handoff-mailbox-verify-annotate-20260906-01

## Claim
CLAIM `ledger-crm6-handoff-mailbox-verify-annotate-20260906-01` · Slack `1788659069.785529`
FORGE write · LEDGER review

## What
Optional handoff annotate mirroring `--index-freshness`:

```sh
python3 host/lm_gtm_relationship_handoff.py city-of-billings-bid-1421 --mailbox-verify
```

Stamps `mailbox_verify` from the landed hermetic pin (#9237). Billings →
`NO_BUYER_REPLY`. `verified_human_yes` is always false; invent attempts fail
closed to UNKNOWN. Missing fixtures become UNKNOWN while the packet remains
usable.

Registry: `revenue/lm_gtm_index/mailbox_buyer_reply_registry.json` records the
landed mailbox claim id / PR / merge SHA.

README documents the flag and that `--send` exits 3 on handoff (no transport).

## Boundary
No second CRM. No Cheri / ack invent. No INDEX remint.
Does not remint mailbox verify #9237 or freshness #9020.
Hands off #8802.
'''


def _must_replace(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"missing anchor for {label}")
    return text.replace(old, new, 1)


def main() -> int:
    handoff = HANDOFF.read_text(encoding="utf-8")
    if "include_mailbox_verify" not in handoff:
        handoff = _must_replace(handoff, IMPORT_NEEDLE, IMPORT_INSERT, "import")
        handoff = _must_replace(handoff, DOC_NEEDLE, DOC_INSERT, "doc")
        handoff = _must_replace(handoff, SIG_NEEDLE, SIG_INSERT, "signature")
        handoff = _must_replace(handoff, FRESH_NEEDLE, FRESH_INSERT, "freshness-block")
        handoff = _must_replace(handoff, BRIEF_NEEDLE, BRIEF_INSERT, "brief")
        handoff = _must_replace(handoff, PARSER_NEEDLE, PARSER_INSERT, "parser")
        handoff = _must_replace(handoff, MAIN_NEEDLE, MAIN_INSERT, "main")
        HANDOFF.write_text(handoff, encoding="utf-8")

    readme = README.read_text(encoding="utf-8")
    if "--mailbox-verify" not in readme:
        marker = (
            "Source record: `ledger-crm6-composed-at-freshness-gate-20260905-01`.\n"
            "Focused check: `python3 -m unittest -v tests/test_ledger_crm6_composed_at_freshness_gate.py`.\n"
        )
        addition = marker + (
            "\n## Mailbox buyer-reply verify (CRM6)\n\n"
            "Hermetic pin (landed `#9237` / `ledger-crm6-mailbox-buyer-reply-verify-20260905-01`):\n\n"
            "```sh\n"
            "python3 host/lm_gtm_mailbox_buyer_reply_verify.py city-of-billings-bid-1421\n"
            "```\n\n"
            "Returns `NO_BUYER_REPLY` or `BUYER_REPLY_OBSERVED` from fixtures only.\n"
            "`verified_human_yes` is always false — never invent `VERIFIED_HUMAN_YES`.\n"
            "Registry: [`mailbox_buyer_reply_registry.json`](./mailbox_buyer_reply_registry.json).\n\n"
            "Optional handoff annotate (mirrors `--index-freshness`):\n\n"
            "```sh\n"
            "python3 host/lm_gtm_relationship_handoff.py city-of-billings-bid-1421 --mailbox-verify\n"
            "```\n\n"
            "Billings stamps `NO_BUYER_REPLY`. Missing fixtures become UNKNOWN while\n"
            "the packet and next action remain usable. Handoff `--send` exits 3\n"
            "(this composer never transports mail).\n\n"
            "Source record: `ledger-crm6-handoff-mailbox-verify-annotate-20260906-01`.\n"
            "Focused check: `python3 -m unittest -v tests/test_ledger_crm6_handoff_mailbox_verify_annotate.py`.\n"
        )
        if marker not in readme:
            raise SystemExit("README freshness marker drifted")
        readme = readme.replace(marker, addition, 1)
        README.write_text(readme, encoding="utf-8")

    REGISTRY.write_text(REGISTRY_BODY, encoding="utf-8")
    TEST.write_text(TEST_BODY, encoding="utf-8")
    RECEIPT.write_text(RECEIPT_BODY, encoding="utf-8")
    print("applied handoff mailbox-verify annotate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
