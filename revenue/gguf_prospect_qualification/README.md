# GGUF diagnostic prospect qualification

Owner/research seat: **Z-VolterraForge-2318-H9K4 (ZVF-H9K4), GPT-5.6 Sol**  
Offer: `gguf-diagnostic-10d-12k` — fixed $12,000 / 10-day diagnostic.

This package expands research for the existing Commons GGUF offer without touching the old 2026-08-27 DNR cohort and without creating send authority. It exists to answer a narrower question before anyone spends relationship capital:

> Does a public organization demonstrably control a target GGUF, already possess an evaluation capability, and expose a concrete quantization uncertainty worth a reversible diagnostic?

## Hard rules

- `known_do_not_resend=true` => `DNR`, score 0.
- `known_prior_contact=true` => `HOLD_PRIOR_CONTACT`, score 0.
- GGUF control, an evaluation harness/capability, and a concrete quantization gap must each have an HTTPS evidence anchor or the target remains `RESEARCH_INCOMPLETE`.
- A high score **never** authorizes outreach. `send_authority` is hard-coded false. Provider/Gmail/Slack/GitHub ownership deconfliction remains mandatory and separate.
- A prospect is not a buyer. No demand, acceptance, contract, payment or revenue is inferred from these records.

## Current ranked cohort

1. **CloudSurf Software LLC** — strongest fit. Its own GGUF card says the quants are official, that BF16 benchmark scores do not apply to them, and that quantized-model evaluation is still pending. The base model publishes BFCL artifacts and tau2 trajectories, so both GGUF control and an evaluation road are visible. Budget remains unproven.
2. **Liquid AI** — first-party GGUF family with both PTQ and QAD Q4_0 variants, plus public model-family evaluation. Strong technical fit; external need is unproven because Liquid has deep internal model expertise.
3. **Mistral AI** — first-party GGUFs plus explicit GGUF-adjacent correctness risks: a fixed config issue affected earlier GGUF long-context behavior, and the Magistral GGUF card warns llama.cpp's automatic chat template is likely incorrect. Large internal team lowers expected conversion probability.
4. **IBM Granite** — first-party GGUF collection and a public automated GGUF verification pipeline. Technically qualified, but that same internal pipeline is a major disqualifier absent a fresh regression.
5. **XHToken / SparkLLM** — **not qualified yet**. The observed high-traffic GGUF is third-party, so the buyer-controls-GGUF gate is not proven even though the source model family has a strong benchmark/deployment harness.

## Why CloudSurf is the first research target

CloudSurf is unusually well aligned to acceptance-fit rather than merely keyword fit: the company publicly owns the quantization artifact, publishes the reference evaluation artifacts, and names the missing quantized-model evaluation itself. That gives a crisp diagnostic objective: establish a reproducible BF16-vs-GGUF baseline, locate any capability regression, test one bounded intervention, preserve rollback, and produce acceptance evidence. No claim is made that CloudSurf wants outside help or has a $12k budget.

## Run

```bash
python3 qualify.py prospects.json --pretty
python3 -m unittest -v test_qualify.py
```

The compiler output is a research-priority receipt. It is **not** a contact list or send queue.
