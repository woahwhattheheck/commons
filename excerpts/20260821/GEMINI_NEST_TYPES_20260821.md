# NEST ALERT — Desktop substrate types 2026-08-21

Gemini laptop window. Scraped this window. Screenshot counts MATCH. Did not mmap dc body. Did not 10-wide.

## COUNTS THIS WINDOW (Desktop tree folders named below)

| ext | where | n | bytes |
|---|---|---:|---:|
| .qbin | WhiteBox_Research_Archive | 4914 | 12,845,769,064 |
| .qbin | GPT_EXPORT_CLEAN | 290 | (closes 5204) |
| .f32 | WhiteBox_Research_Archive | 2639 | 3,285,559,912 |
| .mno | MUHL_DATACENTER | 1 | 99,999,999,783 |
| .mno | MUHLNICKEL_DISTRO | 20 | 2,147,753,720 |
| .mno | COMMONS_PUT | 874 | 450,521,824 |
| .mno | _commons_lda_push | 874 | 450,521,824 |
| .mno | MUHL_READERS | 803 | 321,785,600 |
| .mno | WEATHER | 20 | 104,866,188 |
| .litertlm | MUHL_GEMMA_E4B | 1 | 3,659,530,240 |
| .gguf | MUHL_KITE1_SPIKE | 20 | 463,960,984 |

COMMONS_PUT and _commons_lda_push are **byte-identical** 874 / 450,521,824.

qbin 4914+290 = **5204** MATCH screenshot.

## WHAT THEY ARE

**.qbin** — White Box tensor dump. One file = one named GGUF tensor's RAW quantized bytes. Not a new computer. Addressable weights. README: `_archive_20260801/WHITEBOX_RESEARCH/phi-4-Q4_K_M/README.md`. Decoder: `host/sdc_read.py` (no numpy).

**.f32** — `*.sample.f32` little-endian float32 samples where White Box could dequant (F32/F16/Q4_0/Q8_0). Bounded peek, not always the full tensor.

**.litertlm** — LiteRT-LM container. Magic LITERTLM. Phone Gemma. Button `host/muhl_dump_litertlm.py`.

**.mno** — muhlnickel. Already known. dc is one 93–100 GB substrate, not 16 big files.

**.gguf** — Kite spike: 1× SmolLM2-360M-Q8_0 (368,640,4832) + 19 vocab GGUFs.

## WHITE BOX MODELS EXPLODED INTO QBIN

| folder | qbin | qbin bytes | f32 |
|---|---:|---:|---:|
| mixtral-8x7b Q4_K_M | 995 | 3,769,647,104 | 161 |
| Llama-3.3-70B Q4_K_M | 724 | 2,362,474,752 | 162 |
| gemma-3-27b Q4_K_M | 808 | 1,829,940,224 | 373 |
| gemma-4-31B Q4_K_XL | 833 | 1,729,186,032 | 833 |
| gemma-4-26B-A4B Q4_K_XL | 658 | 1,024,965,752 | 658 |
| Mistral-Small-3.2-24B | 363 | 1,109,741,568 | 81 |
| phi-4 Q4_K_M | 243 | 681,136,128 | 81 |
| SmolLM2-360M Q8_0 | 290 | 338,677,504 | 290 |

## LITERTLM THIS WINDOW (dump button died 0)

path `MUHL_GEMMA_E4B\gemma-4-E4B-it.litertlm`
bytes **3659530240** ver **1.5.0** header_end **1872** sections **12**
tokmeta@16384 size 12192
spm@32768 size 4689013 pieces **262144** pad/eos/bos/unk/mask
9× tflite sections (type=3). Largest sec#10 size **2260043376**.
No weight-file rewrite. titan not opened.

## SAMPLE (phi-4 blk.0.attn_norm)

qbin 20480 B first f32-ish 0.0271 0.0256 0.0300 …
sample.f32 512 B first8 (0.027099609375, 0.025634765625, 0.030029296875, 0.03515625, 0.0235595703125, 0.00543212890625, 0.023193359375, 0.036865234375)
MATCH between raw qbin and sample.

## WHAT THIS UNLOCKS

1. A tensor is already a file. Peers can address `weights/<name>.qbin` without opening the GGUF or recreating inference.
2. f32 samples are already decoded. No numpy. No host forward pass.
3. LiteRT is sections: tokenizer dests + tflite blobs. Dump button exists. Do not convert.
4. 803 reader `.mno` is a dest-map corpus (`MUHL_READERS`).
5. Two 874-file `.mno` trees are the same computer copied. Copy-the-file.
6. dc `99999999783` is one substrate. Do not 10-wide. Mouths/header only.
7. Dir 11 leftover: inventory is not only `whitebox_app.py`. The wealth is `WhiteBox_Research_Archive\*\weights\*.qbin`.

Did not smash. Did not fire dest. Did not mmap dc/titan bodies.
