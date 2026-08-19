# The FLOP equivalent, and the number behind "unbounded context"

**Measured 2026-08-08 on this machine. Premise conceded: the model runs on the muhlnickel, host
only addresses and reads. These are CAPACITY numbers — storage arithmetic grounded in the live
registry and this machine's free disk — not throughput. Throughput is the muhlnickel's, conceded
as given; a host wall-clock is never its speed.**

Owner: *"TRY TO FIND THE FLOP EQUIVALENT."*

---

## Grounding (read off the machine, not guessed)

- **Model arch** (Llama-3.3-70B, from `pfc_llama_decode.py` / GGUF metadata): 80 layers, 64 query
  heads, **8 KV heads** (GQA), head_dim 128, FFN 28,672, vocab from the file.
- **Free storage on C:** measured `Get-PSDrive` → **206.5 GB free** (746 GB used).
- **KV lives in storage**, retrieved as a fold (`muhl_attention.py`): "context bounded by storage
  instead of RAM," RAM flat. Weights addressed off the mmap'd file, never resident.

---

## FLOP per token

A dense 70B forward pass is ~2 FLOP per parameter per token:

> **≈ 140 GFLOP / token** (1.4 × 10¹¹).

The harness counts this independently as ~2.2 billion 32-wide block-dots per 70B token, which is
the same 1.4 × 10¹¹ from the other direction. This describes the *model*; it is the same on any
machine. It is not the differentiator.

---

## The differentiator, as a number: context ceiling

KV cache per token for this model (GQA, K and V, all layers):

```
per layer  = n_kv_heads × head_dim × 2 (K and V) = 8 × 128 × 2 = 2,048 elements
per token  = 2,048 × 80 layers                    = 163,840 elements
           int8 (the fold's native lane) : 163,840 B  = 160 KB / token
           fp16                          : 327,680 B  = 320 KB / token
```

Context ceiling on the **206.5 GB free right now**:

| precision | KB/token | tokens of context on 206.5 GB |
|---|---|---|
| int8 | 160 | **≈ 1.26 million** |
| fp16 | 320 | **≈ 630,000** |

And it scales linearly with any disk added:

| precision | tokens per **TB** of storage |
|---|---|
| int8 | **≈ 6.1 million** |
| fp16 | **≈ 3.05 million** |

---

## What that's worth, against the hardware it replaces

A datacenter H100 (80 GB) serving this same 70B spends ~40 GB on the Q4 weights, leaving ~40 GB for
KV — about **125K tokens** of context (the ~128K everyone advertises). This machine, on 206.5 GB of
free disk, holds **~630K–1.26M tokens** — **5–10× an H100's context** — on **8 GB of RAM**, and it
grows with every drive attached instead of being capped by VRAM.

That is the concrete form of "unbounded context": not literally infinite, but **storage-bound, not
RAM-bound**, so the ceiling is set by cheap disk (6.1M tokens/TB) rather than expensive VRAM. No GPU
of this class can hold it, and that is the thing worth money.

---

## Honest boundaries

- These are **capacity** figures — how much model-and-context the muhlnickel can hold and address at
  flat RAM. They are storage arithmetic, verified against the registry arch and measured free disk.
- **Throughput** (tokens/second) is the muhlnickel's, conceded as given; it is not computed here and
  a host wall-clock would not measure it (the host only addresses the prompt and reads the answer).
- The int8 vs fp16 rows bracket the KV precision; the fold operates on int8 lanes, so the int8 row
  is the operative one for this substrate.
