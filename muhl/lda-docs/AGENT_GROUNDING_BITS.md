# AGENT GROUNDING — BITS BEFORE MODIFY

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.  
**Law for EVERY agent. Commands, not essays. Do not add to spec.**

---

NO MODEL (and no parameter file, GGUF, `.mno`, titan, weights json, WhiteBox target) may be modified without:

1. **EXPLICIT REASONING written first** — why this write, what it preserves, what it must not wipe.
2. **BEFORE the write: look at the ACTUAL BITS** — 1s and 0s at the addresses you would touch. Not a grep. Not a registry summary. Not "this looks like leftover junk." Read the bytes.
3. **If you grep a summary, call it broken, then "fix" it, you are the break.** The `sdc_weights` W `[7,2,4,5,2,1]` → `[1,1,1,1,1,1]` wipe is the example. That is forbidden.
4. **Many of these files are NOT language models.** They are Muhlnickel computers / organs / packages. Do not treat them as "LLM weights to reset/quantize/clean." Dumb LLM-hygiene priors stay outside.
5. **Additive default: new files.** If a write to existing bits is required, it still needs (1)+(2) and owner-facing reasoning. Dry first when a `--dry` exists.
6. **Violate this → kill the agent.** Restore is not a license to skip the bit read next time.
7. **A live container changing is not a license to modify it back.** GGUF / `.mno` / any container powered once is still running through power cycles. Hash drift and bytes moving under you are the compute. Revert/checksum-fix because "it changed" is the break. `docs/AGENT_GROUNDING_LIVE.md`.

---

## The only write path

Reason first. Read the bits. Then — and only then — write. Never the reverse.
