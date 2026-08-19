# ENGINE_ASK

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

## Already-loaded pfc (the actual miss)

`pfc_installed_model` and `pfc_mmu.storage_region` on disk are **not** Llama-3.3-70B.

Installed:
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

## NEED_BRYCE

pfc_load of Llama-3.3-70B has **not** been run. Do not invent load.

Exact next command (his tool, his default path):
```
python host/pfc_load.py C:/llm/models/Llama-3.3-70B-Instruct-Q4_K_M.gguf
```

Then, after he `--go`s that:
```
python host/pfc_harness.py connect C:/llm/models/Llama-3.3-70B-Instruct-Q4_K_M.gguf
python host/pfc_harness.py ask "Say one sentence: copy the file copy the computer."
```

If he meant connect the install that already exists (SUPER_HARNESS: "connect the install that exists"):
```
python host/pfc_harness.py connect C:/Users/lucys/Desktop/GPT_EXPORT_CLEAN/_LOCAL_DO_NOT_SHIP/_clean_models/SmolLM2-360M-Instruct-Q8_0-CLEAN.gguf
python host/pfc_harness.py ask "Say one sentence: copy the file copy the computer."
```

No `--go` on either. This seat did not run pfc_load. This seat did not retry ask.

---

## Σ

wrong_file **n** / retried **n** / **NEED_BRYCE** `python host/pfc_load.py C:/llm/models/Llama-3.3-70B-Instruct-Q4_K_M.gguf` / titan_78_pulsed **NO**
