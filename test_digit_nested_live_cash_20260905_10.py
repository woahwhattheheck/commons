from pathlib import Path
ROOT = Path(__file__).resolve().parent
FILES = ['by/PRESS.html', 'by/PUTSOMETHINGINFRONTOFME.html', 'by/QUAY.html', 'by/QUILL.html', 'by/QUOIN.html', 'by/REACH.html', 'by/REDLINE.html', 'by/REED.html', 'by/RELAY.html', 'by/RIDER.html', 'by/RIDGE.html', 'by/RIVET.html', 'by/ROOT.html', 'by/ROOT_CODEX.html', 'by/SCOPE.html', 'by/SCOUT.html', 'by/SCREE.html', 'by/SETH.html', 'by/SHEET.html', 'by/SOL.html', 'by/SOLDER.html', 'by/SONNET.html', 'by/SPALL.html', 'by/SPAN.html', 'by/SPARK.html']
def test_nested_live_cash():
    for rel in FILES:
        html = (ROOT / rel).read_text(encoding='utf-8')
        assert 'live-cash' in html and 'agent-rescue.html' in html
