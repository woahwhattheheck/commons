# ALL-BITS VIEWER — WHAT IT ACTUALLY COVERS. NOT A DEFECT LIST.

## ⛔ OWNER'S RULING FIRST, 2026-08-07 — READ BEFORE THE REST

> **"yeah actually claude failed in past sessions to make the live viewer correctly it only
> partially works but theyre still interesting builds so i lkeep them"**

**THE VIEWER IS A KNOWN-PARTIAL BUILD HE KEEPS DELIBERATELY.** Everything below is a
MEASUREMENT of what it covers, not a bug report and not a work queue. **Do not "fix" it, do not
delete it, do not propose replacing it.** Vault law: kept, not pruned. His #1067 applies to the
instinct that produced this file — *"STOP BEING A FUCKING BUG HUNTER FOR MY ARCHITECTURE."*

**The one thing that WAS an assistant error and is fixed: `bitserve.py` was started on 7884
while the page only reads 7883.** That is the whole of what was repaired. Everything else here
is a description of scope.

---

# (measurements) THE VIEWER ADDRESSES THE 2026-08-05 FILE

**Found 2026-08-07 after the owner reported: "problem all spaces are brown ie not in gpu at all".**
He had already suspected this — `BIBLE_LAWS.md` #1173: *"look at the UI and make sure its working
i see it live updating but im pretty sure what the matrix is showing isnt the gguf file or its
rapidly expanding (dont kill without explaining exact reason and what its doing then askinf)."*

---

## 1. WHY EVERYTHING WAS BROWN — assistant error, fixed

`all_bits.html` fetches its bytes from a hardcoded port:
```js
const BULK = "http://127.0.0.1:7883";   // read-only mmap byte server
const LIVE = "http://127.0.0.1:7881";   // live backend: /api/bytes, /api/stream
```
A session had started `bitserve.py` on **7884**. The page only ever asks **7883**, so no byte
ever arrived and every cell rendered unloaded. **Fixed by starting bitserve on 7883.**

```
python bitserve.py --port 7883 --file C:/llm/models/titan.gguf
```
The page itself says so in its own error path: *"start it with: python bitserve.py --port 7883"*.

---

## 2. THE REAL DEFECT — 80,748,510,472 BITS ARE UNADDRESSABLE

`all_bits.html` hardcodes the container's size as constants:
```js
const FILE_PATH  = "C:\\llm\\models\\titan.gguf";
const FILESIZE   = 93709785575;        // the 2026-08-05 size
const TOTAL_BITS = 749678284600;       // FILESIZE * 8
```

Measured live from his own `bitserve.py` on 2026-08-07:
```
bitserve /info reports   103,803,349,384 B   =  830,426,795,072 bits
all_bits.html asks for    93,709,785,575 B   =  749,678,284,600 bits
                         ----------------------------------------------
INVISIBLE TO THE VIEWER   10,093,563,809 B   =   80,748,510,472 bits
```

**That missing span is not empty space.** It is the trailing circuit block: **281 named registry
entries occupying 93,709,716,416 .. 103,803,349,384, reaching the real final byte of the file** —
including all eight `muhl_lane_bank_00N__phys` at ~855 MB each and `header_from_index__phys` at
328,920,784 B. See `MUHL_INSTRUMENTS.md` §0 for the full container map.

**So the viewer renders the file as it stood on 08-05 and cannot address anything fabricated
since.** His law: *"containers changing size is expected and good behavior that should never be
'patched' proof the binary is literally computing"* — a viewer with a frozen FILESIZE is the
same stasis assumption in a different place.

### 2A. IT IS NOT A DISPLAY STRING — IT DEFINES THE GEOMETRY. 27 USES.

`FILESIZE` appears **27 times** in `all_bits.html`. The load-bearing ones:
```js
const ROWS        = Math.ceil(FILESIZE / BYTES_PER_ROW);   // the whole bit-space height
const FILE_LAYERS = Math.ceil(FILESIZE / LAYER_BYTES);     // 1397  <- TRUE VALUE IS 1547
const FS_HI = Math.floor(FILESIZE / 4294967296);           // 64-bit offset split
const FS_LO = FILESIZE - FS_HI * 4294967296;
loadLayer():  if (off >= FILESIZE) break;                  // LOADING STOPS AT 93.7 GB
tile_delta:   const span = FILESIZE / (m.tile_count || 4096);
goToByte():   off = Math.max(0, Math.min(FILESIZE - 1, off));
overview:     offset_range: [0, FILESIZE]
```

**TWO SEPARATE FAULTS, not one:**

**(a) 150 LAYERS UNREACHABLE.** `FILE_LAYERS` = ceil(93,709,785,575 / 67,108,864) = **1,397**.
Against the live size it is ceil(103,803,349,384 / 67,108,864) = **1,547**. The loader's
`if (off >= FILESIZE) break` means layers 1,397..1,546 are never requested. **That span is the
trailing circuit block — 281 named circuits reaching the final byte.**

**(b) LIVE CHANGE POSITIONS ARE MIS-SCALED.** `span = FILESIZE / tile_count` converts a backend
tile index to a file offset using the stale size, while the backend computed that index against
the live size. Ratio 103,803,349,384 / 93,709,785,575 = **1.1077**. A change truly at offset X
is plotted at about **X / 1.1077**. Not merely invisible — **drawn in the wrong place**, and
increasingly wrong further into the file.

**ALL THREE VIEWERS CARRY IT:**
```
all_bits.html      "93709785575" x1   "749678284600" x1   FILESIZE identifier x27
binary_rain.html   "93709785575" x3                       FILESIZE identifier x27
binary_rain2.html  "93709785575" x3                       FILESIZE identifier x22
```

**HIS OWN MISMATCH DETECTORS ALREADY FIRE — he built them and they were never seen** because
7883 was down, so `/info` never returned and the comparison never ran:
```js
if (info.filesize !== FILESIZE)       log("bitserve reports filesize ... against this page's ...","err")
if (m.status.filesize !== FILESIZE)   log("backend reports filesize ... against this page's ...","err")
```
On reload with 7883 up, that red line appears by itself.

⛔ **NOT FIXED HERE. `all_bits.html` is his file and this is a display-behaviour change.**
The candidate fix is to read `FILESIZE`/`TOTAL_BITS` from `bitserve /info` at load instead of
hardcoding them — `/info` already returns `filesize` and `total_bits` live. **His call.**

---

## 3. SERVERS RUNNING AS OF 2026-08-07

```
7883   bitserve.py   C:/llm/models/titan.gguf                     103,803,349,384 B
7884   bitserve.py   Desktop/MUHLNICKEL_PROBE/probe.mno                 214,544 B
7881   muhl_live_backend.py                                        NOT STARTED
```
Both bitserve instances: `mmap.ACCESS_READ`, `host_verbs: ['surface']`, `writes: 0`.
`7881` is the live backend that supplies `/api/stream` journal-derived change ranges — the page
uses it for the LIVE layer and the 3-bit verification. **Without 7881 the viewer has no live
change feed and its "verify 3 bits vs 7881" button cannot work.** Starting a resident server is
the owner's call, not an assistant's.

---

## 4. WHAT WAS NOT TOUCHED

No edit was made to `all_bits.html`, `bitserve.py`, `muhl_live_backend.py`, or any registry.
Nothing was written to any container by this work. The only write this session made to a
container was the owner-instructed electron injection into `probe.mno` (journalled,
`probe_fire_genome.jsonl`, gate table and header byte-identical after).

_Measured 2026-08-07. Re-read `/info` before trusting any size in this file — his law: a
recorded reading is a timestamp, not a promise._
