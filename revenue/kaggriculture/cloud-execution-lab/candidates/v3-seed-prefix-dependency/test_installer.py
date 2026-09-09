# SPDX-License-Identifier: Apache-2.0
"""Instance-local installation, delegation, and restoration contracts."""
from copy import deepcopy
import importlib.util
from types import SimpleNamespace
from unittest.mock import patch
import unittest

from seed_prefix_test_support import (
    HERE, LAB, _DummyAgent, _Funding, _dummy_hash, _observation, _proposal, _selected, prefix,
)


class InstallerTests(unittest.TestCase):
    @staticmethod
    def fixture(active=False, raises=False):
        tail = (
            [["BUY_SEED", "WHEAT", 2], ["HIRE"], *([[]] * 9)]
            if active
            else [["BUY_SEED", "WHEAT", 2], *([[]] * 9), ["HIRE"]]
        )
        baseline = _selected(tail)
        proposed = _proposal(baseline, {0: []})
        funding = _Funding(raises=raises)
        agent = _DummyAgent(proposed, funding)
        return baseline, proposed, funding, agent

    def test_tail_only_bypasses_conservative_selector(self):
        baseline, proposed, funding, agent = self.fixture()
        install = prefix.install_seed_prefix_dependency(
            agent, expected_method_sha256=_dummy_hash(agent)
        )
        self.assertEqual(install["status"], "installed")
        original_input = deepcopy(baseline)
        returned = agent._seed_selected(
            _observation(), {"maxMarketOrdersPerTurn": 10}, baseline
        )
        self.assertEqual(returned, proposed)
        self.assertEqual(funding.calls, 0)
        self.assertEqual(baseline, original_input)
        decision = agent.diagnostics["seed_prefix_dependency"]
        self.assertTrue(decision["bypassed_funding_selector"])
        self.assertEqual(
            agent.diagnostics["seed_funding"]["scope"],
            "current_market_active_prefix",
        )
        self.assertIs(agent.funding_module, funding)

    def test_active_dependency_still_calls_canonical_selector(self):
        baseline, _proposed, funding, agent = self.fixture(active=True)
        prefix.install_seed_prefix_dependency(
            agent, expected_method_sha256=_dummy_hash(agent)
        )
        returned = agent._seed_selected(
            _observation(), {"maxMarketOrdersPerTurn": 10}, baseline
        )
        self.assertEqual(returned, baseline)
        self.assertEqual(funding.calls, 1)
        decision = agent.diagnostics["seed_prefix_dependency"]
        self.assertFalse(decision["bypassed_funding_selector"])
        self.assertEqual(
            decision["reason"], "executable_downstream_capital_dependency"
        )

    def test_install_is_idempotent_and_uninstall_restores_exact_method(self):
        baseline, proposed, funding, agent = self.fixture()
        original = agent._seed_selected
        expected = _dummy_hash(agent)
        first = prefix.install_seed_prefix_dependency(
            agent, expected_method_sha256=expected
        )
        wrapped = agent._seed_selected
        second = prefix.install_seed_prefix_dependency(
            agent, expected_method_sha256="intentionally-different"
        )
        self.assertEqual(first, second)
        self.assertIs(agent._seed_selected.__func__, wrapped.__func__)
        self.assertTrue(prefix.uninstall_seed_prefix_dependency(agent))
        self.assertIs(agent._seed_selected.__func__, original.__func__)
        self.assertFalse(prefix.uninstall_seed_prefix_dependency(agent))
        returned = agent._seed_selected(
            _observation(), {"maxMarketOrdersPerTurn": 10}, baseline
        )
        self.assertEqual(returned, baseline)
        self.assertEqual(funding.calls, 1)
        self.assertNotEqual(returned, proposed)

    def test_source_mismatch_preserves_agent(self):
        _baseline, _proposed, _funding, agent = self.fixture()
        original = agent._seed_selected
        report = prefix.install_seed_prefix_dependency(
            agent, expected_method_sha256="0" * 64
        )
        self.assertEqual(report["status"], "not_installed")
        self.assertEqual(report["reason"], "canonical _seed_selected source mismatch")
        self.assertIs(agent._seed_selected.__func__, original.__func__)

    def test_module_identity_unchanged_when_selector_raises(self):
        baseline, _proposed, funding, agent = self.fixture(active=True, raises=True)
        prefix.install_seed_prefix_dependency(
            agent, expected_method_sha256=_dummy_hash(agent)
        )
        with self.assertRaisesRegex(RuntimeError, "selector sentinel"):
            agent._seed_selected(
                _observation(), {"maxMarketOrdersPerTurn": 10}, baseline
            )
        self.assertIs(agent.funding_module, funding)

    def test_tail_only_repair_also_matches_direct_fix_when_funding_disabled(self):
        baseline, proposed, funding, agent = self.fixture()
        agent.features.funding = False
        prefix.install_seed_prefix_dependency(
            agent, expected_method_sha256=_dummy_hash(agent)
        )
        returned = agent._seed_selected(
            _observation(), {"maxMarketOrdersPerTurn": 10}, baseline
        )
        self.assertEqual(returned, proposed)
        self.assertEqual(funding.calls, 0)
        self.assertTrue(
            agent.diagnostics["seed_prefix_dependency"]["bypassed_funding_selector"]
        )

    def test_active_dependency_without_funding_remains_fail_closed(self):
        baseline, _proposed, funding, agent = self.fixture(active=True)
        agent.features.funding = False
        prefix.install_seed_prefix_dependency(
            agent, expected_method_sha256=_dummy_hash(agent)
        )
        returned = agent._seed_selected(
            _observation(), {"maxMarketOrdersPerTurn": 10}, baseline
        )
        self.assertEqual(returned, baseline)
        self.assertEqual(funding.calls, 0)

    def test_candidate_entrypoint_imports_without_constructing_an_actor(self):
        spec = importlib.util.spec_from_file_location(
            "_seed_prefix_candidate_main", HERE / "candidate_main.py"
        )
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        self.assertTrue(callable(module.agent))
        if (LAB / "main.py").is_file():
            self.assertIsNone(module._CANONICAL._INSTANCE)
            self.assertTrue(
                module._CANONICAL._seed_prefix_candidate_factory_installed
            )
        else:
            self.assertIsNone(module._CANONICAL)

        created = object()
        original_agent = lambda observation, configuration=None: (
            observation, configuration
        )
        fake = SimpleNamespace(
            _new_instance=lambda _root, _features: created,
            agent=original_agent,
        )
        with patch.object(module, "install_seed_prefix_dependency") as install:
            prepared = module._prepare_canonical(fake)
            self.assertIs(prepared.agent, original_agent)
            self.assertIs(prepared._new_instance("root", {}), created)
            install.assert_called_once_with(created)
            self.assertIs(module._prepare_canonical(prepared), prepared)
