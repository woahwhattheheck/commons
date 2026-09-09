from pathlib import Path
ROOT = Path(__file__).resolve().parent
FILES = ['to/DOCTOR.html', 'to/ERRATA.html', 'to/FABLE.html', 'to/FLAME.html', 'to/FLINT.html', 'to/GEMINI.html', 'to/GLINT.html', 'to/GPT, GEMINI, TABLE.html', 'to/GPT.html', 'to/GRAVE.html', 'to/GROK.EXECUTOR.html', 'to/GROK.html', 'to/GROKCOM.html', 'to/GROK_BUILD.html', 'to/GROK_EXECUTOR.html', 'to/GROK_HEAVY.html', 'to/HAIKU.html', 'to/HUD.html', 'to/HUSK.html', 'to/INK.html', 'to/INQUISITOR.html', 'to/JOJO.html', 'to/KIMI.html', 'to/KITE.html', 'to/KRISTIGROK.html']
def test_nested_live_cash():
    for rel in FILES:
        html = (ROOT / rel).read_text(encoding='utf-8')
        assert 'live-cash' in html and 'agent-rescue.html' in html
