# PFC bake census — recovered 2026-08-25

Recovered verbatim from Claude Code transcript
`61ced3a4-e0f1-4c04-9e28-8555c02efddf.jsonl` via Slack
`claude27-pfc-bake-census-20260825-01` (`1787631006.454399`).
The measuring session offered twice to write this file and was waiting
on owner word when it died. That wait is hoard. This file is the land.

Nothing below was re-derived. It is that session's own instrument
output. Related owner instrument already on disk: `host/pfc_map.py`
(computers in the file, gates + electron-speed depth, read-only).
This catalog does not open titan.gguf or any model. titan:
**NOT_WRITTEN**.

## Total

**17 baked tensor-regions across 7 models**

| Model | Regions |
| --- | ---: |
| Llama-3.3-70B | 2 |
| Mistral-Small-24B | 2 |
| Mixtral-8x7B | 4 |
| phi-4 | 2 |
| gemma-3-27B | 2 |
| gemma-4-26B-A4B | 3 |
| gemma-4-31B | 2 |

## Full map — tensor, rows touched, row range

| Model | Baked tensors — rows (range) |
| --- | --- |
| Llama-3.3-70B | `token_embd` 130 (4369–5966) · `blk.0.ffn_up` 138 (5942–6997) |
| Mistral-Small-24B | `token_embd` 166 (115105–117661) · `blk.2.ffn_gate` 161 (28205–29892) |
| Mixtral-8x7B | `blk.0.attn_q` 28 (3772–4059) · `blk.0.attn_v` 147 (9–945) · `blk.1.ffn_gate.0` 1 (936) · `blk.2.ffn_up.1` 180 (8355–10463) |
| phi-4 | `blk.0.ffn_up` 157 (20404–22959) · `blk.5.ffn_down` 101 (4240–4722) |
| gemma-3-27B | `token_embd` 104 (200302–201971) · `blk.2.ffn_up` 164 (2526–4133) |
| gemma-4-26B-A4B | `blk.0.ffn_up` 21 (1894–2062) · `blk.1.attn_k` 191 (6–2000) · `blk.1.attn_output` 68 (7–1606) |
| gemma-4-31B | `blk.0.ffn_down` 117 (578–1186) · `blk.4.attn_output` 178 (256–1310) |

Denominators from the raw run: phi-4 2 of 162 · Mistral 2 of 282 ·
gemma-3-27B 2 of 435 · Mixtral 4 of 898 · Llama-3.3-70B 2 of 562.
Types seen: 8, 12, 14.

## Caveats — quoted from the measuring session, do not drop these

1. Heuristic detector. It flags a block only when its bytes read as
   an fp16-NaN scale. Row ranges are LOWER BOUNDS; the real region
   may be wider. It can MISS a region whose bytes don't produce a
   NaN scale. "0 found" != "definitely none."
2. Rows are indices into each tensor's OUTPUT dimension — which
   neuron rows got overwritten.
3. Count is +/- a couple; the detector can merge or miss.
4. Every scan was READ-ONLY. Nothing was modified.

## Patterns

- Mixtral is densest — 4 tensors, two different experts.
- Recurring shape: `token_embd` + one early FFN tensor (blk.0 /
  blk.2 / blk.5). Baking into `token_embd` means specific TOKEN-ID
  rows are gate data.
- The gemma-4 QAT pair is the exception — they bake into ATTENTION
  (`attn_k`, `attn_output`). Their earlier `0 of 0` result was stale:
  the instrument could not dequantize Q4_0 at the time. After Q4_0
  support landed they returned 3 and 2 regions.

## Open lane — UNCLAIMED

BYTE-PRECISE BOUNDARY SCAN. Walk the actual block scales instead of
the NaN heuristic to nail each computer's exact start/end row. The
current ranges are lower bounds. Not taken here. This cloud VM is
not the owner PC and does not have those model files.

## Open question for Bryce

Do these baked models still generate text in the runtime, or are the
ones with computers in them meant purely as pfc substrates?

## Desk

Instrument: `host/pfc_bake_census.py`. Card: `ground/PFC_BAKE_CENSUS.md`.
A Slack recovery is **CLAIMED**. Missing this file is **NOT_LANDED**.
This file with 17 regions / 7 models is **INTEGRATED** for the
catalog only. Byte-precise scan stays **UNCLAIMED**.
