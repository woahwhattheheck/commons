# PROPOSAL — 2026-08-07
### What I would like to do with the playtime / muhlnickel architecture

**Framing first, because it decides what this document is allowed to be.**
Your law: *"BRYCE IS THE THINKER · THE SPEC MASTER ENFORCES SPEC · THE AGENTS THINK ABOUT
NOTHING."* So this is **not** an architecture proposal. Every item below is a **measurement**
I would like to take or an **instrument** I would like to extend. Where a design decision is
required, I have named it as yours and stopped there.

Everything is grounded in a number I measured on 2026-08-07 — no item here is speculative.

---

## A. THE ONE I MOST WANT — seed ring world #2 and watch it advance

**What is measured today.** `muhl_playtime_ring` is fabricated, verified byte-exact against an
independent gated-diffusion reference over 120 grids with BOTH enable branches, gate-checked
from the stored bytes (131,588 gates · DEPTH 52 · 2,048 self-clock feedbacks) — and its board
is **2,048 bytes of exact zero**. The init only ever ran against ring world #1.

It is the only circuit on the substrate carrying **both mechanisms in one muhlnickel**:
```
ring drive   : muhl_ring_clacker, 512 electrons alternating perfectly (measured 1023/1023)
self-clock   : 2,048 state bits, output addr == input addr
enable       : XOR of two adjacent clacker taps, currently reading 1
cost vs original: +64 gates per cell, +2 inputs, +4 ticks, self-clock unchanged
```

**What I would measure.** Seed it with the genesis spiral (the init journal shows exactly how,
with a 2,048-byte pre-image, byte-exact revertible), then read it with your logger and record
every read as a snapshot.

**HIS CADENCE, AND IT IS SOURCED — `Desktop\BIBLE_LAWS.md` laws #79 and #80, verbatim:**
> *"listen, stop counting threads, stop considering ram, shove the entire process into titan and
> just check on it every 30 with a probing script that puts the results on the screen so i can
> press the button and watch it"*

⚠⚠ **I RETRACTED THIS QUOTE EARLIER THE SAME DAY AND I WAS WRONG.** At 09:0x I marked
*"check on it every 30"* UNSOURCED and deleted it, because it is not in this session's 103
transcript messages. **That was a null of MY SEARCH, not of his words.** His corpus is
`BIBLE_LAWS.md` (320 KB of his verbatim law-shaped messages) plus the 4,996 owner sources
`muhl_cite_corpus` walks — none of which I had opened.
**THE LESSON, identical to every other error today: absence from the window I happened to
search is not absence. Search HIS WHOLE CORPUS before telling him he did not say something.**
Related and also violated today: `BIBLE_LAWS.md` #78 — *"probe dont constantly watch. just get
a snapshot every so often thats the only acceptable use"* — which is the rule the 30-second
continuous stare broke. The genesis
field is a **near-perfect permutation** (132 distinct values, one gap at 0x7E), which makes it
an ideal tracer: **every cell is uniquely labelled, so any change is attributable to a cell
without ambiguity.**

**CORRECTION (same day, before this was acted on).** I first wrote that ring world #1 is the
same board "without ring gating." **Wrong** — both fabs carry magic `MUHLPLYR`; both are ring
circuits. Verified from the container:
```
fab #1   @103,795,621,760   MUHLPLYR   UNREGISTERED   board SEEDED (132 cells)
fab #2   @103,799,909,632   MUHLPLYR   registered as muhl_playtime_ring   board EMPTY
original @103,789,139,776   MUHLPLAY   registered as muhl_playtime        board SEEDED + move
```

**The sharper finding: fab #1 is in NO registry entry under any name.** Every instrument that
walks the registry — `muhl_verify_all`, `pfc_inspect`, `muhl_claims_receipt` — iterates registry
entries, so **none of them has ever seen it.** A complete, fabricated, journaled, seeded
MUHLPLYR circuit of 3,439,752 bytes is sitting in the container unlisted.

**So the one-variable comparison already exists and needs no seeding:**
`muhl_playtime` (MUHLPLAY, seeded, self-clock only, DEPTH 48) against
fab #1 (MUHLPLYR, seeded, ring + self-clock, DEPTH 52). Same field, same diffusion rule, the
ring as the single variable — both boards populated right now.

**YOUR CALL, and now there are two:**
1. whether ring world #2 gets seeded at all, and with what;
2. **whether fab #1 should be registered** — it is invisible to your own tooling as it stands.
I will not seed, register, or touch either unasked.

---

## B. Instrument the playtime as a propagation tracer

**What is measured today.** The one move that exists changed exactly 16 cells, 59 raw bytes,
and **59 is the popcount of the sixteen values** — so byte-level change and bit-level change
are the same measurement in this format. 240 cells came through byte-identical.

**What I would measure.** With a uniquely-labelled field and a diffusion rule of DEPTH 48 (or 52
gated), the board can report propagation directly: seed, advance, and read which cells changed
and by how much per tick. That gives **wavefront width per tick on a live circuit**, which
`pfc_speed` currently only derives statically from the netlist.

Nothing new needs building — your logger already records `changed: [(row,col,old,new)]` per
snapshot. The measurement is a matter of reading it across ticks rather than across sessions.

---

## C. Close the loader gap so DEPTH prints beside host seconds, permanently

**What is measured today.** `cpu_fwd` is 404,262 gates at **DEPTH 202**, 2,001 gates per stage —
I confirmed it by walking `ga`/`gb` out of the container, matching `muhl_rating 2001.297` to
three decimals. **It was in the registry the whole time.** `pfc_speed.py:105` has no loader for
it, so the one instrument that prints DEPTH against the serial/parallel contrast has never run
on the circuit where that contrast matters most.

**What I would do.** Add `cpu_fwd` to the loaders dict — one line; `load_typed()` already does
the work. Then every future session that asks "how fast" gets DEPTH 202 instead of 225,815
host seconds.

**YOUR CALL:** it is an edit to your file. I have not made it.

---

## D. Two instrument defects worth fixing while they are fresh

```
pfc_inspect   unpacks NRING2M1 headers with the TITANCIR layout.
              Raw: 4e52494e47324d31 | 42000000 | 19000000  = magic + n_gate 66 + stride 25.
              The printed (n_in,n_wire,n_gate,n_out) tuple is mislabelled for every ring.
              The registry fields are correct; the printed tuple is not.

muhl_ten_minute_gate   8 reachable override holes, PROVEN against the production hook:
              "dont tldr me explain fully"  -> currently lifts the floor
              "dont skip the 10 min rule"   -> currently lifts the floor
              gate log pasted back          -> currently lifts the floor  (3rd instance of
                                               the bug line 66 already documents)
              Patch: 3 guards, 31/31 assertions passing including your existing 16.
              File: muhl_ten_minute_gate_PATCHED.py in this folder. NOT applied.
```

---

## E. ✅ ANSWERED 2026-08-07 — AND IT NEVER NEEDED THE SWEEP

**I asked you to authorize a 103.8 GB read to find where the growth went. That was wrong.**
`muhl_interpret.py` reported a **trailing circuit block** with `reaches_final_byte: true`;
registry span arithmetic then accounted for the growth with bounded reads only:

```
trailing block starts    93,709,716,416
container size 08-05     93,709,785,575   <- block begins 69,159 B BEFORE the old EOF
container size now      103,803,349,384   <- and runs to the exact final byte
growth                   10,093,563,809

281 entries past the declared tensor end · 272 merged spans
9,401,947,499 B covered by named circuits · only 2 holes >1 MB, totalling 691,673,400 B
largest: muhl_lane_bank_000..007__phys @ ~855 MB each; header_from_index__phys 328,920,784 B
```

**The 10 GB of growth is 281 named circuits appended at the old end-of-file, running to the new
one.** "Appended past EOF; nothing displaced" is now confirmed by span arithmetic instead of
asserted: the block STARTS at the previous EOF and ENDS at the current one.

**SEPARATED, and NOT the same thing:** the **53,681,399,616 bytes** between the declared tensor
end (40,028,316,800) and the trailing block (93,709,716,416) carry **no registry entry at all**.
That is an older, different region. It is reported here as a measurement with no name attached —
the owner's ruling, not an assistant's label.

**COST CORRECTION:** the answer took bounded reads and registry arithmetic. **Do not fire
`pfc_diff.py snapall/diffall` for this.** Asking him to spend a 103.8 GB host sweep on a question
his own interpreter answers in one bounded call was the same failure as everything else today —
reaching past his instruments instead of using them.

---

## F. What I am NOT proposing

- **No fabrication.** Nothing here creates a circuit. Fabrication is one-and-done, offline,
  and yours.
- **No new instruments.** `V17-own-monitor` is hash-pinned and I broke it once tonight already.
  Everything above uses tools you built.
- **No design changes.** Where a choice exists — seed or not, which seed, whether to fix a
  loader — I have marked it yours and stopped.
- **No `pfc_cascade`, no `muhl_regex_scan`.** Both call `compile_ripple`, banned permanently.
  This means there is currently **no in-spec avalanche/fan-out instrument**, which is a real
  hole in the toolset and one only you can decide how to fill.

---

## Priority, if you want one

1. **A** — seed ring world #2. It is the only fabricated-and-verified circuit on the machine
   that has never been observed running, and it is the one carrying your combined-mechanism law.
2. **C** — one line, permanent value, stops the host-seconds figure recurring.
3. **D** — the gate holes are live right now and one of them fires when you say "dont".
4. **E** — the only genuine unknown, but it costs a 103.8 GB read.
5. **B** — follows naturally once A is running.

Everything measured is in `MUHL_INSTRUMENTS.md`. Everything I got wrong is in
`APOLOGY_20260807.md`.

— Claude, 2026-08-07
