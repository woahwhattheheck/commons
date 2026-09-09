#!/usr/bin/env python3
"""Synthetic parser and real-file regressions; no live commercial data is used."""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from host import human_outcomes as outcomes


NON_OBJECTS = (None, [], [1], True, False, 0, 1, 1.5, "", "text")
NON_ARRAYS = ({}, {"unexpected": 1}, True, False, 0, 1, 1.5, "", "text")
COLLECTIONS = ("offers", "does_not_replace", "fulfillment_modules_remain", "gate.open")


def pack_fixture():
    """A synthetic complete pack, not a claim about current customer readiness."""
    return {
        "kind": "HUMAN_OUTCOMES_PACK",
        "mandate": "demon-human-outcomes-revenue-20260825-01",
        "demand": "UNKNOWN",
        "collectable_usd": "NOT_LANDED",
        "collected_cash_usd": 0,
        "no_checkout": True,
        "no_auth": True,
        "no_gate": True,
        "no_buyer_fiction": True,
        "founder_sent_contact": True,
        "human_value_not_proof_worship": True,
        "does_not_replace": ["white-box-gguf-pilot-30d", "gguf-diagnostic-10d-12k"],
        "fulfillment_modules_remain": ["SUBZERO", "compression", "DIO"],
        "white_box_upgrade": {"offer_id": "white-box-gguf-pilot-30d"},
        "taking_state": "CARRIER_ONLY",
        "xyz_required": True,
        "remeasurement_owner": "Codex / Grok Build",
        "titan": "NOT_WRITTEN",
        "payment_collection": "NOT_PROVIDED_ON_THIS_PAGE",
        "offers": [
            {"id": name, "fixed_amount": amount}
            for name, amount in outcomes.REQUIRED_PRICES.items()
        ],
        "gate": {
            "pack": "READY", "owner_private": "NEEDS_OWNER_PRIVATE",
            "buyer": "NEEDS_BUYER", "collected_cash": "NOT_LANDED",
            "collected_cash_usd": 0,
            "open": ["NEEDS_OWNER_PRIVATE", "NEEDS_BUYER", "NOT_LANDED"],
            "ready_does_not_mean_cash": True,
        },
    }


def set_collection(pack, name, value):
    if name == "gate.open":
        pack.setdefault("gate", {})["open"] = value
    else:
        pack[name] = value


def write_json(root, relative, value):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def make_tree(root):
    for rel in (*outcomes.SEARCH_SPACE, *outcomes.CALIBRATION):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Synthetic fixture; no checkout; no auth; no gate.\n", encoding="utf-8")
    (root / outcomes.DEFAULT_CARD).write_text("Human outcomes leftover\n", encoding="utf-8")
    (root / "revenue/human_outcomes/fulfillment.md").write_text(
        "Founder-sent contact\nRefund\n", encoding="utf-8"
    )
    (root / outcomes.DOOR).write_text(
        "ho-issue-to-pr HUMAN OUTCOMES INTEREST\n", encoding="utf-8"
    )
    write_json(root, outcomes.DEFAULT_OFFERS, pack_fixture())
    write_json(root, outcomes.COMMERCIAL_PATH, {
        "offer": {"offer_id": "white-box-gguf-pilot-30d", "fee": {"fixed_amount": 30000}}
    })
    write_json(root, outcomes.PAYMENT_PACK, {
        "offer": {"offer_id": "gguf-diagnostic-10d-12k", "fixed_amount": 12000}
    })


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


class HumanOutcomesInputShapeTests(unittest.TestCase):
    def test_commercial_rejects_non_objects(self):
        for value in NON_OBJECTS:
            with self.subTest(value=value):
                self.assertEqual(outcomes.measure_commercial(json.dumps(value)), {
                    "error": "commercial is not an object", "offer_id": "", "fixed_amount": 0
                })

    def test_payment_rejects_non_objects(self):
        for value in NON_OBJECTS:
            with self.subTest(value=value):
                self.assertEqual(outcomes.measure_payment_pack(json.dumps(value)), {
                    "error": "payment pack is not an object", "offer_id": "", "fixed_amount": 0
                })

    def test_offer_pack_root_error_is_unchanged(self):
        for value in NON_OBJECTS:
            with self.subTest(value=value):
                self.assertEqual(outcomes.load_pack(json.dumps(value)), {"error": "offers is not an object"})

    def test_invalid_json_diagnostics_are_unchanged(self):
        for fn, label in ((outcomes.load_pack, "offers"),
                          (outcomes.measure_commercial, "commercial"),
                          (outcomes.measure_payment_pack, "payment pack")):
            for text in ("{", "[", "not JSON"):
                with self.subTest(parser=fn.__name__, text=text):
                    self.assertEqual(fn(text)["error"], label + " is not JSON")

    def test_offers_rejects_non_arrays(self):
        self.check_collection("offers")

    def test_replacements_rejects_non_arrays(self):
        self.check_collection("does_not_replace")

    def test_modules_rejects_non_arrays(self):
        self.check_collection("fulfillment_modules_remain")

    def test_gate_open_rejects_non_arrays(self):
        self.check_collection("gate.open")

    def check_collection(self, name):
        for value in NON_ARRAYS:
            with self.subTest(field=name, value=value):
                pack = pack_fixture()
                set_collection(pack, name, value)
                self.assertEqual(outcomes.load_pack(json.dumps(pack)), {"error": name + " is not an array"})

    def test_absent_and_null_collections_keep_empty_defaults(self):
        self.assertEqual(outcomes.load_pack("{}")["offer_ids"], [])
        pack = {"gate": {}}
        for field in COLLECTIONS:
            set_collection(pack, field, None)
        null_pack = outcomes.load_pack(json.dumps(pack))
        absent_pack = outcomes.load_pack("{}")
        for field in ("offers", "offer_ids", "does_not_replace", "fulfillment_modules_remain", "gate_open"):
            self.assertEqual(null_pack[field], absent_pack[field])
            self.assertEqual(null_pack[field], [])

    def test_array_normalization_is_unchanged(self):
        pack = pack_fixture()
        pack["offers"].extend([None, "ignored", 0, {}, {"id": ""}])
        pack["does_not_replace"] = [" a ", None, "", 3]
        pack["gate"]["open"] = [" needs_buyer ", None, "", "NOT_LANDED"]
        result = outcomes.load_pack(json.dumps(pack))
        self.assertEqual(result["offer_prices"], outcomes.REQUIRED_PRICES)
        self.assertEqual(result["does_not_replace"], ["a", "3"])
        self.assertEqual(result["gate_open"], ["NEEDS_BUYER", "NOT_LANDED"])

    def test_empty_input_and_empty_object_defaults_are_unchanged(self):
        for fn in (outcomes.load_pack, outcomes.measure_commercial, outcomes.measure_payment_pack):
            for text in (None, ""):
                with self.subTest(parser=fn.__name__, text=text):
                    self.assertEqual(fn(text), fn("{}"))
        self.assertEqual(outcomes.measure_commercial("{}"), {"error": "", "offer_id": "", "fixed_amount": None})
        self.assertEqual(outcomes.measure_payment_pack("{}"), {"error": "", "offer_id": "", "fixed_amount": None})

    def test_valid_offer_measurements_are_unchanged(self):
        self.assertEqual(outcomes.measure_commercial(json.dumps({
            "offer": {"offer_id": "example", "fee": {"fixed_amount": 123}}
        })), {"error": "", "offer_id": "example", "fixed_amount": 123})
        self.assertEqual(outcomes.measure_payment_pack(json.dumps({
            "offer": {"offer_id": "example", "fixed_amount": 456}
        })), {"error": "", "offer_id": "example", "fixed_amount": 456})

    def test_nested_offer_fallbacks_are_unchanged(self):
        for value in NON_OBJECTS:
            with self.subTest(value=value):
                for fn in (outcomes.measure_commercial, outcomes.measure_payment_pack):
                    self.assertEqual(fn(json.dumps({"offer": value})), {
                        "error": "", "offer_id": "", "fixed_amount": None
                    })

    def test_complete_synthetic_tree_still_integrates_without_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_tree(root)
            before = snapshot(root)
            row = outcomes.measure_root(str(root))
            self.assertEqual(outcomes.classify(row)["state"], "INTEGRATED")
            self.assertEqual(row["collected_cash_usd"], 0)
            self.assertEqual(snapshot(root), before)

    def test_bad_file_roots_fail_closed_without_writes(self):
        for rel in (outcomes.DEFAULT_OFFERS, outcomes.COMMERCIAL_PATH, outcomes.PAYMENT_PACK):
            for value in NON_OBJECTS:
                with self.subTest(path=rel, value=value), tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    make_tree(root)
                    write_json(root, rel, value)
                    before = snapshot(root)
                    self.assertEqual(outcomes.classify(outcomes.measure_root(str(root)))["state"], "NOT_LANDED")
                    self.assertEqual(snapshot(root), before)

    def test_bad_pack_collections_fail_closed_without_writes(self):
        for field in COLLECTIONS:
            for value in NON_ARRAYS:
                with self.subTest(field=field, value=value), tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    make_tree(root)
                    pack = pack_fixture()
                    set_collection(pack, field, value)
                    write_json(root, outcomes.DEFAULT_OFFERS, pack)
                    before = snapshot(root)
                    self.assertEqual(outcomes.classify(outcomes.measure_root(str(root)))["state"], "NOT_LANDED")
                    self.assertEqual(snapshot(root), before)

    def test_mapping_keys_cannot_masquerade_as_required_arrays(self):
        for field in ("does_not_replace", "fulfillment_modules_remain", "gate.open"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                make_tree(root)
                pack = pack_fixture()
                names = pack["gate"]["open"] if field == "gate.open" else pack[field]
                set_collection(pack, field, {name: False for name in names})
                write_json(root, outcomes.DEFAULT_OFFERS, pack)
                before = snapshot(root)
                self.assertEqual(outcomes.classify(outcomes.measure_root(str(root)))["state"], "NOT_LANDED")
                self.assertEqual(snapshot(root), before)

    def test_cli_returns_diagnostic_json_for_bad_file_shapes(self):
        for rel, value in ((outcomes.COMMERCIAL_PATH, []),
                           (outcomes.PAYMENT_PACK, None),
                           (outcomes.DEFAULT_OFFERS, {"offers": True})):
            with self.subTest(path=rel), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                make_tree(root)
                write_json(root, rel, value)
                before = snapshot(root)
                result = subprocess.run(
                    [sys.executable, str(Path(outcomes.__file__).resolve()), "--root", str(root)],
                    capture_output=True, text=True, timeout=10, check=False,
                )
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                payload = json.loads(result.stdout)
                self.assertEqual(payload["verdict"]["state"], "NOT_LANDED")
                self.assertEqual(snapshot(root), before)

    def test_existing_self_test_still_passes(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(outcomes.main(["--self-test"]), 0)
        self.assertEqual(output.getvalue().strip(), "ok")


if __name__ == "__main__":
    unittest.main()
