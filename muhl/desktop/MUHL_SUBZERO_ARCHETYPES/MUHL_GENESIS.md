# `muhl_genesis` — deep dive

**Files (2 copies, byte-identical, sha256 `ac49b63c079b71dc16f93bdc54ba2f6152da2f4d48e577f3f4df435eed10eecd`, 4,557 B):**
- `C:/llm/muhl_builds/muhl_genesis.py`
- `C:/Users/lucys/OneDrive/Desktop/Titan/engines/muhl_genesis.py`

**Artifact:** `C:/llm/muhl_builds/TITAN_GENESIS.json` (3,568 B) — exists in `muhl_builds` **only**, not mirrored to `Titan/engines`.

**NOT RUN by this agent.** Everything below is from reading source + parsing the artifact + hashing files it names.

---

## 1. What it computes

1. `glob` `C:/llm/muhl_builds/*.py`, sorted by filename.
2. SHA-256 each file **with `hashlib`** (host library — explicitly stated in its own docstring: *"Leaf hashing (arbitrary-length source files) uses hashlib"*).
3. Merkle root over the sorted 32-byte leaves, Bitcoin-style duplicate-last on an odd level.
4. Recompute the **internal nodes** a second time through `muhl_merkle.build_node()`, compare to the hashlib root, record the boolean.
5. Write `TITAN_GENESIS.json` = `{engine: sha256hex}` + `merkle_root` + `count` + `genesis_seal` + `root_verified_through_gates`.
6. `genesis_seal = sha256(merkle_hex + str(count) + "".join(sorted(engine_names)))`.

It is a **content-addressed manifest generator over host files**. It hashes *source text*, not substrate state.

## 2. Which fabricated SHA-256 structure does it address?

**None. It addresses no resident structure.** This is the central finding, and it contradicts the natural reading of the docstring.

`muhl_genesis` calls `from muhl_merkle import build_node`. `muhl_merkle.build_node()` (source read in full, `C:/llm/muhl_builds/muhl_merkle.py:69-95`):

```python
g = CC.CircuitCompiler(64*8)        # a fresh, empty in-memory compiler
...                                  # SHA-256 of two 64-byte blocks emitted as gates
gates, out2 = g.dce(outs)
run = g.compile_ripple(gates, 2 + g.n_in + len(gates))
```

`CC` is `sdc_cc` from `C:/llm/sdc_sandbox/sdc_cc.py`. `CircuitCompiler.__init__(n_in)` starts empty; `compile_ripple` returns a **host-Python evaluator closure**. So on every invocation the netlist is **synthesised fresh in host memory and evaluated by a host ripple**. Confirmed absences:

| Candidate resident structure | Result |
|---|---|
| `miner_physical` (339,136 physical-address gates) | present in the registry, **never referenced** by `muhl_genesis` or `muhl_merkle` |
| `muhl_rx_*` family (5 keys, carry per-circuit `sha256`) | **never referenced** |
| `titan.gguf` | **never opened** — neither file contains any `open()` of it |
| `titan_circuits.json` | **never read** — neither file mentions it |

`muhl_merkle.py` has **no registry entry** (`json.load` + recursive key-walk of `titan_circuits.json`: no key named `muhl_merkle`, no `name` field with that value) and **no genome journal** in `C:/llm/models/`.

**Therefore:** *"recomputed THROUGH THE FABRICATED SHA-256 GATES … signed by the substrate itself"* means **a host-side gate netlist compiled at call time and rippled in host Python**, not an addressed read of a stored structure. The gate netlist is real and its byte-exactness vs `hashlib` is a real check; the word "substrate" in that sentence is not load-bearing on any resident state.

**Classification: INSTRUMENT (host tool). It does not reside in the substrate and does not address a resident structure.**
Note it also re-fabricates at run time, which is why it is an instrument and not a fabricator — the netlist it builds is never stored.

## 3. What `TITAN_GENESIS.json` actually contains

| Field | Value |
|---|---|
| `titan` | `"genesis"` |
| `generated` | `2026-07-29T10:55:03.030442+00:00` |
| `builds_dir` | `C:/llm/muhl_builds` |
| `hash_algo` | `sha256` |
| `merkle_scheme` | `sha256(left\|\|right), duplicate-last on odd level` |
| `count` | **33** |
| `engines` | dict of **33** `filename -> sha256hex` |
| `merkle_root` | `5e5a4ff0e672c9417672aea1de06ae3169677e8accbadba804d049ca945a7909` |
| `root_verified_through_gates` | `true` |
| `genesis_seal` | `dce989f30aaae06d8468bb464d4304899e94fc6cb2072ae3f6478591810b18d8` |

**Engines covered: 33 — EXACTLY COUNTED** (`len(manifest["engines"])` == `manifest["count"]` == 33; both agree). 32 `muhl_*.py` + `titan.py`.

### Hashes are present and ARE verifiable against files on disk — I verified them

| Check | Result |
|---|---|
| committed files still present on disk | **33 / 33** |
| committed files still byte-identical | **32 / 33** |
| changed since genesis | **1** — `titan.py`: recorded `c78e0313ec0b3207…`, now `4bb266432fdcb591…` |
| Merkle root recomputed with `hashlib` from the 33 recorded leaves | `5e5a4ff0…a7909` — **equals the stored `merkle_root`** |
| `genesis_seal` recomputed from the stored fields | `dce989f3…b18d8` — **equals the stored seal** |

So the artifact is **internally consistent and self-verifying**, and 32 of its 33 commitments still hold. The tamper-evidence claim works exactly as advertised: `titan.py` was edited after 2026-07-29 and the manifest detects it.

`root_verified_through_gates: true` is a **self-report by the run that wrote the file** (it records the outcome of its own comparison). I did not re-run it, so that boolean is HISTORICAL CLAIM, not independently verified here. The *hashlib* root and the seal, by contrast, I recomputed myself — those are EXACTLY COUNTED.

### The manifest is STALE

`glob("*.py")` over `C:/llm/muhl_builds` today returns **73** files. The manifest holds **33**. **40 `.py` files present today are not committed** by this genesis block — including every fabricator that actually writes to `titan.gguf` (`muhl_fab_fold_latch`, `muhl_fab_nonce_list`, `muhl_fab_nonce_map`, `muhl_lookup_table`), `muhl_life`, `muhl_selfevolve`, `muhl_selfimprove`, `muhl_chaos`, and the ring/bitcoin work. Re-running it would produce a different root over 73 leaves.

`muhl_genesis.py` hashes **itself** into its own manifest (it is one of the 33). Its recorded hash still matches disk, so the tool's own bytes are unchanged since the run.

## 4. Scope caveat

`builds_dir` is hard-coded to `C:/llm/muhl_builds`. The genesis block commits to **nothing** in `C:/Users/lucys/OneDrive/Desktop/Titan/engines/`, and nothing anywhere else. It is not a birth certificate over "every engine" in the system — it is a birth certificate over one directory's `*.py` glob, as of one moment on 2026-07-29.
