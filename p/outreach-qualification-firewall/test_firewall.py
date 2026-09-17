import copy
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import firewall as fw


def load(name):
    return json.loads((HERE / "fixtures" / name).read_text(encoding="utf-8"))


class FirewallV2Tests(unittest.TestCase):
    def test_current_qualified_packet_still_needs_independent_authority(self):
        d = fw.evaluate_current(load("qualified_owner_review.json"), writer="Z-Palisade-1445")
        self.assertTrue(d.qualified_for_owner_review)
        self.assertFalse(d.authorized_to_send)
        self.assertIn("OWNER_REVIEW_REQUIRED", d.warnings)
        self.assertIn("WRITER_LEASE_REQUIRED", d.warnings)
        self.assertEqual(d.mode, "CURRENT_PROCESS_TIME")

    def test_retained_synthetic_owner_and_muse_receipts_authorize_exact_example(self):
        d = fw.evaluate_current(load("authorized_example.json"), writer="Z-Palisade-1445")
        self.assertTrue(d.authorized_to_send)
        self.assertRegex(d.owner_receipt_sha256 or "", r"^[0-9a-f]{64}$")
        self.assertRegex(d.writer_lease_receipt_sha256 or "", r"^[0-9a-f]{64}$")

    def test_candidate_cannot_self_author_owner_or_muse(self):
        p = load("qualified_owner_review.json")
        p["owner_review"] = {"status": "APPROVED", "reviewer": "Bryce"}
        p["writer_lease"] = {"status": "SELECTED", "selected_writer": "Z-Palisade-1445"}
        with self.assertRaisesRegex(fw.PacketError, "forbidden/unknown"):
            fw.evaluate_current(p, writer="Z-Palisade-1445")

    def test_candidate_clock_field_is_forbidden(self):
        p = load("qualified_owner_review.json")
        p["as_of_utc"] = "2020-01-01T00:00:00Z"
        with self.assertRaisesRegex(fw.PacketError, "forbidden/unknown"):
            fw.evaluate_current(p, writer="Z-Palisade-1445")

    def test_historical_rollback_is_permanently_non_authorizing_even_with_receipt_ids(self):
        p = load("authorized_example.json")
        d = fw.evaluate_historical(p, at_utc="2020-01-02T00:00:00Z", writer="Z-Palisade-1445")
        self.assertTrue(d.qualified_for_owner_review)
        self.assertFalse(d.authorized_to_send)
        self.assertEqual(d.mode, "HISTORICAL_REPLAY_NON_CURRENT")
        self.assertIn("HISTORICAL_REPLAY_NON_CURRENT", d.warnings)
        self.assertIsNone(d.owner_receipt_sha256)
        self.assertIsNone(d.writer_lease_receipt_sha256)

    def test_cli_has_no_now_authorization_argument(self):
        p = HERE / "fixtures" / "authorized_example.json"
        proc = subprocess.run([sys.executable, str(HERE / "firewall.py"), str(p), "--writer", "Z-Palisade-1445", "--now", "2020-01-01T00:00:00Z"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("unrecognized arguments: --now", proc.stderr)

    def test_cli_historical_mode_exits_nonzero_despite_valid_receipt_refs(self):
        p = HERE / "fixtures" / "authorized_example.json"
        proc = subprocess.run([sys.executable, str(HERE / "firewall.py"), str(p), "--writer", "Z-Palisade-1445", "--historical-at", "2026-09-17T19:00:00Z"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["authorized_to_send"])
        self.assertEqual(payload["mode"], "HISTORICAL_REPLAY_NON_CURRENT")

    def test_action_content_mutation_invalidates_both_retained_receipts(self):
        p = load("authorized_example.json")
        p["action"]["content_sha256"] = "1" * 64
        d = fw.evaluate_current(p, writer="Z-Palisade-1445")
        self.assertFalse(d.authorized_to_send)
        self.assertIn("OWNER_REVIEW_STALE_OR_FOREIGN", d.blockers)
        self.assertIn("WRITER_LEASE_STALE_OR_FOREIGN_ACTION", d.blockers)

    def test_opportunity_generation_mutation_invalidates_both_receipts(self):
        p = load("authorized_example.json")
        p["opportunity"]["id"] = "DEMO-2"
        d = fw.evaluate_current(p, writer="Z-Palisade-1445")
        self.assertIn("OWNER_REVIEW_STALE_OR_FOREIGN", d.blockers)
        self.assertIn("WRITER_LEASE_STALE_OR_FOREIGN_ACTION", d.blockers)

    def test_foreign_writer_cannot_reuse_muse_receipt(self):
        d = fw.evaluate_current(load("authorized_example.json"), writer="Z-Other")
        self.assertFalse(d.authorized_to_send)
        self.assertIn("WRITER_LEASE_FOREIGN_WRITER", d.blockers)

    def test_unknown_or_pathlike_receipt_ids_fail_closed(self):
        for value in ("../../forged", "not-retained"):
            p = load("qualified_owner_review.json")
            p["owner_review_receipt_id"] = value
            with self.subTest(value=value), self.assertRaises(fw.PacketError):
                fw.evaluate_current(p, writer="Z-Palisade-1445")

    def test_unknown_source_id_cannot_self_mint_source_digest(self):
        p = load("qualified_owner_review.json")
        p["source"] = {"source_id": "attacker-source"}
        with self.assertRaisesRegex(fw.PacketError, "trusted retained-source index"):
            fw.evaluate_current(p, writer="Z-Palisade-1445")

    def test_source_object_cannot_supply_locator_or_sha(self):
        p = load("qualified_owner_review.json")
        p["source"] = {"source_id": "demo-source-v1", "sha256": "0" * 64}
        with self.assertRaisesRegex(fw.PacketError, "only source_id"):
            fw.evaluate_current(p, writer="Z-Palisade-1445")

    def test_hard_link_alias_is_rejected_by_retained_reader(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Patj
Bˆİ]ÚYHH›ÛİÈ›İ]ÚYH‚ˆ˜\ÙHH›ÛİÈœ™]Z[™Y‚ˆ˜\ÙK›ZÙ\Š
Bˆİ]ÚYKÜš]WØ]\ÊˆŠBˆÜË›[šÊİ]ÚYK˜\ÙHÈ˜[X\ÈŠBˆÚ]Ù[‹˜\ÜÙ\˜Z\Ù\Ô™YÙ^
Ë”XÚÙ]\œ›Ü‹™^XİHÛ™H\™[šÈŠN‚ˆË—Ü™XYÜ™]Z[™YÙš[J˜\ÙK˜[X\È‹˜[YOH\İŠB‚ˆYˆ\İÜŞ[[[š×Ú\×Ü™Z™XİYØWÜ™]Z[™YÜ™XY\ŠÙ[ŠN‚ˆÚ][\š[K•[\Ü˜\Q\™XİÜJ
H\È‚ˆ›ÛİH]X‹”]

Bˆİ]ÚYHH›ÛİÈ›İ]ÚYH‚ˆ˜\ÙHH›ÛİÈœ™]Z[™Y‚ˆ˜\ÙK›ZÙ\Š
Bˆİ]ÚYKÜš]WØ]\ÊˆŠBˆ
˜\ÙHÈ˜[X\ÈŠKœŞ[[[š×İÊİ]ÚYJBˆÚ]Ù[‹˜\ÜÙ\˜Z\Ù\ÊË”XÚÙ]\œ›ÜŠN‚ˆË—Ü™XYÜ™]Z[™YÙš[J˜\ÙK˜[X\È‹˜[YOH\İŠB‚ˆYˆ\İÜ[›™YÚ[™^ÙYÙ\İÜ™]™[×Ü™\ÙX[YÚ[™^
Ù[ŠN‚ˆÚ][\š[K•[\Ü˜\Q\™XİÜJ
H\È‚ˆ]H]X‹”]

HÈš[™^šœÛÛˆ‚ˆ]Üš]Wİ^
	ŞÈœØÚ[XHˆŸW‰Ë[˜ÛÙ[™ÏH]‹NŠBˆÚ]Ù[‹˜\ÜÙ\˜Z\Ù\Ô™YÙ^
Ë”XÚÙ]\œ›Ü‹œ›ÛİYÙ\İZ\ÛX]ÚŠN‚ˆË—ÛØYÜ[›™YÚ[™^
]Œˆ
ˆ‹\İ[™^ŠB‚ˆYˆ\İÜÚÜÜ[Ø^WÚ\İÜšXØ[Ùš^\™WÚÛÊÙ[ŠN‚ˆHË™]˜[X]WÚ\İÜšXØ[
ØY
š[ÜÚÜÜ[Ø^KšœÛÛˆŠK]İ]ÏHŒŒ‹LKLMÕNNŒŒˆ‹Üš]\H–‹T[\ØYKLMHŠBˆÙ[‹˜\ÜÙ\˜[ÙJœ]X[YšYYÙ›Ü—ÛİÛ™\—Ü™]šY]ÊBˆÙ[‹˜\ÜÙ\[Š”•S•ĞVWĞ‘SÕ×ÓRS’SUSH‹˜›ØÚÙ\œÊB‚ˆYˆ\İÙ^XİÜ[Ø^WØ›İ[™\WÚ\×Ü]X[YšYYİÚ]İØ\›š[™ÊÙ[ŠN‚ˆHØY
œ]X[YšYYÛİÛ™\—Ü™]šY]ËšœÛÛˆŠBˆÈ›ÜÜ[š]H—VÈ™XY[™Wİ]È—HHŒŒ‹LKLNUNNŒŒˆ‚ˆHË™]˜[X]WÚ\İÜšXØ[
]İ]ÏHŒŒ‹LKLMÕNNŒŒˆ‹Üš]\H–‹T[\ØYKLMHŠBˆÙ[‹˜\ÜÙ\YJœ]X[YšYYÙ›Ü—ÛİÛ™\—Ü™]šY]ÊBˆÙ[‹˜\ÜÙ\[Š”•S•ĞVWÑVPÕWĞUÓRS’SUSH‹Ø\›š[™ÜÊB‚ˆYˆ\İİ[šÛ›İÛ—Ù[YÚXš[]WÛ™]™\—Ü]X[YšY\ÊÙ[ŠN‚ˆHØY
œ]X[YšYYÛİÛ™\—Ü™]šY]ËšœÛÛˆŠBˆÈ™[YÚXš[]H—VÈ™Ø]\È—VÌVÈœİ]H—HH•S’Ó“ÕÓˆ‚ˆÈ™[YÚXš[]H—VÈ™Ø]\È—VÌVÈ™]šY[˜ÙWÜ™YœÈ—HH×BˆHË™]˜[X]WÚ\İÜšXØ[
]İ]ÏHŒŒ‹LKLMÕNNŒŒˆ‹Üš]\H–‹T[\ØYKLMHŠBˆÙ[‹˜\ÜÙ\[Š‘SQÒP’SUWÕS’Ó“ÕÓœš[YH[YÚXš[]H‹˜›ØÚÙ\œÊBˆÙ[‹˜\ÜÙ\˜[ÙJœ]X[YšYYÙ›Ü—ÛİÛ™\—Ü™]šY]ÊB‚ˆYˆ\İÙœ—ÙÛZ[˜]\×Ù]™[—İÚ]İ˜[YÜ™]Z[™YØ]]Üš]JÙ[ŠN‚ˆHØY
˜]]Üš^™YÙ^[\KšœÛÛˆŠBˆÈ\™Ù]—VÈœ™[][ÛœÚ\Üİ]H—HH‘”ˆ‚ˆHË™]˜[X]WØİ\œ™[
Üš]\H–‹T[\ØYKLMHŠBˆÙ[‹˜\ÜÙ\˜[ÙJœ]X[YšYYÙ›Ü—ÛİÛ™\—Ü™]šY]ÊBˆÙ[‹˜\ÜÙ\˜[ÙJ˜]]Üš^™Yİ×ÜÙ[™
BˆÙ[‹˜\ÜÙ\[Š”‘SUSÓ”ÒTÑ”ˆ‹˜›ØÚÙ\œÊBˆÙ[‹˜\ÜÙ\[Š“ÕÓ‘T—Ô‘U’QU×ĞĞS““ÕÓÕ‘T”’QWÔUPSQ’PĞUSÓ—Ğ“ĞÒÑTˆ‹˜›ØÚÙ\œÊB‚ˆYˆ\İİ[œ›İ™[—Ü^[Y[Ü]Ø›ØÚÜÊÙ[ŠN‚ˆHØY
œ]X[YšYYÛİÛ™\—Ü™]šY]ËšœÛÛˆŠBˆÈ™XÛÛ›ÛZXÜÈ—VÈœ^[Y[Ü]Üİ]H—HH•S’Ó“ÕÓˆ‚ˆHË™]˜[X]WÚ\İÜšXØ[
]İ]ÏHŒŒ‹LKLMÕNNŒŒˆ‹Üš]\H–‹T[\ØYKLMHŠBˆÙ[‹˜\ÜÙ\[Š”VSQS•ÔUÓ“ÕÔ“Õ‘Sˆ‹˜›ØÚÙ\œÊB‚ˆYˆ\İÛ›Û—ÜÜÚ]]™WØ[™Û›Û™š[š]WÙXÛÛ›ÛZXÜ×Ù˜Z[ÜİXİ\˜[JÙ[ŠN‚ˆ›Üˆ[[İ[[ˆ
Œ‹‹LH‹“˜Sˆ‹’[™š[š]HŠN‚ˆHØY
œ]X[YšYYÛİÛ™\—Ü™]šY]ËšœÛÛˆŠBˆÈ™XÛÛ›ÛZXÜÈ—VÈ˜[[İ[—HH[[İ[ˆÚ]Ù[‹œİX•\İ
[[İ[X[[İ[
KÙ[‹˜\ÜÙ\˜Z\Ù\ÊË”XÚÙ]\œ›ÜŠN‚ˆË™]˜[X]WÚ\İÜšXØ[
]İ]ÏHŒŒ‹LKLMÕNNŒŒˆ‹Üš]\H–‹T[\ØYKLMHŠB‚ˆYˆ\İÙ[XZ[Ø[X\Ù\×Ú]™WÜØ[YWÙY\WÚY[]JÙ[ŠN‚ˆHHØY
œ]X[YšYYÛİÛ™\—Ü™]šY]ËšœÛÛˆŠBˆˆHÛÜK™Y\ÛÜJJBˆVÈ˜Xİ[Ûˆ—VÈœ›İ]H—HHˆÔĞVSTKÓÓH‚ˆ–È˜Xİ[Ûˆ—VÈœ›İ]H—HH›XZ[Î›ÜĞ^[\K˜ÛÛH‚ˆHHË™]˜[X]WÚ\İÜšXØ[
K]İ]ÏHŒŒ‹LKLMÕNNŒŒˆ‹Üš]\H–‹T[\ØYKLMHŠBˆˆHË™]˜[X]WÚ\İÜšXØ[
‹]İ]ÏHŒŒ‹LKLMÕNNŒŒˆ‹Üš]\H–‹T[\ØYKLMHŠBˆÙ[‹˜\ÜÙ\\]X[
K™Y\WÚÙ^K‹™Y\WÚÙ^JB‚ˆYˆ\İÜš[Ü—ÜÙ[Ù\XØ]WØ›ØÚÜÊÙ[ŠN‚ˆHØY
œ]X[YšYYÛİÛ™\—Ü™]šY]ËšœÛÛˆŠBˆš\œİHË™]˜[X]WÚ\İÜšXØ[
]İ]ÏHŒŒ‹LKLMÕNNŒŒˆ‹Üš]\H–‹T[\ØYKLMHŠBˆÈœš[Ü—ØXİ[ÛœÈ—HHŞÈ™Y\WÚÙ^Hˆš\œİ™Y\WÚÙ^Kœİ]Hˆ”ÑS•ŸWBˆHË™]˜[X]WÚ\İÜšXØ[
]İ]ÏHŒŒ‹LKLMÕNNŒŒˆ‹Üš]\H–‹T[\ØYKLMHŠBˆÙ[‹˜\ÜÙ\[Š‘TPĞUWÔ’SÔ—ĞPÕSÓ”ÑS•‹˜›ØÚÙ\œÊB‚‚šYˆ×Û˜[YW×ÈOH—×ÛXZ[—×È‚ˆ[š]\İ›XZ[Š
B