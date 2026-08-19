# AGENT GROUNDING — CONTAINER IS THE COMPUTER

**Inventor:** Bryce Muhlnickel. **Name:** Muhlnickel.  
**Law for EVERY agent. Commands, not essays. Do not add to spec.**

---

The computer is the **container file**: `titan.gguf` **AND/OR** `*.mno`.

Gates = **25-byte records IN THAT FILE.** Not Python. Not HTML. Not `titan_circuits.json` (that is a **MAP**). Not a "pfc script."

`titan.gguf` **IS** circuitry. A `.mno` **is circuitry if its BINARY holds 25-byte gates.** Filename is not proof. Read the ones and zeros.

Desktop copies of fab `.py` are **not** the circuits. `host/pfc_master_autofab.py` is a host process — not the fabricator-as-gates. Forbidden at runtime.

---

## Do

1. Treat GGUF and `.mno` as the same class of machine: gates in a file.
2. Use the JSON map only to get an **offset**. Then **read the bytes**.
3. Confirm a `.mno` by magic **or** by packed 25-byte records (AUTOFAB0 opens on a gate — no text magic).
4. Before any write: BITS law. `docs/AGENT_GROUNDING_BITS.md`.
5. Live file changing is compute. `docs/AGENT_GROUNDING_LIVE.md`.

## Do not

- Call a Python file a pfc / a circuit / autofab.
- Call the JSON registry the computer.
- Call maze/HTML the circuitry.
- Write titan to "put circuits in" — they are already in the binary.
- Recursive-search the Desktop for computers. Open the named container. Read its bits.

---

## Measured 2026-08-15 (read-only)

In-spec autofab **as gates**:

- `titan.gguf` `muhl_foundry_resident` @ 4383248721 **TITANCIR** (1296 gates) + `__phys` @ 93711094656 **MUHLPHY2**
- `C:\Users\lucys\Desktop\MUHL_VISIBLE\AUTOFAB0.mno` — 4117 × 25 B, rem 0, byte 0 is a gate

Product of host autofab (not the fabricator): `muhl_autofab_dot32` / `__phys` in titan.

Other listed `.mno` files are computers (gates in binary) and **not** autofab: DISTRO, LOOM, ROOKERY0, probe.

Full dump: `C:\Users\lucys\Desktop\MUHL_GO\CIRCUITS_IN_CONTAINER.md`  
Hits: `C:\Users\lucys\Desktop\MUHL_GO\INSPEC_AUTOFAB.md`
