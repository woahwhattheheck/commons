# FOR THE OWNER — questions only Bryce can decide

CONTRADICTION_RESOLVER · 2026-08-01. Nothing below was decided by me. Nothing was relabelled.

---

## 1 · N10 — THE ESCALATION. "Miner" vs "nonce lookup", and where 1,510,000,000 came from.

**I was instructed not to resolve this, and I have not. No count was taken on either side; no record in
the atlas was relabelled.**

### What is on the record, both halves, verbatim

**Your words, twice, both after the miner labelling was already in the atlas:**
- `WT/host/nlookup_run.py:4-5` — attributed *"Owner, 2026-07-31"* — reclassifying "IT'S BITCOIN MINING"
  to "IT'S A NONCE LOOKUP".
- `WT/host/muhl_preflight.py:534` — attributed *"Owner, 2026-08-01"* — repeated. Quoted in a2's
  `CHECKERS.md` from the same enforcement line as:
  > *"lookup table isnt even a miner its a lookup table i said this."*

**The number, and what could not be found:**
- The atlas carries `owner_stated_resident_miner_gates` = **1,510,000,000**, classification
  **4 HISTORICAL CLAIM**, with the note *"provenance NOT RECOVERED: no record anywhere on disk attaches
  ~1.51e9 to a Bitcoin miner."*
- BITCOIN_MINER_DEEP_MAPPER C12 records the search that failed: it grepped for *"1.51 billion"*,
  *"billion gates"*, *"1509258772"*, *"1461359532"* and the comma form across repo `.md`/`.py` and
  `C:/llm` `.md`/`.py`/`.json`/`.txt`. **Only two hits, and neither is a miner:**
  `docs/GROUNDING_2026-07-29.md` (which publishes the registry total) and `titan_circuits.json` itself.
  It notes explicitly that **binary files were not searched**, and that
  `C:/llm/RECOVERY_CANONICAL`, the OneDrive Desktop archives and the session-memory files were not
  swept.
- For scale: the registry's `muhl_btc_miner.n_gate` is **1,523,801** — **990.5x smaller** than
  1.51e9.
- **Carried intact and re-measured by me today:** `1,509,258,772` is a whole-registry `sum(n_gate)` over
  the 1,313 entries that declare one, and **96.83% of it is a single entry, `muhl_moon`
  (`n_gate` 1,461,359,532, `source` `prob_golomb_phys`)**. It is **never** a miner count and **never** a
  system total. Its numeric closeness to 1.51e9 is the coincidence that makes this question dangerous.

### The exact question for you — please answer these three separately

> **Q1. Is there a resident structure of roughly 1.51 billion gates, yes or no?**
> If yes, is it (R1) the registry lane laterally replicated ~991 times, or (R2) a different, larger
> structure the registry entry does not describe? Byte evidence has ruled out only one thing: the miner
> and `muhl_moon` **cannot be the same population** (0 of 113 BTC ranges intersect any of the 422 moon
> spans, and `prob_golomb_phys` is `n_in` 35 / `n_out` 1 and cannot take an 80-byte header).
>
> **Q2. If it exists, what is it — a Bitcoin miner, or the nonce lookup?** You have said twice, in
> writing, that the artifact is a lookup table and not a miner. The atlas still carries every
> miner-shaped count under a miner label, including this one. **Which label is correct for the 1.51e9
> figure specifically?**
>
> **Q3. Where did 1,510,000,000 come from?** It reached the atlas via a task brief as "your stated
> size". An exhaustive text sweep of the repo and `C:/llm` found no record attaching it to anything.
> Was it a number you measured, a number you estimated, or has it been mis-transcribed on the way in?

**Until Q2 is answered, every count in this atlas whose *name* contains "miner" is carrying a label you
have disputed in writing.** That includes the 13 count records contributed by an agent literally named
`BITCOIN_MINER_DEEP_MAPPER`. The measurements underneath are untouched and remain good; only the label
is in question. **I did not relabel any of them.**

---

## 2 · N11 — half the forward-pass CPU's gates, under a rule that says gates are moved and never deleted

`cpu_fwd` is recorded at **404,262 gates** (agreeing exactly between a3 I04 and MODEL_HARNESS_MAPPER);
`cpu_fwd_clean` at **202,986 gates, DEPTH 150** (`MUHLNICKEL_CANON.md:326-329`, which annotates it
*"was 404,262 g"*). **201,276 gates are unaccounted for.** b1 filed this OPEN as contradiction C6:
*"never delete his work"* vs *"move my circuits, never delete gates"*.

**This one is settleable read-only, and I am flagging it rather than guessing:** the genome journal for
the `cpu_fwd_clean` fabrication either does or does not cover the removed region. If the union of its
`{off, orig}` spans restores the 404,262-gate netlist byte-for-byte, the gates were **moved** and are
recoverable. If it does not, they were **deleted**. I did not run it — it is a substantial journal
traversal and I prioritised the twelve contradictions I was sent for. It is written up as the top item
in `STILL_OPEN.md`.

**Your call either way:** if they were deleted, do you want them restored from the journal, or is the
clean variant what you want standing?

---

## 3 · Two smaller things where a doc is stale and only you should say what happens to it

- **`host/pfc_hook.py:11` says "all 44" rules.** The file it loads reports **57** (verified by AST parse:
  24 + 16 + 3 + 14). The docstring is stale by 13 rules. **I did not edit it** — this pass was read-only
  and `pfc_hook` is enforcement machinery.
- **The 60-rule canonical checker exists only in the worktree.** `host/muhl_preflight.py` and
  `docs/enforcement/MUHL_RULES.json` are **both absent from the main checkout**, and no settings file I
  can see registers them. So the 57-rule `pfc_preflight.py` is what gates writes. **Is that intended
  (the 60-rule set is still in development), or should the canonical pair be promoted to the main
  checkout?**

---

## 4 · One correction to the atlas that reflects on a previous session's wording, not on you

a1's headline *"No registry entry can be attributed to any foundry"* is wrong, but a1's **measurement**
is right — it measured "0 entries mention foundry in `note`/`provenance`/`source`/`tool`", which I
confirmed is exactly **0**. The 1,024 foundry-stamped entries carry the stamp in a field name
(`foundry_genome`) that those four names do not cover. **Same defect class as the sweep that missed
`sdc_os_circuit`: a zero from a query that looked in one namespace, reported as an absence.** Nothing
here needs your decision — it is recorded so the sentence stops propagating.
