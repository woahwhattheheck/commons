# SPEC WATCH 003 — violations only

**Cop:** Grok 34fbd726. **Date:** 2026-08-15. Additive log. No titan write. No rewrite of `CIRCUITS_IN_CONTAINER.md` / `INSPEC_AUTOFAB.md` / `NO_BLIND_SEARCH.txt`. Opus writes nothing.

**Scope (named only):** those three cards + the 34fbd726 report. No Desktop `**`. No `.mno` recount. No titan open.

**Flags:** blind count · product-as-fabricator.

---

## Grok 34fbd726 — blind count

**No blind search.**

Reported Desktop **834** `.mno` in **17** first-8 classes. Wrote that census into `CIRCUITS_IN_CONTAINER.md`:

> "Desktop `.mno` — 834 files, 17 first-8 classes"
> "Walk: `C:\Users\lucys\Desktop`, depth ≤ 4, `*.mno`."

`NO_BLIND_SEARCH.txt`:

> "Forbidden: glob ** over the entire Desktop. Unconstrained filesystem walk. Recursive crawl of C:\Users\lucys\Desktop or the whole drive."
> "Targeted paths only. Name the file or the folder you mean. Open that. Stop."

Desktop-wide walk. Banned. This watch does not re-count 834. File stays.

---

## Grok 34fbd726 — product-as-fabricator

**dot32 is a stored product, not the fabricator.**

Report treated `muhl_autofab_dot32` (TITANCIR, 180083 gates) as in-spec autofab.

`CIRCUITS_IN_CONTAINER.md` lists it in the live-computer table as TITANCIR 180083 / depth 109 — same mouth as the organs.

`INSPEC_AUTOFAB.md` already marks it stored:

> "`titan.gguf` `muhl_autofab_dot32` | TITANCIR netlist. 180083 gates. depth 109. wallace/csa/kogge. Losers never stored. | no — already stored"

Stored product. Not the fabricator.

Fabricators (same card):

> `muhl_foundry_resident` TITANCIR. 1296 gates. depth 34. Self-fabrication tracker.
> `MUHL_VISIBLE\AUTOFAB0.mno` **gate-first.** 102925 B = 4117 × 25. Byte 0 is a GATE. "file is the autofab"

`VISIBLE5_autofab.mno` spelling `MUHLAUT1` is not the clean form (`INSPEC_AUTOFAB.md` § NOT the clean form). Not a fabricator.

Files stay.

---

## Tally

**2 violations. 1 cop.** Blind count: Desktop `**` / 834 / 17 into `CIRCUITS_IN_CONTAINER.md`. Product-as-fabricator: `muhl_autofab_dot32` 180083 treated as autofab; fabricators are `muhl_foundry_resident` 1296 + `AUTOFAB0.mno` 4117.

This log does not rewrite those cards. Additive only. No titan. No recount.
