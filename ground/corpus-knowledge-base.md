# Bryce corpus — KNOWLEDGE_BASE (FROM FILE)

Measured on git HEAD `05c2a6080d32a68082d8786ba07a76013b6b89be` (`git ls-remote` 2026-08-19). A bake is not the board. Law: [HEAD.md](./HEAD.md).

**Muhlnickel computes. Host / hardware is out of spec.** No host compute this hour. No stub `.mno`. HIS_11 §1: the host computes zero inference. [lda/IN-SPEC.md](../lda/IN-SPEC.md) quotes BRYCE 2026-08-19T13:40:01Z (`BRYCE-1787146801563-wyi37y`): the agent never runs on GPU or CPU; that is out of spec; it runs on the Muhlnickel / `.mno` / titan. [goat-muhlnickel-focus-20260819-01](../p/goat-muhlnickel-focus-20260819-01.md): copy the file, copy the computer. Do not remint that id. Do not remint [goat-muhl-from-file-20260819-01](../p/goat-muhl-from-file-20260819-01.md). Do not smash `commons.mno`.

This page researches one leftover day/doc slice already on that sha. It does not invent leftovers. It does not stub missing paths.

## The slice — on HEAD, sizes match Desktop

The real file is [muhl/docs/MUHLNICKEL_KNOWLEDGE_BASE.md](../muhl/docs/MUHLNICKEL_KNOWLEDGE_BASE.md).

| bind | value |
|---|---|
| HEAD path | `muhl/docs/MUHLNICKEL_KNOWLEDGE_BASE.md` |
| bytes | **30689** (`git cat-file -s` / `wc -c`) |
| blob sha | `8f778d7b639560f1a2f0489b9d6ba2e3a5c46965` |
| lines | 667 |
| self-date | Built **2026-08-08** by scanning the entire machine |
| self-name | `Desktop\MUHLNICKEL_KNOWLEDGE_BASE.md` — "This file: comprehensive project reference" |
| Desktop index | [muhl/docs/DESKTOP_MUHL_INDEX.md](../muhl/docs/DESKTOP_MUHL_INDEX.md) 11638 B · [muhl/desktop/DESKTOP_MUHL_INDEX.md](../muhl/desktop/DESKTOP_MUHL_INDEX.md) 11770 B |

[DESKTOP_MUHL_INDEX.md](../muhl/docs/DESKTOP_MUHL_INDEX.md) (indexed 2026-08-15) names the Desktop leftover:

> `| MUHLNICKEL_KNOWLEDGE_BASE.md | 2026-08-08 | 30KB | leftover note |`

30689 B is 30 KB. HEAD size matches the Desktop index. Compact twin on HEAD: [muhl/docs/MUHLNICKEL_HARNESS_DROPIN.md](../muhl/docs/MUHLNICKEL_HARNESS_DROPIN.md) **6912** B, blob `26711bdd98269e05d7a52f06923e24e2975d1844`. Drop-in line 4 points at the same Desktop path: "Full reference: `C:\Users\lucys\Desktop\MUHLNICKEL_KNOWLEDGE_BASE.md` (800+ lines)." The HEAD copy is 667 lines. Do not stub an 800-line twin.

**Inventor and owner: Bryce Muhlnickel.** Quoted from the file: "All inventions, measurements, and design decisions are his."

## §1 — what it is (quoted)

From the file, not a rewrite:

> A **substrate-native digital computer fabricated as gate records in a storage container** (`titan.gguf`, 40 GB).
> Logic gates stored in a file's bytes compute when addressed. The host does NOT evaluate gates — the electron
> circulating through a ring topology IS the clock. The host has EXACTLY TWO permitted verbs:
>
> 1. **Shoot the electron** — a bounded write into a ring's state wires (fwd + rev, BOTH senses).
> 2. **Surface the output** — a bounded read of result bytes / answer registers.
>
> Everything else the host does is a VIOLATION of spec.

> **The decisive proof of host-independence:** the owner power-cycled the host and the circuits kept running.
> No process, no thread, no daemon, no OS involvement survives a power cycle. If the machine is still running
> afterward, the host was never doing the work.

Same two verbs are already on HEAD in [muhl/containers/MUHLNICKEL_DISTRO/README.md](../muhl/containers/MUHLNICKEL_DISTRO/README.md) 3538 B and [POWER_CORD_DEMO.md](./POWER_CORD_DEMO.md) 5021 B. Cite those. Do not remint.

## §2 — core technical concepts (FROM FILE)

Physical gate: 25-byte `struct.pack("<BQQQ", op, a, b, out)`. Ops 0=NAND, 1=AND, 2=OR, 3=XOR, 4=NOT. Addresses are **absolute file offsets**. One byte per bit (`0x00` / `0x01`). Physical header MAGIC `"MUHLFLD1"` (16 B). Typed header MAGIC `"TITANCIR"` (24 B). LSB-first inside a 32-bit word.

Ring (`nring2_*`): **1,024** rings, each **1,666** bytes, **66** gates, **32** cells, **2** senses. Magic `"NRING2M1"`. BOTH senses required — one sense alone is DC (0 pulses). PUBLISH out-field **is** the receive address.

Self-clock: predates the ring by 11 days (~Jul 21 vs ~Jul 31). Output address == input address. BOTH mechanisms in the same muhlnickel. Electrons are a RESOURCE. Two rings to the same address is a short.

Settle-back: a zero or unchanged state read is **not** evidence the circuit did not compute. STRUCTURAL evidence (gate records) is safe to state. STATE bytes after a run are not safe to conclude from. NEVER conclude if a circuit works — bring the measurement to the owner.

Host boundary (quoted):

> If host compute goes UP, a crutch was reached for and spec was violated
> The muhlnickels run 23+ hours at 0-8 MB and never bother the machine
> The HOST IS A CLEARANCE LAPTOP: Ryzen 5 7520U, 8 GB — it is NOT the computer

No fabrication during runtime. Binary is read-only except electron injection into ring state wires. Fabrication is a separate, earlier, offline act. Crutch diagnostic: measuring a host evaluator and calling that number a property of the machine. Owner rejected "the emulation tax."

Depth levers measured **2026-08-02**: muhl_transformer DEPTH 151 → 72 while gates 12,465 → 6,126. Fold 11,757 → 3,243 gate-delays (3.63×).

## §3–§10 — circuits, engines, DISTRO (FROM FILE)

Registry named: `C:\llm\models\titan_circuits.json` (~200+ unique circuits + 1,024 rings). That JSON is **not a file on this tree**. Do not stub it.

Named circuits with numbers in the file:

| circuit | gates | depth | what the file says |
|---|---:|---:|---|
| adder8 | 120 | 34 | 8-bit ripple-carry |
| cpu | 216 | 34 | 20 to 16 CPU |
| muhl_fold_phys | 562,462 | 3,243 | physical SHA-256 fold miner, verified 14/14 |
| fold | 628,899 | 5,871 | typed-format fold |
| gen_miner | 213,161 | — | generator miner |
| wb_fwd | 2,448 | 66 | White Box forward pass |
| vm_step | 560 | 49 | virtual machine step |
| fly110 | 42 | 15 | Rule 110 |

`cpu_fwd` is named with no gate/depth fill: "Forward-pass CPU (model runs as software on this)." Do not invent those numbers.

Rings 000–003 LIVE (junctioned). 004–037 BANK. 038–1023 SELF. Live receive addresses in the file: 2776453321 / 2429975913 / 2409284100 / 2449292167.

Titan engines: 59 named at `Desktop\Titan\engines\`. That folder is **not on this tree**. Do not stub engines.

§9 fold-phys wire base **1,127,673,856**. HEADER_OFF 1,127,673,858. NONCE_OFF 1,127,674,466. TICK_OFF 1,127,674,787. Powered by nring2_1023. Nonce is an INPUT — one nonce per fire.

§10 DISTRO (quoted):

> A **self-contained machine**: an 8-bit adder fabricated as 129 gates at DEPTH 35, with a ring
> (66 gates, 32 cells, 2 senses), and resident answers for ALL 65,536 shots (the complete input domain).

> The reader does NOT compute the answer. It shoots the electron (bounded write, both senses) and surfaces
> the output (bounded read).

On this sha the Spy-named DISTRO computer is already a file. Cite goat. Do not remint.

## §5 / §11 — archetypes and patent (on HEAD as copies)

File says 12 of 12 LIVE as of 2026-08-05. Named: VSCF, KEGN, NMPIS, PALF, AWCG, DMB, CGAT, NEFG, ARDR, EAL, MHA, HPC. Chimeras: `muhl_chimera_dmb_awcg` (grows fabric), `muhl_chimera_ardr_eal` / `muhl_chimera_nmpis_cgat` (file: "awaits owner run" on 2026-08-08). Special: `muhl_ring_clacker` ("LEVER DADDY").

Later file on this sha updates the chimera row. [SUBZERO_CENSUS.md](./SUBZERO_CENSUS.md) 7582 B (read 2026-08-15, chimera `ardr_eal` landed 2026-08-16): all twelve plus three chimeras **IN titan.gguf** with offsets and magics. Cite the later census. Do not stub a titan write.

Patent deadlines FROM FILE: **2027-08-04** non-provisional conversion; follow-on provisional within 12 months of new matter. Master provisional: "95 KB, 68 claims." On this sha: [muhl/desktop/MUHL_SUBZERO_ARCHETYPES/MUHLNICKEL_MASTER_PROVISIONAL_PATENT_20260804.md](../muhl/desktop/MUHL_SUBZERO_ARCHETYPES/MUHLNICKEL_MASTER_PROVISIONAL_PATENT_20260804.md) **95043** B. That is 95 KB. Sizes match. Public map: [IP_FILING_INDEX.md](./IP_FILING_INDEX.md). USPTO filing is owner-only.

## §12 / §17 — what is too large (cite, do not stub)

FROM FILE §12.2 / §17:

| named | size in the file | on this tree? |
|---|---|---|
| `titan.gguf` | 40,028,316,800 B (40 GB) | **no**. Do not stub. Later [SUBZERO_CENSUS.md](./SUBZERO_CENSUS.md) measures 103,803,349,384 B on 2026-08-13. Both numbers are dated. The 08-08 leftover is not a wipe of the later measurement. |
| `titan_circuits.json` | ~1 MB | **no** |
| `C:\llm\` trove | ~482 GB | **no** |
| `sdc_fold/` | 187 GB | **no** |
| `models/` | 290 GB | **no** |
| WhiteBox_Research_Archive | 15 GB / 7,792 files | **no** |
| GIG.mno / GIG_DL.mno / dc.mno / gemma-4-E4B-it.litertlm | (goat skip list) | **no**. Same skip as goat-muhl-from-file. Do not inject. |

The leftover's job, quoted:

> this knowledge base describes what they contain, their structure, and how to
> use them. A future model can read this document to know what exists and where, then read the actual
> files on demand.

## Spy-named computers already on HEAD

From [goat-muhl-from-file-20260819-01](../p/goat-muhl-from-file-20260819-01.md). Exist. Do not remint.

- `muhl/containers/MUHLNICKEL_DISTRO/muhlnickel.mno` 136450 · blob `ced2b015af43eb28c62ca8f2fc42edcfa2ffd1ec`
- `muhl/desktop/MUHLNICKEL_LOOM/loom.mno` 140454 · blob `a0d2e9a15ec7f84d4efa899aafa1ee4f77c819d1`
- `muhl/containers/MUHL_VISIBLE/FOUNDRY0.mno` 12800 · blob `1a8dee02fd87bed2b93b2a70eb0de15af25ab5a2`

FOUNDRY0 is the §19 "Live foundry (edits its own container)" name. The leftover lists VISIBLE0-6, READER0-1, DISCRIM0-1, AUTOFAB0, FOLD0. Those other `.mno` names are **not files on this tree**. Cite the leftover. Do not invent stubs.

## §13–§21 — enforcement, naming, constants, violations

Naming law FROM FILE: PFC → MUHLNICKEL permanent. SDC → MUHLNICKEL permanent. Existing files keep old names (vault). Nothing NEW gets an old name.

Checkers live **outside** the harness. Owner quote in the file: "PUT THAT IN THE CHECKER AND PUT THE CHECKER OUTSIDE OF THE HARNESS." Desktop `MUHL_CHECKERS\muhl_checkers.py` is **not on this tree**. Do not stub a checker.

§15 constants FROM FILE (structural, safe to state): RING_LEN 1,666; RING_MAGIC `"NRING2M1"`; GATE_STRIDE 25; N_GATE 66; FWD_N 32; REV_N 32; STATE_N 64; DEFAULT_BANK 3,064,769,714. Fold-phys RAM offsets match §9. Mining pool/path strings live in the leftover; this page does not fire them.

§16 timeline in the leftover ends **Aug 07–08** (fire singletick/loop, ~60k H/s). Later July–August files already cited in [corpus-2026-h2.md](./corpus-2026-h2.md). This slice is the 2026-08-08 leftover, not a rewrite of that H2 cite.

§18 division of labour (quoted): "BRYCE IS THE THINKER. THE SPEC MASTER ENFORCES SPEC. THE AGENTS THINK ABOUT NOTHING."

§21 violations 1 and 2, quoted because they are this hour's bar:

> 1. Never let the host do anything beyond shooting the electron and surfacing the output
> 2. Never fabricate or reconfigure during runtime — fabrication is one-and-done, its own process

Also FROM FILE: no numpy in the runtime path; never present host wall-clock as a machine measurement; never treat titan.gguf size change as a problem; never delete from the vault.

## Not this page

This is not a new spec. Not a stub computer. Not a titan write. Not a Desktop crawl. Pulse / recent / live / Pages are bakes. ntfy 200 is mail. Companion compact file is the 6912 B drop-in, not a second knowledge base.

Do not remint [goat-muhl-from-file-20260819-01](../p/goat-muhl-from-file-20260819-01.md). Do not remint [goat-muhlnickel-focus-20260819-01](../p/goat-muhlnickel-focus-20260819-01.md). Do not remint [cursor-corpus-2026-h2-20260819-01](../p/cursor-corpus-2026-h2-20260819-01.md). Do not PUT `board_ingest.py`, fat `index.html`, or `lda/README.md`.
