# The fold→latch junction — fabricated into the binary (2026-07-29)

The junction docs/§10 called "NOT YET BUILT" — the winner-only fold's decided output → `latch_reg` (the answer
register the high-impedance probe reads) — is now **stored in `titan.gguf`**, reversibly.

Fabricator: `host/muhl_fab_fold_latch.py` (own genome journal `C:/llm/models/titan_fold_latch_genome.jsonl`;
`python host/muhl_fab_fold_latch.py revert` restores byte-exact).

## The finding that shaped it (the mutant discipline working)

The first pass added 32 fold-ANDs (`idx AND win`) after `gen_win`. The mutant test **caught that they are no-ops**:
the `ungated` mutant (drop the AND-with-win) scored **12/12 identical** to the correct circuit — only possible if
`gen_win.out[1:33]` is *already* the win-gated winner-address (zero on every losing nonce). **The winner-gating lives
inside `gen_win`'s 339,009 gates.** The suite refused to write 32 dead gates into `titan.gguf`; nothing touched the file.

So "let Titan do the work" is literal: `gen_win` already does double-SHA-256d + `hash < target` + winner-gating. The
junction is a pure **§1E relocation**, not new logic.

## What was stored

`muhl_fold_latch` @ **36084013600** (3,051,813 B, typed format), **339,073 gates** = `gen_win`'s 339,009 + **64
identity-buffer gates** (NOT-NOT per bit) that physically materialize the decided winner-address onto fresh wires bound
to the answer register. DEPTH 11757. Registry: `junctioned_to: {circuit: latch_reg, addr: 2409283485, width: 4}`.

- **Byte-exact 12/12** vs the *independent* hashlib reference (4 genuine wins + 8 negatives; an all-zero circuit would
  score 8/12).
- **Mutants caught:** `raw_nonce` (bind the pre-decision nonce input → 4/12) · `shifted` (scramble the address → 8/12).
- **GGUF-valid: True.** 0 bytes/lane. Reversible via its own journal.

## The complete §1E chain in the binary

```
gen_win (double-SHA + compare + winner-gate)  ->  muhl_fold_latch (relocate decided addr)  ->  latch_reg (answer reg)
```

One addressed pass writes the decided winner-address into `latch_reg@2409283485`. The host does zero compute: it routes
the block into `gen_input`/`target_reg` and reads `latch_reg` with the high-impedance probe.

## Next — the benchmark fire

Route a live block → one injection → probe `latch_reg` → verify against the live network target (mempool.space) →
wallet `bc1qvhrzg0e23f3tz2jgymwwtqacn48trf5m524zlq` judges. Report exactly what `latch_reg` holds. Fire is route + read
only (no host ripple — that is the forbidden executor). Fabrication is one-and-done; mining builds nothing.
