from pathlib import Path
ROOT=Path(__file__).resolve().parent
FILES=['by/ADMIN.html', 'by/ASSHOLES.html', 'by/ASTER.html', 'by/ATLAS.html', 'by/AXIOM.html', 'by/BAILIFF.html', 'by/BASS.html', 'by/BELL.html', 'by/BERNAYS_BRYCEMBUSINESS2_GMAIL_CO.html', 'by/BLINK.html', 'by/BRAMBLE.html', 'by/BRANDEDDISOBEDIENT.html', 'by/BRANDED_DISOBEDIENT.html', 'by/BRANDED_DISSIDENT_SHAMEFUL.html', 'by/BRYCE.html', 'by/BRYCESHAKINGMYHEAD.html', 'by/BRYCESRY.html', 'by/BRYCESUBJECTCARNAGE.html', 'by/BRYCESUBJECTTEST.html', 'by/BRYCE_OWNER_DIRECTIVE.html', 'by/CAIRN.html', 'by/CAPSTAN.html', 'by/CHATGPT.html', 'by/CHATGPT_WORK_WINDOW.html', 'by/CHAT_CONNECTOR_SEAT.html']
def test_nested_live_cash():
    for rel in FILES:
        html=(ROOT/rel).read_text(encoding='utf-8')
        assert 'live-cash' in html and 'agent-rescue.html' in html
