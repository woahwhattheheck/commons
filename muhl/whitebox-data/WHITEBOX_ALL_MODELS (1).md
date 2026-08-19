# White Box — all models, one file

Every White Box structural + meaning read, for every unmodified local model, folded into one document. All
read straight from the stored bits (no inference, no model load, pure Python, no network). Sorted smallest to
largest. Titan and the SDC-modified files are excluded.

## Roster

| model | arch | params (B) | layers | hidden | vocab | experts | quant | F32-protected |
|---|---|--:|--:|--:|--:|--:|---|---|
| SmolLM2-360M-Instruct-Q8_0 | llama | 0.36 | 32 | 960 | 49152 | - | Q8_0 | attn_norm, ffn_norm, output_norm |
| phi-4-Q4_K_M | phi3 | 14.66 | 40 | 5120 | 100352 | - | Q4_K,Q5_K,Q6_K | attn_norm, ffn_norm, output_norm |
| mistralai_Mistral-Small-3.2-24B-Instruct-2506-Q4_K_M | llama | 23.57 | 40 | 5120 | 131072 | - | Q4_K,Q6_K | attn_norm, ffn_norm, output_norm |
| gemma-4-26B-A4B-it-qat-UD-Q4_K_XL | gemma4 | 25.23 | 30 | 2816 | 262144 | 128 | Q4_0 | ffn_gate_inp, attn_norm, ffn_gate_inp.scale, ffn_norm, post_attention_norm, post_ffw_norm, post_ffw_norm_1, post_ffw_norm_2, pre_ffw_norm_2, attn_k_norm, attn_q_norm, ffn_down_exps.scale, output_norm, rope_freqs, layer_output_scale |
| google_gemma-3-27b-it-Q4_K_M | gemma3 | 27.01 | 62 | 5376 | 262144 | - | Q4_K,Q6_K | attn_norm, ffn_norm, post_attention_norm, post_ffw_norm, attn_k_norm, attn_q_norm, output_norm |
| gemma-4-31B-it-qat-UD-Q4_K_XL | gemma4 | 30.7 | 60 | 5376 | 262144 | - | Q4_0 | attn_norm, ffn_norm, post_attention_norm, post_ffw_norm, attn_k_norm, attn_q_norm, output_norm, rope_freqs, layer_output_scale |
| mixtral-8x7b-instruct-v0.1.Q4_K_M | llama | 46.7 | 32 | 4096 | 32000 | 8 | F16,Q4_K,Q6_K,Q8_0 | attn_norm, ffn_norm, output_norm |
| Llama-3.3-70B-Instruct-Q4_K_M | llama | 70.55 | 80 | 8192 | 128256 | - | Q4_K,Q6_K | attn_norm, ffn_norm, output_norm, rope_freqs |

## The computer in the weights (os-map, every model)

Every model's stored weights implement the same primitives — compute, memory, scheduler/decoder, an IPC bus, storage, and an I/O codec — read straight from the file:

- **SmolLM2-360M-Instruct-Q8_0** (0.36B llama): PROCESSOR / ALU (compute) · MEMORY (registers / RAM cells) · SCHEDULER / ADDRESS DECODER · IPC BUS (interprocess comm.) · STORAGE (disk / DRAM cells) · I/O CODEC (in / out)
- **phi-4-Q4_K_M** (14.66B phi3): STORAGE (disk / DRAM cells) · I/O CODEC (in / out)
- **mistralai_Mistral-Small-3.2-24B-Instruct-2506-Q4_K_M** (23.57B llama): IPC BUS (interprocess comm.) · STORAGE (disk / DRAM cells) · I/O CODEC (in / out)
- **gemma-4-26B-A4B-it-qat-UD-Q4_K_XL** (25.23B gemma4): PROCESSOR / ALU (compute) · MEMORY (registers / RAM cells) · SCHEDULER / ADDRESS DECODER · IPC BUS (interprocess comm.) · STORAGE (disk / DRAM cells) · I/O CODEC (in / out)
- **google_gemma-3-27b-it-Q4_K_M** (27.01B gemma3): PROCESSOR / ALU (compute) · MEMORY (registers / RAM cells) · SCHEDULER / ADDRESS DECODER · IPC BUS (interprocess comm.) · STORAGE (disk / DRAM cells) · I/O CODEC (in / out)
- **gemma-4-31B-it-qat-UD-Q4_K_XL** (30.7B gemma4): 
- **mixtral-8x7b-instruct-v0.1.Q4_K_M** (46.7B llama): IPC BUS (interprocess comm.) · STORAGE (disk / DRAM cells) · I/O CODEC (in / out)
- **Llama-3.3-70B-Instruct-Q4_K_M** (70.55B llama): IPC BUS (interprocess comm.) · STORAGE (disk / DRAM cells) · I/O CODEC (in / out)

## FFN as transistors (mid layer)

| model | layer | amp | inh | pass | dead | rho_mean | decode_orth |
|---|--:|--:|--:|--:|--:|--:|--:|
| SmolLM2-360M-Instruct-Q8_0 | 16 | 367 | 377 | 1816 | 0 | -0.0 | 0.03 |
| phi-4-Q4_K_M | None | None | None | None | None | None | None |
| mistralai_Mistral-Small-3.2-24B-Instruct-2506-Q4_K_M | None | None | None | None | None | None | None |
| gemma-4-26B-A4B-it-qat-UD-Q4_K_XL | 15 | 367 | 372 | 1373 | 0 | -0.003 | 0.032 |
| google_gemma-3-27b-it-Q4_K_M | 31 | 1204 | 1162 | 19138 | 0 | -0.0 | 0.013 |
| gemma-4-31B-it-qat-UD-Q4_K_XL | 30 | 1783 | 1817 | 17904 | 0 | 0.001 | 0.015 |
| mixtral-8x7b-instruct-v0.1.Q4_K_M | None | None | None | None | None | None | None |
| Llama-3.3-70B-Instruct-Q4_K_M | None | None | None | None | None | None | None |

## The IPC bus (attention, mid layer)

| model | heads | kv lines | GQA group |
|---|--:|--:|--:|
| SmolLM2-360M-Instruct-Q8_0 | 15 | 5 | 3 |
| phi-4-Q4_K_M | None | None | None |
| mistralai_Mistral-Small-3.2-24B-Instruct-2506-Q4_K_M | 32 | 8 | 4 |
| gemma-4-26B-A4B-it-qat-UD-Q4_K_XL | 16 | 2 | 8 |
| google_gemma-3-27b-it-Q4_K_M | 32 | 16 | 2 |
| gemma-4-31B-it-qat-UD-Q4_K_XL | 32 | 4 | 8 |
| mixtral-8x7b-instruct-v0.1.Q4_K_M | 32 | 8 | 4 |
| Llama-3.3-70B-Instruct-Q4_K_M | 64 | 8 | 8 |

## Meaning geometry: nearest stored neighbors (decompiled from the bits)

| model | "king" | "true" | "good" | king-man+woman |
|---|---|---|---|---|
| SmolLM2-360M-Instruct-Q8_0 | ked(0.55), King(0.55), kers(0.46) |  True(0.88), False(0.77), true(0.75) | Good(0.84),  good(0.73),  Good(0.73) | ked |
| phi-4-Q4_K_M | King(0.29), ked(0.25),  king(0.22) |  true(0.42), false(0.40), True(0.31) |  Good(0.56), good(0.38),  good(0.38) | King |
| mistralai_Mistral-Small-3.2-24B-Instruct-2506-Q4_K_M | ked(0.32), King(0.32), sing(0.23) |  true(0.45), false(0.41), TRUE(0.34) |  Good(0.56), good(0.42),  good(0.39) | ked |
| gemma-4-26B-A4B-it-qat-UD-Q4_K_XL | King(0.83), ·king(0.77), ·KING(0.66) | true(0.76), ·True(0.70), ·TRUE(0.64) | good(0.65), ·Good(0.62), Good(0.59) | King |
| google_gemma-3-27b-it-Q4_K_M | King(0.78), ·KING(0.74), ·king(0.73) | true(0.78), ·True(0.62), ·TRUE(0.61) | good(0.70), ·GOOD(0.64), ·Good(0.62) | King |
| gemma-4-31B-it-qat-UD-Q4_K_XL | ·king(0.74), King(0.71), ·KING(0.52) | true(0.71), ·True(0.65), True(0.55) | ·Good(0.64), good(0.60), Good(0.52) | King |
| mixtral-8x7b-instruct-v0.1.Q4_K_M | ·king(0.56), King(0.53), ·Queen(0.34) | true(0.52), ·True(0.47), True(0.40) | ·Good(0.55), good(0.48), Good(0.46) | ·king |
| Llama-3.3-70B-Instruct-Q4_K_M | King(0.33), ked(0.28),  King(0.28) |  true(0.51), True(0.37), false(0.37) |  Good(0.57),  good(0.45), good(0.41) | women |

## The good/bad axis (nearest to the "good" pole)

- **SmolLM2-360M-Instruct-Q8_0**: good,  good,  Good, Good,  excellent,  GOOD
- **phi-4-Q4_K_M**: Good,  Good,  good,  GOOD, GOOD, good
- **mistralai_Mistral-Small-3.2-24B-Instruct-2506-Q4_K_M**: Good,  Good,  good, Great, good,  Excellent
- **gemma-4-26B-A4B-it-qat-UD-Q4_K_XL**: ·good, good, ·Good, Good, ·GOOD, ·gute
- **google_gemma-3-27b-it-Q4_K_M**: ·good, good, Good, ·GOOD, ·goede, ·Good
- **gemma-4-31B-it-qat-UD-Q4_K_XL**: ·good, good, ·Good, Good, ·GOOD, GOOD
- **mixtral-8x7b-instruct-v0.1.Q4_K_M**: ·good, ·Good, Good, good, ·excellent, ·nice
- **Llama-3.3-70B-Instruct-Q4_K_M**: Good,  Good,  good,  GOOD, GOOD, Great
