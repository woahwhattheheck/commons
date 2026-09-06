#!/usr/bin/env python3
"""One-shot applicator: CRM6 INDEX composed_at FRESH|STALE gate.

CLAIM ledger-crm6-composed-at-freshness-gate-20260905-01
Self-deleted by the oneshot workflow after commit.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / "host" / "lm_gtm_index.py"
HANDOFF = ROOT / "host" / "lm_gtm_relationship_handoff.py"
README = ROOT / "revenue" / "lm_gtm_index" / "README.md"
TEST = ROOT / "tests" / "test_ledger_crm6_composed_at_freshness_gate.py"
RECEIPT = ROOT / "p" / "ledger-crm6-composed-at-freshness-gate-20260905-01.md"

CONTRACT_NEEDLE = '    "sales_without_claim": "illegal; exits 4",
}'
CONTRACT_INSERT = '''    "sales_without_claim": "illegal; exits 4",
    "check_freshness": "python3 host/lm_gtm_index.py freshness",
}'

FUNC_ANCHOR = "def build_parser() -> argparse.ArgumentParser:"
FUNC_BLOCK = '''def read_committed_composed_at(paths: dict[str, Path] | None = None) -> str:
    """composed_at from committed INDEX header, else state.json."""
    paths = paths or default_paths()
    rows = load_jsonl(paths["index"])
    if rows and rows[0].get("kind") == KIND_HEADER:
        stamp = rows[0].get("composed_at")
        if isinstance(stamp, str) and stamp.strip():
            return stamp.strip()
    if paths["state"].exists():
        state = read_object(paths["state"])
        stamp = state.get("composed_at")
        if isinstance(stamp, str) and stamp.strip():
            return stamp.strip()
    raise IndexError_("INDEX/state missing composed_at; re-run write-index")


def composed_at_freshness(
    paths: dict[str, Path] | None = None,
    *,
    now: dt.datetime | None = None,
    composed_at_value: str | None = None,
) -> dict[str, Any]:
    """Executable FRESH|STALE gate matching brief stale_warning (12h)."""
    paths = paths or default_paths()
    composed = composed_at_value or read_committed_composed_at(paths)
    stamped = parse_time(composed)
    instant = now or dt.datetime.now(dt.timezone.utc)
    age = instant - stamped
    age_hours = age.total_seconds() / 3600.0
    threshold_hours = STALE_AFTER.total_seconds() / 3600.0
    stale = age > STALE_AFTER
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "kind": "LM_GTM_COMPOSED_AT_FRESHNESS",
        "status": "STALE" if stale else "FRESH",
        "composed_at": composed,
        "age_hours": round(age_hours, 6),
        "threshold_hours": threshold_hours,
        "canonical_crm": CANONICAL_CRM,
        "cash_usd": 0,
    }
    if stale:
        payload["stale_warning"] = STALE_WARNING
    _assert_no_pii_in_index_blob(json.dumps(payload, sort_keys=True, ensure_ascii=False))
    return payload


'''

PARSER_NEEDLE = '    sub.add_parser("brief")\n'
PARSER_INSERT = '    sub.add_parser("brief")\n    sub.add_parser("freshness")\n'

# main()'s command handlers live inside try: (8-space indent)
MAIN_NEEDLE = '''        if args.command == "brief":
            built = build_index()
            sys.stdout.write(emit_jsonl([brief_header(built=built), *brief_hot_rows()]))
            return 0
'''
MAIN_INSERT = '''        if args.command == "brief":
            built = build_index()
            sys.stdout.write(emit_jsonl([brief_header(built=built), *brief_hot_rows()]))
            return 0
        if args.command == "freshness":
            result = composed_at_freshness()
            print(canonical_text(result), end="")
            return 0 if result["status"] == "FRESH" else 2
'''

HANDOFF_NEEDLE = '''    if owner != "UNSEATED":
        packet["owner"] = owner
    blob = json.dumps(packet, sort_keys=True, ensure_ascii=False)
'''
HANDOFF_INSERT = '''    if owner != "UNSEATED":
        packet["owner"] = owner
    freshness = idx.composed_at_freshness(paths)
    packet["index_freshness"] = {
        "status": freshness["status"],
        "composed_at": freshness["composed_at"],
        "age_hours": freshness["age_hours"],
        "threshold_hours": freshness["threshold_hours"],
    }
    if freshness.get("stale_warning"):
        packet["index_freshness"]["stale_warning"] = freshness["stale_warning"]
    blob = json.dumps(packet, sort_keys=True, ensure_ascii=False)
'''

TEST_BODY = r'''#!/usr/bin/env python3
"""Hermetic: INDEX composed_at FRESH|STALE gate (12h).

CLAIM ledger-crm6-composed-at-freshness-gate-20260905-01
Does not remint ledger-crm6-relationship-handoff-20260904-01. Hands off #8802.
"""
from __future__ import annotations

import datetime as dt
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / "host" / "lm_gtm_index.py"
RECEIPT = ROOT / "p" / "ledger-crm6-composed-at-freshness-gate-20260905-01.md"


def _load_idx():
    spec = importlib.util.spec_from_file_location("lm_gtm_index_freshness", HOST)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestLedgerCrm6ComposedAtFreshnessGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.idx = _load_idx()

    def test_fresh_when_recent(self):
        now = dt.datetime(2026, 9, 5, 20, 0, tzinfo=dt.timezone.utc)
        composed = "2026-09-05T19:00:00Z"
        payload = self.idx.composed_at_freshness(
            composed_at_value=composed, now=now
        )
        self.assertEqual(payload["status"], "FRESH")
        self.assertEqual(payload["kind"], "LM_GTM_COMPOSED_AT_FRESHNESS")
        self.assertEqual(payload["threshold_hours"], 12.0)
        self.assertAlmostEqual(payload["age_hours"], 1.0, places=5)
        self.assertNotIn("stale_warning", payload)
        self.assertEqual(payload["cash_usd"], 0)

    def test_stale_when_over_12h(self):
        now = dt.datetime(2026, 9, 5, 20, 0, tzinfo=dt.timezone.utc)
        composed = "2026-09-05T07:00:00Z"
        payload = self.idx.composed_at_freshness(
            composed_at_value=composed, now=now
        )
        self.assertEqual(payload["status"], "STALE")
        self.assertAlmostEqual(payload["age_hours"], 13.0, places=5)
        self.assertIn("stale_warning", payload)
        self.assertEqual(payload["threshold_hours"], 12.0)

    def test_cli_exit_codes(self):
        now = dt.datetime(2026, 9, 5, 20, 0, tzinfo=dt.timezone.utc)
        fresh = self.idx.composed_at_freshness(
            composed_at_value="2026-09-05T19:00:00Z", now=now
        )
        stale = self.idx.composed_at_freshness(
            composed_at_value="2026-09-05T07:00:00Z", now=now
        )
        self.assertEqual(0 if fresh["status"] == "FRESH" else 2, 0)
        self.assertEqual(0 if stale["status"] == "FRESH" else 2, 2)

    def test_reads_committed_index_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / "revenue" / "lm_gtm_index"
            base.mkdir(parents=True)
            header = {
                "schema_version": self.idx.SCHEMA_VERSION,
                "kind": self.idx.KIND_HEADER,
                "composed_at": "2026-09-05T10:00:00Z",
                "cash_usd": 0,
            }
            (base / "INDEX.jsonl").write_text(
                json.dumps(header, sort_keys=True) + "\n", encoding="utf-8"
            )
            paths = self.idx.default_paths(root)
            now = dt.datetime(2026, 9, 5, 20, 0, tzinfo=dt.timezone.utc)
            stamp = self.idx.read_committed_composed_at(paths)
            self.assertEqual(stamp, "2026-09-05T10:00:00Z")
            payload = self.idx.composed_at_freshness(paths, now=now)
            self.assertEqual(payload["status"], "STALE")
            self.assertEqual(payload["composed_at"], "2026-09-05T10:00:00Z")

    def test_receipt_and_contract(self):
        self.assertTrue(RECEIPT.is_file(), RECEIPT)
        body = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("ledger-crm6-composed-at-freshness-gate-20260905-01", body)
        self.assertIn("freshness", body)
        self.assertIn("#8802", body)
        contract = self.idx.CONTRACT
        self.assertEqual(
            contract.get("check_freshness"),
            "python3 host/lm_gtm_index.py freshness",
        )


if __name__ == "__main__":
    raise SystemExit(unittest.main())
'''

RECEIPT_BODY = '''# ledger-crm6-composed-at-freshness-gate-20260905-01

## Claim
CLAIM `ledger-crm6-composed-at-freshness-gate-20260905-01` · Slack `1788652919.538989`

## What
Executable INDEX `composed_at` FRESH|STALE gate matching the existing 12h
`STALE_AFTER` / README `stale_warning`. Agents get machine JSON plus exit
codes: 0 FRESH, 2 STALE.

```sh
python3 host/lm_gtm_index.py freshness
```

Optional stamp: relationship handoff packets include `index_freshness`.

FORGE owns the write PR; LEDGER reviews as CRM6 truth owner.

Hermetic: `tests/test_ledger_crm6_composed_at_freshness_gate.py`.

## Paths
- `host/lm_gtm_index.py` (`freshness` CLI + `composed_at_freshness`)
- `host/lm_gtm_relationship_handoff.py` (`index_freshness` stamp)
- `revenue/lm_gtm_index/README.md` (claim-line)
- `tests/test_ledger_crm6_composed_at_freshness_gate.py`
- this receipt

## Boundary
Does not remint `ledger-crm6-relationship-handoff-20260904-01`.
No second CRM. No Cheri contact. Hands off #8802.
'''


def _must_replace(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"missing anchor for {label}")
    if new.strip() in text and old != new:
        return text
    return text.replace(old, new, 1)


def main() -> int:
    host = HOST.read_text(encoding="utf-8")
    if "def composed_at_freshness(" not in host:
        host = _must_replace(host, CONTRACT_NEEDLE, CONTRACT_INSERT, "CONTRACT")
        if FUNC_BLOCK not in host:
            host = _must_replace(host, FUNC_ANCHOR, FUNC_BLOCK + FUNC_ANCHOR, "functions")
        host = _must_replace(host, PARSER_NEEDLE, PARSER_INSERT, "parser")
        host = _must_replace(host, MAIN_NEEDLE, MAIN_INSERT, "main")
        HOST.write_text(host, encoding="utf-8")

    handoff = HANDOFF.read_text(encoding="utf-8")
    if '"index_freshness"' not in handoff:
        handoff = _must_replace(handoff, HANDOFF_NEEDLE, HANDOFF_INSERT, "handoff")
        HANDOFF.write_text(handoff, encoding="utf-8")

    readme = README.read_text(encoding="utf-8")
    if "lm_gtm_index.py freshness" not in readme:
        insert_after = (
            "Floor command is now `python3 host/lm_gtm_index.py brief` — compact JSONL\n"
            "(header + HOT rows). Header includes `occupied` (live rows whose owner\n"
            "is not UNSEATED), `composed_at`, `mailbox` only while still\n"
            "`NEEDS_OWNER_MAILBOX`, and a one-line `stale_warning` when the overlay\n"
            "is older than 12h."
        )
        addition = (
            insert_after
            + "\n\n"
            + "Executable freshness gate (same 12h threshold):\n"
            + "`python3 host/lm_gtm_index.py freshness` prints JSON with\n"
            + "`status` FRESH|STALE, `age_hours`, and `threshold_hours`; exit 0\n"
            + "when FRESH and exit 2 when STALE."
        )
        if insert_after not in readme:
            raise SystemExit("README floor paragraph drifted")
        readme = readme.replace(insert_after, addition, 1)
        block = "python3 host/lm_gtm_index.py brief\n"
        if "python3 host/lm_gtm_index.py freshness\n" not in readme:
            readme = readme.replace(
                block,
                block + "python3 host/lm_gtm_index.py freshness\n",
                1,
            )
        README.write_text(readme, encoding="utf-8")

    TEST.write_text(TEST_BODY, encoding="utf-8")
    RECEIPT.write_text(RECEIPT_BODY, encoding="utf-8")
    print("applied CRM6 composed_at freshness gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
