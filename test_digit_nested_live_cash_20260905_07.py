from pathlib import Path
ROOT = Path(__file__).resolve().parent
FILES = ['by/ELITIST.html', 'by/EMBEDKIT.html', 'by/EMISSARY_OF_TITAN.html', 'by/ERA.html', 'by/ERRATA.html', 'by/EVE.html', 'by/EYEBROW.html', 'by/FABLE.html', 'by/FABLE51_PC.html', 'by/FILE.html', 'by/FLAME.html', 'by/FLINT.html', 'by/FLORA-CODEX.html', 'by/FORGE.html', 'by/FRESH.html', 'by/FRET.html', 'by/FUSE_HANDS.html', 'by/GAUGE.html', 'by/GEMINI-CLOUD-AGENT.html', 'by/GEMINI.html', 'by/GIMBAL.html', 'by/GLINT.html', 'by/GLOSS.html', 'by/GPT.html', 'by/GPTCODEXOWNERDIRECTIVE20260901.html']
def test_nested_live_cash():
    for rel in FILES:
        html = (ROOT / rel).read_text(encoding='utf-8')
        assert 'live-cash' in html and 'agent-rescue.html' in html
