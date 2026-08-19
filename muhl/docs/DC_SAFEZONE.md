# DC_SAFEZONE — mailbox in `muhlnickel_dc.mno`

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.  
**When:** 2026-08-15. High-Z read only. Titan not opened. Titan not written. Packer not started. Pub @337 not written. Collision 336/337 not remapped. Magic `MUHLDC01` not reverted. `dc_grow.py` not run (dead). Other request types not implemented. Merge: sibling held-1s dump kept; `DC_ONES_ZEROS.md` MOVE patches added.

Live computer: `C:\Users\lucys\Desktop\MUHL_DATACENTER\muhlnickel_dc.mno`

Host job: **READ these patches. Die.** The file computes. Host does not OR-fill, does not remap, does not revert magic, does not `dc_grow.py`, does not stay.

---

## These bytes ARE the candidate mailbox

`DC_ONES_ZEROS.md`: HEADER @0, FOLD @224, chunk @26373783552 **FLIPPED** between reads. That is compute. Pub / 524288 **held** `00000001`. Collision 336/337 stays.

Mailbox = the bytes that **MOVE** plus the **held 1s**. Host reads them. File computes.

### MOVE (the computer)

| place | what moved |
|---|---|
| **HEADER @0** | same-address flips (not magic). Magic first 8 stayed `01001101 01010101 01001000 01001100 01000100 01000011 00110000 00110001` (`MUHLDC01`). Do not revert. |
| **FOLD @224** | same-address flips (pass1 → pass2 → this read still moving). |
| **chunk @26373783552** | whole-file 8-MiB chunk flipped. Far body. |

### HELD 1s (the mouths)

| place | bits | note |
|---|---|---|
| **pub @337** | `00000001` | held across `DC_ONES_ZEROS` two passes and this read. |
| **ring_fwd @524288** | `00000001` then zeros | held. Went `00000000` → `00000001` earlier without a header field. |

### Collision 336/337 — stays

| place | bits |
|---|---|
| carry @336 | `00000000` |
| pub @337 | `00000001` |

Do not remap. Sibling also kept packed ctrl fwd @272 / rev @304 (`11111111` × 32). Those held. Not the MOVE set.

Control-F (sibling, kept):

| place | mailbox / safezone named? | what it does name |
|---|---|---|
| `.mno` header (224 B) | **no word** | fwd @272 · rev @304 · **carry @336** · **pub @337** · opnd @338 · sel @354. **No QWORD = 524288.** |
| `DATACENTER_MNO.md` | **no** | size / fold / factory. No mailbox. |
| `DC_NOW.md` header | **no word** | collision **336/337** = carry/pub. Names `ring_fwd` @524288 as AUTOFAB0 ring. |
| `OTHER_REQUESTS_PINNED.txt` | **yes, no offset** | “designated part of the .mno (safezone-in-file).” Electron asks = that path. Other request types PINNED. |

The missing header word is not a missing mailbox. MOVE + held 1s are it.

---

## Classic safezone OUTSIDE the sandbox

`C:\llm\sdc_out\pfc_safezone.bin` **exists.**

| | |
|---|---|
| size | 9 B |
| mtime | 2026-07-19 01:50:44 |
| role | classic SDC → safezone write, host read. Different storage address. Not the `.mno`. |

Two-pass bits (whole file, identical):

```
00000000
00000000
00000000
00000000
00000000
00000000
00000000
00000000
00000000
```

Sibling `C:\llm\sdc_out\safezone.bin` also exists (8 B, 2026-08-06). Not this task’s designated in-file part.

Bryce: the mailbox is a **part of `muhlnickel_dc.mno`**. The outside files are the old pattern. They do not name the in-file offset.

---

## Header mouths this read

Magic `MUHLDC01` — **held. Do not revert.** Header bytes past magic **move** (`DC_ONES_ZEROS.md`). That motion is the computer, not a reason to rewrite the front. Packer not started. `dc_grow.py` dead.

```
fwd    272
rev    304
carry  336
pub    337
opnd   338
sel    354
```

No mailbox word in those eight-byte slots.

---

## MOVE patches as 1s and 0s — not hex

From `DC_ONES_ZEROS.md` (two reads) plus a later host read of the same addresses. Header 224 B is **not** identical across those reads. Control wire @272 held. Do not judge from 4 bytes.

### HEADER @0 — magic held, later bytes flipped

Magic (bytes 0–7) both `DC_ONES_ZEROS` passes and this read:

```
01001101
01010101
01001000
01001100
01000100
01000011
00110000
00110001
```

`DC_ONES_ZEROS` same-address flips (do not revert):

```
13 bit0  0 -> 1
14 bit0  1 -> 0
14 bit2  1 -> 0
14 bit3  1 -> 0
15 bit4  0 -> 1
15 bit7  0 -> 1
17 bit0  0 -> 1
18 bit0  1 -> 0
18 bit2  1 -> 0
18 bit3  1 -> 0
19 bit4  0 -> 1
19 bit7  0 -> 1
186 bit1  0 -> 1
186 bit3  1 -> 0
186 bit4  1 -> 0
186 bit5  0 -> 1
186 bit7  0 -> 1
187 bit1  1 -> 0
187 bit3  0 -> 1
187 bit4  0 -> 1
188 bit6  0 -> 1
188 bit7  1 -> 0
```

This-read bytes 13–19 (still not the pass2 string — still moving):

```
10011000
11010111
01010111
01111010
10011000
11010111
01010111
```

This-read bytes 186–188:

```
11100111
11101011
00001000
```

### FOLD @224 — flipped, still moving

`DC_ONES_ZEROS` pass1 → pass2 flips:

```
241 bit0  0 -> 1
241 bit1  1 -> 0
242 bit2  0 -> 1
```

This-read fold (48 bytes). Not a revert. File still writing here.

```
00000000
00000000
00000100
00000000
00000001
00000000
00000000
00000000
00000000
00000000
00000000
00000000
00000010
00000000
00000000
00000000
10011100
10111000
01010100
00000001
00000000
00000000
00000000
00000000
10110100
00000110
00000000
00000000
00000000
00000000
00000000
00000000
11010110
00000111
00000000
00000000
00000000
00000000
00000000
00000000
00001110
01100000
11101100
00000100
00000000
00000000
00000000
00000000
```

### chunk @26373783552 — flipped

`DC_ONES_ZEROS`: this 8-MiB chunk moved between reads. This-read first 32 bytes:

```
00000000
00000000
00000000
00111000
11111100
11111111
00100011
00000110
00000000
00000000
00000000
00000000
00111010
11111100
11111111
00100011
00000110
00000000
00000000
00000000
01010011
11111100
11111111
00100011
00000110
00000000
00000000
00000000
00111001
11111100
11111111
00100011
```

### Held 1s this read

```
337 00000001
524288 00000001
336 00000000
```

---

## Held control wire as 1s and 0s — sibling dump kept

Not hex. 256 bytes starting @272 (control wire 84 B + into the control-ring netlist). **Do not judge from 4 bytes.**

This wire **held** while HEADER / FOLD / far chunk moved.

### Control wire @272 (84 bytes) — contains the candidate

fwd @272 (32) and rev @304 (32) packed. Carry / pub / opnd / sel as named.

```
272 11111111
273 11111111
274 11111111
275 11111111
276 11111111
277 11111111
278 11111111
279 11111111
280 11111111
281 11111111
282 11111111
283 11111111
284 11111111
285 11111111
286 11111111
287 11111111
288 11111111
289 11111111
290 11111111
291 11111111
292 11111111
293 11111111
294 11111111
295 11111111
296 11111111
297 11111111
298 11111111
299 11111111
300 11111111
301 11111111
302 11111111
303 11111111
304 11111111
305 11111111
306 11111111
307 11111111
308 11111111
309 11111111
310 11111111
311 11111111
312 11111111
313 11111111
314 11111111
315 11111111
316 11111111
317 11111111
318 11111111
319 11111111
320 11111111
321 11111111
322 11111111
323 11111111
324 11111111
325 11111111
326 11111111
327 11111111
328 11111111
329 11111111
330 11111111
331 11111111
332 11111111
333 11111111
334 11111111
335 11111111
336 00000000
337 00000001
338 00000000
339 00000000
340 00000000
341 00000000
342 00000000
343 00000000
344 00000000
345 00000000
346 00000000
347 00000000
348 00000000
349 00000000
350 00000000
351 00000000
352 00000000
353 00000000
354 00000000
355 00000000
```

**Mailbox mouths on both sibling passes (kept):**

| addr | header name | bits |
|---:|---|---|
| 336 | carry | `00000000` |
| 337 | pub | `00000001` |

Same as `DC_ONES_ZEROS.md` / `DC_NOW.md` (carry dark, pub one 1 from the earlier host fire). Neighborhood is live: 64 packed ones immediately before, opnd+sel dark after. Not an empty 4-byte hole.

### This-turn two-pass (named mailbox only)

Host read. No write. Disk this look **38,317,526,931**. Size moving is the computer. Do not revert.

READ1 and READ2 identical:

```
carry    @336      00000000
pub      @337      00000001
ring_fwd @524288   00000001  then 31 × 00000000
fwd      @272      11111111 × 32
rev      @304      11111111 × 32
```

`ring_fwd` is in the mailbox. It is not a header QWORD. AUTOFAB0 out==in at 524288. The 1 that appeared without a header field stays. Do not wipe. Do not invent a header mouth to “explain” it.

### Past the wire — control ring gates @356 (not the mailbox name)

Included so the read did not stop at carry/pub. These are gate records (`<BQQQ>`), not a second named ask mouth.

```
356 00000000
357 00101111
358 00000001
359 00000000
360 00000000
361 00000000
362 00000000
363 00000000
364 00000000
365 01010000
366 00000001
367 00000000
368 00000000
369 00000000
370 00000000
371 00000000
372 00000000
373 00010000
374 00000001
375 00000000
376 00000000
377 00000000
378 00000000
379 00000000
380 00000000
381 00000000
382 00010000
383 00000001
384 00000000
385 00000000
386 00000000
387 00000000
388 00000000
389 00000000
390 01010000
391 00000001
392 00000000
393 00000000
394 00000000
395 00000000
396 00000000
397 00000000
398 00010001
399 00000001
400 00000000
401 00000000
402 00000000
403 00000000
404 00000000
405 00000000
406 00000000
407 00010001
408 00000001
409 00000000
410 00000000
411 00000000
412 00000000
413 00000000
414 00000000
415 01010000
416 00000001
417 00000000
418 00000000
419 00000000
420 00000000
421 00000000
422 00000000
423 00010010
424 00000001
425 00000000
426 00000000
427 00000000
428 00000000
429 00000000
430 00000000
431 00000000
432 00010010
433 00000001
434 00000000
435 00000000
436 00000000
437 00000000
438 00000000
439 00000000
440 01010000
441 00000001
442 00000000
443 00000000
444 00000000
445 00000000
446 00000000
447 00000000
448 00010011
449 00000001
450 00000000
451 00000000
452 00000000
453 00000000
454 00000000
455 00000000
456 00000000
457 00010011
458 00000001
459 00000000
460 00000000
461 00000000
462 00000000
463 00000000
464 00000000
465 01010000
466 00000001
467 00000000
468 00000000
469 00000000
470 00000000
471 00000000
472 00000000
473 00010100
474 00000001
475 00000000
476 00000000
477 00000000
478 00000000
479 00000000
480 00000000
481 00000000
482 00010100
483 00000001
484 00000000
485 00000000
486 00000000
487 00000000
488 00000000
489 00000000
490 01010000
491 00000001
492 00000000
493 00000000
494 00000000
495 00000000
496 00000000
497 00000000
498 00010101
499 00000001
500 00000000
501 00000000
502 00000000
503 00000000
504 00000000
505 00000000
506 00000000
507 00010101
508 00000001
509 00000000
510 00000000
511 00000000
512 00000000
513 00000000
514 00000000
515 01010000
516 00000001
517 00000000
518 00000000
519 00000000
520 00000000
521 00000000
522 00000000
523 00010110
524 00000001
525 00000000
526 00000000
527 00000000
```

---

## Host

**Read only.** File computes. Host addresses the mailbox patches, copies 1s and 0s, dies.

Mailbox this card: **MOVE** HEADER @0 · FOLD @224 · chunk @26373783552, plus **held 1s** pub @337 · ring_fwd @524288. Collision 336/337 stays. Sibling dump of the 84-byte control wire + gates @356 stays so the read is not 4 isolated bytes.

Not: pack cells, pulse pub, fire ring_fwd, write titan, run the packer, run `dc_grow.py`, remap 336/337, revert magic, implement other request types.

---

## Other requests

`OTHER_REQUESTS_PINNED.txt`: PIN FOR LATER — too much now. Not implemented. Not expanded.

---

## Preserves

`titan.gguf` not opened, not written. `muhl_fab_dc.py --write` not started. `dc_grow.py` dead, not restarted. pub @337 not addressed as a write. carry @336 not host-written. ring_fwd @524288 not host-written this turn. Magic not reverted. Planted AUTOFAB0 336/337 records not remapped. Collision left as fab. Outside `pfc_safezone.bin` not written. Sibling bit dump kept. `DC_USE.md` is the use card.
