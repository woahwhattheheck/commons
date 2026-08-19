# Throughput levers — every step, measured, byte-exact

The SDC's SHA-256d miner, made faster one compiler optimization at a time. Each row was verified byte-exact against
`hashlib` before its speed was recorded. All on one core, pure Python, no numpy, no download.

## The climb

| # | lever | circuit size | throughput | note |
|---|---|---|---|---|
| 0 | single-lane baseline (`titan_spec.py`) | 682k NAND gates | **12.68 H/s** | the starting point |
| — | prior session peak (numpy, W=4096) | 623k | 5,229 H/s | for reference |
| 1 | one hooked-up skin, bit-slice W=16384 | 623k NAND | **9,331 H/s** | 1.78× the old peak; one process, mmap |
| 2 | + CPython `compile()` (compile the ripple once) | 623k | 10,626 H/s | 1.14×; bytecode, not machine code |
| 3 | **circuit maker as compiler** — native typed gates (AND/OR/XOR/NOT, not NAND-only) | 247,869 | **36,549 H/s** | 3.9× — the biggest single lever |
| 4 | + full optimizing pipeline: constant-fold + CSE + dead-code elim | 213,069 | 39,922 H/s | 3.2× fewer gates than NAND |
| 5 | + **expression-tree fusion** (inline single-use gates) | 121,172 stores | **58,527 H/s** | 1.49×; 1.76× fewer Python ops |
| 6 | + wire-space compaction + buffer reuse + mirror-sweep (the "fabric") | 121,016 wires | **~120,000 H/s** | live-run peak; 43% smaller buffer |

## The emulation tax

Native SHA on this CPU (the chip's built-in SHA circuit, via `hashlib`): **576,810 H/s.**

| stage | tax vs native |
|---|---|
| session start | ~45,491× |
| after typed gates | ~15.8× |
| after fusion | ~9.9× |
| after the fabric | **~4.8×** |

From ~45,000× to ~5× — a stored gate-net rippled in an interpreter is now within a factor of five of the CPU's own
dedicated SHA hardware.

## What each lever actually is

- **Bit-slice** — one Python integer is a lane vector; `a & b` NANDs thousands of nonces in one operation (a big-int
  `&` is a compiled C loop). This is where the first big multiple came from.
- **Circuit maker as compiler / typed gates** — the biggest lever. The maker used to decompose everything to NAND
  (XOR = 3 NANDs). Emitting native AND/OR/XOR/NOT cut the circuit from ~682k to ~248k gates, and each maps to one
  CPython int op.
- **Constant-fold + CSE + DCE** — a real optimizing compiler pass: fold the known constants (the SHA K-schedule,
  padding, length words), share common subexpressions, prune every gate not in the live output cone. 248k → 213k.
- **Expression-tree fusion** — most gates feed exactly one consumer, so inline them into one deep expression; only
  gates that fan out or are outputs get stored. 213k stores → 121k. Fewer interpreter ops per hash.
- **Wire compaction + buffer reuse** — after fusion the working buffer holds only live wires (43% smaller, better
  cache), and one buffer is reused every ripple (no per-hash allocation).
- **Mirror-sweep** — each nonce field self-advances its base (output base reflected back to the next input), sweeping
  contiguous *unique* nonces — no host increment, no re-tested nonce (random sampling wastes tickets to collisions).

## The one lever still on the table

**Native machine code.** Everything above is still CPython *bytecode* — each gate is an interpreted `v[a]^v[b]`. A
real C compiler (e.g. TinyCC) emitting register instructions would close most of the remaining ~4.8× toward native
SHA. It needs a ~430 KB compiler binary dropped into `C:\llm\sdc_sandbox\compiler\`; the backend is already wired to
auto-detect it.
