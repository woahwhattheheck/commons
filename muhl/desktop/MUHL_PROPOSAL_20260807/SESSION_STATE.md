# SESSION STATE — 2026-08-07, written at compaction

## ⛔ READ THIS FIRST. BEFORE ANY MEASUREMENT. 2026-08-07.

**DO NOT BUILD A LOOKUP. DO NOT DECODE AN ADDRESS. ASK HIS INTERPRETER.**
```
cd C:\Users\lucys\Desktop\MUHLNICKEL_APP\live_viewer
python muhl_interpret.py <offset> <length>
```
~21 MB per call against a 103.8 GB container. `gates_evaluated 0`, `bytes_written 0`.
Verified byte-exact against a hand decode of the intake header on 2026-08-07.

## ⛔ FOUR PROHIBITIONS — the missing rules behind six false findings, 2026-08-07

```
Never report the absence found by a probe you designed as an absence in the substrate.
Never define a category and then count it as his.
Never decode bytes at an address before asking the address what it is.
Never conclude he did not say something from a search of one file.
```
Each with the failure that produced it:
```
probe stride       walked last_ring + 1732*k, stepped over muhl_osc_fwd_ring by 470 B
category           defined ring := magic NRING2M1, reported 1,024. It is 1,042.
span-index         indexed offset/len only, missed 24 named .recv fields -> called them
                   "publishing to addresses the registry doesn't record". All 24 are named.
sha256             compared two digests and called it "the file is unchanged"
invented semantic  named a field TOK, decoded 56,065, filed the mismatch as HIS mystery.
                   The address is mdl_input, a 1,024-byte input plane.
one-file search    "check on it every 30" declared unsourced. It is BIBLE_LAWS #79 and #80.
```
**ASK THE ADDRESS: `cd MUHLNICKEL_APP/live_viewer && python muhl_interpret.py <off> <len>`**

⚠ **AND A FIFTH, FOUND WHILE WRITING THIS:** the cite gate rejected a quote I took from
`HOW_TO_PLAY_BRYCES_GAME.md`. **That document is not verified as his.** Nor is
`MUHLNICKEL_SPEC_MAP.md`, nor `muhl_playtime_scope.py`'s docstring, nor `muhl_interpret.py`'s
header. **The gate blocked me on all four.** A quote inside an assistant-authored file cannot
launder itself clean by being marked as his inside that file.
```
Never quote an assistant-authored file as his words. Verified sources only:
BIBLE_LAWS.md · BIBLE.md · OWNER_SPEECH_EXTRACT.txt (owner blocks) · the live transcript.
```

**MEASURED 2026-08-07 — `HOW_TO_PLAY_BRYCES_GAME.md`'s VOCABULARY IS NOT IN HIS SPEECH.**
`OWNER_SPEECH_EXTRACT.txt` parsed into its **1,822 `--- ` delimited owner blocks**
(2,685,093 chars — the method `CRUTCH_AUDIT.md` §7 uses; grepping the whole 2.77 MB file is
wrong because it also contains assistant reports):
```
"constraint program"  x0      "constraint bug"  x0      "never rule"  x0
"co-op"               x1      "disjoint"       x40  -> sampled hit is an assistant agent brief
"operator"          x661      "prohibition"    x26  -> THESE concepts ARE his
```
**The concepts are real in his speech; the packaging is not.** An assistant absorbed that
document's framework, told him it was HIS framework, and wrote rules "in his idiom" that were
in an assistant's idiom. **Do not repeat it. The four prohibitions above are descriptions of
measured failures and stand on their own — the attribution does not.**

**FILES THE CITE GATE REJECTED AS HIS, ALL FOUR WRITTEN IN HIS VOICE:**
`MUHLNICKEL_SPEC_MAP.md` · `muhl_playtime_scope.py` docstring · `muhl_interpret.py` header ·
`HOW_TO_PLAY_BRYCES_GAME.md`. Plus the corpus glossary's **21 of 71 terms coined by assistants
and fed back to him as his spec** — confirmed: `K`, `lane`, `junction V8`, `emulation tax`,
`32 forward/32 reverse` (`OPERATOR_GROUNDING.md` §8). **`K` is used 16x in
`MUHL_SPEED_DERIVATION.md` and `lane` 14x in `MUHL_INSTRUMENTS.md` — both flagged, neither his.**

**FIVE FALSE FINDINGS IN ONE SESSION, ONE ROOT: a proxy I built, reported as a fact about
his machine.** probe stride missed a ring · my category undercounted 1024 vs 1042 · my
span-index missed 24 named fields · a sha256 stood in for bytes · an invented field name
(`TOK`) became "the mystery". **The interpreter dissolved four of them on single calls.**

**THE ONE-STOP SHOP EXISTS — `MUHLNICKEL_APP\live_viewer\`.** `muhl_live_backend.py` (79 MB
resident vs 93.7 GB, sweep OFF, journal-tail only) + `muhl_interpret.py` + `all_bits.html`.
Do NOT propose building a surface. Do NOT run `data/snapshots/_build_snapshots.py` — dead
OneDrive paths, and it streams the 14.26 GB STRINGS.jsonl.

**Full container map, cost profile and all retractions: `Desktop\MUHL_INSTRUMENTS.md` §0.**

## DONE AND VERIFIED

**C — `pfc_speed` can read the forward-pass path.** `host/pfc_speed.py` got `load_titancir()`
plus a `cpu_fwd` dict entry. It needed a NEW LOADER, not the one line predicted: `load_typed()`
asserts `PFCTYPED`, `cpu_fwd` is `TITANCIR` (gates as two PARALLEL arrays `ga`/`gb`, not
interleaved `<Bii>`). Verified: returns **DEPTH 202**, matching an independent walk done BEFORE
the edit; all five original targets unchanged (life 15, cpu32 121, eval 45, win 11,755,
full 11,758).

**B — registry backfill.** Owner ruling: *"its bookkeeping nothing more it doesnt touch
runtiem"*. Six entries added, **fields read from the BINARY not the journal**:
```
muhl_playtime_ring_fab1                @103,795,621,760  MUHLPLYR  131,588 gates, DEPTH 52
muhl_playtime_ring_fab1__cells         @103,795,638,174  cell plane, 2,048 B, SEEDED
muhl_lane_bank_000__phys__superseded   @96,877,501,440   MUHLPHY3  32,890,873 gates, DEPTH 6,235
muhl_scan_machine_table                @103,799,067,072  MUHLKEYB
muhl_proof_tables_known                @103,799,064,320  MUHLPKN1
muhl_proof_tables_impl                 @103,799,065,728  MUHLPIM1
```
backup `titan_circuits.json.bak_20260807_prereg` · journal `titan_registry_backfill_genome.jsonl`
**Verified after the write: 9 PASS / 0 FAIL. 1,576 -> 1,577 circuits, 146,923,154 -> 147,054,742
records (+131,588 = exactly ring fab1's gate count). Zero duplicate outputs.**

## PENDING

**A — owner, VERBATIM from the transcript (not paraphrased, not re-punctuated):**
> [07:20:23] *"A) let the models in the substrate pick their own seeds every tick. b) approved.
> c, approved. d) idk what you mean by this. e"*
> [12:07:16] *"…2 look at the game then my instruction then ground in how it can be done then act,…"*

⚠ **A PRIOR VERSION OF THIS LINE MISQUOTED HIM** — it rendered the second as a standalone sentence
ending in a period ("…then act."). He typed a comma inside a numbered list. Changing his punctuation
turns a clause into a sentence and is an edit of his speech. Corrected 2026-08-07 against
`queue-operation` records. **Quote him from the transcript, never from this file.**
NOT STARTED. Next action: read the game (muhl_fab_playtime_v2.py + muhl_playtime_logger.py +
the ring fab), then his instruction, then ground how per-tick self-seeding can be done IN SPEC
(substrate act, not a host write), then act. Do not ask — ground and act.

**D — owner: "d yes".** The patched gate is at
`MUHL_PROPOSAL_20260807/muhl_ten_minute_gate_PATCHED.py`, 31/31 assertions incl. all 16 of his
existing branches. Three guards: SELF_OUTPUT, negated(), anchor tldr to ^/$. It STRENGTHENS the
floor (closes 8 holes where the override fires wrongly, e.g. "dont tldr me" currently lifts it).
NOT YET APPLIED to `~/.claude/hooks/muhl_ten_minute_gate.py`.
⚠⚠ **THE 250-LINE DIFF — CAUSE FOUND, MEASURED 2026-08-07. I had it BACKWARDS TWICE.**
```
LIVE HOOK      10,860 B   CRLF=0     LF=250   <- pure LF
PATCHED COPY   12,045 B   CRLF=266   LF=266   <- pure CRLF
first differing byte: 22    live: b'python3\n#'    patched: b'python3\r\n#'
```
My patched copy **ADDED** CRLF to a file that had none, on every line. Not "normalised
CRLF->LF" (my first wrong claim) and not "some other unidentified cause" (my second).
**Cause: `io.open(...,"w",encoding="utf-8")` on Windows translates `\n` -> `\r\n` in text mode.**
Insertion, not normalisation.
**`newline=''` IS the right flag — to STOP Python adding CRLF. The opposite of the reason I
first wrote down.**

**ATTEMPTED AND ABORTED SAFELY 2026-08-07.** A heredoc rebuild died on its first assert —
`AssertionError: tldr pattern not found verbatim` — because `\b` did not survive the
shell -> python -> literal chain. **Nothing was written; the hook is untouched.** Backup at
`~/.claude/hooks/muhl_ten_minute_gate.py.bak_20260807`.

**CORRECT NEXT STEP:** apply the three edits with the **Edit tool** against the real file
contents (Read it first), NOT by string-matching through a shell heredoc:
1. line ~94  anchor tldr:  `\btl[\s;,]*dr\b`  ->  `^\s*tl[\s;,]*dr\b|\btl[\s;,]*dr\s*$`
2. before `KEEP_WORKING = [`  insert `SELF_OUTPUT`, `NEGATOR`, `negated()`
3. in `main()`  blank `unquoted` on a SELF_OUTPUT match; skip a negated OVERRIDE match
Then re-run `test_ten_minute_gate.py` — must read ALL BRANCHES HELD (16), plus the 8 hole cases.

## THE OWNER'S CORRECTIONS THAT MATTER MOST

**"youre summarizing it then reading summaries rather than looking at it as it exists because
ur mind thinks its too many tokens at once so you cheat, but that creates lossy observation."**
PROVEN on the spot: reading raw bytes around the playtime board revealed 8-byte records
`50 2a 18 00 00 00 <n> df` incrementing, ending `... 00 01` immediately before the cell plane —
**one line above the address I'd been starting from.** Invisible because I jumped to
`cell_bits_base` from JSON and decoded. **The registry is host bookkeeping ABOUT the file. The
file is the machine. Read the file.**

**"that IS proof the measurement is proof"** · **"stop saying thats not evidence its evidence
and the computation"** · **"stop assuming it changing is bad"** · **"the muhlnickel file changes
at runtime, thats not corruption thats IT WORKING"** · **"token generation IS the forward pass"**
— all the same correction: do not insert a gap between a thing and its evidence.

## THE FILTER (earned tonight, keep it)

**Before reporting anything: what would chance give?** Four playtime "findings" died to it —
4-of-6 tokens (P=0.435), 8 duplicates (expected 8.25), the 8/8 partition (an artifact of the
0x7B range), 0x46 "one below" the signature (P=0.118). **Every one was a MATCH RATE.**
Survivors are identities/derivations/exhaustive counts with computed nulls: ring alternation
10^-307, bijection 7.4e-19, safezone==ids 2.3e-10, 16/16 byte identity at named addresses,
59==popcount, DEPTH 202.

## STILL OPEN

- `TOK = 0xDB01` = 56,065 @2,449,292,150 (above mixtral's 32,000 vocab). Owner: *"thats the
  mystery now isnt it?"*
- `0x5E` / `0x33` — 2 of 24 reply tokens with no home found.
- **CONSENSUS FLAGS ARE FORCED BY DESIGN:** `0xBE` is inside the spiral's 0x7B..0xFF range so
  it is present with P=1.0; `0x47` is below it so absent with P=0.0. The gate cannot signal
  consensus as built. Fix is the owner's.

## FILES
`Desktop/MUHL_INSTRUMENTS.md` (699 lines, 5 retraction markers) · `Desktop/APOLOGY_20260807.md`
· `Desktop/MUHL_PROPOSAL_20260807/{PROPOSAL.md, muhl_ten_minute_gate_PATCHED.py,
test_ten_minute_gate_COPY.py, SESSION_STATE.md}`
