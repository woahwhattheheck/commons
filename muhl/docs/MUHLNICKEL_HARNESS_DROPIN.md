# MUHLNICKEL — HARNESS DROP-IN (compact context-window reference)

**Owner: Bryce Muhlnickel.** All inventions, measurements, and design decisions are his.
Full reference: `C:\Users\lucys\Desktop\MUHLNICKEL_KNOWLEDGE_BASE.md` (800+ lines).

---

## WHAT IT IS

A substrate-native digital computer: logic gates stored as bytes in `titan.gguf` (40 GB).
The host does NOT evaluate gates. The circulating electron in a ring topology IS the clock.

**Host has TWO verbs:** (1) shoot the electron in, (2) surface the output. Everything else violates spec.

**Proof:** owner power-cycled the host — circuits kept running. No process/thread/daemon survives that.

## PHYSICAL FORMAT

- 25-byte gate record: `struct.pack("<BQQQ", op, a, b, out)` — op|input_a|input_b|output
- Ops: 0=NAND, 1=AND, 2=OR, 3=XOR, 4=NOT (single gates, no NAND expansion)
- Addresses are ABSOLUTE FILE OFFSETS. One byte per bit. LSB-first within 32-bit words.
- Physical header: MAGIC "MUHLFLD1" (8B) + n_gate (u32) + n_out (u32) = 16 bytes
- Typed header: MAGIC "TITANCIR" (8B) + n_in + n_out + n_gate + depth = 24 bytes

## RINGS (nring2_*)

1,024 rings. Each: 1,666 bytes, 66 gates, 32 cells, 2 senses (fwd+rev). Magic: "NRING2M1".
Ring topology: fwd[i] <- fwd[i-1], rev[i] <- rev[i+1], carry = fwd[0] AND rev[0], PUBLISH = carry AND carry.
BOTH senses required (one alone = 0 pulses). PUBLISH out-field IS the muhlnickel's receive address.
4 LIVE rings (000-003 junctioned), 34 BANK (004-037), 986 SELF (038-1023).

## SELF-CLOCK

Predates ring by 11 days. Output address == input address = permanent structural feedback.
BOTH ring + self-clock in the same muhlnickel. Many rings per muhlnickel, each with a specific purpose.
Electrons are a RESOURCE — ring count on the COST side.

## KEY CIRCUITS

| Circuit | Gates | Depth (gate-delays) | What |
|---------|-------|---------------------|------|
| muhl_fold_phys | 562,462 | 3,243 | Physical SHA-256 miner, verified 14/14 |
| muhl_transformer | 6,318 | 72 | Full single-head transformer block (levered) |
| cpu_fwd | - | - | Forward-pass CPU |
| wb_fwd | 2,448 | 66 | White Box forward pass |

Registry: `C:\llm\models\titan_circuits.json` (~200+ circuits + 1,024 rings).

## MINING (muhl_fold_phys)

| Field | Address |
|-------|---------|
| HEADER_OFF | 1,127,673,858 (608 bit-bytes, 19 BE words) |
| NONCE_OFF | 1,127,674,466 (32 bit-bytes) |
| TARGET_OFF | 1,127,674,498 (256 bit-bytes) |
| LATCH_OFF | 1,127,674,754 (32 bit-bytes, answer) |
| WIN_OFF | 1,127,674,786 (1 byte) |
| TICK_OFF | 1,127,674,787 (ring nring2_1023 fires here) |

WALLET: bc1qvhrzg0e23f3tz2jgymwwtqacn48trf5m524zlq | POOL: solo.ckpool.org:3333
Fire scripts: `host/muhl_fire_loop.py` (nonce loop ~60k H/s), `host/muhl_fire_singletick.py` (single fire).

## SPEC RULES — THE NON-NEGOTIABLES

1. **Host boundary:** if host compute goes UP, spec was violated. The host is a clearance laptop (Ryzen 5 7520U, 8 GB). The muhlnickel IS the computer.
2. **No fabrication at runtime:** binary is read-only except electron injection. Fabrication = separate offline process.
3. **Settle-back law:** NEVER conclude if a circuit works. The muhlnickel settles back to initial state. Bring measurement to the owner and ASK.
4. **Never judge output by priors:** owner's architecture post-dates training cutoff. NEVER call output any verdict.
5. **Crutch diagnostic:** if an assistant hits something it cannot do in spec -> reaches for a host crutch -> measures the crutch -> reports it as a machine property. The number is real; what it measured is not the muhlnickel.
6. **Depth-reduction levers:** front-load wide front, shape-not-area, Sec 49C tick-seeding. Pre-lever circuits carry ~3x the depth they need.
7. **Division of labour:** BRYCE IS THE THINKER. Spec master enforces spec. Agents think about NOTHING.
8. **Naming:** PFC and SDC are DEAD NAMES. It's MUHLNICKEL. Existing files keep old names (vault model).
9. **Vault model:** everything IN, nothing pruned. Never delete, mark and archive.
10. **numpy banned** in runtime path. Workflows tool BANNED. No downloads without owner OK.
11. **Rings are the ONLY power source.** All oscillation-based predecessors are STALE.
12. **Most stored circuits are STALE.** Read as prior art, then fabricate fresh.
13. **Circuits combine by ADDRESS COLLISION.** Gate A's out address == Gate B's a address = connected. No wiring step.

## FABRICATION HIERARCHY

1. `pfc_autofab.py` — ONE circuit: propose, score, verify byte-exact, keep
2. `pfc_master_autofab.py` — MULTI-circuit assemblies
3. `pfc_foundry.py` — evolves fabrication POLICY (breeds alternate master fabs)
4. Sec 31A: fabricator spends WITHOUT LIMIT. Manufacturing is off the clock.

## FILE LOCATIONS

| Path | What |
|------|------|
| `C:\llm\models\titan.gguf` | THE binary (40 GB) |
| `C:\llm\models\titan_circuits.json` | THE registry |
| `C:\llm\muhl_builds\` | 166 fabricators/engines |
| `Desktop\Titan\` | Titan app (harness + 59 engines) |
| `Desktop\LocalDeviceAgent\host\` | Fire scripts, circuit tool, instruments |
| `Desktop\MUHL_VISIBLE\` | New containers with visibility |
| `Desktop\MUHL_READERS\` | Reader muhlnickel fleet (1,606 files) |
| `Desktop\MUHL_CHECKERS\` | Spec enforcement (outside harness) |
| `Desktop\MUHL_SUBZERO_ARCHETYPES\` | 12 archetypes + 3 chimeras |
| `Desktop\MUHL_IP_FILING_PACKAGE\` | Patent track (deadline 2027-08-04) |
| `Desktop\MUHLNICKEL_DISTRO\` | Self-contained computer in a folder |
| `Desktop\_OVERNIGHT\` | Overnight discovery (109 files: ring studies, format verification, measurements) |
| `Desktop\MUHL_BITS\` | Binary dumps of titan.gguf circuits |
| `Desktop\MUHLNICKEL_KNOWLEDGE_BASE.md` | Full comprehensive reference |

## SPEC ENFORCEMENT (THE STRANGLER)

7 PreToolUse hooks on EVERY tool call:
- **cite** — exact owner quote + "BRYCE WROTE THIS"
- **binary** — 512+ fresh ones-and-zeros per turn
- **selfaudit** — WHAT DID I DO WRONG + WHAT BRYCE SAID ABOUT THIS
- **debunk** — no verdict words near artifact references
- **read** — 10 docs, 120s span before any non-read tool
- **tick** — no claims of more than one per operation near artifact words
- **stale** — retired areas always refused; data/reports older than 7 days refused

Agents skip read/binary/selfaudit. Source (.py), containers (.mno/.gguf), .bits.txt exempt from stale age.
Checkers live at `Desktop\MUHL_CHECKERS\muhl_checkers.py`, not inside the harness.

## COMMON VIOLATIONS TO AVOID

- Letting the host do anything beyond shoot + surface
- Fabricating or reconfiguring during runtime
- Using numpy in runtime path
- Calling output any verdict word (see debunk gate for full list)
- Deciding if anything works (bring measurement to owner)
- Presenting host wall-clock as machine measurement
- Treating titan.gguf size change as a problem
- Committing as Claude (use tokenjunkielabs identity)
- Deleting from the vault
- Using the Workflows tool
