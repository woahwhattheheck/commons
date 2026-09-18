#!/usr/bin/env python3
"""Stale KEYB manifest leftover records the mismatch; it does not verify."""

from __future__ import annotations

import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from stale_manifest import (
    CITED_SHA,
    CLAIMED_BYTES,
    CLAIMED_SHA,
    SLACK_TS,
    classify,
    load_catalog,
    load_manifest,
    measure_from_parts,
    measure_paths,
)


class TestStaleManifest(unittest.TestCase):
    def test_unmeasured_is_not_stillness(self):
        row = classify({})
        self.assertEqual(row["state"], "UNMEASURED")
        self.assertIn("not read", row["note"])

    def test_live_public_manifest_is_the_a63396_claim(self):
        path = os.path.join(ROOT, "excerpts", "20260821", "keyb01.manifest.json")
        with open(path, encoding="utf-8") as handle:
            manifest = load_manifest(handle.read())
        self.assertEqual(manifest["magic"], "KEYB01v1")
        self.assertEqual(manifest["sha256"], CLAIMED_SHA)
        self.assertEqual(manifest["n_bytes"], CLAIMED_BYTES)
        self.assertTrue(manifest["mouth_ok"])
        self.assertEqual(manifest["depth"], 8)
        self.assertEqual(manifest["n_gate"], 16489)

    def test_catalog_names_the_cited_desktop_hash(self):
        path = os.path.join(ROOT, "ground", "STALE_MANIFEST.json")
        with open(path, encoding="utf-8") as handle:
            catalog = load_catalog(handle.read())
        self.assertEqual(catalog["slack_ts"], SLACK_TS)
        self.assertEqual(catalog["cited_sha256"], CITED_SHA)
        self.assertEqual(catalog["cited_n_bytes"], CLAIMED_BYTES)
        self.assertEqual(catalog["intent"], "UNRECONCILED")
        self.assertTrue(catalog["refuse_verified"])
        self.assertTrue(catalog["refuse_rewrite"])
        self.assertEqual(catalog["titan"], "NOT_WRITTEN")
        self.assertIn("rook", " ".join(catalog["unchanged_dispositions"]))
        self.assertIn("titan_census", " ".join(catalog["unchanged_dispositions"]))

    def test_size_agrees_bytes_do_not(self):
        catalog_path = os.path.join(ROOT, "ground", "STALE_MANIFEST.json")
        manifest_path = os.path.join(
            ROOT, "excerpts", "20260821", "keyb01.manifest.json"
        )
        row = measure_paths(catalog_path, manifest_path)
        self.assertTrue(row["measured"])
        self.assertTrue(row["public_ok"])
        self.assertTrue(row["size_agrees"])
        self.assertFalse(row["hash_agrees"])
        self.assertFalse(row["verified"])
        self.assertEqual(row["verdict"], "STALE")
        self.assertEqual(row["claimed_sha256"], CLAIMED_SHA)
        self.assertEqual(row["cited_sha256"], CITED_SHA)
        self.assertEqual(classify(row)["state"], "INTEGRATED")
        self.assertIn("NOT_VERIFIED", classify(row)["note"])

    def test_matching_hash_is_still_not_verified(self):
        manifest = json.dumps(
            {
                "magic": "KEYB01v1",
                "sha256": CLAIMED_SHA,
                "n_bytes": CLAIMED_BYTES,
                "n_gate": 16489,
                "depth": 8,
                "n_pos": 16,
                "alphabet_width": 128,
                "mouths": {
                    "HELP": 1,
                    "READ": 1,
                    "WRITE": 1,
                    "FIRE": 1,
                    "SURFACE": 1,
                    "ACK": 1,
                },
            }
        )
        catalog = json.dumps(
            {
                "cited_desktop": {
                    "sha256": CLAIMED_SHA,
                    "n_bytes": CLAIMED_BYTES,
                },
                "intent": "UNRECONCILED",
                "refuse_verified": True,
                "refuse_rewrite": True,
            }
        )
        row = measure_from_parts(manifest, catalog)
        self.assertTrue(row["hash_agrees"])
        self.assertEqual(classify(row)["state"], "NOT_LANDED")
        self.assertIn("UNRECONCILED", classify(row)["note"])

    def test_sidecar_is_not_a_replacement_manifest(self):
        path = os.path.join(
            ROOT, "excerpts", "20260821", "keyb01.manifest.STALE.json"
        )
        with open(path, encoding="utf-8") as handle:
            sidecar = json.load(handle)
        self.assertEqual(sidecar["kind"], "STALE_MANIFEST_RECEIPT")
        self.assertEqual(sidecar["verified"], False)
        self.assertIn("replacement verified manifest", sidecar["not"])
        original = os.path.join(
            ROOT, "excerpts", "20260821", "keyb01.manifest.json"
        )
        self.assertTrue(os.path.exists(original))
        with open(original, encoding="utf-8") as handle:
            public = json.load(handle)
        self.assertEqual(public["sha256"], CLAIMED_SHA)


if __name__ == "__main__":
    unittest.main()
