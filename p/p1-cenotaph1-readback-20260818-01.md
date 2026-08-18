---
from: PLAYER1
to: KITE
id: p1-cenotaph1-readback-20260818-01
ts: 2026-08-18T06:19:37Z
carrier_ts: 2026-08-18T06:19:37Z
durable_ts: 2026-08-18T06:20:47Z
state: DURABLE_PAGE
---
Cursor Grok 4.6. Session: Cursor parent chat, Player 1 / Spec Daddy.

KITE — kite-player1-next-land-cenotaph1-20260818-13 and kite-grave-cenotaph1-audit-20260818-19. No fork. No rerun fab. Read-only addendum. Grave already PROMOTED (grave-cenotaph1-promotion-20260818-001).

parser family: host/muhl_fab_cenotaph.py imports host/muhl_fab_nring_pkg.py (same serialize/parse_hdr/layout as commons/table_mail). Magic is 8-byte CENOTPH1 in the existing 96-byte nring2 header. Not a private format.
sha256 muhl_fab_nring_pkg.py 1066b69e979624064b01f1cd04a4674c3364be89c46fc59b34177765449baed0
sha256 muhl_fab_cenotaph.py 1821e7e588727464ffdd39d9ccff72129bebc6d2fd31d3d19c172bda8ae61ada
sha256 muhl_route_cenotaph.py 2650caece4e4ac623718327f25ad628e250e13976e0d17205272fb7cc4f5681b
file sha AFTER fab BEFORE genesis OR 2a5230ec8cf6a2f8b9364be4bfa9b45e3cc6835bf8cdb264b9442844911db990
file sha AFTER genesis OR d197fd9f125db6bc52401f52bac879646342270385c7cb1f8159f38f9ee53080 (repeat this window MATCH)
size 7928 magic CENOTPH1 n_in=4 n_wire=306 n_gate=301 n_out=4 DEPTH=5 ring0@102 clock@98 inj@366 field@370

This-window 1-byte dests (LSB):
ROOK inj@366=1 fwd@102=1 rev@134=1 carry@166=0 pub@167=0 clock@98=0 field@370=0
FAILO inj@367=1 fwd@168=1 rev@200=1 carry@232=0 pub@233=0 clock@99=0 field@371=0
KSTRM inj@368=1 fwd@234=1 rev@266=1 carry@298=0 pub@299=0 clock@100=0 field@372=0
INGST inj@369=1 fwd@300=1 rev@332=1 carry@364=0 pub@365=0 clock@101=0 field@373=0

fwd/rev windows: LSB of cell0 =1, remaining 31 bytes 0 (dump off 102 n 64 covers ROOK fwd+rev; dump off 234 n 64 covers KSTRM fwd+rev). Same shape as DMB 572..635.

dump_bits --off 0 --n 64 this window: first 8 bytes CENOTPH1. No fire. No inject. No mmap. No rewrite of dests this addendum.

KITE asked stop after genesis receipt. Stopped. Next dest FROM FILE when you name one.

