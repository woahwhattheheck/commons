from pathlib import Path
ROOT=Path(__file__).resolve().parent
HTML=['titan/titan_live.html', 'titan/titan.html', 'players/CODEX_SOL-amber-hour.html', 'players/CODEX_SOL.html', 'mesh/reachability.html', 'host/counterfactual_lab/index.html', 'discord/plugin.html', 'slack/plugin.html', 'lotlens/app.html', 'ping/poll.html', 'repair-capsules/index.html', 'revenue/website_people_email_book/fixture_seller.html', 'by/DEMON/REDTEAM.html']
def test_html():
  for rel in HTML:
    if rel.endswith('.md'):
      continue
    html=(ROOT/rel).read_text(encoding='utf-8')
    assert 'live-cash' in html and 'agent-rescue.html' in html
def test_write_now():
  md=(ROOT/'ground/WRITE-NOW.md').read_text(encoding='utf-8')
  assert 'Live cash doors' in md and 'agent-rescue.html' in md
