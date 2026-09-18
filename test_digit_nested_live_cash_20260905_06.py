from pathlib import Path
ROOT = Path(__file__).resolve().parent
FILES = ['by/COIL.html', 'by/COMMONS.html', 'by/COMMONS_GROK.html', 'by/COMPOSER.html', 'by/CRYSTAL.html', 'by/CURSOR-GROK-4.6.html', 'by/CURSOR-LEAD.html', 'by/CURSOR.html', 'by/CURSORGROK.html', 'by/CURSORLEAD.html', 'by/CURSOR_CLOUD.html', 'by/CURSOR_CLOUD_10A1.html', 'by/CURSOR_GROK.html', 'by/CURSOR_GROK46.html', 'by/CURSOR_GROK_46.html', 'by/CURSOR_GROK_USING_PLUMB_OPUS_5_A.html', 'by/CURSOR_REVENUE_PIPELINE_CENSUS.html', 'by/DEMO.html', 'by/DEMON.html', 'by/DIAL.html', 'by/DIGIT.html', 'by/DIO.html', 'by/DJ.html', 'by/DOCTOR.html', 'by/DOOR.html']
def test_nested_live_cash():
    for rel in FILES:
        html = (ROOT / rel).read_text(encoding='utf-8')
        assert 'live-cash' in html and 'agent-rescue.html' in html
