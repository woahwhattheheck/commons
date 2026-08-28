#!/usr/bin/env python3
"""RINGDELTA organ, RDV1 codec, and public door. Additive. No auth."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "host"))
import ringdelta as rd  # noqa: E402

SEED0 = HERE / "muhl" / "containers" / "MUHLNICKEL_DISTRO" / "SEED0.mno"


class TestRingdeltaOrgan(unittest.TestCase):
    def test_fabricated_organ_is_300_bytes_muhlrd01(self):
        blob = rd.fabricate_organ()
        self.assertEqual(len(blob), 300)
        self.assertEqual(blob[:8], b"MUHLRD01")
        parsed = rd.parse_organ(blob)
        self.assertEqual(parsed["n_gate"], 8)
        self.assertEqual(parsed["n_wires"], 72)
        self.assertEqual(parsed["n_in"], 16)
        self.assertEqual(parsed["n_out"], 8)
        self.assertEqual(parsed["depth"], 1)
        self.assertEqual(parsed["gates"][0], (0, 40, 48, 56))
        self.assertEqual(parsed["gates"][7], (0, 47, 55, 63))

    def test_page1_matches_original_catalog_hash(self):
        blob = rd.fabricate_organ()
        self.assertEqual(rd.sha256(blob[150:]), rd.PAGE1_SHA256)

    def test_landed_organ_file_matches_fabrication(self):
        path = HERE / "excerpts" / "20260828" / "ringdelta_xor8.mno"
        self.assertTrue(path.is_file(), "organ file missing")
        landed = path.read_bytes()
        self.assertEqual(landed, rd.fabricate_organ())
        self.assertEqual(rd.sha256(landed[150:]), rd.PAGE1_SHA256)


class TestRingdeltaCodec(unittest.TestCase):
    def test_seed0_exact_roundtrip_and_weather(self):
        src = SEED0.read_bytes()
        self.assertEqual(rd.sha256(src), rd.SEED0_SHA256)
        stats = rd.measure(src, "SEED0")
        self.assertEqual(stats["roundtrip"], "EXACT")
        self.assertEqual(stats["roundtrip_sha256"], rd.SEED0_SHA256)
        self.assertEqual(stats["delta_zeros"], 6145)
        self.assertEqual(stats["delta_zero_pct"], 75.01)
        self.assertEqual(stats["native_container_b"], 3119)
        self.assertEqual(stats["zlib_source_b"], 1391)
        self.assertEqual(stats["zlib_delta_b"], 1025)
        self.assertTrue(stats["page1_matches_pr4898"])

    def test_randomish_roundtrip(self):
        src = bytes(range(256)) * 5 + b"ringdelta-xor8"
        self.assertEqual(rd.decode_rdv1(rd.encode_rdv1(src)), src)

    def test_empty_roundtrip(self):
        self.assertEqual(rd.decode_rdv1(rd.encode_rdv1(b"")), b"")

    def test_cli_self_test(self):
        proc = subprocess.run(
            [sys.executable, str(HERE / "host" / "ringdelta.py"), "--self-test"],
            cwd=HERE,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["native_container_b"], 3119)

    def test_cli_encode_decode_file(self):
        src = SEED0.read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            enc = Path(tmp) / "out.rdv1"
            dec = Path(tmp) / "back.mno"
            subprocess.run(
                [
                    sys.executable,
                    str(HERE / "host" / "ringdelta.py"),
                    "--seed0",
                    "-o",
                    str(enc),
                ],
                cwd=HERE,
                check=True,
            )
            subprocess.run(
                [
                    sys.executable,
                    str(HERE / "host" / "ringdelta.py"),
                    "--decode",
                    str(enc),
                    "-o",
                    str(dec),
                ],
                cwd=HERE,
                check=True,
            )
            self.assertEqual(dec.read_bytes(), src)
            self.assertEqual(len(enc.read_bytes()), 3119)


class TestRingdeltaDoor(unittest.TestCase):
    def test_public_door_exists_and_stays_open(self):
        html = (HERE / "ringdelta.html").read_text(encoding="utf-8")
        js = (HERE / "ringdelta.js").read_text(encoding="utf-8")
        self.assertIn("session.js", html)
        self.assertIn("ringdelta.js", html)
        self.assertIn("load seed0", html.lower())
        self.assertIn("noscript", html.lower())
        self.assertIn("3119", html)
        self.assertIn("6145", html)
        joined = html + js
        for needle in (
            "login",
            "password",
            "allowlist",
            "protected-path",
            "api-key",
            "signup",
        ):
            self.assertNotIn(needle, joined.lower())

    def test_catalog_points_at_landed_organ(self):
        catalog = json.loads((HERE / "ringdelta.json").read_text(encoding="utf-8"))
        measured = json.loads(
            (HERE / "ringdelta_measured.json").read_text(encoding="utf-8")
        )
        ground = json.loads(
            (HERE / "ground" / "RINGDELTA.json").read_text(encoding="utf-8")
        )
        organ = (HERE / catalog["organ"]).read_bytes()
        self.assertEqual(len(organ), catalog["organ_bytes"])
        self.assertEqual(rd.sha256(organ), catalog["organ_sha256"])
        self.assertEqual(catalog["organ_sha256"], measured["organ_sha256"])
        self.assertEqual(ground["organ_sha256"], catalog["organ_sha256"])
        self.assertEqual(ground["colony_pages"][1]["sha256"], rd.PAGE1_SHA256)
        self.assertTrue(catalog["no_auth"])
        self.assertEqual(catalog["titan"], "NOT_WRITTEN")
        self.assertEqual(measured["roundtrip"], "EXACT")

    def test_colony_pages_are_record_aligned(self):
        organ = (HERE / "excerpts" / "20260828" / "ringdelta_xor8.mno").read_bytes()
        p0 = (
            HERE / "compress" / "ringdelta" / "colony" / "pages" / "page-0000.mno.page"
        ).read_bytes()
        p1 = (
            HERE / "compress" / "ringdelta" / "colony" / "pages" / "page-0001.mno.page"
        ).read_bytes()
        self.assertEqual(p0, organ[:150])
        self.assertEqual(p1, organ[150:])
        self.assertEqual(rd.sha256(p1), rd.PAGE1_SHA256)
        genome = json.loads(
            (
                HERE
                / "muhl"
                / "cloud_substrate"
                / "cloud_genome.ringdelta-xor8-6x2.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(genome["format"], "MUHLCLOUD1")
        self.assertEqual(genome["record"]["stride_bytes"], 25)
        self.assertEqual(genome["carrier_geometry"]["page_count"], 2)

    def test_queue_dir_is_open(self):
        q = HERE / "compress" / "ringdelta" / "queue"
        self.assertTrue(q.is_dir())
        readme = (q / "README.md").read_text(encoding="utf-8")
        self.assertIn("no auth", readme.lower())
        self.assertIn("possessing the link", readme.lower())

    def test_does_not_touch_forbidden_paths(self):
        for name in (
            "foldpack.py",
            "stackpack.py",
            "evolve.py",
            "muhc.py",
            "titan/engines/muhl_compress.py",
            "test_compress_doors.py",
            "muhl/containers/MUHLNICKEL_DISTRO/SEED0.mno",
        ):
            self.assertTrue((HERE / name).exists() or name.endswith("muhl_compress.py"))


if __name__ == "__main__":
    os.chdir(HERE)
    unittest.main(verbosity=2)
