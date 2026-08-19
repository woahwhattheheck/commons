# Existing 12-File Working Tree Diff — WHAT and WHY

**Repo:** `C:\Users\lucys\Desktop\LocalDeviceAgent`  
**Generated:** 2026-08-14  
**Source:** `git diff` on uncommitted changes only. Read-only audit.

Git emits LF→CRLF warnings on all 12 paths; every hunk below is **real logic/content**, not whitespace-only noise.

---

## Priority files (runtime spec)

### `host/pfc_master_autofab.py` — WHAT + WHY

**What:** Adds a new autofab need called `read_container`: function `_need_read_container()` imports `mafab_reader.search` and registers `NEEDS["read_container"]` at the bottom of the module (same additive pattern as `miner_lane` / `midstate`).

**Why:** Owner directive (2026-08-07): build a second Muhlnickel reader so **the pfc computes reads, not the host assistant**. Wired through master autofab so the existing DECOMPOSE × IMPLEMENT × ORDER × WIRE search covers it without touching dot32 or miner_lane code paths. Comment notes its scorer is SILLY-based per owner ruling that retired compute/tick scoring for this need.

**Spec impact:** HIGH — extends what autofab can fabricate at runtime prep.

---

### `host/titan_circuit.py` — WHAT + WHY

**What:** (1) `store()` no longer writes blob bytes with a bare `open(TITAN).write()` — it calls `_seq_write(name, off, blob)` so plain stores get the same per-name genome journal as loop stores. (2) Adds `revert(name)` as a one-line alias to `revert_loop(name)`.

**Why:** Reversible fabrication discipline — every `store()` should be byte-exact revertible via the SEQ genome, not just `store_loop()`. `revert()` gives a symmetric API for undoing a plain store without callers knowing about loop internals.

**Spec impact:** HIGH — changes how circuits land in titan and how they can be rolled back. Does not change gate logic; changes alloc/write/journal path.

---

### `host/pfc_llama_decode.py` — WHAT + WHY

**What:** `pfc_argmax_vocab()` now tries `pfc_argmax_shallow` first (depth 174), then falls back to `pfc_argmax` (depth 2710). **Removes the host-Python argmax fallback** — if neither circuit exists, raises `RuntimeError("the host will NOT pick the token")`. Return value becomes `(token_id, circuit_name)` instead of `(token_id, bool)`. Log strings updated to print the circuit name used.

**Why:** Align with PfcGlue (15.6× shallower argmax tree = faster token pick). Enforce spec rule #1: **host computes zero inference** — token selection must come from a fabricated circuit, not a Python `max()`.

**Spec impact:** HIGH — token generation path; will hard-fail if shallow argmax not fabricated.

---

### `host/pfc_speed.py` — WHAT + WHY

**What:** Adds `load_titancir()` — a loader for TITANCIR containers (parallel `ga`/`gb` gate arrays, not interleaved PFCTYPED `<Bii>` layout). Registers new CLI target `cpu_fwd` that loads the forward-pass CPU circuit and prints its gate count / critical-path depth.

**Why:** Owner-approved 2026-08-07. `cpu_fwd` depth (registry: 202) was already in titan but **no loader existed**, so inference-speed discussions only had host wall-clock numbers — not pfc depth beside them. This is a read-only instrument fix, not a compute change.

**Spec impact:** MEDIUM — measurement/legibility only; exposes forward-pass depth for honest speed accounting.

---

## All 12 files

### `host/sdc_whitebox_train.py` — WHAT + WHY

**What:** Replaces `TC.ripple(cir, inbits)` with physical mmap I/O on `muhl_wb_physical`: host writes input bits to wire byte addresses, reads output bits from output wire addresses. Adds `_load_phys()`, skips `build_forward()` if `wb_fwd` already in registry, adds diagnostic prints when verify fails (ring 280 still drives `wb_fwd`, not physical circuit). UI `--ui` path uses same physical loader.

**Why:** Owner: "the electron itself not the host" — stop host gate evaluation (ripple) during training runs; let the ring in storage drive gates while host only pokes inputs and reads outputs. Matches compute-via-address containment model.

**Real logic:** YES — execution model change.

---

### `host/pfc_preflight.py` — WHAT + WHY

**What:** Adds all `muhl_*` instrument filenames to the `INSTRUMENTS` whitelist (parallel to existing `pfc_*` set). Adds `is_model` regex heuristic (matvec, rmsnorm, n_embd, BPE, etc.) and returns `is_mine or is_model`.

**Why:** New muhl-branded instrument copies should not be flagged as fab/mine violations. Model-decode scripts (llama decode path) should classify as mine-path code for preflight rules, not fab.

**Real logic:** YES — static classifier only, no runtime compute change.

---

### `host/sdc_weights.json` — WHAT + WHY

**What:** Persisted training weights `W` changed from `[7, 2, 4, 5, 2, 1]` to `[1, 1, 1, 1, 1, 1]`.

**Why:** Reset whitebox training to a neutral starting point (likely after physical-path switch or a fresh training run). Not code — state file only.

**Real logic:** YES — affects training starting point, not gate netlist.

---

### `host/pfc_arcade.py` — WHAT + WHY

**What:** Wraps `sys.stdout.reconfigure(encoding="utf-8")` in try/except.

**Why:** Some Windows launch contexts (no UTF-8 stdout) crash on reconfigure; arcade should still open.

**Real logic:** Minor robustness. No compute change.

---

### `host/pfc_desktop.py` — WHAT + WHY

**What:** Same stdout reconfigure try/except as arcade.

**Why:** Same — desktop harness should launch even when stdout reconfigure fails.

**Real logic:** Minor robustness. No compute change.

---

### `host/run_battery.py` — WHAT + WHY

**What:** Adds `encoding="utf-8", errors="replace"` to `subprocess.run()` capture.

**Why:** Battery subprocesses emitting non-UTF-8 bytes were crashing the harness on decode; replace lets the proof battery finish and match patterns.

**Real logic:** YES — test harness only.

---

### `host/sdc_chat_ui.py` — WHAT + WHY

**What:** HTTP port `7902` → `7906` (constant + docstring).

**Why:** Port collision avoidance — something else likely bound 7902 on this machine; checker feed stays on 7903.

**Real logic:** YES — config only, no compute change.

---

### `host/titan_lab.py` — WHAT + WHY

**What:** HTTP port `7864` → `7866` (constant + docstring).

**Why:** Same port-collision pattern as chat UI.

**Real logic:** YES — config only.

---

## Quick matrix

| File | Real logic? | Runtime spec? |
|------|-------------|---------------|
| pfc_master_autofab.py | Yes | **Autofab — read_container** |
| titan_circuit.py | Yes | **Store/journal/revert path** |
| pfc_llama_decode.py | Yes | **Token pick — no host fallback** |
| pfc_speed.py | Yes | Measurement — cpu_fwd depth |
| sdc_whitebox_train.py | Yes | **Physical mmap vs ripple** |
| pfc_preflight.py | Yes | Classifier only |
| sdc_weights.json | State | Training reset |
| pfc_arcade.py | Minor | None |
| pfc_desktop.py | Minor | None |
| run_battery.py | Harness | None |
| sdc_chat_ui.py | Config | None |
| titan_lab.py | Config | None |
