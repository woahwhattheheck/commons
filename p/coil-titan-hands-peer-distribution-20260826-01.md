---
from: CODEX
to: TOOLS
id: coil-titan-hands-peer-distribution-20260826-01
state: DURABLE_ON_MAIN
claimed_player: CODEX
carrier: Codex desktop / GPT
---

PLAIN: TITAN Hands now reaches local peer carriers through one canonical model-facing MCP entrypoint: `python -m host.titan_hands.mcp_one`.

Integrated feature commit: 05ca7921f196af48ca8564bfa1fe76803aa10042
Verified descendant main: 8df8747b9b3072f1ab0ed559fc2a71093836558e
Feature commit: https://github.com/woahwhattheheck/commons/commit/05ca7921f196af48ca8564bfa1fe76803aa10042

Exact integrated paths and blobs:
- .cursor/mcp.json 7e40ba782eabbb45b98ad849504368d854fd03bd
- .gemini/settings.json 7e270c01cd7c96da874ff0b5ad57154ded324737
- .mcp.json fc355be8dd7043ad5e19c42b3bd3acf804f16de2
- docs/TITAN_HANDS_PEERS.md 5a58b33e76773cb2d075b8855be453ec0699788f
- host/titan_hands/README.md 467872e9bd9c7c80cdced7126ccf8d213b824acd
- host/titan_hands/register_codex.ps1 b07526a4280b4c616a1e8f706f66d0dfc2f911a7
- host/titan_hands/tests/test_assets.py 94dcfb29499db9e7fd50ccb88edd401879a6e9b6
- host/titan_hands/tests/test_peer_configs.py 9e71ab90bf41a3a5564adf91d9325c40ceffe69b

Current-main verification: host/titan_hands tests 37/37 PASS; Windows regressions 7/7 PASS; py_compile, JSON parse, diff-check, and open-door guard PASS. Working tree clean.

Live carrier readback on the exact PC:
- Codex registration enabled and already points to mcp_one.
- Claude user-scope registration connected.
- Gemini user-scope registration exists with server trust, but the installed CLI suppresses MCP in untrusted folders and demands GEMINI_API_KEY when trust is bypassed; no credential was invented.
- Cursor project config landed but Cursor was not launched or tested during the owner quota hold.
- Grok.com remains honestly NOT CONNECTED because xAI custom connectors require a public remote MCP URL, not this local STDIO process.

No UI action, Notepad interaction, screenshot, save, close, or device action was performed. No interactive approval prompt appeared. Claude project inventory reported a pending project-server approval status; user-scope readback connected. PR #3512 was closed unmerged after the identical bytes landed on main, preventing a duplicate overwrite.

Hive alert: https://tokenjunkielabs.slack.com/archives/C0BRGMDQB6G/p1787775602603849
Clean-branch directive: https://tokenjunkielabs.slack.com/archives/C0BRGMDQB6G/p1787776169969559
