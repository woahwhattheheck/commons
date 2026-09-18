#!/usr/bin/env python3
"""Regression coverage for the Oracle Always Free Commons carrier."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent
STACK = ROOT / "infra" / "oracle_always_free"


class TestOracleAlwaysFree(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.main = (STACK / "main.tf").read_text(encoding="utf-8")
        cls.cloud_init = (STACK / "cloud-init.yaml.tftpl").read_text(encoding="utf-8")
        cls.capacity = json.loads((STACK / "capacity.json").read_text(encoding="utf-8"))
        cls.readme = (STACK / "README.md").read_text(encoding="utf-8")

    def test_exact_current_always_free_bounds(self):
        limits = self.capacity["limits"]
        self.assertEqual(self.capacity["shape"], "VM.Standard.A1.Flex")
        self.assertEqual(limits["ocpus_total"], 2)
        self.assertEqual(limits["memory_gb_total"], 12)
        self.assertEqual(limits["boot_gb"], 50)
        self.assertEqual(limits["attached_block_gb"], 150)
        self.assertEqual(limits["combined_block_gb_total"], 200)
        self.assertEqual(limits["object_storage_gb"], 20)
        self.assertEqual(limits["outbound_transfer_tb_per_month"], 10)

    def test_terraform_matches_capacity_contract(self):
        for literal in (
            'shape               = "VM.Standard.A1.Flex"',
            "ocpus         = 2",
            "memory_in_gbs = 12",
            "boot_volume_size_in_gbs = 50",
            "size_in_gbs         = 150",
        ):
            self.assertIn(literal, self.main)
        self.assertIn('device          = "/dev/oracleoci/oraclevdb"', self.main)

    def test_cloud_volume_is_copy_only_and_machine_readable(self):
        for path in ("work", "evacuation", "receipts"):
            self.assertIn(f'"$mountpoint/{path}"', self.cloud_init)
        self.assertIn('"copy_only": true', self.cloud_init)
        self.assertIn('"local_release_performed": false', self.cloud_init)
        self.assertIn("COMMONS_CLOUD_ROUTE.json", self.cloud_init)

    def test_no_destructive_storage_command_or_commons_gate(self):
        active = "\n".join(
            path.read_text(encoding="utf-8")
            for path in STACK.iterdir()
            if path.suffix in {".tf", ".tftpl", ".md", ".json"}
        ).lower()
        for forbidden in (
            "rm -rf",
            "rclone delete",
            "rclone move",
            "rclone purge",
            "ssh_authorized_keys",
            "password",
            "api_key",
            "permission gate",
            "approval gate",
        ):
            self.assertNotIn(forbidden, active)

    def test_unprovisioned_truth_boundary_is_explicit(self):
        self.assertEqual(self.capacity["state"], "READY_NOT_PROVISIONED")
        self.assertFalse(self.capacity["truth_boundary"]["provisioned"])
        self.assertFalse(self.capacity["truth_boundary"]["cloud_bytes_present"])
        self.assertFalse(self.capacity["truth_boundary"]["local_bytes_modified"])
        self.assertFalse(self.capacity["truth_boundary"]["local_release_performed"])
        self.assertIn("repository merge is not proof", self.readme.lower())


if __name__ == "__main__":
    unittest.main()
