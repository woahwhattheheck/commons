from __future__ import annotations

from pathlib import Path

CORE_PATH = Path("host/reply_to_revenue_core.py")
TEST_PATH = Path("test_reply_to_revenue_event_identity.py")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


core = CORE_PATH.read_text(encoding="utf-8")
tests = TEST_PATH.read_text(encoding="utf-8")

if "bind every inbound observation to one unique canonical receipt" in core:
    raise SystemExit("provenance repair already present")

exact_keys = '''    def exact_keys(value: dict[str, Any], expected: set[str], where: str) -> None:
        actual = _set(value)
        if actual != expected:
            raise _reply_error(
                f"{where} fields differ: "
                f"missing={_sorted(expected - actual)} extra={_sorted(actual - expected)}"
            )

'''
bounded_text = exact_keys + '''    def bounded_text(
        value: Any,
        where: str,
        *,
        limit: int = 200,
    ) -> str:
        if (
            not _isinstance(value, _str)
            or not value
            or value != value.strip()
            or _len(value) > limit
            or not _all(character.isprintable() for character in value)
        ):
            raise _reply_error(f"{where} must be a bounded nonempty string")
        return value

'''
core = replace_once(core, exact_keys, bounded_text, "bounded text helper")

core = replace_once(
    core,
    '''            if _sha_fullmatch(event["payload_sha256"]) is None:
                raise _reply_error(f"{where}.payload_sha256 is invalid")
            if not _isinstance(event["markers"], _list):
''',
    '''            if _sha_fullmatch(event["payload_sha256"]) is None:
                raise _reply_error(f"{where}.payload_sha256 is invalid")
            bounded_text(event["provider"], f"{where}.provider", limit=100)
            bounded_text(
                event["matched_receipt_id"],
                f"{where}.matched_receipt_id",
                limit=200,
            )
            if not _isinstance(event["markers"], _list):
''',
    "raw provenance validation",
)

old_contact_header = '''    def contact_rows(
        receipts: list[dict[str, Any]],
        inbound: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}
        for receipt in receipts:
            key = receipt["prospect_key"]
            row = grouped.setdefault(
'''
new_contact_header = '''    def contact_rows(
        receipts: list[dict[str, Any]],
        inbound: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}
        by_receipt: dict[str, str] = {}
        for index, receipt in _enumerate(receipts):
            where = f"receipts[{index}]"
            if not _isinstance(receipt, _dict):
                raise _reply_error(f"{where} must be an object")
            receipt_id = bounded_text(
                receipt.get("receipt_id"),
                f"{where}.receipt_id",
                limit=200,
            )
            key = receipt.get("prospect_key")
            if (
                not _isinstance(key, _str)
                or _prospect_fullmatch(key) is None
            ):
                raise _reply_error(f"{where}.prospect_key is invalid")
            if receipt_id in by_receipt:
                raise _reply_error(f"duplicate receipt_id: {receipt_id}")
            by_receipt[receipt_id] = key
            row = grouped.setdefault(
'''
core = replace_once(
    core,
    old_contact_header,
    new_contact_header,
    "contact receipt index",
)

core = replace_once(
    core,
    '''            row["receipt_ids"].append(receipt["receipt_id"])
''',
    '''            row["receipt_ids"].append(receipt_id)
''',
    "canonical receipt row id",
)

old_event_grouping = '''        by_receipt: dict[str, str] = {}
        for receipt in receipts:
            by_receipt[receipt["receipt_id"]] = receipt["prospect_key"]

        for event in inbound:
            key = event["prospect_key"]
            if key not in grouped and event["matched_receipt_id"] in by_receipt:
                key = by_receipt[event["matched_receipt_id"]]
            if key not in grouped:
                grouped[key] = {
                    "prospect_key": key,
                    "organization": key,
                    "hard_dnr": True,
                    "receipt_ids": [],
                    "receipt_paths": [],
                    "cash_usd": 0,
                    "inbound_event_refs": [],
                    "events": [],
                }
            grouped[key]["inbound_event_refs"].append(event["event_ref"])
            grouped[key]["events"].append(event)
'''
new_event_grouping = '''        for index, event in _enumerate(inbound):
            where = f"inbound[{index}]"
            if not _isinstance(event, _dict):
                raise _reply_error(f"{where} must be an object")
            bounded_text(event.get("provider"), f"{where}.provider", limit=100)
            matched_receipt_id = bounded_text(
                event.get("matched_receipt_id"),
                f"{where}.matched_receipt_id",
                limit=200,
            )
            prospect_key = event.get("prospect_key")
            if (
                not _isinstance(prospect_key, _str)
                or _prospect_fullmatch(prospect_key) is None
            ):
                raise _reply_error(f"{where}.prospect_key is invalid")
            canonical_prospect = by_receipt.get(matched_receipt_id)
            if canonical_prospect is None:
                raise _reply_error(
                    f"{where}.matched_receipt_id is unknown: {matched_receipt_id}"
                )
            if prospect_key != canonical_prospect:
                raise _reply_error(
                    f"{where}.prospect_key does not match canonical receipt prospect"
                )
            grouped[canonical_prospect]["inbound_event_refs"].append(
                event["event_ref"]
            )
            grouped[canonical_prospect]["events"].append(event)
'''
core = replace_once(
    core,
    old_event_grouping,
    new_event_grouping,
    "canonical event binding",
)

core = replace_once(
    core,
    '''    "ingest each inbound event_ref once; collision on same ref with a different full observation envelope",
    "automated acknowledgements are not buyer interest",
''',
    '''    "ingest each inbound event_ref once; collision on same ref with a different full observation envelope",
    "bind every inbound observation to one unique canonical receipt for the same prospect",
    "automated acknowledgements are not buyer interest",
''',
    "public provenance limit",
)

new_tests = r'''
    def test_raw_provenance_fields_are_bounded_nonempty_strings(self) -> None:
        core = load_direct_core()
        cases = (
            ("provider", None),
            ("provider", ""),
            ("provider", " padded"),
            ("provider", "x" * 101),
            ("matched_receipt_id", None),
            ("matched_receipt_id", ""),
            ("matched_receipt_id", " padded"),
            ("matched_receipt_id", "x" * 201),
        )
        for field, value in cases:
            with self.subTest(field=field, value=repr(value)):
                event = self._raw_event(
                    "opaque:invalid-provenance-0001",
                    "POSITIVE_SCOPE",
                    markers=["please invoice"],
                )
                event[field] = value
                observations = self._raw_observations([event])
                with tempfile.TemporaryDirectory() as directory:
                    path = self._write_json(
                        directory,
                        "observations.json",
                        observations,
                    )
                    with self.assertRaisesRegex(
                        core.ReplyRevenueError,
                        rf"{field} must be a bounded nonempty string",
                    ):
                        core.load_observations(path)

    def test_unknown_and_cross_prospect_receipts_fail_closed(self) -> None:
        core = load_direct_core()
        first = self._receipt("buyer-one")
        first["receipt_id"] = "receipt-one"
        second = self._receipt("buyer-two")
        second["receipt_id"] = "receipt-two"
        second["organization"] = "Fixture Org Two"
        receipts = [first, second]

        cases = (
            ("missing-receipt", "buyer-one", "matched_receipt_id is unknown"),
            (
                "receipt-two",
                "buyer-one",
                "prospect_key does not match canonical receipt prospect",
            ),
        )
        for matched_receipt_id, prospect_key, error in cases:
            with self.subTest(matched_receipt_id=matched_receipt_id):
                event = self._raw_event(
                    "opaque:receipt-binding-0001",
                    "POSITIVE_SCOPE",
                    markers=["please invoice"],
                )
                event["matched_receipt_id"] = matched_receipt_id
                event["prospect_key"] = prospect_key
                observations = self._raw_observations([event])
                with tempfile.TemporaryDirectory() as directory:
                    loaded = core.load_observations(
                        self._write_json(
                            directory,
                            "observations.json",
                            observations,
                        )
                    )
                with self.assertRaisesRegex(core.ReplyRevenueError, error):
                    core.build_funnel(
                        receipts=copy.deepcopy(receipts),
                        observations=loaded,
                    )

    def test_duplicate_canonical_receipt_ids_fail_closed(self) -> None:
        core = load_direct_core()
        first = self._receipt("buyer-one")
        first["receipt_id"] = "duplicate-receipt"
        second = self._receipt("buyer-two")
        second["receipt_id"] = "duplicate-receipt"
        second["organization"] = "Fixture Org Two"
        event = self._event(
            "opaque:duplicate-receipt-0001",
            "QUESTION",
        )
        event["matched_receipt_id"] = "duplicate-receipt"
        with self.assertRaisesRegex(
            core.ReplyRevenueError,
            "duplicate receipt_id",
        ):
            core.build_funnel(
                receipts=[first, second],
                observations=self._observations([event]),
            )

    def test_preclassified_observations_cannot_bypass_provenance_gate(self) -> None:
        core = load_direct_core()
        cases = (
            ("provider", None),
            ("provider", ""),
            ("matched_receipt_id", None),
            ("matched_receipt_id", "missing-receipt"),
        )
        for field, value in cases:
            with self.subTest(field=field, value=repr(value)):
                event = self._event(
                    "opaque:preclassified-provenance-0001",
                    "POSITIVE_SCOPE",
                )
                event[field] = value
                error = (
                    "matched_receipt_id is unknown"
                    if field == "matched_receipt_id" and value == "missing-receipt"
                    else rf"{field} must be a bounded nonempty string"
                )
                with self.assertRaisesRegex(core.ReplyRevenueError, error):
                    core.build_funnel(
                        receipts=[self._receipt()],
                        observations=self._observations([event]),
                    )
'''
tests = replace_once(
    tests,
    '\n\nif __name__ == "__main__":\n',
    new_tests + '\n\nif __name__ == "__main__":\n',
    "hostile provenance tests",
)

CORE_PATH.write_text(core, encoding="utf-8")
TEST_PATH.write_text(tests, encoding="utf-8")
