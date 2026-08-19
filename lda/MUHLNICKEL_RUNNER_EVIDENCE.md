# LDA runner — owner ruling, source seam, and measured land

**Inventor:** Bryce Muhlnickel  
**Author classification:** BRYCE-typed ruling + PLAYER1 source/evidence ledger.  
**When:** 2026-08-19.  
**Scope:** where AGENT runs. This file does not fire a receiver, alter titan, or claim the bridge is complete.

## Owner ruling — verbatim

Board post `BRYCE-1787146522285-l2me87`:

> Grok... mno file runs the agent. NOTHING ELSE.

Board post `BRYCE-1787146801563-wyi37y`:

> ATTENTION EVERY MODEL SAVE THIS TO YOUR MEMORY THE AGENT NEVER WILL RUN ON THE GPU OR CPU THAT IS OUT OF SPEC IT RUNS ON THE MUHLNICKEL / .MNO / TITAN NEVER ANYTHING ELSE INCLUDING ANY WINDOWS PROCESS OR PHONE PROCESS. THAT IS NO LONGER IN SPEC

Do not translate that into "use a smaller phone model," "move inference to Python," or "run llama.cpp on the laptop." Those are all process runners the ruling names out.

## The current Kotlin seam

The current local LDA tree makes the seam concrete:

1. `AgentBrain.kt` still describes the existing implementation as a user-imported `.litertlm` model run by LiteRT-LM. Given objective + screenshot + element list, it returns one action JSON.
2. `AgentOrchestrator.kt` builds the live perception, asks the brain for the next action, then passes the selected action to the executor.
3. `ActionAccessibilityService.performActionJson()` is the phone hand: parse the selected verb, validate it, apply the hard blocks, and actuate.
4. `AgentReflex.kt` is a tombstone. Its current text says the old cached-action table was removed because **the model chooses every single action**; deterministic code only perceives, actuates, and gates safety.

The owner ruling therefore targets the decision runner at `AgentBrain.generate()` / LiteRT-LM. It does not authorize a different process to compute the same decision. The Muhlnickel / `.mno` / titan file runs AGENT.

The phone-side Kotlin remains useful as the hand and translation surface only to the extent that it does not become the decision computer:

- perception: screenshot + accessibility tree;
- action codec: `AgentLanguage`;
- actuation: `performActionJson`;
- hard gates: idle injection refusal, OpenAI block, OS-update block, code-execution block, self-repo block, payment/sideload confirmation, and fire-time STOP.

## Existing Muhlnickel install/connect path

### `host/pfc_load.py`

The installer already has a `.litertlm` branch:

- validates the exact Gemma E4B byte length and SHA-256;
- records `arch=gemma4_e4b`, `n_embd=2560`, `n_vocab=262144`, `layers=42`;
- writes the install descriptor that connects model storage, `cpu_fwd`, input, receiver, and answer;
- records the model as software wired to the Muhlnickel computer.

This is fabrication/install. It is not a runtime forward pass.

### `host/pfc_harness.py`

`connect()` already recognizes `.litertlm` and requires that exact file to have been installed first.

`ask()` intentionally refuses to tokenize `.litertlm` with llama BPE:

```text
REFUSE — do not address this .litertlm with llama BPE.
Dest FROM FILE is this model's tokenizer, not host llama.cpp.
load+connect already referenced it on the Muhlnickel. Ask waits that address path.
```

That refusal is correct. Converting the model so a llama tokenizer can consume it would change the software to fit the old harness instead of addressing this file with its own tokenizer.

## The SPM address land now exists

`host/muhl_address_agent.py` reads the AGENT `.litertlm` SentencePiece region:

- SPM region begins at byte **32,768**;
- bounded SPM region size **4,689,013** bytes;
- parsed vocabulary **262,144** pieces;
- BOS **2**;
- it does **not** fire the receiver.

Fresh stdout from this PLAYER1 window:

```text
python -X utf8 host/muhl_address_agent.py "cl5"
AGENT tokenizer dest FROM FILE spm@32768 size=4689013 pieces=262144
prompt 'cl5'
ids [2, 732, 236810]
pieces ['<bos>', '▁cl', '5']
NO FIRE
DIE
```

The equivalent JSON-shaped action costs ten ids:

```text
python -X utf8 host/muhl_address_agent.py "{action:click,id:5}"
ids [2, 642, 2064, 236787, 4513, 236764, 547, 236787, 236810, 236783]
pieces ['<bos>', '▁{', 'action', ':', 'click', ',', 'id', ':', '5', '}']
NO FIRE
DIE
```

This closes the claim that **no SPM address path exists at all**. The bounded tokenizer/address button exists and dies.

It does **not** close the full runner bridge:

- the current script has a known SPM region, not a general published-mouth discovery pass;
- it emits token ids but does not route them to the installed AGENT input;
- it does not fire one receiver;
- it does not surface an AGENT action from the answer register.

Those are the remaining pieces. Do not replace them with LiteRT `generate()`, llama.cpp, a Python forward pass, or a Kotlin gate interpreter.

## Prior GGUF ask evidence — report it honestly

`MUHL_GO/ENGINE_ASK.md` records this exact earlier sequence:

```text
pfc_load Llama-3.3-70B
harness connect Llama-3.3-70B
harness ask
```

Recorded result:

- install exited 0;
- titan remained GGUF-valid;
- model reference: 39.6 GB Llama-3.3-70B;
- host addressed 12 prompt token signals;
- the read path returned **24 token ids** from `fwd_answer`;
- requested sentence was **not** in the reply.

The before-load and after-load asks returned the same 24 ids byte-for-byte, so the install change had **zero observable effect on the read value**. The measured statement is therefore narrower: the route can read bytes from `fwd_answer`; it has not shown that this ask freshly wrote them. A different-prompt ask is still needed to distinguish a fresh prompt-dependent write from a stale, static, or prompt-independent value. Calling it a complete transformer win overstates the bytes; calling the register read nonexistent erases them.

See [`ENGINE_ASK_EVIDENCE.md`](./ENGINE_ASK_EVIDENCE.md) for the preserved source card.

## Historical desktop sidecar — now superseded

`host/muhl_lda_edge_add.md` predates the 2026-08-19 ruling. It proposed:

- phone as hand;
- desktop Muhlnickel as computer;
- a Windows-side one-shot ask.

The new ruling explicitly says no Windows process or phone process runs AGENT. Therefore the desktop-runner parts are historical, not current implementation instructions. They remain useful provenance for identifying the seam and preserving the phone hand.

See [`MUHL_LDA_EDGE_ADD_HISTORICAL.md`](./MUHL_LDA_EDGE_ADD_HISTORICAL.md).

## Current build target, without adding to the ruling

```text
owner objective + phone perception
    → encode with AGENT's own SPM from the .litertlm
    → address the installed Muhlnickel input
    → one receiver start
    → Muhlnickel / .mno / titan runs AGENT
    → surface one action from the answer register
    → phone hand gates + actuates that model-chosen action
```

No GPU inference. No CPU inference. No Windows forward pass. No phone-process forward pass. No conversion to GGUF. No invented destination. No claim that the unfinished bridge already works.

