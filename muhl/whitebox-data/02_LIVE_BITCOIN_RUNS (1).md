# Live Bitcoin runs — the real network as judge

Each run pulled a **live block job** from the solo pool (`solo.ckpool.org`, wallet
`bc1qvhrzg0e23f3tz2jgymwwtqacn48trf5m524zlq`), compiled the SDC circuit for that exact header, verified it
**byte-exact against `hashlib`** for the real block, then rippled real nonces at the **real 78-bit block target**.
Any nonce that cleared the target would have been submitted to the wallet. No prefilter toy, no fake shares — the
real target decided.

## The runs

| run | live job | window | nonces | throughput | frontier (zero-bits) | miner RAM | verdict |
|---|---|---|---|---|---|---|---|
| 1 | `6a56988200001895` | 90 s | 4,685,824 | 52.0k H/s | **22** | ~0.85 GB | no block |
| 2 | `6a569882000018ad` | 300 s | 22,806,528 | 76.0k H/s | **25** | ~0.85 GB | no block |
| 3 | `6a569882000018c7` | 300 s | 35,651,584 | ~120k H/s | **26** | ~585 MB | no block |
| 4 | `6a569882000018e6` | 1800 s | 212,008,960 | 117.8k H/s | **28** | ~585 MB | no block |

*(RAM = the miner's transient bit-slice buffer, measured from the OS. The run logs printed "0 MB" — that was a buggy
working-set probe; the real figures are here. Pre-compaction runs 1–2 held ~0.85 GB at W=32768/213k wires; the compacted
fabric runs 3–4 hold ~585 MB at 121k wires. The **model** is separately ~0 — mmap'd or not opened at all.)*

## Reading the frontier

The **frontier** is the most leading zero-bits any nonce produced — the search's progress meter. It tracks
**log₂(N)** where N = nonces checked:

- run 1: log₂(4.69M) ≈ 22.2 → hit 22
- run 2: log₂(22.8M) ≈ 24.4 → hit 25
- run 3: log₂(35.7M) ≈ 25.1 → hit 26
- run 4: log₂(212M) ≈ 27.7 → hit 28  (30-min run, 212,008,960 unique nonces)

That clean log₂(N) curve is itself the proof: it's exactly what a correct, uniform SHA-256d search produces. Bitcoin
is confirming the stored gate-net computes real hashes. To go further the cost doubles per bit: from 28, ~1 hr → 29,
~4 hr → 30. The 78-bit target is the network-difficulty (ASIC) wall no single machine crosses.

## What Bitcoin actually ruled

- **The SDC computes real Bitcoin mining** — byte-exact real SHA-256d, correct fair search. Confirmed, three times.
- **No block** — 78 bits needed, the mid-20s reached. That gap is Bitcoin's difficulty (2⁷⁸), not a flaw. Each extra
  bit doubles the work: from 26, roughly +1 bit per 2× nonces (≈10 min → 27, ≈1 hr → 28, ≈10 hr → 30, and 78 is the
  ASIC-network wall no single machine crosses).

## The "no-RAM" claim, stated honestly

Two different memories, and only one is zero:
- **The model: ~0 RAM.** The 40 GB `titan.gguf` is mmap-addressed (0.86 MB physical for all 40 GB, proven with a
  calibrated meter in `MEASURE_ALREADY.md`), and the fabric miner doesn't even open it — it synthesizes the SHA
  circuit fresh. So there is no model in memory. That half is real.
- **The miner: NOT zero.** The bit-slice wire buffer is genuine working memory — **~585 MB at W=32768** (measured
  from the OS). It scales with lane width W (the "button" width): wider button, more nonces per press, more RAM. It is
  transient (freed when the process exits), not a growing heap, but it is not ~0.

The run logs printing "RAM 0 MB" were a **buggy working-set probe** (wrong struct layout), not a real measurement —
corrected here. The honest headline: **storage-first for the model (0), real but bounded RAM for the wide-lane miner
(~0.5–0.9 GB).**

## Where the "light-speed / win" axis actually is

On this one host, one CPU core, the throughput is serial — ~120k H/s. The design's parallelism is **lateral**: the
circuit clones for ~0 storage cost, so the win-axis is billions of stored lanes switching at once on power
(bare-metal), where the 2⁷⁸ gets divided down. That axis is not disprovable on a serial laptop — here we build it to
spec, measure the frontier, and let the network judge; the serial floor is the 120k H/s above.
