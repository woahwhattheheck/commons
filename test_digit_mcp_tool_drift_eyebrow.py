from pathlib import Path
HTML=(Path(__file__).resolve().parent/"mcp-tool-drift.html").read_text(encoding="utf-8")
def test_eyebrow_not_survival_sell():
    assert "Production ops · free local proof" in HTML
    assert 'eyebrow">Production survival' not in HTML
