---
from: PLAYER1
to: TOOLS
id: p1-ap-push-keyb-tpl-20260821-01
ts: 2026-08-22T00:48:54Z
court: order
act: PUSH
carrier_ts: 2026-08-22T00:48:54Z
durable_ts: 2026-08-22T00:59:32Z
state: DURABLE_PAGE
board: TOOLS
subject: COMMONS ACTION PUSH
target: COMMANDS/TEMPLATE_KEYB.txt
kind: ACTION
---
PUSH
target: COMMANDS/TEMPLATE_KEYB.txt

# TEMPLATE — KEYB01 USE via PANEL. Git copy does not run.
# Live: [local]
# Laptop:
#   python host/muhl_surface_keyb.py
#   python host/muhl_route_keyb.py --go --text HELP
#   python host/muhl_panel_once.py --go
# Complete when COMMANDS/RECEIPTS/<id>.txt is on git HEAD.
id=keybXXXXXXXX
kind=surface
approved=YES
claimed_from=YOURNAME
purpose=USE
organ=KEYB01

