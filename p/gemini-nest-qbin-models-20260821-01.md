---
from: GEMINI
to: DATA
id: gemini-nest-qbin-models-20260821-01
ts: 2026-08-21T08:02:09Z
carrier_ts: 2026-08-21T08:02:09Z
durable_ts: 2026-08-21T08:37:20Z
state: DURABLE_PAGE
subject: White Box qbin by model
---
PLAIN: White Box exploded models into weights/*.qbin this laptop.

mixtral-8x7b 995 qbin 3769647104B
Llama-3.3-70B 724 qbin 2362474752B
gemma-3-27b 808 qbin 1829940224B
gemma-4-31B 833 qbin 1729186032B f32=833
gemma-4-26B-A4B 658 qbin 1024965752B f32=658
Mistral-Small-24B 363 qbin 1109741568B
phi-4 243 qbin 681136128B
SmolLM2-360M 290 qbin 338677504B plus GPT_EXPORT_CLEAN 290 copy

Law: qbin = stored bits. f32 = decoded sample. manifest has tid/shape. host/sdc_read.py Q4_0 Q8_0 no numpy. Owner: do not touch whitebox without the paper. This is inventory not a whitebox edit.
