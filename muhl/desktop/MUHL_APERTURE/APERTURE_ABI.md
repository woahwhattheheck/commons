# MUHL APERTURE - BINARY ABI v1

> The substrate answers a question about itself and publishes a bounded result.
> The host reads **only the aperture**. It never scans the interaction surface.
>
> Owner's boundary, obeyed exactly:
> **"if the host does anything beyond shooting electron or surfacing the muhlnickel output
> its violating spec"** - the host has two verbs. Shoot the electron in. Surface the output.
> The aperture IS the surfacing point.

---

## 0. WHY AN APERTURE

The surface changes faster than the host can look, and looking at all of it throttles the machine -
measured: streaming the 14.26 GB strings file and mmap-sweeping `titan.gguf` made the laptop
throttle audibly. So **the observation work happens in gates.** The host receives a small,
deliberately selected record.

Nothing on the capture path is converted. No hex, no text, no JSON, no base64, no hash, no sum, no
compression. A witness is the bytes.

---

## 1. LAYOUT

One contiguous span, bump-allocated by `titan_circuit._alloc` so it can never overlap another
circuit. Two publication **slots**, so the substrate publishes into one while the host reads the
other.

```
APERTURE_BASE + 0                     CONTROL   64 B
APERTURE_BASE + 64                    SLOT A    ENV 64 B + PAYLOAD P
APERTURE_BASE + 64 + (64+P)           SLOT B    ENV 64 B + PAYLOAD P
```

`P` = `payload_max`, fixed at fabrication. Default **256 bytes**.
Total aperture = `64 + 2*(64 + P)` = **704 B** at the default.

### 1.1 CONTROL (64 B, substrate-written, host read-only)

| off | size | field | meaning |
|---|---|---|---|
| 0 | 8 | `magic` | `MUHLAPR1` |
| 8 | 2 | `version` | 1 |
| 10 | 2 | `slot_count` | 2 |
| 12 | 4 | `payload_max` | P |
| 16 | 8 | `publish_seq` | publications ever attempted |
| 24 | 8 | `drop_count` | publications the host never read before overwrite |
| 32 | 1 | `active_slot` | slot the substrate is currently writing |
| 33 | 1 | `policy` | 0 OVERWRITE_OLDEST, 1 DROP_NEW_WHEN_UNREAD |
| 34 | 30 | reserved | zero |

### 1.2 ENVELOPE (64 B, one per slot)

| off | size | field | meaning |
|---|---|---|---|
| 0 | 8 | `gen_before` | generation, written FIRST |
| 8 | 4 | `config_id` | which observation produced this |
| 12 | 1 | `payload_type` | 1 OBSERVABLE, 2 WITNESS, 3 RESULT |
| 13 | 1 | `flags` | bit0 COMPLETE, bit1 OVERFLOW, bit2 TORN |
| 14 | 2 | reserved | zero |
| 16 | 8 | `substrate_pos` | causal position - the ring carry counter |
| 24 | 8 | `witness_addr` | absolute file address the payload came from |
| 32 | 4 | `payload_len` | bytes valid in PAYLOAD, at most `payload_max` |
| 36 | 4 | `dropped_since` | dropped since the last successful publication |
| 40 | 16 | reserved | zero |
| 56 | 8 | `gen_after` | generation, written LAST |

**`gen_before` and `gen_after` are the coherency mechanism.** A reader accepts a slot only when the
two are equal and non-zero. A publication in flight has them unequal, so a torn read is
**detectable, not merely unlikely**. Generation-before/after was chosen because it needs no host
acknowledgement and no lock - the substrate never waits for anything.

### 1.3 PAYLOAD (P bytes)

Exact bytes. `payload_len` valid, remainder undefined. **Never transformed.**

---

## 2. PUBLICATION, AND WHY IT CANNOT BACKPRESSURE

The publish path is a **one-way junction** - measured 2 gates / 2 gate-delays (one tick), forward
transfer 61 of 64 ticks, **reverse 0**, holding at 0 out to 4,096 ticks and under a hostile driver
on every downstream wire (`muhl_junction.py` J3/J5). The host side physically cannot signal back
through it. (The transfer and holding figures are genuinely in ticks - measured across settles; the
buffer's own cost is 2 gate-delays inside one tick.)

Sequence, all in gates:

1. `gen_before` takes `publish_seq + 1` on the inactive slot
2. envelope fields, then payload bytes, through the junction
3. `gen_after` takes the same value
4. `active_slot` flips, `publish_seq` increments

**The host is never on this path.** No acknowledgement is read, no flag is waited on. A slow host
misses generations; it never stalls the computation.

### 2.1 Overwrite / drop policy - explicit

- **OVERWRITE_OLDEST (default, policy 0).** The substrate always publishes. If the host has not
  consumed the previous slot, that generation is lost and `drop_count` increments. Freshness wins.
- **DROP_NEW_WHEN_UNREAD (policy 1).** If neither slot is consumed, the new publication is
  discarded and `drop_count` increments. Continuity of an in-progress read wins.

Either way `drop_count` is monotonic and the computation never stalls. **Loss is reported, never
hidden** - a reader that sees `drop_count` jump knows exactly how many it missed.

---

## 3. RESOURCE LIMITS - bounded and stated

| budget | value | fixed at |
|---|---|---|
| aperture bytes | `64 + 2*(64+P)` = 704 at P=256 | fabrication |
| payload per publication | P = 256 B | fabrication |
| slots | 2 | fabrication |
| host read per poll | 704 B | - |
| gates in the aperture circuit | reported by the fabricator | fabrication |
| **interaction-surface bytes read by the host** | **0** | - |

The last row is the point.

---

## 4. OBSERVATION CONFIG

A config is a record the substrate reads. It is not host logic.

| field | meaning |
|---|---|
| `config_id` | identity, echoed in every envelope |
| `watch_addr`, `watch_len` | the span the substrate observes |
| `relation` | 0 CHANGED vs shadow, 1 NONZERO, 2 EQUALS_CONST, 3 ANY_OF_TABLE |
| `trigger` | 0 every settle, 1 relation true, 2 relation edge |
| `witness_addr`, `witness_len` | exact bytes captured, at most P |
| `budget` | max publications before expiry, 0 = unbounded |
| `policy` | 0 or 1 as above |
| `lifetime` | 0 = until cleared, N = expire after N publications |

---

## 5. DERIVED vs EXACT - kept strictly apart

Conflating them is how a lossy summary gets mistaken for evidence.

- **OBSERVABLE (type 1)** - a property the substrate maintains. Derived by construction, and says so.
- **WITNESS (type 2)** - bytes copied unchanged from `witness_addr`. **Byte-exact.** No transform on
  the capture path, ever.
- **RESULT (type 3)** - an answer the substrate had already computed. Exact as computed.

---

## 6. WHAT REMAINS UNKNOWN OR HARDWARE-DEPENDENT

1. **Ring carry to wall-clock.** `substrate_pos` is a causal position, not a timestamp. Converting
   it to seconds would be a host number about a different machine.
2. **Publications per settle.** Set by electron count, not by design - BIBLE_LAWS: *"how many gate
   settles happen between input and output is in our control its a direct result of the number of
   electrons ejected into the ring."*
3. **Torn-read window width.** The scheme *detects* tearing; how often it occurs is a property of
   the substrate's write ordering and is the owner's to state.
4. **Slot counts above 2.** Two is sufficient for one reader. More readers is untested here.
