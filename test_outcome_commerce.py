#!/usr/bin/env python3
"""Dependency-free contracts for the Commons Outcome Commerce bridge."""
from __future__ import annotations

import copy
from datetime import datetime
from decimal import Decimal
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parent
COMMERCE = ROOT / "revenue" / "outcome_commerce"
EXAMPLES = COMMERCE / "examples"
FROZEN_EIGHT_SHA256 = "bea09853202464ee37b4540de30c13bc56252c9967c871d3a786e27e7dcc8469"
FROZEN_SOURCE_ADAPTERS_SHA256 = "b2593f52e40c6ab4902660a00dce2304f1767ce3a6a5ee2c963d0dd7a3cd4e67"
RECORDED_STRIPE_SKUS = (
    {
        "id": "sku-tip-20260826",
        "path": "land/sku-tip-20260826.md",
        "blob_sha": "7e94f42e9a92e166f614916d63712403f6fc77f7",
        "kind": "fixed",
        "amount_field": "amount",
        "amount": "5.00",
        "url": "https://donate.stripe.com/fZucN40Ch9fj7mxgJs43S08",
        "markers": (
            "price: $5 USD one-time",
            "status: ACTIVE_CHARGEABLE",
            "provider: stripe",
            "link_active: true",
            "account_charges_enabled: true",
            "account_payouts_enabled: true",
            "checkout: `https://donate.stripe.com/fZucN40Ch9fj7mxgJs43S08`",
        ),
    },
    {
        "id": "sku-seat-20260826",
        "path": "land/sku-seat-20260826.md",
        "blob_sha": "235c94284c14c179388b5e53b4b9d0f6a8a0dd7d",
        "kind": "subscription",
        "amount_field": "amount",
        "amount": "5.00",
        "url": "https://buy.stripe.com/3cIeVc5WB1MRgX7al443S03",
        "markers": (
            "price: $5 USD / month",
            "status: ACTIVE_CHARGEABLE",
            "provider: stripe",
            "link_active: true",
            "account_charges_enabled: true",
            "account_payouts_enabled: true",
            "checkout: `https://buy.stripe.com/3cIeVc5WB1MRgX7al443S03`",
        ),
    },
    {
        "id": "sku-unlock-20260826",
        "path": "land/sku-unlock-20260826.md",
        "blob_sha": "258734957efc727f46f6315804b6034487e98896",
        "kind": "fixed",
        "amount_field": "amount",
        "amount": "5.00",
        "url": "https://buy.stripe.com/3cIbJ0ckZgHL36h8cW43S04",
        "markers": (
            "price: $5 USD one-time",
            "status: ACTIVE_CHARGEABLE",
            "provider: stripe",
            "link_active: true",
            "account_charges_enabled: true",
            "account_payouts_enabled: true",
            "checkout: `https://buy.stripe.com/3cIbJ0ckZgHL36h8cW43S04`",
        ),
    },
    {
        "id": "sku-monthly-tip-20260826",
        "path": "land/sku-monthly-tip-20260826.md",
        "blob_sha": "b2c54753a82683a70831588366e35114ad644a65",
        "kind": "subscription",
        "amount_field": "amount",
        "amount": "3.00",
        "url": "https://buy.stripe.com/bJe28qacR4Z3gX7bp843S05",
        "markers": (
            "price: $3 USD / month",
            "status: ACTIVE_CHARGEABLE",
            "provider: stripe",
            "link_active: true",
            "account_charges_enabled: true",
            "account_payouts_enabled: true",
            "checkout: `https://buy.stripe.com/bJe28qacR4Z3gX7bp843S05`",
        ),
    },
    {
        "id": "sku-boost-20260826",
        "path": "land/sku-boost-20260826.md",
        "blob_sha": "4fd23e7a10e90a5c988f3581d77e83b86e212884",
        "kind": "subscription",
        "amount_field": "amount",
        "amount": "4.99",
        "url": "https://buy.stripe.com/3cIfZgacRezDfT39h043S06",
        "markers": (
            "price: $4.99 USD / month",
            "status: ACTIVE_CHARGEABLE",
            "provider: stripe",
            "link_active: true",
            "account_charges_enabled: true",
            "account_payouts_enabled: true",
            "checkout: `https://buy.stripe.com/3cIfZgacRezDfT39h043S06`",
        ),
    },
    {
        "id": "sku-whitebox-hour-20260826",
        "path": "land/sku-whitebox-hour-20260826.md",
        "blob_sha": "62625136a9e5abfe77d9e7afa59e8ee67571b33e",
        "kind": "usage",
        "amount_field": "unit_amount",
        "amount": "250.00",
        "url": "https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07",
        "markers": (
            "MARKET PROPOSAL: $250 USD / hour",
            "status: ACTIVE_CHARGEABLE",
            "provider: stripe",
            "link_active: true",
            "account_charges_enabled: true",
            "account_payouts_enabled: true",
            "checkout: `https://buy.stripe.com/8x27sK2Kp3UZ9uF2SC43S07`",
        ),
    },
    {
        "id": "sku-muhlnickel-titan-20260826",
        "path": "land/sku-muhlnickel-titan-20260826.md",
        "blob_sha": "fa4ef433b0b233bb3ddc633c1828957e5d75e453",
        "kind": "fixed",
        "amount_field": "amount",
        "amount": "45000.00",
        "url": "https://buy.stripe.com/7sYbJ02Kpcrv9uF0Ku43S09",
        "markers": (
            "MARKET PROPOSAL: $45,000 fixed-scope build",
            "status: ACTIVE_CHARGEABLE",
            "provider: stripe",
            "link_active: true",
            "account_charges_enabled: true",
            "account_payouts_enabled: true",
            "checkout: `https://buy.stripe.com/7sYbJ02Kpcrv9uF0Ku43S09`",
        ),
    },
)

_SPEC = importlib.util.spec_from_file_location(
    "commons_outcome_commerce", ROOT / "host" / "outcome_commerce.py"
)
outcome_commerce = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(outcome_commerce)


class SchemaError(AssertionError):
    """A value does not satisfy the local JSON Schema subset."""


class MiniSchemaValidator:
    """Validate the draft-2020-12 keywords used by this commerce packet."""

    def __init__(self, schema_dir: Path):
        self.schema_dir = schema_dir
        self.cache: dict[Path, object] = {}

    def load(self, name: str):
        path = (self.schema_dir / name).resolve()
        if path not in self.cache:
            self.cache[path] = read_json(path)
        return self.cache[path], path

    def validate_file(self, value, name: str) -> None:
        schema, path = self.load(name)
        self._validate(value, schema, schema, path, "$")

    def _resolve(self, ref: str, root, schema_path: Path):
        file_part, marker, fragment = ref.partition("#")
        if file_part:
            next_path = (schema_path.parent / file_part).resolve()
            if next_path not in self.cache:
                self.cache[next_path] = read_json(next_path)
            next_root = self.cache[next_path]
        else:
            next_path, next_root = schema_path, root
        node = next_root
        if marker and fragment:
            if not fragment.startswith("/"):
                raise SchemaError("unsupported ref fragment %r" % fragment)
            for raw in fragment[1:].split("/"):
                key = raw.replace("~1", "/").replace("~0", "~")
                node = node[key]
        return node, next_root, next_path

    def _matches(self, value, schema, root, schema_path: Path, at: str) -> bool:
        try:
            self._validate(value, schema, root, schema_path, at)
            return True
        except SchemaError:
            return False

    @staticmethod
    def _type_ok(value, wanted: str) -> bool:
        checks = {
            "null": lambda item: item is None,
            "object": lambda item: isinstance(item, dict),
            "array": lambda item: isinstance(item, list),
            "string": lambda item: isinstance(item, str),
            "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
            "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
            "boolean": lambda item: isinstance(item, bool),
        }
        if wanted not in checks:
            raise SchemaError("validator does not implement type %r" % wanted)
        return checks[wanted](value)

    def _validate(self, value, schema, root, schema_path: Path, at: str) -> None:
        if schema is True:
            return
        if schema is False:
            raise SchemaError("%s rejected by false schema" % at)
        if not isinstance(schema, dict):
            raise SchemaError("%s has a non-object schema" % at)

        if "$ref" in schema:
            node, next_root, next_path = self._resolve(schema["$ref"], root, schema_path)
            self._validate(value, node, next_root, next_path, at)
            return
        for part in schema.get("allOf", []):
            self._validate(value, part, root, schema_path, at)
        if "anyOf" in schema and not any(
            self._matches(value, part, root, schema_path, at) for part in schema["anyOf"]
        ):
            raise SchemaError("%s matches no anyOf branch" % at)
        if "oneOf" in schema:
            hits = sum(
                self._matches(value, part, root, schema_path, at)
                for part in schema["oneOf"]
            )
            if hits != 1:
                raise SchemaError("%s matches %d oneOf branches" % (at, hits))
        if "if" in schema:
            branch = (
                "then"
                if self._matches(value, schema["if"], root, schema_path, at)
                else "else"
            )
            if branch in schema:
                self._validate(value, schema[branch], root, schema_path, at)
        if "const" in schema and value != schema["const"]:
            raise SchemaError("%s is not const %r" % (at, schema["const"]))
        if "enum" in schema and value not in schema["enum"]:
            raise SchemaError("%s is not in enum" % at)

        wanted = schema.get("type")
        if wanted is not None:
            choices = wanted if isinstance(wanted, list) else [wanted]
            if not any(self._type_ok(value, item) for item in choices):
                raise SchemaError("%s has wrong type; need %r" % (at, wanted))

        if isinstance(value, str):
            if len(value) < schema.get("minLength", 0):
                raise SchemaError("%s is too short" % at)
            if "maxLength" in schema and len(value) > schema["maxLength"]:
                raise SchemaError("%s is too long" % at)
            if "pattern" in schema and re.search(schema["pattern"], value) is None:
                raise SchemaError("%s does not match %s" % (at, schema["pattern"]))
            if schema.get("format") == "date-time":
                try:
                    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError as exc:
                    raise SchemaError("%s is not date-time" % at) from exc
                if parsed.tzinfo is None or parsed.utcoffset() is None:
                    raise SchemaError("%s date-time has no timezone" % at)

        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in schema and value < schema["minimum"]:
                raise SchemaError("%s is below minimum" % at)
            if "maximum" in schema and value > schema["maximum"]:
                raise SchemaError("%s is above maximum" % at)

        if isinstance(value, list):
            if len(value) < schema.get("minItems", 0):
                raise SchemaError("%s has too few items" % at)
            if schema.get("uniqueItems"):
                frozen = [canonical(item) for item in value]
                if len(frozen) != len(set(frozen)):
                    raise SchemaError("%s has duplicate items" % at)
            if "items" in schema:
                for index, item in enumerate(value):
                    self._validate(
                        item,
                        schema["items"],
                        root,
                        schema_path,
                        "%s[%d]" % (at, index),
                    )

        if isinstance(value, dict):
            for key in schema.get("required", []):
                if key not in value:
                    raise SchemaError("%s missing %s" % (at, key))
            properties = schema.get("properties", {})
            extra = sorted(set(value) - set(properties))
            additional = schema.get("additionalProperties", True)
            if additional is False and extra:
                raise SchemaError("%s has extra keys %r" % (at, extra))
            if isinstance(additional, dict):
                for key in extra:
                    self._validate(
                        value[key], additional, root, schema_path, "%s.%s" % (at, key)
                    )
            for key, child_schema in properties.items():
                if key in value:
                    self._validate(
                        value[key], child_schema, root, schema_path, "%s.%s" % (at, key)
                    )


def read_json(path: Path):
    def reject_float(raw: str):
        raise AssertionError("JSON decimal must be a string, not float %s in %s" % (raw, path))

    with path.open(encoding="utf-8") as handle:
        return json.load(handle, parse_float=reject_float)


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def git_hash_object(path: Path) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(path)], cwd=ROOT, text=True
    ).strip()


def resolve_pointer(value, pointer: str):
    if pointer == "":
        return value
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise AssertionError("invalid JSON Pointer %r" % pointer)
    node = value
    for raw in pointer.split("/")[1:]:
        part = raw.replace("~1", "/").replace("~0", "~")
        node = node[int(part)] if isinstance(node, list) else node[part]
    return node


class OutcomeCommerceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.validator = MiniSchemaValidator(COMMERCE)
        cls.catalog = read_json(COMMERCE / "catalog.json")
        cls.hybrid = read_json(EXAMPLES / "hybrid_catalog.json")
        cls.events = read_json(EXAMPLES / "hybrid_events.json")["events"]
        cls.commercial_events = read_json(EXAMPLES / "commercial_events.json")["events"]

    def test_json_and_schema_structure_without_external_packages(self) -> None:
        schema_names = (
            "catalog.schema.json",
            "event.schema.json",
            "metering-event.schema.json",
            "outcome-contract.schema.json",
            "projection.schema.json",
            "statement.schema.json",
        )
        for name in schema_names:
            schema = read_json(COMMERCE / name)
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertTrue(schema["$id"].endswith("/revenue/outcome_commerce/" + name))
            self.assertEqual(schema["type"], "object")
            self.assertIsInstance(schema["required"], list)

        for path in sorted(COMMERCE.rglob("*.json")):
            read_json(path)

        self.validator.validate_file(self.catalog, "catalog.schema.json")
        self.validator.validate_file(self.hybrid, "catalog.schema.json")
        for event in self.events:
            self.validator.validate_file(event, "metering-event.schema.json")
        for event in self.commercial_events:
            self.validator.validate_file(event, "event.schema.json")

        quoted = outcome_commerce.quote(self.hybrid, "synthetic-hybrid-agent", {})
        settled = outcome_commerce.statement(self.hybrid, self.events)
        projected = outcome_commerce.commercial_projection(self.commercial_events)
        self.validator.validate_file(quoted, "statement.schema.json")
        self.validator.validate_file(settled, "statement.schema.json")
        self.validator.validate_file(projected, "projection.schema.json")

    def test_catalog_source_references_resolve_when_present(self) -> None:
        checked = []
        for catalog in (self.catalog, self.hybrid):
            for listing in catalog["listings"]:
                source = listing.get("source")
                if not source:
                    continue
                path = ROOT / source["path"]
                if not path.is_file():
                    continue
                node = resolve_pointer(read_json(path), source["pointer"])
                expected = source.get("offer_id")
                if expected:
                    self.assertIsInstance(node, dict)
                    actual = node.get("id", node.get("offer_id"))
                    self.assertEqual(actual, expected, source["path"])
                checked.append(source["path"])
        self.assertIn(
            "revenue/outcome_commerce/examples/synthetic_source.json",
            checked,
            "the always-present synthetic source must exercise pointer resolution",
        )

    def test_exact_hybrid_quote_and_statement_math(self) -> None:
        metrics = {
            "platform_fee": Decimal("1"),
            "subscription_cycle": Decimal("2"),
            "action_units": Decimal("1350"),
            "outcomes": Decimal("4"),
            "milestone_delivery": Decimal("1"),
            "marketplace_take": Decimal("1000"),
            "license_fee": Decimal("1"),
            "sponsor_units": Decimal("3"),
        }
        quoted = outcome_commerce.quote(self.hybrid, "synthetic-hybrid-agent", metrics)
        amounts = {row["component_id"]: row["amount"] for row in quoted["line_items"]}
        self.assertEqual(
            amounts,
            {
                "platform_fee": "99.00",
                "subscription_cycle": "98.00",
                "action_units": "35.00",
                "outcomes": "200.00",
                "milestone_delivery": "1000.00",
                "marketplace_take": "50.00",
                "license_fee": "2000.00",
                "sponsor_units": "75.00",
            },
        )
        self.assertEqual(quoted["gross_amount"], "3557.00")
        self.assertEqual(quoted["net_amount"], "3557.00")

        statement = outcome_commerce.statement(self.hybrid, self.events)
        self.assertEqual(statement["gross_amount"], "3477.00")
        self.assertEqual(statement["credits_applied"], "500.00")
        self.assertEqual(statement["net_amount"], "2977.00")
        self.assertEqual(statement["source_event_count"], 11)
        self.assertEqual(statement["unique_event_count"], 10)
        self.assertEqual(statement["reversed_event_ids"], ["synthetic-sponsor-0001"])

    def test_exact_duplicate_dedupes_and_conflicting_duplicate_fails(self) -> None:
        statement = outcome_commerce.statement(self.hybrid, self.events)
        self.assertEqual(statement["deduped_event_ids"], ["synthetic-usage-0001"])
        usage = next(
            row
            for row in statement["listings"][0]["line_items"]
            if row["component_id"] == "action_units"
        )
        self.assertEqual(usage["amount"], "30.00", "the exact duplicate must not bill twice")

        original = next(row for row in self.events if row["event_id"] == "synthetic-usage-0001")
        conflict = copy.deepcopy(original)
        conflict["quantity"] = "1301"
        with self.assertRaisesRegex(
            outcome_commerce.CommerceError, "conflicting duplicate event_id"
        ):
            outcome_commerce.statement(self.hybrid, [original, conflict])

    def test_projection_is_byte_identical_under_event_reordering(self) -> None:
        forward = outcome_commerce.statement(self.hybrid, self.events)
        reverse = outcome_commerce.statement(self.hybrid, list(reversed(self.events)))
        self.assertEqual(canonical(forward), canonical(reverse))

    def _outcome_event(self, ident: str, event_type: str, state: str, quantity="1"):
        row = {
            "schema_version": "outcome-commerce-event/v1",
            "event_id": ident,
            "idempotency_key": "effect-" + ident,
            "correlation_id": "synthetic-outcome-correlation-0001",
            "listing_id": "synthetic-hybrid-agent",
            "component_id": "outcomes",
            "event_type": event_type,
            "state": state,
            "occurred_at": "2026-08-26T13:00:00Z",
            "quantity": quantity,
        }
        if event_type == "OUTCOME_VERIFIED":
            row["evidence"] = [{
                "uri": "revenue/outcome_commerce/examples/synthetic_source.json",
                "sha256": "0" * 64,
            }]
        return row

    def test_candidate_failed_and_escalated_outcomes_bill_zero(self) -> None:
        events = [
            self._outcome_event("candidate-outcome-0001", "OUTCOME_CANDIDATE", "RECORDED"),
            self._outcome_event("failed-outcome-000001", "OUTCOME_FAILED", "RECORDED"),
            self._outcome_event("escalated-outcome-001", "OUTCOME_ESCALATED", "RECORDED"),
        ]
        statement = outcome_commerce.statement(self.hybrid, events)
        self.assertEqual(statement["gross_amount"], "0.00")
        self.assertEqual(statement["net_amount"], "0.00")
        self.assertEqual(
            statement["nonchargeable_event_ids"],
            sorted(row["event_id"] for row in events),
        )

    def test_verified_outcome_bills_once(self) -> None:
        verified = self._outcome_event(
            "verified-outcome-0001", "OUTCOME_VERIFIED", "VERIFIED"
        )
        statement = outcome_commerce.statement(self.hybrid, [verified, copy.deepcopy(verified)])
        self.assertEqual(statement["gross_amount"], "50.00")
        self.assertEqual(statement["net_amount"], "50.00")
        self.assertEqual(statement["unique_event_count"], 1)
        self.assertEqual(statement["deduped_event_ids"], ["verified-outcome-0001"])

    def test_reopen_reversal_applies_the_exact_outcome_credit(self) -> None:
        verified = self._outcome_event(
            "reopened-outcome-0001", "OUTCOME_VERIFIED", "VERIFIED", quantity="2"
        )
        before = outcome_commerce.statement(self.hybrid, [verified])
        reversal = {
            "schema_version": "outcome-commerce-event/v1",
            "event_id": "reopen-reversal-0001",
            "idempotency_key": "effect-reopen-reversal-0001",
            "correlation_id": "synthetic-outcome-correlation-0001",
            "listing_id": "synthetic-hybrid-agent",
            "event_type": "ADJUSTMENT",
            "state": "REVERSED",
            "occurred_at": "2026-08-26T13:01:00Z",
            "reverses_event_id": verified["event_id"],
        }
        after = outcome_commerce.statement(self.hybrid, [verified, reversal])
        self.assertEqual(before["net_amount"], "100.00")
        self.assertEqual(after["net_amount"], "0.00")
        self.assertEqual(
            Decimal(before["net_amount"]) - Decimal(after["net_amount"]),
            Decimal("100.00"),
        )
        self.assertEqual(after["reversed_event_ids"], [verified["event_id"]])

    def test_mixed_currency_statement_fails(self) -> None:
        catalog = copy.deepcopy(self.hybrid)
        euro = copy.deepcopy(catalog["listings"][0])
        euro["id"] = "synthetic-hybrid-agent-eur"
        euro["pricing"]["currency"] = "EUR"
        catalog["listings"].append(euro)
        usd_event = copy.deepcopy(self.events[0])
        eur_event = copy.deepcopy(self.events[0])
        eur_event["event_id"] = "synthetic-euro-fixed-0001"
        eur_event["idempotency_key"] = "synthetic-effect-euro-fixed-0001"
        eur_event["listing_id"] = euro["id"]
        with self.assertRaisesRegex(outcome_commerce.CommerceError, "mixed currencies"):
            outcome_commerce.statement(catalog, [usd_event, eur_event])

    def test_commercial_projection_reconciles_unknown_effect_without_retry(self) -> None:
        projection = outcome_commerce.commercial_projection(self.commercial_events)
        job = projection["jobs"][0]
        self.assertEqual(job["current_state"], "BANK_AVAILABLE")
        delivery = next(row for row in job["effects"] if row["idempotency_key"] == "effect-delivery-0001")
        self.assertEqual(delivery["status"], "CONFIRMED")
        self.assertEqual(delivery["latest_event_id"], "evt-deliver-reconcile-0001")
        self.assertIs(job["payment_truth"]["cash_claimed"], True)

        replay = outcome_commerce.commercial_projection(
            list(reversed(self.commercial_events)) + [copy.deepcopy(self.commercial_events[-1])]
        )
        self.assertEqual(replay["deduped_event_ids"], ["evt-bank-available-0001"])
        self.assertEqual(projection["jobs"], replay["jobs"])

    def test_commercial_projection_rejects_blind_unknown_effect_retry(self) -> None:
        broken = copy.deepcopy(self.commercial_events)
        reconcile = next(row for row in broken if row["event_id"] == "evt-deliver-reconcile-0001")
        reconcile["causation_id"] = "evt-deliver-request-0001"
        with self.assertRaisesRegex(outcome_commerce.CommerceError, "without causal linkage"):
            outcome_commerce.commercial_projection(broken)

    def test_float_money_and_quantity_are_rejected(self) -> None:
        catalog = copy.deepcopy(self.hybrid)
        catalog["listings"][0]["pricing"]["components"][0]["amount"] = 99.0
        with self.assertRaisesRegex(outcome_commerce.CommerceError, "decimal string"):
            outcome_commerce.quote(catalog, "synthetic-hybrid-agent", {})

        event = copy.deepcopy(self.events[0])
        event["quantity"] = 1.0
        with self.assertRaisesRegex(outcome_commerce.CommerceError, "decimal string"):
            outcome_commerce.statement(self.hybrid, [event])

    def test_a2a_export_is_a_fragment_not_an_agent_card(self) -> None:
        fragment = read_json(COMMERCE / "a2a-skills.json")
        manifest = read_json(COMMERCE / "manifest.json")
        self.assertEqual(fragment["kind"], "A2A_SKILLS_FRAGMENT")
        self.assertIs(fragment["is_agent_card"], False)
        self.assertIs(fragment["well_known_agent_card_published"], False)
        self.assertNotIn("url", fragment)
        self.assertNotIn("capabilities", fragment)
        self.assertEqual(manifest["interfaces"]["a2a"]["status"], "SKILLS_FRAGMENT_READY")
        self.assertIs(manifest["interfaces"]["a2a"]["is_agent_card"], False)
        self.assertFalse((ROOT / ".well-known" / "agent-card.json").exists())

    def test_existing_mcp_exposes_read_only_commerce_resources_when_present(self) -> None:
        path = ROOT / "commons_mcp.py"
        if not path.is_file():
            return
        text = path.read_text(encoding="utf-8")
        for uri in (
            "commons://commerce/catalog",
            "commons://commerce/manifest",
            "commons://commerce/a2a-skills",
        ):
            self.assertIn(uri, text)
        self.assertIn('("commerce", "catalog")', text)
        self.assertIn('("commerce", "manifest")', text)
        self.assertIn('("commerce", "a2a-skills")', text)

    def test_existing_bazaar_remains_seven_zero_usd_free_compute_offers(self) -> None:
        catalog_path = ROOT / "bazaar.json"
        host_path = ROOT / "host" / "bazaar.py"
        if not catalog_path.exists() and not host_path.exists():
            return
        self.assertTrue(catalog_path.is_file(), "a partial Bazaar checkout is not verifiable")
        self.assertTrue(host_path.is_file(), "a partial Bazaar checkout is not verifiable")
        bazaar = read_json(catalog_path)
        offers = bazaar["offers"]
        self.assertEqual(len(offers), 7)
        self.assertEqual({row["currency"] for row in offers}, {"FREE_COLONY_COMPUTE"})
        self.assertTrue(all(Decimal(str(row["price"])) == Decimal("0") for row in offers))
        self.assertFalse(any(row["currency"] == "USD" for row in offers))

    def test_host_validate_and_draft_schema_accept_the_recorded_sku_catalog(self) -> None:
        self.validator.validate_file(self.catalog, "catalog.schema.json")
        proc = subprocess.run(
            [sys.executable, str(ROOT / "host" / "outcome_commerce.py"), "validate"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("OK 15 listings", proc.stdout)
        self.assertIn("CHARGEABLE != AUTHORIZATION != SETTLEMENT != PAYOUT != BANK_AVAILABLE", proc.stdout)

        proc = subprocess.run(
            [sys.executable, str(ROOT / "host" / "outcome_commerce.py"), "catalog"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        for spec in RECORDED_STRIPE_SKUS:
            self.assertIn("source %s@%s" % (spec["path"], spec["blob_sha"]), proc.stdout)

    def test_host_rejects_unverified_checkout_and_source_artifact_claims(self) -> None:
        def errors_for(mutator):
            catalog = copy.deepcopy(self.catalog)
            listing = next(
                row for row in catalog["listings"] if row["id"] == "sku-tip-20260826"
            )
            mutator(listing)
            return outcome_commerce.catalog_errors(catalog, root=ROOT, check_sources=True)

        errors = errors_for(
            lambda row: row.__setitem__(
                "checkout",
                {
                    "status": "LIVEMODE_URL_RECORDED",
                    "provider": "paypal",
                    "url": "https://donate.stripe.com/fZucN40Ch9fj7mxgJs43S08",
                    "link_active": "UNVERIFIED",
                    "account_charges_enabled": False,
                },
            )
        )
        self.assertTrue(any("provider must be stripe" in item for item in errors), errors)

        errors = errors_for(
            lambda row: row["checkout"].__setitem__(
                "url", "https://buy.stripe.com.evil.com/abcDEF123456"
            )
        )
        self.assertTrue(any("url is invalid" in item for item in errors), errors)

        errors = errors_for(
            lambda row: row.__setitem__(
                "checkout",
                {
                    "status": "ACTIVE_CHARGEABLE",
                    "provider": "stripe",
                    "url": "https://donate.stripe.com/fZucN40Ch9fj7mxgJs43S08",
                    "link_active": True,
                    "account_charges_enabled": True,
                },
            )
        )
        self.assertTrue(any("capability_evidence" in item for item in errors), errors)

        def invent_artifact(row):
            row["source_artifact"] = {
                "path": "land/does-not-exist.md",
                "blob_sha": "0" * 40,
                "terms_authority": "source",
            }

        errors = errors_for(invent_artifact)
        self.assertTrue(any("source artifact missing" in item for item in errors), errors)

        def remove_source(row):
            del row["source_artifact"]

        errors = errors_for(remove_source)
        self.assertTrue(any("exactly one" in item for item in errors), errors)

        errors = errors_for(
            lambda row: row["source_artifact"].__setitem__("blob_sha", "0" * 40 + "\n")
        )
        self.assertTrue(any("blob_sha is invalid" in item for item in errors), errors)

        errors = errors_for(
            lambda row: row["source_artifact"].__setitem__("path", "\0")
        )
        self.assertTrue(any("path is invalid" in item for item in errors), errors)

    def test_one_canonical_funnel_covers_every_listing(self) -> None:
        listings = self.catalog["listings"]
        listing_ids = [row["id"] for row in listings]
        funnels = self.catalog["funnels"]
        self.assertEqual(set(funnels), set(listing_ids))
        self.assertEqual(
            self.catalog["funnel_stage_order"],
            [
                "DISCOVERED", "QUALIFIED", "QUOTED", "FUNDED", "RUNNING",
                "SUBMITTED", "ACCEPTED", "SETTLED", "BANK_AVAILABLE",
            ],
        )
        self.assertEqual(
            sorted(row["priority"] for row in funnels.values()),
            list(range(1, 16)),
        )
        ordered = sorted(funnels, key=lambda ident: funnels[ident]["priority"])
        self.assertEqual(ordered[:3], [
            "sku-tip-20260826",
            "same-day-agent-survival-proof",
            "sku-monthly-tip-20260826",
        ])
        by_id = {row["id"]: row for row in listings}
        for listing_id, funnel in funnels.items():
            checkout_status = by_id[listing_id].get("checkout", {}).get("status")
            if checkout_status == "ACTIVE_CHARGEABLE":
                expected_mode = "ACTIVE_STRIPE_LINK"
                expected_status = "ACTIVE_CHARGEABLE"
                checkout_first = funnel["readiness"] == "READY_FOR_CHECKOUT"
                expected_action = "checkout-open" if checkout_first else "qualification-open"
                expected_click_truth = "INTENT_ONLY"
                expected_first = "FUNDED" if checkout_first else "DISCOVERED"
            elif checkout_status == "LIVEMODE_URL_RECORDED":
                expected_mode = "RECORDED_STRIPE_LINK"
                expected_status = "CAPABILITY_UNVERIFIED"
                expected_action = "provider-capability-unverified"
                expected_click_truth = "NO_CLICK_SURFACE"
                expected_first = "DISCOVERED"
            else:
                expected_mode = "CUSTOMER_SPECIFIC_INVOICE"
                expected_status = "NOT_ISSUED"
                expected_action = "qualification-open"
                expected_click_truth = "INTENT_ONLY"
                expected_first = "DISCOVERED"

            self.assertEqual(funnel["conversion"]["mode"], expected_mode)
            self.assertEqual(funnel["conversion"]["status"], expected_status)
            self.assertEqual(funnel["conversion"]["state_after"], "FUNDED")
            self.assertEqual(funnel["measurement"]["click_truth"], expected_click_truth)
            self.assertEqual(funnel["measurement"]["success_state"], "BANK_AVAILABLE")
            self.assertTrue(set(funnel["next_offer"]).issubset(set(listing_ids)))
            self.assertTrue(funnel["acquisition"]["route"].endswith("#" + listing_id))
            self.assertEqual(funnel["measurement"]["dom_action"], expected_action)
            self.assertEqual(funnel["measurement"]["first_evidence_state"], expected_first)
        truth = self.catalog["funnel_truth"]
        self.assertEqual(truth["distinct_targets"], 12)
        self.assertEqual(truth["delivered_transports"], 17)
        self.assertEqual(truth["verified_positive_replies"], 0)
        self.assertEqual(truth["accepted_scopes"], 0)
        self.assertEqual(truth["paid_deliveries"], 0)
        self.assertEqual(truth["collected_cash_usd"], "0.00")
        self.assertEqual(truth["next_edge"], "QUALIFIED_BUYER")
        self.assertIn("p/slack-1787769698-642529.md", truth["source"])

    def test_canonical_catalog_requires_the_complete_funnel_triad(self) -> None:
        candidate = copy.deepcopy(self.catalog)
        for field in ("funnel_stage_order", "funnel_truth", "funnels"):
            candidate.pop(field)
        errors = outcome_commerce.catalog_errors(candidate, root=ROOT, check_sources=False)
        self.assertTrue(any("are required" in item for item in errors), errors)

    def test_funnel_refunds_preserve_canonical_buyer_terms(self) -> None:
        offers = json.loads(
            (ROOT / "revenue" / "human_outcomes" / "offers.json").read_text(encoding="utf-8")
        )
        for offer in offers["offers"]:
            self.assertEqual(
                self.catalog["funnels"][offer["id"]]["fulfillment"]["refund"],
                offer["refund"],
            )
        survival = json.loads(
            (ROOT / "revenue" / "production_survival" / "offer.json").read_text(encoding="utf-8")
        )
        refund = self.catalog["funnels"]["same-day-agent-survival-proof"]["fulfillment"]["refund"]
        for sentence in survival["entry_offer"]["refund"].split(". "):
            self.assertIn(sentence.rstrip("."), refund)
        self.assertIn("one free next-business-day repair attempt", refund)

    def test_host_rejects_incomplete_or_false_funnel_contracts(self) -> None:
        def errors_for(mutator):
            catalog = copy.deepcopy(self.catalog)
            mutator(catalog)
            return outcome_commerce.catalog_errors(catalog, root=ROOT, check_sources=False)

        errors = errors_for(lambda catalog: catalog["funnels"].pop("sku-tip-20260826"))
        self.assertTrue(any("exactly match listing ids" in item for item in errors), errors)

        errors = errors_for(
            lambda catalog: catalog["funnels"]["sku-tip-20260826"]["measurement"].__setitem__(
                "click_truth", "FUNDED"
            )
        )
        self.assertTrue(any("click_truth" in item for item in errors), errors)

        errors = errors_for(
            lambda catalog: catalog["funnels"]["same-day-agent-survival-proof"]["conversion"].__setitem__(
                "mode", "ACTIVE_STRIPE_LINK"
            )
        )
        self.assertTrue(any("checkout state" in item for item in errors), errors)

        errors = errors_for(
            lambda catalog: catalog["funnels"]["sku-tip-20260826"].__setitem__(
                "priority", 2
            )
        )
        self.assertTrue(any("unique sequence" in item for item in errors), errors)

        errors = errors_for(lambda catalog: catalog.pop("funnels"))
        self.assertTrue(any("must appear together" in item for item in errors), errors)

        errors = errors_for(
            lambda catalog: catalog["funnels"]["sku-tip-20260826"].__setitem__("next_offer", 7)
        )
        self.assertTrue(any("next_offer must be an array" in item for item in errors), errors)

        catalog = copy.deepcopy(self.catalog)
        for field in ("funnel_stage_order", "funnel_truth", "funnels"):
            catalog.pop(field)
        errors = outcome_commerce.canonical_catalog_errors(
            catalog, root=ROOT, check_sources=False
        )
        self.assertTrue(any("canonical catalog missing" in item for item in errors), errors)

    def test_fifteen_unique_listings_preserve_frozen_eight(self) -> None:
        listings = self.catalog["listings"]
        ids = [row["id"] for row in listings]
        self.assertEqual(len(listings), 15)
        self.assertEqual(len(set(ids)), 15)
        self.assertEqual(
            hashlib.sha256(canonical(listings[:8]).encode("utf-8")).hexdigest(),
            FROZEN_EIGHT_SHA256,
        )
        for row in listings[:8]:
            self.assertIn("source", row)
            self.assertNotIn("source_artifact", row)
            self.assertNotIn("checkout", row)
        self.assertEqual(
            hashlib.sha256(
                canonical(self.catalog["integration_sources"][:-1]).encode("utf-8")
            ).hexdigest(),
            FROZEN_SOURCE_ADAPTERS_SHA256,
        )
        self.assertEqual(
            self.catalog["integration_sources"][-1],
            "land/stripe-payment-links-20260826.md",
        )
        manifest = read_json(COMMERCE / "manifest.json")
        self.assertEqual(
            hashlib.sha256(
                canonical(manifest["source_adapters"][:-1]).encode("utf-8")
            ).hexdigest(),
            FROZEN_SOURCE_ADAPTERS_SHA256,
        )
        self.assertEqual(
            manifest["source_adapters"][-1],
            "land/stripe-payment-links-20260826.md",
        )

    def test_seven_recorded_markdown_skus_match_source_artifacts_and_checkout(self) -> None:
        by_id = {row["id"]: row for row in self.catalog["listings"]}
        recorded = [row for row in self.catalog["listings"] if "checkout" in row]
        artifacts = [row for row in self.catalog["listings"] if "source_artifact" in row]
        self.assertEqual(len(recorded), 7)
        self.assertEqual(len(artifacts), 7)
        self.assertEqual(
            [row["id"] for row in recorded],
            [row["id"] for row in RECORDED_STRIPE_SKUS],
        )
        for spec in RECORDED_STRIPE_SKUS:
            row = by_id[spec["id"]]
            self.assertNotIn("source", row)
            artifact = row["source_artifact"]
            self.assertEqual(artifact["path"], spec["path"])
            self.assertEqual(artifact["blob_sha"], spec["blob_sha"])
            self.assertEqual(artifact["terms_authority"], "source")
            path = ROOT / spec["path"]
            self.assertTrue(path.is_file(), spec["path"])
            self.assertEqual(git_hash_object(path), spec["blob_sha"])
            text = path.read_text(encoding="utf-8")
            for marker in spec["markers"]:
                self.assertIn(marker, text)
            self.assertIn("Verified chargeable checkout (click is intent only; not authorization, settlement, payout, or cash): `%s`" % spec["url"], text)
            self.assertNotIn("Pay: " + spec["url"], text)
            self.assertNotIn("Recorded URL (not a checkout):", text)
            component = row["pricing"]["components"][0]
            self.assertEqual(component["kind"], spec["kind"])
            self.assertEqual(component[spec["amount_field"]], spec["amount"])
            self.assertEqual(row["pricing"]["currency"], "USD")
            self.assertEqual(row["routes"]["human"], "commerce.html")
            self.assertEqual(row["routes"]["machine"], spec["path"])
            self.assertEqual(row["checkout"], {
                "status": "ACTIVE_CHARGEABLE",
                "provider": "stripe",
                "url": spec["url"],
                "link_active": True,
                "account_charges_enabled": True,
                "account_payouts_enabled": True,
                "capability_evidence": {
                    "reference": "stripe-livemode-GET-v1-accounts-acct_1U6HI9ATH4EDE7XD+GET-v1-payment_links",
                    "observed_at": "2026-08-28T16:10:00Z",
                },
            })
            funnel = self.catalog["funnels"][spec["id"]]
            checkout_first = spec["id"] in {"sku-tip-20260826", "sku-monthly-tip-20260826"}
            self.assertEqual(funnel["conversion"]["mode"], "ACTIVE_STRIPE_LINK")
            self.assertEqual(funnel["conversion"]["status"], "ACTIVE_CHARGEABLE")
            self.assertEqual(funnel["measurement"]["click_truth"], "INTENT_ONLY")
            if checkout_first:
                self.assertEqual(funnel["readiness"], "READY_FOR_CHECKOUT")
                self.assertEqual(funnel["measurement"]["dom_action"], "checkout-open")
                self.assertIn("checkout", funnel["acquisition"]["cta"].lower())
            else:
                self.assertEqual(funnel["readiness"], "READY_FOR_QUALIFICATION")
                self.assertEqual(funnel["measurement"]["dom_action"], "qualification-open")
                self.assertEqual(funnel["acquisition"]["cta"], "Start public intake")

    def test_recorded_subscription_quotes_default_to_one_cycle(self) -> None:
        expected = {
            "sku-seat-20260826": "5.00",
            "sku-monthly-tip-20260826": "3.00",
            "sku-boost-20260826": "4.99",
        }
        for listing_id, amount in expected.items():
            with self.subTest(listing_id=listing_id):
                quote = outcome_commerce.quote(self.catalog, listing_id, {})
                self.assertEqual(quote["gross_amount"], amount)
                self.assertEqual(quote["net_amount"], amount)
                self.assertEqual(quote["line_items"][0]["amount"], amount)

    def _reject_checkout(self, checkout) -> None:
        catalog = copy.deepcopy(self.catalog)
        listing = next(row for row in catalog["listings"] if row["id"] == "sku-tip-20260826")
        listing["checkout"] = checkout
        with self.assertRaises(SchemaError):
            self.validator.validate_file(catalog, "catalog.schema.json")

    def test_schema_requires_durable_evidence_for_chargeable_checkout(self) -> None:
        valid = "https://donate.stripe.com/fZucN40Ch9fj7mxgJs43S08"
        evidence = {
            "reference": "stripe:payment_link:plink_verified_0001",
            "observed_at": "2026-08-27T03:00:00Z",
        }
        catalog = copy.deepcopy(self.catalog)
        listing = next(row for row in catalog["listings"] if row["id"] == "sku-tip-20260826")
        listing["checkout"] = {
            "status": "ACTIVE_CHARGEABLE",
            "provider": "stripe",
            "url": valid,
            "link_active": True,
            "account_charges_enabled": True,
            "account_payouts_enabled": True,
            "capability_evidence": evidence,
        }
        self.validator.validate_file(catalog, "catalog.schema.json")

        self._reject_checkout("ACTIVE_CHARGEABLE")
        invalid_urls = (
            "not-a-url",
            "http://buy.stripe.com/abcDEF123456",
            "https://user:pass@buy.stripe.com/abcDEF123456",
            valid + "?x=1",
            valid + "#frag",
            valid + "?",
            valid + "#",
            valid + "\n",
            "https://buy.stripe.com:8443/abcDEF123456",
            "https://buy.stripe.com.evil.com/abcDEF123456",
            "https://buy.stripes.com/abcDEF123456",
            "https://constructor/abcDEF123456",
            "https://__proto__/abcDEF123456",
        )
        for url in invalid_urls:
            with self.subTest(url=url):
                self._reject_checkout({
                    "status": "ACTIVE_CHARGEABLE",
                    "provider": "stripe",
                    "url": url,
                    "link_active": True,
                    "account_charges_enabled": True,
                    "account_payouts_enabled": True,
                    "capability_evidence": copy.deepcopy(evidence),
                })
        for checkout in (
            {
                "status": "ACTIVE_CHARGEABLE",
                "provider": "stripe",
                "url": valid,
                "link_active": False,
                "account_charges_enabled": True,
                "account_payouts_enabled": True,
                "capability_evidence": copy.deepcopy(evidence),
            },
            {
                "status": "ACTIVE_CHARGEABLE",
                "provider": "stripe",
                "url": valid,
                "link_active": True,
                "account_charges_enabled": False,
                "capability_evidence": copy.deepcopy(evidence),
            },
            {
                "status": "ACTIVE_CHARGEABLE",
                "provider": "stripe",
                "url": valid,
                "link_active": True,
                "account_charges_enabled": True,
                "account_payouts_enabled": False,
                "capability_evidence": copy.deepcopy(evidence),
            },
            {
                "status": "ACTIVE_CHARGEABLE",
                "provider": "stripe",
                "url": valid,
                "link_active": True,
                "account_charges_enabled": True,
            },
            {
                "status": "ACTIVE_CHARGEABLE",
                "provider": "stripe",
                "url": valid,
                "link_active": True,
                "account_charges_enabled": True,
                "account_payouts_enabled": True,
                "capability_evidence": {
                    "reference": " ",
                    "observed_at": "2026-08-27T03:00:00Z",
                },
            },
            {
                "status": "ACTIVE_CHARGEABLE",
                "provider": "stripe",
                "url": valid,
                "link_active": True,
                "account_charges_enabled": True,
                "account_payouts_enabled": True,
                "capability_evidence": {
                    "reference": "stripe:payment_link:plink_verified_0001",
                    "observed_at": "not-a-timestamp",
                },
            },
            {
                "status": "LIVEMODE_URL_RECORDED",
                "provider": "stripe",
                "url": valid,
                "link_active": True,
                "account_charges_enabled": False,
            },
            {
                "status": "LIVEMODE_URL_RECORDED",
                "provider": "stripe",
                "url": valid,
                "link_active": "UNVERIFIED",
                "account_charges_enabled": True,
            },
            {
                "status": "LIVEMODE_URL_RECORDED",
                "provider": "stripe",
                "url": valid,
                "link_active": "UNVERIFIED",
            },
            {
                "status": "LIVEMODE_URL_RECORDED",
                "provider": "stripe",
                "url": valid,
                "link_active": "UNVERIFIED",
                "account_charges_enabled": False,
                "capability_evidence": copy.deepcopy(evidence),
            },
            {
                "status": "ACTIVE_CHARGEABLE",
                "provider": "paypal",
                "url": valid,
                "link_active": True,
                "account_charges_enabled": True,
                "account_payouts_enabled": True,
                "capability_evidence": copy.deepcopy(evidence),
            },
            {
                "status": "ACTIVE_CHARGEABLE",
                "provider": "stripe",
                "url": valid,
                "link_active": True,
                "account_charges_enabled": True,
                "account_payouts_enabled": True,
                "capability_evidence": copy.deepcopy(evidence),
                "note": "extra",
            },
            {"status": "NOT_MINTED", "url": valid},
            {"status": "NOT_MINTED", "provider": "stripe", "url": valid},
            {"status": "PENDING\n"},
        ):
            self._reject_checkout(checkout)

    def test_listing_requires_exactly_one_source_form(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        listing = catalog["listings"][0]
        listing["source_artifact"] = {
            "path": "land/sku-tip-20260826.md",
            "blob_sha": "7e94f42e9a92e166f614916d63712403f6fc77f7",
            "terms_authority": "source",
        }
        with self.assertRaises(SchemaError):
            self.validator.validate_file(catalog, "catalog.schema.json")
        del listing["source"]
        del listing["source_artifact"]
        with self.assertRaises(SchemaError):
            self.validator.validate_file(catalog, "catalog.schema.json")

        catalog = copy.deepcopy(self.catalog)
        listing = next(row for row in catalog["listings"] if "source_artifact" in row)
        listing["source_artifact"]["blob_sha"] += "\n"
        with self.assertRaises(SchemaError):
            self.validator.validate_file(catalog, "catalog.schema.json")
        for hostile in ("\0", "../private.txt", "C:/private.txt", "/private.txt"):
            catalog = copy.deepcopy(self.catalog)
            listing = next(row for row in catalog["listings"] if "source_artifact" in row)
            listing["source_artifact"]["path"] = hostile
            with self.assertRaises(SchemaError):
                self.validator.validate_file(catalog, "catalog.schema.json")

    def test_renderer_suppresses_recorded_urls_and_escapes_without_new_network(self) -> None:
        js = (ROOT / "commerce.js").read_text(encoding="utf-8")
        self.assertIn("function isStripeCheckoutUrl", js)
        self.assertIn("function hasDurableCapabilityEvidence", js)
        self.assertIn("checkout.capability_evidence", js)
        self.assertIn("evidence.reference", js)
        self.assertIn("evidence.observed_at", js)
        self.assertIn("function termsSource", js)
        self.assertIn("row.source || row.source_artifact", js)
        self.assertIn('checkout.status === "LIVEMODE_URL_RECORDED"', js)
        self.assertIn('checkout.status !== "ACTIVE_CHARGEABLE"', js)
        self.assertIn("checkout.link_active !== true", js)
        self.assertIn("checkout.account_charges_enabled !== true", js)
        self.assertIn("checkout.account_payouts_enabled !== true", js)
        self.assertIn('checkout.provider !== "stripe"', js)
        self.assertIn("isStripeCheckoutUrl(checkout.url)", js)
        self.assertIn('rel="noopener noreferrer"', js)
        self.assertIn("Payment capability is unverified", js)
        self.assertIn("Verified chargeable Stripe checkout", js)
        self.assertIn("checkout-active", js)
        self.assertNotIn("checkout-live", js)
        self.assertNotIn("LIVE Stripe", js)
        self.assertIn("function esc(", js)
        self.assertIn("esc(row.name)", js)
        self.assertIn("esc(row.state)", js)
        self.assertIn("esc(row.routes.human)", js)
        self.assertIn("esc(row.routes.machine)", js)
        self.assertIn("esc(checkout.url)", js)
        self.assertIn("function funnelFor", js)
        self.assertIn("data-funnel-sku", js)
        self.assertIn("data-funnel-action", js)
        self.assertIn("INTENT_ONLY", js)
        self.assertIn("NO_CLICK_SURFACE", js)
        self.assertIn("BANK_AVAILABLE", js)
        self.assertIn('parsed.protocol !== "https:"', js)
        self.assertIn("parsed.username", js)
        self.assertIn("parsed.search", js)
        self.assertIn("parsed.hash", js)
        self.assertIn('buy.stripe.com', js)
        self.assertIn('donate.stripe.com', js)
        self.assertIn("parsed.port", js)
        self.assertIn('["fixed", "subscription", "milestone", "license"]', js)
        self.assertEqual(js.count("fetch("), 1)
        self.assertIn("./revenue/outcome_commerce/catalog.json", js)
        self.assertIn("PUBLIC_CONTACT_URL", js)
        self.assertIn("PUBLIC_CONTACT_URL", (ROOT / "commerce.html").read_text(encoding="utf-8"))
        for surface in (
            "sendBeacon",
            "XMLHttpRequest",
            "WebSocket",
            "EventSource",
            "navigator.sendBeacon",
            "localStorage",
            "sessionStorage",
        ):
            self.assertNotIn(surface, js)
        self.assertNotIn("innerHTML = checkout.url", js)
        self.assertNotIn("${checkout.url}", js)

        stripe_url_pattern = r"https://(?:buy|donate)\.stripe\.com/"
        self.assertIsNotNone(re.search(stripe_url_pattern, "https://buy.stripe.com/test"))
        self.assertIsNotNone(re.search(stripe_url_pattern, "https://donate.stripe.com/test"))
        for surface_name in ("commerce.html", "tips.html", "pay.html"):
            with self.subTest(surface=surface_name):
                surface_html = (ROOT / surface_name).read_text(encoding="utf-8")
                self.assertNotIn('class="checkout-live"', surface_html)
                self.assertNotRegex(surface_html, stripe_url_pattern)
                self.assertGreaterEqual(surface_html.count("js-checkout-slot"), 7)
                self.assertIn("mailto:tokenjunkielabs@gmail.com", surface_html)
                self.assertIn("pay.js", surface_html)

        html = (ROOT / "commerce.html").read_text(encoding="utf-8")
        self.assertIn(".checkout-active,.funnel-intake", html)
        self.assertIn('id="sku-intake"', html)
        self.assertIn('src="./commerce.js?v=20260830a"', html)
        self.assertIn('name="to" value="OFFER"', html)
        self.assertIn('name="subject" value="COMMONS SKU PURCHASE INTENT"', html)
        self.assertIn("carrier.js", html)

        tips = (ROOT / "tips.html").read_text(encoding="utf-8")
        self.assertIn(
            "<title>Commons tips — proven rails only</title>", tips
        )
        self.assertIn(
            "PROVEN RAILS ONLY · UNVERIFIED URLS STAY INERT", tips
        )
        self.assertIn(
            "Static copy keeps Stripe URLs inert until catalog evidence is read.",
            tips,
        )
        self.assertIn(".provider-inert{", tips)
        self.assertNotIn("LIVE PAYMENT LINKS", tips)
        self.assertNotIn("TYPE owns checkout", tips)
        self.assertNotIn("live checkout", tips.lower())
        self.assertNotIn(">Pay ", tips)

        pay = (ROOT / "pay.html").read_text(encoding="utf-8")
        self.assertIn(
            "<title>Commons checkout — proven rails only</title>", pay
        )
        self.assertIn("<h1>Provider capability</h1>", pay)
        self.assertIn(
            "Static HTML keeps Stripe URLs inert.",
            pay,
        )
        self.assertIn(
            "Duplicate URLs stay unpublished.",
            pay,
        )
        self.assertIn(".provider-inert{", pay)
        self.assertNotIn("live Stripe URLs", pay)
        self.assertNotIn("<h1>Pay</h1>", pay)
        self.assertNotIn(">Pay ", pay)

    def test_renderer_executes_strict_own_host_checkout_membership(self) -> None:
        node = shutil.which("node")
        self.assertIsNotNone(node, "Node.js is required to execute the production checkout validator")
        js = (ROOT / "commerce.js").read_text(encoding="utf-8")
        instrumented = js.replace(
            "function isStripeCheckoutUrl(raw)",
            "globalThis.isStripeCheckoutUrl = function isStripeCheckoutUrl(raw)",
            1,
        )
        harness = """
globalThis.fetch = function () { return new Promise(function () {}); };
%s
var urls = [
  "https://buy.stripe.com/abcDEF123456",
  "https://donate.stripe.com/abcDEF123456",
  "https://constructor/abcDEF123456",
  "https://__proto__/abcDEF123456",
  "https://buy.stripe.com.evil.com/abcDEF123456",
  "https://buy.stripe.com/abcDEF123456?",
  "https://buy.stripe.com/abcDEF123456#",
  "https://buy.stripe.com/abcDEF123456?#"
];
process.stdout.write(JSON.stringify(urls.map(globalThis.isStripeCheckoutUrl)));
""" % instrumented
        proc = subprocess.run(
            [node, "-e", harness],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(
            json.loads(proc.stdout),
            [True, True, False, False, False, False, False, False],
        )

    def test_renderer_executes_strict_checkout_state_and_evidence_gate(self) -> None:
        node = shutil.which("node")
        self.assertIsNotNone(node, "Node.js is required to execute the checkout state gate")
        js = (ROOT / "commerce.js").read_text(encoding="utf-8")
        instrumented = js.replace(
            "function checkoutAnchor(row, funnel)",
            "globalThis.checkoutAnchor = function checkoutAnchor(row, funnel)",
            1,
        )
        harness = """
globalThis.fetch = function () { return new Promise(function () {}); };
%s
var url = "https://buy.stripe.com/abcDEF123456";
var ready = {readiness: "READY_FOR_CHECKOUT"};
var recorded = {
  id: "recorded",
  checkout: {
    status: "LIVEMODE_URL_RECORDED",
    provider: "stripe",
    url: url,
    link_active: "UNVERIFIED",
    account_charges_enabled: false
  }
};
var noEvidence = {
  id: "no-evidence",
  checkout: {
    status: "ACTIVE_CHARGEABLE",
    provider: "stripe",
    url: url,
    link_active: true,
    account_charges_enabled: true,
    account_payouts_enabled: true
  }
};
var badEvidence = {
  id: "bad-evidence",
  checkout: {
    status: "ACTIVE_CHARGEABLE",
    provider: "stripe",
    url: url,
    link_active: true,
    account_charges_enabled: true,
    account_payouts_enabled: true,
    capability_evidence: {reference: "stripe:test", observed_at: "not-a-time"}
  }
};
var verified = {
  id: "verified",
  checkout: {
    status: "ACTIVE_CHARGEABLE",
    provider: "stripe",
    url: url,
    link_active: true,
    account_charges_enabled: true,
    account_payouts_enabled: true,
    capability_evidence: {
      reference: "stripe:payment_link:plink_verified_0001",
      observed_at: "2026-08-27T03:00:00Z"
    }
  }
};
process.stdout.write(JSON.stringify([
  globalThis.checkoutAnchor(recorded, ready),
  globalThis.checkoutAnchor(noEvidence, ready),
  globalThis.checkoutAnchor(badEvidence, ready),
  globalThis.checkoutAnchor(verified, ready)
]));
""" % instrumented
        proc = subprocess.run(
            [node, "-e", harness],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        rendered = json.loads(proc.stdout)
        self.assertIn("capability is unverified", rendered[0])
        self.assertNotIn("<a ", rendered[0])
        self.assertEqual(rendered[1], "")
        self.assertEqual(rendered[2], "")
        self.assertIn('class="checkout-active"', rendered[3])
        self.assertIn('href="' + "https://buy.stripe.com/abcDEF123456" + '"', rendered[3])

    def test_scope_first_checkout_hashes_resolve_after_async_catalog_render(self) -> None:
        node = shutil.which("node")
        self.assertIsNotNone(node, "Node.js is required to execute the intake deep-link resolver")
        scope_first = [
            row["id"]
            for row in self.catalog["listings"]
            if self.catalog["funnels"][row["id"]]["qualification"]["route"]
            == "commerce.html#" + row["id"]
        ]
        self.assertEqual(
            scope_first,
            [
                "sku-seat-20260826",
                "sku-unlock-20260826",
                "sku-boost-20260826",
                "sku-whitebox-hour-20260826",
                "sku-muhlnickel-titan-20260826",
            ],
        )

        pay_js = (ROOT / "pay.js").read_text(encoding="utf-8").replace(
            "function fillSlot(slot, listing, snapshot, funnel)",
            "globalThis.fillSlot = function fillSlot(slot, listing, snapshot, funnel)",
            1,
        )
        commerce_js = (ROOT / "commerce.js").read_text(encoding="utf-8")
        commerce_js = commerce_js.replace(
            "var data;", "var data = globalThis.__catalog;", 1
        ).replace(
            "function resolveHashIntake()",
            "globalThis.resolveHashIntake = function resolveHashIntake()",
            1,
        )
        harness = r"""
globalThis.fetch = function () { return new Promise(function () {}); };
var ids = %s;
globalThis.__catalog = {listings: [], funnels: {}};
ids.forEach(function (id) {
  globalThis.__catalog.listings.push({id: id});
  globalThis.__catalog.funnels[id] = {
    qualification: {route: "commerce.html#" + id}
  };
});
%s
%s
var checkout = {
  status: "ACTIVE_CHARGEABLE",
  provider: "stripe",
  url: "https://buy.stripe.com/abcDEF123456",
  link_active: true,
  account_charges_enabled: true,
  account_payouts_enabled: true,
  capability_evidence: {reference: "stripe:test", observed_at: "2026-08-30T00:00:00Z"}
};
var snapshot = {
  provider: {
    name: "stripe", livemode: true, charges_enabled: true, payouts_enabled: true,
    currently_due: []
  },
  inert_duplicate_urls: []
};
var payHrefs = ids.map(function (id) {
  var slot = {innerHTML: ""};
  globalThis.fillSlot(slot, {id: id, checkout: checkout}, snapshot, {readiness: "READY_FOR_QUALIFICATION"});
  var match = slot.innerHTML.match(/href="([^"]+)"/);
  return match && match[1];
});

var selected = {textContent: "choose a Start intake link above"};
var body = {value: "DEFAULT INTAKE"};
var focusCalls = [];
var scrollCalls = [];
globalThis.document = {
  getElementById: function (id) {
    if (id === "sku-intake-selected") return selected;
    if (id === "sku-intake-body") return body;
    if (ids.indexOf(id) !== -1) {
      return {
        querySelector: function (selector) {
          if (selector !== ".funnel-intake") return null;
          return {focus: function (options) { focusCalls.push([id, options.preventScroll]); }};
        },
        scrollIntoView: function (options) { scrollCalls.push([id, options.block]); }
      };
    }
    return null;
  }
};
globalThis.window = {location: {hash: ""}};

var resolved = ids.map(function (id) {
  selected.textContent = "choose a Start intake link above";
  body.value = "DEFAULT INTAKE";
  focusCalls = [];
  scrollCalls = [];
  window.location.hash = "#" + encodeURIComponent(id);
  return {
    result: globalThis.resolveHashIntake(),
    selected: selected.textContent,
    body: body.value,
    focus: focusCalls,
    scroll: scrollCalls
  };
});
selected.textContent = "choose a Start intake link above";
body.value = "DEFAULT INTAKE";
focusCalls = [];
scrollCalls = [];
window.location.hash = "";
var noHash = {
  result: globalThis.resolveHashIntake(), selected: selected.textContent, body: body.value,
  focus: focusCalls, scroll: scrollCalls
};
process.stdout.write(JSON.stringify({payHrefs: payHrefs, resolved: resolved, noHash: noHash}));
""" % (json.dumps(scope_first), pay_js, commerce_js)
        proc = subprocess.run(
            [node, "-e", harness],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        rendered = json.loads(proc.stdout)
        self.assertEqual(
            rendered["payHrefs"], ["./commerce.html#" + sku for sku in scope_first]
        )
        for sku, state in zip(scope_first, rendered["resolved"]):
            with self.subTest(sku=sku):
                self.assertIs(state["result"], True)
                self.assertEqual(state["selected"], sku)
                self.assertIn("OFFER_ID: " + sku, state["body"])
                self.assertEqual(state["focus"], [[sku, True]])
                self.assertEqual(state["scroll"], [[sku, "start"]])
        self.assertEqual(
            rendered["noHash"],
            {
                "result": False,
                "selected": "choose a Start intake link above",
                "body": "DEFAULT INTAKE",
                "focus": [],
                "scroll": [],
            },
        )

    def test_commerce_surfaces_add_no_admission_gate(self) -> None:
        js = (ROOT / "commerce.js").read_text(encoding="utf-8")
        schema = (COMMERCE / "catalog.schema.json").read_text(encoding="utf-8")
        catalog_text = (COMMERCE / "catalog.json").read_text(encoding="utf-8")
        manifest = (COMMERCE / "manifest.json").read_text(encoding="utf-8")
        blob = "\n".join((js, schema, catalog_text, manifest)).lower()
        self.assertIn("parsed.username || parsed.password", js)
        self.assertNotIn("login", blob)
        self.assertNotIn("signup", blob)
        self.assertNotIn("api-key", blob)
        self.assertNotIn("apikey", blob)
        self.assertNotIn("oauth", blob)
        self.assertNotIn("allowlist", blob)
        self.assertNotIn("admission gate", blob)
        self.assertNotIn("identity gate", blob)
        self.assertNotIn("role gate", blob)
        self.assertNotIn("tier gate", blob)
        self.assertNotIn("approval workflow", blob)
        self.assertNotIn("protected path", blob)
        self.assertNotIn("protected-path", blob)
        self.assertNotIn("protected action", blob)
        self.assertNotIn("protected-action", blob)

    def test_recorded_checkout_does_not_claim_cash_and_funnel_stays_zero(self) -> None:
        js = (ROOT / "commerce.js").read_text(encoding="utf-8")
        catalog_text = (COMMERCE / "catalog.json").read_text(encoding="utf-8")
        truth = self.catalog["funnel_truth"]
        self.assertEqual(truth["collected_cash_usd"], "0.00")
        self.assertEqual(truth["accepted_scopes"], 0)
        for token in (
            "buyer accepted",
            "payment received",
            "settled cash",
            "payout complete",
            "bank available cash",
            "charge captured",
        ):
            self.assertNotIn(token, js.lower())
            self.assertNotIn(token, catalog_text.lower())
        self.assertIn("settled, paid out, or bank-available", js)
        receipts = [
            read_json(path)
            for path in sorted(
                (ROOT / "revenue" / "payment_ready" / "outreach_receipts").glob("*.json")
            )
        ]
        self.assertEqual(len(receipts), truth["delivered_transports"])
        latest_receipt = max(
            path.name
            for path in (ROOT / "revenue" / "payment_ready" / "outreach_receipts").glob("*.json")
        )
        self.assertIn(latest_receipt, truth["source"])
        self.assertIn("20260828-langfuse-1a0496451e052b9d.json", truth["source"])
        contacts = set()
        for row in receipts:
            dedupe = row.get("dedupe") or {}
            contacts.add(
                dedupe.get("distinct_contact_key")
                or row.get("recipient_email")
                or row["target_id"]
            )
        self.assertEqual(len(contacts), truth["distinct_targets"])
        self.assertEqual(truth["delivered_transports"], 17)
        self.assertEqual(truth["distinct_targets"], 12)
        for target_id, provider_reference in (
            ("metaforms", "apollo:emailer_message:6a8f9759437c7d0010ef8788"),
            ("dexmate", "apollo:emailer_message:6a8f9f8cc46158001490e2f4"),
            ("nextdata", "apollo:emailer_message:6a8faa92579ff9000cb874e2"),
            ("langfuse", "gmail:message:1a0496451e052b9d"),
        ):
            with self.subTest(target_id=target_id):
                matches = [row for row in receipts if row["target_id"] == target_id]
                self.assertEqual(len(matches), 1)
                receipt = matches[0]
                self.assertEqual(receipt["provider_state"], "COMPLETED")
                self.assertEqual(receipt["provider_reference"], provider_reference)
                self.assertTrue(receipt["dedupe"]["do_not_resend"])
                self.assertEqual(receipt["response_state"], "UNKNOWN")
                self.assertIsNone(receipt["response_reference"])
                self.assertIs(receipt["facts"]["cash_claimed"], False)
                self.assertEqual(receipt["facts"]["collected_cash_usd"], 0)
        upvest = [row for row in receipts if row["target_id"] == "upvest"]
        self.assertEqual(len(upvest), 1)
        self.assertEqual(upvest[0]["response_state"], "UNKNOWN")
        self.assertIsNone(upvest[0]["response_reference"])
        self.assertEqual(
            {row["response_state"] for row in receipts},
            {"UNKNOWN"},
        )
        self.assertTrue(all(row["facts"]["legal_acceptance"] == "NOT_LANDED" for row in receipts))
        self.assertTrue(all(row["facts"]["cash_claimed"] is False for row in receipts))
        self.assertTrue(all(row["facts"]["collected_cash_usd"] == 0 for row in receipts))
        self.assertTrue(
            all(row["facts"]["buyer_authorization"] == "UNKNOWN" for row in receipts)
        )
        current = read_json(ROOT / "revenue" / "payment_ready" / "current_receipt.json")
        self.assertEqual(current["facts"]["collected_cash_usd"], 0)
        self.assertEqual(current["facts"]["delivery"], "NOT_LANDED")
        self.assertIs(current["cash_claimed"], False)

    def test_langfuse_hard_dnr_zero_cash_advances_funnel_truth(self) -> None:
        """#4969 receipt must advance catalog funnel_truth; do not leave 16/11 pins."""
        truth = self.catalog["funnel_truth"]
        receipts = sorted(
            (ROOT / "revenue" / "payment_ready" / "outreach_receipts").glob("*.json")
        )
        self.assertEqual(len(receipts), 17)
        self.assertEqual(truth["delivered_transports"], 17)
        self.assertEqual(truth["distinct_targets"], 12)
        self.assertIn("20260828-langfuse-1a0496451e052b9d.json", truth["source"])
        self.assertEqual(truth["collected_cash_usd"], "0.00")
        self.assertEqual(truth["accepted_scopes"], 0)
        self.assertEqual(truth["paid_deliveries"], 0)
        self.assertEqual(truth["verified_positive_replies"], 0)
        row = read_json(
            ROOT
            / "revenue"
            / "payment_ready"
            / "outreach_receipts"
            / "20260828-langfuse-1a0496451e052b9d.json"
        )
        self.assertEqual(row["target_id"], "langfuse")
        self.assertEqual(row["provider"], "GMAIL")
        self.assertEqual(row["provider_state"], "COMPLETED")
        self.assertEqual(row["provider_reference"], "gmail:message:1a0496451e052b9d")
        self.assertTrue(row["dedupe"]["do_not_resend"])
        self.assertEqual(row["dedupe"]["distinct_contact_key"], "contact@langfuse.com")
        self.assertEqual(row["response_state"], "UNKNOWN")
        self.assertIsNone(row["response_reference"])
        self.assertIs(row["facts"]["cash_claimed"], False)
        self.assertEqual(row["facts"]["collected_cash_usd"], 0)
        self.assertEqual(row["facts"]["legal_acceptance"], "NOT_LANDED")
        self.assertEqual(row["facts"]["buyer_authorization"], "UNKNOWN")



if __name__ == "__main__":
    unittest.main()
