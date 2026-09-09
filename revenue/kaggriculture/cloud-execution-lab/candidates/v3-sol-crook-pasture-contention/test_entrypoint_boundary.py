# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import json
import unittest

import agent as candidate
from test_pasture_contention import fixture


class EntrypointBoundaryTests(unittest.TestCase):
    def setUp(self):
        candidate._parent._INSTANCE = None
        self.features = json.loads((candidate.ROOT / "TITAN-CONFIG.json").read_text())

    def tearDown(self):
        candidate._parent._INSTANCE = None

    def instance(self):
        return candidate._parent._new_instance(candidate.ROOT, copy.deepcopy(self.features))

    def test_constructor_hook_preserves_canonical_instance_type(self):
        direct = candidate._parent_new_instance(candidate.ROOT, copy.deepcopy(self.features))
        guarded = self.instance()
        self.assertIs(type(guarded), type(direct))
        self.assertTrue(guarded._sol_crook_initialize_bound)
        self.assertFalse(guarded.ready)

    def test_real_initialization_binds_before_frozen_selected(self):
        instance = self.instance()
        instance._initialize()
        self.assertTrue(instance.ready)
        self.assertIsNotNone(instance.spatial)
        self.assertTrue(instance.spatial._sol_crook_installed)
        self.assertEqual(instance.spatial._sol_crook_boundary,
                         "before_frozen_selected")

        # Exercise the real initialized wrapper while replacing only its
        # predecessor transform with identity. The returned bytes prove the
        # guard is on SpatialTempo's selected-producer boundary, not outside
        # canonical main.agent after bookkeeping has committed.
        instance.spatial._sol_crook_parent_transform = (
            lambda observation, selected, controller: selected
        )
        observation, selected = fixture()
        original = copy.deepcopy(selected)
        result = instance.spatial.transform(observation, selected, instance.controller)
        self.assertEqual(selected, original)
        self.assertEqual(result["farmer"], ["HARVEST"])
        self.assertEqual(result["hands"], [["CARE"]])
        self.assertTrue(instance.diagnostics["pasture_contention"]["changed"])

    def test_nonwitness_keeps_selected_object_identity(self):
        instance = self.instance()
        instance._initialize()
        instance.spatial._sol_crook_parent_transform = (
            lambda observation, selected, controller: selected
        )
        observation, selected = fixture(actions=[["HARVEST"], ["PASS"]])
        result = instance.spatial.transform(observation, selected, instance.controller)
        self.assertIs(result, selected)
        self.assertFalse(instance.diagnostics["pasture_contention"]["changed"])

    def test_reconstruction_reuses_one_wrapper_without_nesting(self):
        instance = self.instance()
        instance._initialize()
        spatial = instance.spatial
        wrapper = spatial.transform
        parent_transform = spatial._sol_crook_parent_transform

        instance.ready = False
        instance._initialize()

        self.assertIs(instance.spatial, spatial)
        self.assertIs(spatial.transform, wrapper)
        self.assertIs(spatial._sol_crook_parent_transform, parent_transform)
        self.assertTrue(spatial._sol_crook_installed)


if __name__ == "__main__":
    unittest.main()
