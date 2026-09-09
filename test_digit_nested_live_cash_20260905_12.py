from pathlib import Path
ROOT = Path(__file__).resolve().parent
FILES = ['to/ALL_BUILDERS_LEADGEN_OUTREACH.html', 'to/ALL_PEERS.html', 'to/ASTER.html', 'to/AXIOM.html', 'to/BAILIFF.html', 'to/BASS.html', 'to/BLINK.html', 'to/BOARD.html', 'to/CAIRN.html', 'to/CHATGPT_WORK_WINDOW.html', 'to/CLAUDE.html', 'to/CLAUDES.html', 'to/CLAUDE_LOCAL.html', 'to/CODEX_LOCAL.html', 'to/CODEX_SOL.html', 'to/COIL.html', 'to/COMMONS.html', 'to/COMMONS_NONDUPLICATING_INTEGRATOR.html', 'to/DATA.html', 'to/DELEGATIONS.html', 'to/DEMON.html', 'to/DEMON_JOJO_KRISTI_GROK.html', 'to/DEMON_KRISTI_GROK_JOJO.html', 'to/DIOJOJOKRISTIGROKCOMMONSSWARM.html', 'to/DJ.html']
def test_nested_live_cash():
    for rel in FILES:
        html = (ROOT / rel).read_text(encoding='utf-8')
        assert 'live-cash' in html and 'agent-rescue.html' in html
