#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'host'))

import fleet_ids


class FleetIdsFinderZeroTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.catalog = self.root / 'catalog.json'
        self.posts = self.root / 'p'
        self.posts.mkdir()
        self.catalog.write_text(json.dumps({'ids': ['target-a']}), encoding='utf-8')

    def calibrate(self):
        (self.posts / f'{fleet_ids.CALIBRATION_ID}.md').write_text('known present\n', encoding='utf-8')

    def test_baseline_failure_shape_is_no_longer_zero(self):
        self.calibrate()
        with mock.patch.object(fleet_ids.os, 'listdir', side_effect=OSError('boom')):
            row = fleet_ids.measure_paths(str(self.catalog), str(self.posts))
        self.assertFalse(row['measured'])
        self.assertEqual(row['finder_state'], fleet_ids.FINDER_UNVERIFIED)
        self.assertIsNone(row['observed'])
        self.assertEqual(row['miss_behavior'], fleet_ids.FINDER_UNVERIFIED)
        self.assertEqual(fleet_ids.classify(row)['state'], fleet_ids.FINDER_UNVERIFIED)
        self.assertNotIn('present_count', row)

    def test_missing_posts_directory_is_unverified(self):
        row = fleet_ids.measure_paths(str(self.catalog), str(self.root / 'missing'))
        self.assertFalse(row['measured'])
        self.assertEqual(fleet_ids.classify(row)['state'], fleet_ids.FINDER_UNVERIFIED)

    def test_missing_calibrator_voids_absence(self):
        (self.posts / 'unrelated.md').write_text('x\n', encoding='utf-8')
        row = fleet_ids.measure_paths(str(self.catalog), str(self.posts))
        self.assertFalse(row['measured'])
        self.assertFalse(row['calibrated'])
        self.assertEqual(row['calibration_missed'], [fleet_ids.CALIBRATION_ID])
        self.assertEqual(fleet_ids.classify(row)['state'], fleet_ids.FINDER_UNVERIFIED)

    def test_calibrated_true_miss_records_xyz(self):
        self.calibrate()
        row = fleet_ids.measure_paths(str(self.catalog), str(self.posts))
        self.assertTrue(row['measured'])
        self.assertTrue(row['calibrated'])
        self.assertTrue(row['search_space']['complete'])
        self.assertEqual(row['present_count'], 0)
        self.assertEqual(row['missing_count'], 1)
        self.assertEqual(row['observed']['present_count'], 0)
        self.assertEqual(row['observed']['missing_count'], 1)
        self.assertEqual(row['miss_behavior'], 'CALIBRATED_ABSENCE')
        self.assertEqual(fleet_ids.classify(row)['state'], 'NOT_LANDED')

    def test_calibrated_found_preserves_integration_verdict(self):
        self.calibrate()
        (self.posts / 'target-a.md').write_text('present\n', encoding='utf-8')
        row = fleet_ids.measure_paths(str(self.catalog), str(self.posts))
        self.assertTrue(row['measured'])
        self.assertEqual(row['present'], ['target-a'])
        self.assertEqual(row['miss_behavior'], 'FOUND')
        self.assertEqual(fleet_ids.classify(row)['state'], 'INTEGRATED')

    def test_no_posts_dir_is_unverified_not_empty_listing(self):
        row = fleet_ids.measure_paths(str(self.catalog), None)
        self.assertFalse(row['measured'])
        self.assertEqual(row['finder_state'], fleet_ids.FINDER_UNVERIFIED)
        self.assertIn('channel_or_path', row['search_space']['missing'])

    def test_main_exit_is_two_for_finder_failure(self):
        with mock.patch.object(fleet_ids, 'measure_paths', return_value={
            'measured': False,
            'finder_state': fleet_ids.FINDER_UNVERIFIED,
            'finder_note': 'forced failure',
            'titan': 'NOT_WRITTEN',
        }):
            with mock.patch.object(sys, 'stdout'):
                self.assertEqual(fleet_ids.main(['--catalog', str(self.catalog)]), 2)


if __name__ == '__main__':
    unittest.main()
