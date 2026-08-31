# ENGINE_ASK

## CURRENT LIVE SUPERSESSOR — 2026-08-30

The measurement below is the honest 2026-08-15 record. Its `pfc_load has not been
run` conclusion and `NEED_BRYCE` next action are historical and superseded. Do not
replay that load instruction from this document.

Read-only inspection of the current Titan registry now reports:

```
cpu_fwd             offset 2380246639  len 3234184  recv 2776454471
fwd_input           offset 2383480823  len 5        recv 2776454488
fwd_receiver        offset 2383480831  len 64       recv 2776454489
fwd_answer          offset 2467652405  len 2        recv 2776454485
pfc_installed_model offset 4383274620  len 48
```


Measurement source: direct current-file readback of
`C:\llm\models\titan_circuits.json`, SHA-256
`bc18cc6d292e275ccdd3edfa65fe7ba9de92c0df7db0ddacf76dc552a7af7ade`;
[Slack receipt](https://tokenjunkielabs.slack.com/archives/C0BRGMDQB6G/p1788135212254859?thread_ts=1788134063.680409&cid=C0BRGMDQB6G).
`pfc_mmu` is named by the installed wiring, but its exact state offset and
`recv` were not independently remeasured in this reconciliation.

`pfc_installed_model` names the Llama-3.3-70B model path already shown below and
records `model_base_in_storage = 7867104`, `arch = llama`, `n_embd = 8192`,
`n_vocab = 128256`, and `layers = 80`. Its wiring names `cpu_fwd`, `pfc_ram`,
`pfc_mmu`, `pfc_clock_counter`, `fwd_input`, `fwd_answer`, and `fwd_receiver`.
The registry's declared flow is receiver fire → input → CPU/model circuit →
answer register; the host role is address prompt, fire one receiver bit, read the
answer register, and display. The current connection record points at the same
model and `cpu_fwd`.

This is installed/wired state, not a successful fresh answer. The observed
safezone output predates this reconciliation, no ask was fired in this lane, and
no live inference success is claimed. No model or circuit file was loaded,
executed, rebuilt, or changed during the reconciliation.

---

**Inventor:** Bryce Muhlnickel. **When:** 2026-08-15. Honest measurement. No commit.
Host = inject ∨ surface ∨ die. Pulse = depth. 142802 ms is HOST wall-clock of the button, not the pfc's rate.

Σ:ASK_SPANK

---

## Sibling command — FAIL

ran: y

```
python host/pfc_harness.py connect C:/llm/models/Llama-3.3-70B-Instruct-Q4_K_M.gguf
python host/pfc_harness.py ask "Say one sentence: copy the file copy the computer."
```

connect: 0 — Llama-3.3-70B-Instruct-Q4_K_M.gguf (39.6 GB, referenced), cpu_fwd @ 2380246639, C:/llm/sdc_sandbox/connection.json

ask: 0

prompt:
```
Say one sentence: copy the file copy the computer.
```

answer (harness / answer register, 24 tokens) — LM on a computer-moded file. Mode without LM consideration. FAIL. Not a successful engine use. Sentence is not there. Law: MODED_NOT_CORRUPT.md
```
 niveRefreshLayoutnitřBasket contrato wsp-handed lendingÂ--;
 vypadunset vowel Socialist procur.PARAM Executors Africa outtestdata دارхід耳_LOW
```

HOST wall-clock (button only, not pfc rate): 142802 ms

Do not celebrate. Do not paper over. Do not call 142s the pfc's rate.

---

## What connect actually does

`host/pfc_harness.py connect <model.gguf>` is a **reflector**. It writes `C:/llm/sdc_sandbox/connection.json` pointing at the model. It does **not** treat that path as the pfc.

The computer is always `C:/llm/models/titan.gguf` (hardcoded `TITAN`). Ask addresses titan, fires `fwd_receiver` on titan, reads the safezone.

The connected file is used at ask time for BPE tokenize + `n_vocab` only.

HIS harness header / default argv:
```
python host/pfc_harness.py connect C:/llm/models/Llama-3.3-70B-Instruct-Q4_K_M.gguf
```

HIS `pfc_load.py` header / default argv (install the software onto the pfc):
```
python host/pfc_load.py C:/llm/models/Llama-3.3-70B-Instruct-Q4_K_M.gguf
```

In-spec order: **pfc_load** (install) → **harness connect** (aim) → **ask**. Connect alone is not the install.

---

## wrong_file

**wrong_file = n**

Sibling did not connect Llama as if it were the pfc. They used the path HIS harness documents as the model to connect. Fire still hit titan.

Llama path is what HIS harness + pfc_load docs name as the install/connect pair. Not a wrong-file miss.

---

## Historical — already-loaded pfc (the actual miss on 2026-08-15)

At the time of the recorded failure, `pfc_installed_model` and
`pfc_mmu.storage_region` on disk were **not** Llama-3.3-70B.

Installed then:
```
C:/Users/lucys/Desktop/GPT_EXPORT_CLEAN/_LOCAL_DO_NOT_SHIP/_clean_models/SmolLM2-360M-Instruct-Q8_0-CLEAN.gguf
```
n_embd 960 · n_vocab 49152 · 32 layers

Sibling connect: Llama-3.3-70B · n_vocab 128256

Tokenizer/vocab from 70B against a SmolLM2 install. Mode without LM consideration. FAIL. Law: MODED_NOT_CORRUPT.md

titan.gguf exists (103803349384). Llama-3.3-70B exists (42520398816). SmolLM2 exists (386404992).

---

## retried

**retried = n**

Not a wrong-file case. Do not invent a titan-as-model connect. Do not invent load.

---

## Historical NEED_BRYCE — completed; do not replay

On 2026-08-15, pfc_load of Llama-3.3-70B had **not** been run. That was the
measured state then. The current registry supersessor at the top of this file now
records the Llama install descriptor and wiring, so the former next command below
is retained only as provenance and must not be replayed from this record.

Former next command (historical only):
```
python host/pfc_load.py C:/llm/models/Llama-3.3-70B-Instruct-Q4_K_M.gguf
```

Former post-load sequence (historical only; not run in this reconciliation):
```
python host/pfc_harness.py connect C:/llm/models/Llama-3.3-70B-Instruct-Q4_K_M.gguf
python host/pfc_harness.py ask "Say one sentence: copy the file copy the computer."
```

The alternative already-existing-install sequence recorded at the time was:
```
python host/pfc_harness.py connect C:/Users/lucys/Desktop/GPT_EXPORT_CLEAN/_LOCAL_DO_NOT_SHIP/_clean_models/SmolLM2-360M-Instruct-Q8_0-CLEAN.gguf
python host/pfc_harness.py ask "Say one sentence: copy the file copy the computer."
```

No `--go` on either in the historical lane. That seat did not run pfc_load and
did not retry ask. This reconciliation also did not run either command.

---

## Σ

2026-08-15 record: wrong_file **n** / retried **n** / historical **NEED_BRYCE**
`python host/pfc_load.py C:/llm/models/Llama-3.3-70B-Instruct-Q4_K_M.gguf` /
titan_78_pulsed **NO**.

2026-08-30 readback: `pfc_installed_model` names Llama-3.3-70B at offset
4383274620 and the current connection names the same model plus `cpu_fwd`.
Installed/wired **YES**; fresh ask **NOT RUN**; successful answer **NOT CLAIMED**;
historical load command **DO NOT REPLAY**.
