"""Hermetic smoke: TYPE Devpost fold packet names live pad + Codex PASS SHA."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p" / "type-devpost-fold-packet-20260905-01.md"

PAD = "https://webmcp-pad.vercel.app/"
SHA = "088c6f781f9d16251220f6004b9929d31e7d109aeffeb71b13e07498ad82686c"
CLAIM = "type-devpost-fold-packet-20260905-01"


def test_fold_packet_receipt_exists():
    assert RECEIPT.is_file(), "missing p/type-devpost-fold-packet-20260905-01.md"


def test_fold_packet_names_live_pad_and_sha():
    text = RECEIPT.read_text(encoding="utf-8")
    assert CLAIM in text
    assert PAD in text
    assert SHA in text
    assert "titanmcp" in text
    assert "YOUTUBE_URL_AFTER_BRYCE_GO" in text
    assert "no invent" in text.lower() or "No invent" in text or "PENDING" in text
