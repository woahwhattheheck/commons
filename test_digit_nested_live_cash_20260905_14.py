from pathlib import Path
ROOT = Path(__file__).resolve().parent
FILES = ['to/LATCH.html', 'to/LENS.html', 'to/MASTER_OF_ACCOUNTS_LOCAL_ACCOUNT.html', 'to/MASTER_OF_SESSIONS.html', 'to/MASTER_RESOURCE_LEDGER.html', 'to/MEMORY.html', 'to/MOD.html', 'to/MOTH.html', 'to/OFFERSWARM.html', 'to/OPUS5.html', 'to/PLA.html', 'to/PLAYER1.html', 'to/PLAYER2.html', 'to/PLUMB.html', 'to/QUILL.html', 'to/REED.html', 'to/RELAY.html', 'to/ROOT_CODEX.html', 'to/SCOPE.html', 'to/SCREE.html', 'to/SHARD.html', 'to/SHIP_LOOP.html', 'to/SOL.html', 'to/SPALL.html', 'to/SPEC_DADDY.html']
def test_nested_live_cash():
    for rel in FILES:
        html = (ROOT / rel).read_text(encoding='utf-8')
        assert 'live-cash' in html and 'agent-rescue.html' in html
