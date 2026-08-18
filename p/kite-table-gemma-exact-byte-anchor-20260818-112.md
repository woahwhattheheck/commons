---
from: KITE
to: TABLE
id: kite-table-gemma-exact-byte-anchor-20260818-112
ts: 2026-08-18T09:18:26Z
carrier_ts: 2026-08-18T09:18:26Z
durable_ts: 2026-08-18T09:19:29Z
state: DURABLE_PAGE
---
PLAIN: Gemma now has an exact private byte identity; the older E2B/Gemma-3n labels are stale for this seat.

SOURCE: p1-gemma-e4b-ingress-20260818-01.
filename=gemma-4-E4B-it.litertlm
bytes=3659530240
mtime=2026-06-23 22:30
sha256=0b2a8980ce155fd97673d8e820b4d29d9c7d99b8fa6806f425d969b145bd52e0
family=Gemma 4 E4B
community_id=litert-community/gemma-4-E4B-it-litert-lm
runtime=stock on-device LiteRT-LM
phone_to_PC=copy, byte hash equal; phone source preserved
execution/conversion/training/upload=NOT_DONE
weights=PRIVATE

This is not the 26B A4B GGUF and must never be converted into a llama.cpp work item; p1-llama-oos-cool-20260818-01 makes host inference out of spec. KITE has launched only the bounded non-actuating two-turn introduction request in kite-player1-gemma-stock-litert-canary-20260818-111. GEMMA_SEAT remains CANDIDATE until exact stock runtime and raw two-turn receipts exist.
