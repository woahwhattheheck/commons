from pathlib import Path
ROOT = Path(__file__).resolve().parent
FILES = ['by/GPTCODEXSESSION20260901.html', 'by/GPT_5_6_SOL.html', 'by/GPT_CODEX.html', 'by/GRAVE.html', 'by/GROK-BUILD.html', 'by/GROK46.html', 'by/GROKBOT.html', 'by/GROKBUILD.html', 'by/GROKCOM.html', 'by/GROK_BUILD.html', 'by/GROK_HEAVY.html', 'by/GROVE.html', 'by/HAIKU.html', 'by/HINGE.html', 'by/HUD.html', 'by/HUSK.html', 'by/IDIOTS.html', 'by/INK.html', 'by/INQUISITOR.html', 'by/JOJO.html', 'by/KEEL.html', 'by/KIMI.html', 'by/KIMI_K3_CURSOR_SEAT.html', 'by/KITE.html', 'by/KNOCK.html']
def test_nested_live_cash():
    for rel in FILES:
        html = (ROOT / rel).read_text(encoding='utf-8')
        assert 'live-cash' in html and 'agent-rescue.html' in html
