from __future__ import annotations

import copy
import importlib
import unittest

import revenue.accepted_work_to_cash_reconciler.engine as reconciler_engine
from revenue.revenue_funnel_control import engine as funnel_engine
from test_accepted_work_to_cash_reconciler import (
    _base_events,
    _document,
    _event,
    _opportunity,
)


class AcceptedWorkToCashSemanticRootTests(unittest.TestCase):
    @staticmethod
    def _retained_acceptance_document():
        events = _base_events("root-seal") + [
            _event(
                "root-seal-a",
                "ACCEPTED",
                "2026-09-17T03:00:00Z",
                "GITHUB",
            )
        ]
        return _document([_opportunity("root-seal", events)])

    def test_fake_upstream_generation_cannot_rebind_public_compile_verify_root(self):
        document = self._retained_acceptance_document()
        baseline = reconciler_engine.compile_bundle(document)
        item = baseline["packet"]["items"][0]
        self.assertEqual(item["stage"], "ACCEPTED_OR_MERGED")
        self.assertEqual(item["acceptance_basis"], "RETAINED_ACCEPTANCE_NOT_EXTERNAL")
        self.assertEqual(item["terminal_action"], "ACCEPTANCE_EVIDENCE_REQUIRED")
        self.assertIn("root-seal", baseline["packet"]["open_queue"])

        fake_upstream = copy.deepcopy(funnel_engine.compile_bundle(document["funnel_input"]))
        fake_item = fake_upstream["packet"]["opportunities"][0]
        fake_item["stage"] = "INVOICED_OR_AWARDED"
        fake_item["settlement_target_cents"] = 0

        def fake_compile(_document):
            return fake_upstream

        def fake_verify(_bundle):
            return True

        for name, replacement in (
            ("compile_funnel_bundle", fake_compile),
            ("verify_funnel_bundle", fake_verify),
            ("compile_packet", lambda _document: {"forged": True}),
            ("compile_bundle", lambda _document: {"forged": True}),
        ):
            with self.subTest(name=name):
                with self.assertRaisesRegex(AttributeError, "semantic root is sealed"):
                    setattr(reconciler_engine, name, replacement)

        after = reconciler_engine.compile_bundle(document)
        self.assertEqual(after, baseline)
        self.assertTrue(reconciler_engine.verify_bundle(after))
        item = after["packet"]["items"][0]
        self.assertNotEqual(item["terminal_action"], "DONE_ZERO_VALUE")
        self.assertIn("root-seal", after["packet"]["open_queue"])

    def test_authority_source_class_sets_cannot_be_widened_by_module_assignment(self):
        document = self._retained_acceptance_document()
        for name, replacement in (
            ("EXTERNAL_ACCEPTANCE_CLASSES", frozenset({"GITHUB"})),
            ("ROUTE_SOURCE_CLASSES", frozenset({"GITHUB"})),
        ):
            with self.subTest(name=name):
                with self.assertRaisesRegex(AttributeError, "semantic root is sealed"):
                    setattr(reconciler_engine, name, replacement)

        item = reconciler_engine.compile_packet(document)["items"][0]
        self.assertEqual(item["acceptance_basis"], "RETAINED_ACCEPTANCE_NOT_EXTERNAL")
        self.assertEqual(item["terminal_action"], "ACCEPTANCE_EVIDENCE_REQUIRED")

    def test_reload_restores_trusted_source_without_unsealing_engine(self):
        original_compile = reconciler_engine.compile_bundle
        reloaded = importlib.reload(reconciler_engine)
        self.assertIs(reloaded, reconciler_engine)
        self.assertTrue(getattr(type(reloaded), "__awc_semantic_root_sealed__", False))
        self.assertIsNot(reloaded.compile_bundle, original_compile)
        with self.assertRaisesRegex(AttributeError, "semantic root is sealed"):
            reloaded.EXTERNAL_ACCEPTANCE_CLASSES = frozenset({"GITHUB"})
        bundle = reloaded.compile_bundle(self._retained_acceptance_document())
        self.assertTrue(reloaded.verify_bundle(bundle))


if __name__ == "__main__":
    unittest.main()
