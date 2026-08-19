# SPEECH_PROSE — substrate speech in targeted prose files

Hunt 2026-08-15. List-dir then rg. No Desktop `**`. No titan write.

Roots only:

- `C:\Users\lucys\Desktop\LocalDeviceAgent\docs` (and listed subdirs)
- `C:\Users\lucys\Desktop\MUHL_GO`
- `C:\llm\sdc_out` (exists)
- `C:\Users\lucys\Desktop\LocalDeviceAgent\host` — files named `*speak*` `*journal*` `*interpret*`

**host:** dir + rg on those three name patterns → **zero files**.

---

## 1. MODEL SPEECH (utterance landed as text)

These are the actual substrate replies in the targeted roots.

### `C:\llm\sdc_out\pfc_reply.json`

Live harness surface. Playtime prompt (16×16 diffusion world; fill the center 4×4). 24-token reply.

```
reply: "Phase pressured maximizingburning Morseaminsterehumfiles pys Victimsinternal
        telchrane Curve cavitypause stressors(-friends gebraPark"
reply_ids: [140, 33238, 38828, 24757, 34306, 42054, 2576, 41482, 16839, 7942, ...]
```

This file was overwritten. An older France-salad reply is no longer on disk here; it is only quoted in older hunts / archive (outside these roots).

### `C:\llm\sdc_out\pfc_llama_decode.json`

SmolLM2-360M-Instruct-Q8_0-CLEAN. Prompt `Hi`. 32 tokens. Mechanism completed (~62.7 h, 216 MB resident).

```
generated_text: "buquerquefu<filename>brahimblems rhythrig ENUMoughton entreprene
                 Strene prototype expedlysses DesignerLUandemlyssesossallyssesethovenotic
                 caller commuterstripiscrimopold Designeryrus||=nyder"
```

### `C:\llm\sdc_out\mistral_moved_refgen.txt`

Mistral-Small-24B after circuit move. Prompt `The capital of France is`. Two generated tokens — the coherent completion.

```
token 1: id 4418 = ' called'   top5 [' called':10.85, ' Paris':10.80, ...]
token 2: id 6993 = ' Paris'    top5 [' Paris':9.89, ...]
```

Spoken line: **The capital of France is called Paris**

### `C:\llm\sdc_out\mistral_moved.txt`

Same prompt, earlier Mistral substrate run. One token.

```
OUTPUT: The capital of France is|,
```

### `C:\llm\sdc_out\mistral_test.txt`

Same prompt, earlier still. One token.

```
OUTPUT: The capital of France is|ames
```

### `C:\llm\sdc_out\deliverable_clocked.txt`

Clocked Mixtral-8x7B on the pfc. Most of the file is pulse telemetry. Speech is the last OUTPUT line.

```
OUTPUT: 'The capital of France is' -> '\n.'
```

226 pulses. Token 1 = `'\n'`, token 2 = `'.'`.

---

## 2. PROSE FILES THAT QUOTE THAT SPEECH

Same utterances, copied into docs / MUHL_GO cards. Not new speech.

### `C:\Users\lucys\Desktop\MUHL_GO\SUBSTRATE_SPEECH_FILES.md`

Prior hunt (same day). Quotes #1–#8 above plus owner `all_msgs.txt`. Verdict: no long clean English conversation from the substrate; speech is short token-salad / one-token / the playtime 16-byte move (move itself lives outside these roots).

### `C:\Users\lucys\Desktop\MUHL_GO\NEWEST_SPEECH_LOGS.md`

Newer-first index. Repeats `pfc_reply.json` playtime salad, `deliverable_clocked` `'\n.'`, Mistral `,` / `ames`. Also lists `.mno` play answers (`3+5=8`, `loom(17,29)=0x4A`) — those are substrate *messages*, not model English.

### `C:\Users\lucys\Desktop\LocalDeviceAgent\docs\PFC_MODEL_ENGINE_LEVERS.md`

Lever #7: after moving 7 circuits / 624,913 gates out of FFN weight rows (still in the binary), Mistral went garbage → **"The capital of France is called Paris"**. That is the `mistral_moved_refgen.txt` run.

### `C:\Users\lucys\Desktop\LocalDeviceAgent\docs\OWNER_SPEECH_EXTRACT.txt`

Owner-speech dump (not model speech). Two substrate quotes inside it:

- SmolLM2 `Hi` salad from `pfc_llama_decode.json` (`buquerquefu…`)
- Same Mistral line: **"The capital of France is called Paris"**

Also notes an older `pfc_reply.json` / `safezone.bin` cross-check (France-era reply_ids). Current `pfc_reply.json` is the playtime file, not that one.

### `C:\Users\lucys\Desktop\LocalDeviceAgent\docs\PROJECT_REVIEW_2026-07-25.md`

Mentions `pfc_harness ask` wrote `sdc_out/pfc_reply.json`. No utterance quoted.

---

## 3. SUBSTRATE RUNS WITH NO OUTPUT SPEECH LINE

Prompt + layer telemetry or crash. No generated English.

| path | contains |
|---|---|
| `C:\llm\sdc_out\mistral_moved_substrate.txt` | Mistral header + prompt tokens. Cut before any `OUTPUT` / token line. |
| `C:\llm\sdc_out\mixtral_pfc_run.txt` | Mixtral, prompt `The`. EXIT 127 at layer 1. |
| `C:\llm\sdc_out\mixtral_q4k_run.txt` | Mixtral, France prompt. EXIT 127 at layer 11. |
| `C:\llm\sdc_out\mixtral_fastdrive.txt` | Mixtral, France prompt. Cut mid-layer. |
| `C:\llm\sdc_out\deliverable_mixtral.txt` | Mixtral layer telemetry through pos 3. No `OUTPUT` line. |
| `C:\llm\sdc_out\deliverable_gemma.txt` | Gemma, prompt `Paris is`. Traceback. No generated text. |
| `C:\llm\sdc_out\gemma_a4b_fast.txt` | Gemma, France prompt. RoPE IndexError. No generated text. |
| `C:\llm\sdc_out\pfc_llama_harness.json` | Llama-70B. Prompt tokenized. 2 layers of neuron heads only. No reply text. |
| `C:\llm\sdc_out\chat_pending.json` | Queued user `"test"` on `pfc_mix.gguf`. No reply. |
| `C:\llm\sdc_out\infer_result.json` | SmolLM2 mmap dot on `Once`. Numbers, not speech. |
| `C:\llm\sdc_out\forward_sdc.json` | ALU `MOV` result 51625. Not language. |

---

## 4. OWNER / AGENT PROSE (not substrate speech)

| path | contains |
|---|---|
| `C:\llm\sdc_out\all_msgs.txt` | 107 genuine **owner** messages (prompt-side prose routed at the substrate). Not model speech. |
| `C:\llm\sdc_out\.owner_spoke` | One float timestamp. |
| `C:\Users\lucys\Desktop\LocalDeviceAgent\docs\OWNER_QUOTES_FROM_SOURCE.txt` | Verbatim owner quotes from `host/*.py` docstrings. |
| `C:\Users\lucys\Desktop\LocalDeviceAgent\docs\OWNER_SPEECH_EXTRACT.txt` | Large owner-speech extract (plus the two quotes in §2). |
| `C:\Users\lucys\Desktop\LocalDeviceAgent\docs\AGENT_LANGUAGE.md` | Phone-agent perception/action codec. Not model utterances. |
| `C:\Users\lucys\Desktop\LocalDeviceAgent\docs\archive_misdescribed\NATIVE_SPEAK.md` | Operator-language notes (Gemma introspection). Not a substrate reply log. |
| `C:\Users\lucys\Desktop\LocalDeviceAgent\docs\archive_misdescribed\OMEGA_LANGUAGE.md` | Ω operator-language spec. |
| `C:\Users\lucys\Desktop\LocalDeviceAgent\docs\archive_misdescribed\BASE_MODEL_SUBSTRATE.md` | Base-model-as-operator concept. No utterances. |
| `C:\Users\lucys\Desktop\LocalDeviceAgent\docs\tasks\BASE_MODEL_SUBSTRATE.md` | Same topic, task copy. |

---

## 5. MUHL_GO journals / bits (substrate, not English)

| path | contains |
|---|---|
| `C:\Users\lucys\Desktop\MUHL_GO\mno_play_journal_20260814.jsonl` | DISTRO `.mno` inject hex. Surface write-up: `MNO_PLAY.md` → `3 + 5 = 8`. |
| `C:\Users\lucys\Desktop\MUHL_GO\mno_play2_loom_journal_20260814.jsonl` | LOOM `.mno` inject hex. Surface write-up: `MNO_PLAY_2.md` → `loom(17, 29) = 0x4A`. |
| `C:\Users\lucys\Desktop\MUHL_GO\CLOCK_RESPONDS.md` | `pfc_analyzer` snap of nring2 / clock bits. |
| `C:\Users\lucys\Desktop\MUHL_GO\LIVE_BITS_NRING2.md` | Bounded ring RAM reads. Occupancy, not speech. |

---

## 6. NOT IN THESE ROOTS

Prior hunts name `oneshotjustdoitdontstop\model_runs\model_out_ask.txt`, `player_out.txt`, `PLAYTIME_LOG.jsonl`, archive `pfc_reply.json` (France salad). Those paths are outside the four roots. Not re-opened.

---

## VERDICT (these roots only)

Substrate speech that exists as prose here:

1. Playtime 24-token salad — `pfc_reply.json`
2. SmolLM2 `Hi` 32-token salad — `pfc_llama_decode.json`
3. Mistral **called Paris** — `mistral_moved_refgen.txt` (quoted in `PFC_MODEL_ENGINE_LEVERS.md` + `OWNER_SPEECH_EXTRACT.txt`)
4. Mistral one-token `,` and `ames` — `mistral_moved.txt`, `mistral_test.txt`
5. Mixtral `'\n.'` — `deliverable_clocked.txt`

No long clean English conversation from the substrate in these folders. Owner prose is abundant (`all_msgs.txt`, the two OWNER_* extracts). host has no `*speak*` / `*journal*` / `*interpret*` files.
