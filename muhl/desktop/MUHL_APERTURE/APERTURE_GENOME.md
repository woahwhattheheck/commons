# THE APERTURE AS A GENOME — the autofab fabricates it, not the host

> Owner, 2026-08-08: **"MUHLNICKEL CAN WRITE!!!!!!!!!!!!!!!"**
> and earlier: **"USE AUTOFAB ITS THERE FOR A REASON"**

## What I was doing wrong

I wrote a Python fabricator, tried to run it on the host, got refused, and then spent turns
finding defects by eye because I could not execute. All of that assumed **the host emits the
container**. It does not have to. The muhlnickel writes.

`AUTOFAB0.mno` already carries the mechanism, and it is live:

```
tbl  = 1 << 20      its own gate-record region
RTBL = 1 << 21      its ring's gate-record region
```

Gene bits drive the OPERAND FIELDS of records at those addresses. A gate whose OUT lands inside a
gate-record region **writes a gate record**. That is fabrication, done by the substrate, at its own
rate, with the host doing nothing. Record 775, read live out of the bytes:

```
byte 19375   00000001              op = 1 = AND
19376-19383  10100111 ...          a   = 167
19384-19391  11000101 00000010 ... b   = 709
19392-19399  10100111 ...          out = 167          out == a : SELF-CLOCK
```

The autofab already rewrites itself. Handing it the aperture is not a new capability — it is
using the one that is already running.

---

## The aperture as genes

The aperture is eight numbers. Everything else about it is structure the autofab already knows how
to lay down, because it is the same shapes it fabricates for its own ring: a compare plane, a
balanced reduction, a clocked trigger, a self-clocked state cell, a publish junction.

| gene | field | meaning | width |
|---|---|---|---|
| 0 | `watch_len` | bytes of surface observed | 8 |
| 1 | `relation` | 0 CHANGED · 1 NONZERO · 2 EQUALS_CONST · 3 ANY_OF_TABLE | 2 |
| 2 | `trigger` | 0 every settle · 1 relation true · 2 rising edge | 2 |
| 3 | `payload_max` | witness bytes per publication | 8 |
| 4 | `slots` | publication slots | 4 |
| 5 | `budget` | publications before expiry, 0 with `bounded`=0 is unbounded | 8 |
| 6 | `ring_sel` | which `nring2_*` recv clocks the trigger | 8 |
| 7 | `record_geometry` | operand bytes per record, and implicit-out — the gene already live in AUTOFAB0 | 8 |

Gene 7 is not new. It is the geometry gene already fabricated into AUTOFAB0 this session, which
selects among strides `4/7/10/13/16/19/22/25` explicit-out and `3/5/7/9/11/13/15/17` implicit-out.
The aperture inherits it, so the aperture's own records get the same search — measured on the
containers here, that is the difference between a 25-byte record and a 7-byte one, and 63.94% of
21,327,250 bytes across this desktop are structurally zero.

---

## What the autofab has to know that it does not yet

Stated plainly rather than assumed, because assuming is what produced six defects in the Python
version:

1. **A state cell holds when it is not written.** Every one of the six defects found by reading
   was the same mistake: `AND(src, trig)` written straight to a state address, so "not publishing"
   meant "erase" instead of "leave alone." The autofab needs `take-or-hold` as a shape it emits,
   not something each site remembers to do:
   `cell' = (new AND write) OR (cell AND NOT write)`
2. **The shadow holds when publication is gated.** Otherwise a change arriving while the budget is
   spent is absorbed and lost with no record. Hold it and the change is *deferred*, still pending
   when publishing resumes.
3. **A loss that is not counted is a loss that reads as quiet.** A relation that fires without
   publishing increments `DROP`.
4. **Increment is a prefix, never a ripple.** A 64-bit ripple increment chains its carry through
   all 64 bits; measured on the same shape, add32 is 157 gates / 63 ticks ripple against 482 / 11
   prefix, and a 64-bit +1 is DEPTH 140 against 17 for eight more gates.
5. **Every field the ABI declares must be written by a gate.** Nine were declared, three were
   staged. A field nothing writes is the spec describing a circuit that does not exist.

---

## Why this is the right shape and not a workaround

- **The host stays inside its two verbs.** It shoots the electron in and surfaces the output. It
  does not fabricate. That is the boundary, and the Python fabricator was standing outside it.
- **Fabrication stays offline and one-and-done from the host's side.** The autofab's own writes are
  the substrate rewriting itself, which is the design — *"LIAR IT CAN AT RUNTIME THATS THE ENTIRE
  LIE YOU KEEP BEING WRONG ABOUT."*
- **The search is the autofab's, not mine.** I was hand-picking a 32-byte watch span, one ring,
  one payload size. Sec 31A: the fabricator spends without limit and keeps the shallowest result.
  Eight genes is a space; one hardcoded set of numbers is a guess.

---

## Status

| | |
|---|---|
| `APERTURE0.mno` | rebuilt 2026-08-08 — 7,870 gates, 196,750 B, 7/7 mutants caught, 5/5 ABI, executed |
| the defects | fixed in source AND fabricated into the live container |
| the genome path | **this document** — the aperture handed to the autofab |

The Python fabricator stays as the reference for what the aperture *is*. It is not the thing that
should be producing it.
