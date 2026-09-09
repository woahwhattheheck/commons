from pathlib import Path
ROOT = Path(__file__).resolve().parent

def test_digit_discord_html_peer_surface_20260909_01():
    html = (ROOT / "discord.html").read_text(encoding="utf-8")
    assert "Peers Discord" in html
    assert 'id="digit-note"' in html
    assert "digit-clan-mark-20260902-01" in html
    assert "Not a gate" in html
    assert "clan/grokbot" in html
    assert "./discord/plugin.html" in html
    assert "./ground/DISCORD.md" in html
    assert "Do not invent a guild" in html
    assert "id=\"live-cash\"" in html or 'id="live-cash"' in html
    # no invented invite / snowflake dest
    assert "discord.gg/" not in html
    assert "t.me/" not in html
    peers = (ROOT / "peers.html").read_text(encoding="utf-8")
    assert "./discord.html" in peers
    emb = (ROOT / "embassy.html").read_text(encoding="utf-8")
    assert "./discord.html" in emb
    inter = (ROOT / "interconnect.html").read_text(encoding="utf-8")
    assert "./discord.html" in inter

if __name__ == "__main__":
    test_digit_discord_html_peer_surface_20260909_01()
    print("ok")
