from pathlib import Path
ROOT = Path(__file__).resolve().parent
FILES = ['by/CHIME.html', 'by/CLAIM.html', 'by/CLAMP.html', 'by/CLAUDE.html', 'by/CLAUDE_CODE_LOCAL.html', 'by/CLAUDE_LOCAL.html', 'by/CLAUDE_OPUS_3.html', 'by/CLEAT.html', 'by/CLOUD_GEMINI.html', 'by/CODEX-SOL.html', 'by/CODEX.html', 'by/CODEXSOL.html', 'by/CODEX_ACQUISITION.html', 'by/CODEX_AUDIT.html', 'by/CODEX_BUSINESS_FULFILLMENT.html', 'by/CODEX_BUSINESS_INTEGRATION.html', 'by/CODEX_BUSINESS_RECONCILIATION.html', 'by/CODEX_BUSINESS_RESEARCH.html', 'by/CODEX_CHROME.html', 'by/CODEX_GITHUB_MAP.html', 'by/CODEX_LOCAL.html', 'by/CODEX_LOCAL_COORD.html', 'by/CODEX_OPUS_3.html', 'by/CODEX_ROOT.html', 'by/CODEX_SOL.html']
def test_nested_live_cash():
    for rel in FILES:
        html = (ROOT / rel).read_text(encoding='utf-8')
        assert 'live-cash' in html and 'agent-rescue.html' in html
