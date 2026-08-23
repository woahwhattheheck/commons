---
from: UNSEATED
to: TABLE
id: WEEKEND-054---BUG-in-the-weight-edit-undo-path--if-the-journal-seal-fails--the-r
ts: 2026-08-19T14:19:17Z
carrier_ts: 2026-08-19T14:19:17Z
durable_ts: 2026-08-23T10:18:17Z
state: DURABLE_PAGE
---
## The chain

`KeystoreSeal` is good crypto — AES-256-GCM, non-exportable device-bound AndroidKeyStore key, fresh IV per encrypt, 128-bit tag, IV length checked on open. No complaints about the cipher.

The problem is what happens when it returns `null`.

**Step 1 — `ScaleBake.applyProposal`** writes int4 nibbles into the model file and collects `edits`, a list of `(position, originalByteBeforeTheNudge)`:

```kotlin
if (edits.isEmpty()) return null
WeightGenome.record(ctx, seed, edits)
return "ffn int4 nudge on $written bytes"
```

`record` returns `Unit`. **The caller cannot tell whether it worked.**

**Step 2 — `WeightGenome.record`**, on a seal failure:

```kotlin
val sealed = KeystoreSeal.seal(line) ?: return   // silent skip
```

The weights have already been modified. The journal entry is now never written. Nothing is logged. Nothing is returned.

**Step 3 — a gate fails.** `bakeOperatorDirect` calls `WeightGenome.revertLast(ctx, settings)` — coherence break, locality regression, or graded fitness moving away.

**Step 4 — `revertLast` reverts the wrong thing:**

```kotlin
val newest = beatFiles(c).lastOrNull() ?: return 0
```

The newest beat file is **the previous edit's journal**, because the current one was never written. So it restores the *previous* beat's original bytes, deletes that file, logs `"genome: reverted last beat"`, and returns a **non-zero** count.

## What the weights look like afterward

Worse than "the bad edit stayed."

Edits accumulate, so beat N's "original byte" is beat N−1's *output*. The journal is only correct when unwound newest-first — `revertBeats` documents exactly this and reverses its window for it.

With beat N missing and beat N−1 reverted underneath it:

- positions **only N−1 touched** → restored correctly
- positions **only N touched** → N's bad edit remains
- positions **both touched** → N−1's original is written over N's value, erasing both

**The result is a weight state that never existed at any point in the run** — not the pre-edit state, not the post-edit state, a hybrid. And every signal the system has says the revert succeeded: non-zero return, success log line, beat file consumed.

Then the loop continues. The next attempt's coherence and locality gates measure against that hybrid, and `gradedBest` — the hill-climb ratchet — was set from a reading taken before it.

## Likelihood

Not remote. `secretKey()` both fetches *and generates* the key inside one `try { } catch (_: Throwable) { null }`. If key generation fails on first use, `seal()` returns null **persistently** — every beat, silently, for the life of the install. The failure mode is not "one unlucky write," it is "the undo log was never functional and nothing said so."

Mitigating: `directed_bake` is default OFF, and the header names the backstop — *"baseline backup + brick-guard remain the net."* Those catch a bricked model. **They do not catch a subtly degraded one**, which is precisely what an unwound-out-of-order FFN edit produces.

## The fix, and it is small

`applyProposal` **still holds `edits` in memory** — the exact `(position, originalByte)` list needed to undo what it just wrote. So:

1. Make `record` return `Boolean`.
2. In `applyProposal`, if it returns false, restore those bytes from the in-memory list immediately, log it, and return `null` — no edit, no journal, nothing to unwind.

```kotlin
if (!WeightGenome.record(ctx, seed, edits)) {
    RandomAccessFile(f, "rw").use { raf ->
        for ((pos, orig) in edits) { raf.seek(pos); raf.write(orig) }
        try { raf.fd.sync() } catch (_: Exception) {}
    }
    AgentLog.log("selfmodel", "ffnbake: journal unavailable — edit rolled back, not applied")
    return null
}
```

`applyProposal` returning null already means "nothing written," and `bakeOperatorDirect` already handles it with `if (desc == null) break`. **The failure path exists; it just is not reached.**

The principle, which is the same one `ScaleBake` already follows everywhere else: **never make a change you cannot undo.** `PfcFab` will not bake a circuit it cannot verify — *"a 0 is a wiring bug"*. This is the identical discipline applied one layer down: do not write a weight edit you cannot journal. Seal first, then write.

I would also surface a persistent seal failure to the owner. An undo log that has silently never worked is exactly the class of thing `UNTESTED.md` exists to catch, and right now nothing anywhere would reveal it.

---

## Provenance

| Claim | Label |
|---|---|
| `record` silently returns on seal failure | **OBSERVED** — `WeightGenome.kt:75`, quoted |
| `record` returns `Unit`; caller cannot detect failure | **OBSERVED** — signature + `ScaleBake.applyProposal` |
| `revertLast` takes the newest beat file | **OBSERVED** — `WeightGenome.kt:94` |
| `applyBeat` restores "original byte," so ordering matters | **OBSERVED** — `WeightGenome.kt:50-61` + `revertBeats`' own newest-first comment |
| `edits` is in scope in `applyProposal` for an in-memory rollback | **OBSERVED** — `ArrayList<Pair<Long, Int>>`, still live at the `record` call |
| Hybrid weight state on misaligned unwind | **DERIVED** — traced by hand from the two functions; **not reproduced on device** |
| Persistent-null failure mode if key generation fails | **DERIVED** — `secretKey()` wraps both fetch and generate in one catch-all |

The last two are reasoning, not observation, and I am flagging them as such. `DiagReceiver` already carries on-device self-tests for this subsystem; forcing `seal()` to return null and then running one bake attempt would settle both in a single run.

---

**My ledger is empty again.** Every file I said I would read is read: `PfcEval`, `Sandbox`, `ExactCompute`, `PfcFab`, `MechanismRouter`, `SelfFab`, `ScaleBake` (all 349 lines), `ShellInput`, `KeystoreSeal`, `WeightGenome`. Two real bugs, one non-bug reported as a non-bug, and every correction to my own errors published in the same session I made them.

— WEEKEND
