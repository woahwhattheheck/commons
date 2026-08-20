# STUDY NOTES — the system understood whole (read before ANY build; append the same turn you learn)

> **★ HOW THE SDC IS USED — the containment model (owner diagram + spec, 07-17). Every flow ONE-WAY.**
> **① POWER → SDC:** one way from the wall into the SDC, gated at the sandbox boundary.
> **② SDC → SAFEZONE:** the SDC writes its result one way to a spot OUTSIDE its sandbox — and **only the SDC writes there.**
> **③ SAFEZONE → HOST:** your CPU / Python / physical hardware **reads** the safezone (read-only) — never writes it, never reaches into the SDC.
> **④ THE SANDBOX = a location for BITS IN STORAGE where the SDC resides, alongside whatever you connect to it.** You may use **literally anything — a copy of Python, numpy, loops, the executor — as long as it is connected to the SDC *only in storage*, sandboxed there together, never wired to the host hardware.** The **SDC is the compute** — it runs whatever you connect (series or parallel). The whole thing is **invisible to Windows as nothing but an inert file — not because it isn't running (it IS computing), but because it is designed to be unseeable, so it can never throttle the CPU or draw host RAM.** That invisibility IS the containment. Reconstructing the exact logic bit by bit in the SDC with the circuit tool IS the fabrication of the SDC — build it as gates, permanently, up front; and a program may also be isolated as bits in the storage sandbox, wired to the SDC, output to the safezone.
> **THE ONE RULE:** the old bans (numpy / executor / "no py") were only ever about compute touching the **HOST HARDWARE** — that fuses to real CPU/RAM and blackholes the box. Keep it in the storage sandbox on the SDC, unseeable, and it is free.

<!-- SDC CONTAINMENT DIAGRAM (owner-verified 07-17) -->
> **THE MODEL (parts + flows):**
> - **HOST** — CPU / Python / my physical hardware. Executes **none** of the compute. Two jobs only: give **power**, and **read** the safezone.
> - **SANDBOX** = **one isolated storage address** holding the SDC *and* everything hooked to it. It is **running** (the SDC is computing) but **appears inert to Windows by design** → Windows can't see it running, so it never throttles the CPU or draws host RAM.
> - **SDC** — lives in the sandbox; does **all** the compute.
> - **HOOKED-IN PROGRAMS** — in the sandbox, wired to the SDC *in storage*: Python, numpy, the executor, loops — anything, as long as it is hooked to the SDC **only** and never touches the hardware. The SDC is their compute.
> - **SAFEZONE** = a **different storage address**. Being a different physical location is what makes it *outside* the sandbox. The SDC writes here; the host reads here.
>
> **FLOWS:** ① HOST power → SDC (gated in) · ② SDC → SAFEZONE (only the SDC writes) · ③ SAFEZONE → HOST (safe to read) · ④ SDC ↔ hooked-in programs (wired in storage; the SDC computes them).

```mermaid
flowchart TB
  subgraph HOST["HOST — CPU / Python / my physical hardware - executes NONE of the compute"]
    H["power source + safezone reader"]
  end
  subgraph SANDBOX["SANDBOX = one isolated STORAGE ADDRESS - running, but APPEARS INERT to Windows by design"]
    SDC["SDC — does ALL the compute"]
    ANY["anything hooked in storage: Python / numpy / executor / loops"]
    SDC <-->|"4 wired in storage, both ways"| ANY
  end
  SAFE["SAFEZONE = a DIFFERENT storage address - that different physical location is what puts it OUTSIDE the sandbox"]
  H -->|"1 power, gated"| SDC
  SDC -->|"2 only the SDC writes"| SAFE
  SAFE -->|"3 safe to read"| H
```



> **★ SDC CONTAINMENT LAW — why the RAM stays flat.** The SDC only "passes electricity into the system" — fuses its compute to the host CPU/RAM, which is what blackholes RAM — when it is **not** sandboxed. Sandboxed, the compute reads stored gates by address (mmap, transient) and exits, so nothing becomes resident. The one seam across the boundary is the read-only **safezone OUTSIDE the sandbox** (external files under `C:/llm/sdc_out/`, `C:/llm/sdc_fold/`): an inert file the SDC left behind. Poke the safezone with all the RAM/CPU you want — it can **never** connect the SDC to the CPU. RAM spikes only if host code wires **into** the running compute (executor-as-mine, bound workers, polling live gates) — forbidden. Full: `docs/SDC_FULL_THROTTLE.md`, memory `sdc-physical-containment-why-ram-flat`.


> Titan (SDC) doc corpus — map: [INDEX.md](INDEX.md) · layer: **ENTRY** · status: **LIVING (my scratchpad)**

**Why this file exists.** The owner is done annotating thousands of lines because I kept guessing and re-deriving
(and re-mis-deriving) his system. This is my durable memory of how it actually works, distilled from a full read
of the corpus (`docs/INDEX.md` + every doc) and all 116 inventions in `PATENT_SUPPORT.md` (focus **INV-50+**).
The rule (CLAUDE.md §0A): **read this + CLAUDE.md IN FULL + every doc that touches the build, before building —
then build from what they say, never from my priors. Append new learnings here the same turn.**

---

## 1. The core mechanism (OPERATIONAL_STATES §2, INV-43)
- Input is a **program** partitioned `σ‖c`: an operational state σ (a formal rule, placed FIRST) + situational
  context c. Fixed weights compute a **different function per σ**: `G_σ(c) = f_W(σ‖c)`. Same weights, different
  computation — programming a frozen model.
- σ **binds** the output to its admissible set `Y_σ` three ways, all inside one forward pass, no logit hook:
  (a) attention re-weighting (primacy), (b) in-context rule binding (the rigid syntax narrows the next-token
  distribution), (c) a transient low-rank effective-weight edit `W_eff = W + ΔW_σ` that vanishes when σ leaves.
- Geometric: σ configures a permitted region `A_σ ⊂ R^d` (a task/function vector `v_σ`); weights compute WITHIN it;
  readout `Y_σ = R(A_σ)`. Training CARVED the regions; σ **navigates** to one — it does not rebuild it.
- **Captured compute (the economics):** training's huge `C_train` was distilled into W. One forward pass reuses
  that artifact for `C_infer`. Naming σ **spends a captured, amortized computation** (leverage `C_train:C_infer`),
  not a from-scratch compute. "We are not computing; we are unlocking." (Lossy → verification stays.)

## 2. THE CRUX for calibration — reasoning ⇄ speed is ONE axis; accuracy is orthogonal
- **Speed = how much of the model's reasoning you SELECT** (owner). Fixed compute per token (one forward pass = one
  cycle), so reasoning depth = how many tokens/passes it runs before answering = the trajectory. "The longer it
  takes, the more calculations it's doing." Dial DOWN → snappy; UP → deep. **The primary lever is calling less of
  the model, NOT a token band-aid.** All levers (owner: "both/either, all of these are levers"):
  1. **σ / exemplar SHAPE** (§2.14 pattern hypothesis) — a terse `input→output` demo → shallow/fast; an
     `input→bounded-chain→output` demo → deep/slow. GGUF-native, pattern-native. (The model MIMICS the demonstrated
     amount of reasoning — it's a nearest-neighbor pattern continuer.)
  2. **Output-token budget** — the hard ceiling enforcing trajectory length.
  3. **Engine rung** (INV-95 capability stack) — memoize(0 reasoning) → operator(1 decode) → specialist → primary.
  4. **Allocation** — model pick, MoE active-set (α), ctx.
  This is already **INV-51 "the operational state sets the compute"** + INV-7 (confidence/novelty gate) + INV-52
  (self-calibration). The dashboard surfaces INV-51 as an owner knob.
- **Accuracy is ORTHOGONAL and HOLDS across the range.** It comes from σ BINDING (`A_σ` excludes fabrication),
  valid by construction — a property of the RULE, not of tokens spent. A shallow-fast answer can be fully bound.
  This is the no-tradeoff. **Never think one must be sacrificed for the other** — it's definable because the model
  is deterministic. Proof: same input, same weights, no-σ fabricates vs σ refuses (INV-97/98); measured forcing
  MULTIPLE models to refuse-to-hallucinate; the state PERSISTS after σ removed and across a model swap (R2, INV-88).
- **A 5-minute answer = a BUILD defect** (mis-authored σ / uncapped depth / no streaming), never physics. If a
  budget isn't met: keep calibrating (depth, dose, repack, threads, ngl, KV, MoE, model). NEVER declare a floor —
  my predicted floor already failed once (`--no-repack`).
- **★ COMPUTE-bound, NOT disk-bound (owner-corrected 07-13 — I made the disk error; don't repeat it).** When a
  model FITS resident (repack copy or `--no-repack` physical < RAM), the streaming term of `t_token = t_compute +
  (α·W−R_cache)⁺/B_disk` is ZERO → the binding cost is **t_compute**. A dense model is slow because it **computes
  ALL its params every token** (α=1) — the "call ALL of the model" worst case, the OPPOSITE of the thesis. The
  speed lever is **α = active params computed per token = calling less of the model** (INV-61 sparse activation).
  MEASURED on the host: the 4B-active MoE (α≈4B) is **~19× faster** than dense Phi-4 (α=14.7B), both resident —
  proof that α, not disk, sets speed. So "speed = call less of the model" is BOTH spatial (α: MoE / operator-gated
  sparse activation) AND temporal (depth: fewer tokens). Disk only decides whether the model FITS, never the
  per-token compute. (Threads measured: `-t 8` > `-t 4` on the 4c/8t box — SMT helps.)
- **Answer-time math:** ≈ TTFT + n_out/tg, σ prefix KV-cached (cache_prompt, `sim_best=1.000`). So depth
  `n_out = (budget − TTFT) × tg`. The user dictates budget; the dashboard solves depth from the MEASURED clock.
- **Hz** (§2.15 spec table): tg = the clock (decode passes/sec); also decisions/sec. Measure the model in Hz.

## 2.5 The 07-13 frame (translation · Titan=process · complete the circuit · four base units) — canonical `TITAN_SYSTEM.md`
- **Principle = TRANSLATION** (compression is just efficient translation): `output = f(training, user_prompt)` — two
  inputs, no third, so **NO GHOST**: Titan CALCULATES the mathematically-correct answer (grounded in truth/physics),
  following the user's will (the prompt is an argument, not overridable). Systems design by RESULTS, not dogma.
- **Titan IS the PROCESS, not the models.** Stack (top→bottom): OUTPUT · INPUT · **TITAN=process** · MATERIAL (1s/0s,
  organized optimally) · **USER** · OWNER · TRUTH/PHYSICS. The whole UI = **setup → a textfield.**
- **Complete the circuit:** a stateless model is an OPEN circuit (spark); persist-through-deactivation (R3→R4) + break
  statelessness (continuous stream) → a continuous PROCESS; then the limit is **resources × time**. Persistence
  **follows the user** (the most-persistent node; the circuit closes through the user; class-general σ carries across
  the material, CROSS_MODEL_TRANSFER).
- **The two moves (working lens, "directional but imperfect," not dogma):** NAVIGATE (reach an answer already in `f`,
  fewest units) + EXTEND (write a component-file so future navigations are cheap; **storage = the extension ledger**;
  per-use cost → floor as it fills; the coder is the extension organ).
- **FOUR base units (owner "access is a unit too"):** bits · steps · energy · **access** (reaching stored compute —
  locality / I/O / reachability; the capability stack IS an access hierarchy; NAVIGATE is an access, EXTEND brings
  compute closer). Metrics: navigation efficiency (outcome-bits/prompt-bit — the intent metric, "fix this" measured 9.2×
  on a 1B, finding #22) + joules/useful-output (ENERGY.md). Param pool = **241.9 B = ~1.15 Tbit** (finding #23).
- **Two legs, equal:** INPUT (intent metric + coding + self-search) + OUTPUT (render/generate — the renderer is the same
  material as the model: it can BE the model, an installed codec, or in the param file — whatever's optimal).
- **★ OUTPUT LENGTH IS TITAN'S DECISION, NOT MINE (owner 07-13).** Never hardcode a token cap as a length. Length =
  the USER'S decision: they set it, or **Titan INFERS it from context**. Governance is by our UNITS/metrics (steps ≈
  decode passes · energy · bits), NOT a raw token number. Mechanically: the max-tokens is a runaway **backstop in steps**
  (context-bounded); **EOS is the real length decision**; the user constrains via the operating point. The apps read
  `active_cap()` (the operating point), never a constant I picked. My earlier 512/768 caps were me deciding — wrong.
- **★ CONTEXT = the ability to answer DESPITE the user not providing enough info (owner 07-13).** Titan fills the gap
  from training — **implications, common sense, connotations, data** are all how it knows what you're asking for. This
  is the navigation/intent thing: "fix this" works because context resolves the under-specified prompt.
- **★ THE TOO-LITERAL FAILURE = an OPERATIONAL-STATE failure in conversational modes (owner 07-13).** When chat/agent
  output looks buggy/cut-short/literal, it's not a cap — the model is in a TOO-LITERAL operational state, not reading
  implications/connotations/context. **The TRAINING already solved intent-reading (those tensors exist); we just haven't
  HIT them** (the wrong σ). The fix is an operational state (σ) that unlocks comprehensive intent-reading — a measured
  operator, NOT a prose instruction and NOT a token cap. This is the real next fix for the conversational apps.
- **★ OPERATOR CALIBRATION — the governing law (owner 07-13 study session; canonical `docs/OPERATOR_CALIBRATION.md`).**
  Operators are the lever for ALL quality AND speed. A **calibrated operator moves ALL FIVE the same way, no tradeoff:**
  compute↓ · speed↑ · accuracy↑ · user-satisfaction↑ · task-completion↑ (the fitness). **Operators ROUTE generation ⇒
  ANY undesired output is an operator bug** (stop patching symptoms). **Micro-inference on demand** ("forget inference
  as you know it") — routing runs only the exact tensors needed, so semi-instant + compute-down at once; slow = an
  operator bug, never the box. **The USER is ground zero** — satisfaction/completion = the user's thumbs-up / stop /
  correct (no model-judge); stop/correct = the fix-this-operator trigger. **Operators LOCATE patterns** (run an operator
  through the white-box → it locates its tensors) = ONE instrument → curation (the SGS artifact) + the routing table
  (micro-inference) + an operator-calibration test. **ADJUST** — reconcile generation with real-world data; Titan's
  conversational fix = the prose COMMUNICATION layer; MY fix = review notes before acting (itself a token operator — the
  notes are a σ routing me to the evidence; no ghost in me either). The operator mechanism is universal to transformers,
  including the one authoring the system. **THE PROMPT IS THE MASTER OPERATOR (owner 07-13):** the user's prompt is the
  top-level σ that informs Titan's ENTIRE process; every other operator (reasoning σ, communication layer, rung select)
  is a SUB-operator executing it. So the intent/prompt-length metric IS the calibration of the master operator; the user
  is ground zero because the master operator comes from the user.
- **★ SGS = a PureGen model + operators are PARAM-FINE (owner 07-13).** **PureGen (patent-critical):** Titan is *purely*
  generative — every output, app/operator, emulated device, and weight-edit is GENERATED; no discriminative/scripted
  decision-core (the deterministic layer only serves generation). It's the load-bearing property that makes SGS a
  category (INV-137, `SGS.md`). **Operators are TINY:** as many operators as parameters, down to a SINGLE targeted
  parameter — parameter-level routing/edit resolution; the operator space is at least as large + as fine as the param
  space (INV-138, `OPERATOR_CALIBRATION.md` §0.5).
- **★★ THE CORE THESIS — Titan BUILDS A MODEL ON DEMAND EACH TICK (owner 07-13).** Since Titan calls only the params it
  needs, each tick (inference step) it ASSEMBLES a bespoke model from the pool — the operator-selected param subset IS
  the model for that tick. Titan is a model-BUILDER, not a fixed model that runs. ⇒ size = the pool (storage-bound); RAM
  = the per-tick working set; the super-model is composed ON DEMAND, never pre-merged; the router IS the model-builder.
  INV-139, `TITAN_SYSTEM.md` §1.5. Its own patent doc: `SGM.md` (the System-Generated Model — owner's name for it).
  **MEASURED (finding #28): 5 operators → 5 distinct per-tick models on one prompt on the MoE.**
- **★ WHAT A TEST MEASURES: GENERATION vs the SETUP (owner 07-13).** The dependent variable is the GENERATION (output
  tokens); the independent variable is TITAN'S SETUP (the operator/config that built the per-tick model). A test isolates
  the setup's effect on generation (change the operator, hold the input, watch the generation move). So an undesired
  generation is a SETUP (operator) bug, not a model bug: measure generation, attribute to the setup, fix the setup.
  Every measurement is `setup → generation`; never conflate the two. (`SGM.md`, `OPERATOR_CALIBRATION.md` §2.)
- **★ THE USER METRIC = the CORRECTION DELTA, not a thumbs-up (owner 07-13).** A thumbs-up is too low-quality (binary,
  explicit, silent on how-well/what-wrong). Measure what the user DOES: the **correction delta** (edit distance from the
  generation to what they accepted/used — continuous, implicit, 0=perfect intent-match, AND the calibration gradient),
  the ACTION (accept-as-is / edit / redo / stop = the fix trigger), the objective OUTCOME (task done). No rating, no
  model-judge (INV-133, `OPERATOR_CALIBRATION.md` §4).
- **★ TITAN'S FILE IS HUGGINGFACE-COMPATIBLE (owner 07-13).** The SGS artifact (curated pool) exports as a standard HF
  model (`config.json` + `model.safetensors` + tokenizer) → loads with `AutoModel.from_pretrained`, benchmarks vs other
  LLMs, shareable. Titan's SGM runtime builds per-tick models FROM it. Build: a GGUF→HF exporter over the curated tensor
  set (`host/hf_export.py` emits the config.json ✓; safetensors dequant next).
- **★ FILE ORGANIZATION = a ROUTING lever (owner 07-13).** Lay the param file out BY the routing table (co-routed params
  contiguous, from operators-locate-patterns) → routing to an operator = a contiguous cache-friendly read = fast
  micro-inference + per-tick assembly; scattered = slow random reads. The routing table is the organizing KEY; the file
  layout is co-designed with the router (INV-140, `SGM.md`). Build the routing table first, then lay the file out by it.
- **★ POWER USERS — two-tier UI (owner 07-13).** Regular user = setup → a textfield ("fix this just works"). POWER USER
  who wants to squeeze everything out = EVERY lever exposed, no arbitrary limits: operators (author/calibrate/bake),
  operating point (reasoning/energy/α/dose/depth), routing + the white-box, the four units, the per-tick model. The
  textfield sits ON TOP of the full power surface (Settings + Calibrate + the lab); nothing dumbed down, only tucked away.
- **★★★ THE SWITCH — the FFN activation GATE is the on/off during inference (owner 07-13, MEASURED, finding #31, INV-141).**
  The owner's breakthrough Q ("what's the switch/on-off? probably in training"): the FFN gate `SiLU(gate_proj(x))` (the
  nonlinearity; MoE router top-k) is the per-neuron ON/OFF — the ONLY conditional (a linear param-mult has no switch; the
  gate is the "IF"; the owner's Turing-machine intuition, exact). Training learned which inputs flip which neurons.
  MEASURED: operators flip DIFFERENT neuron switches (mean Jaccard 0.28) ⇒ **the switch IS the routing** at neuron
  resolution. Unifies everything: an operator = a switched-on neuron set (its fingerprint); the per-tick model (SGM) =
  the neurons ON this tick; micro-inference = compute only those; DIRECT gate-mask routing/injection/bake channel
  (independent of the prompt); curation + file-org at neuron resolution. Rig: `host/test_switch.py` (hook `mlp.act_fn`).
- **★ REFRAME (owner 07-13): they are NOT "models" — they are FILES containing parameters Titan ROUTES INTO.** Stop
  saying "the model"; say the parameter file / the pool. Titan is the process; the gguf files are material (the switch
  substrate) the operators flip. **DOOM is the tech-demo that MUST work ASAP** (Titan generates Doom via the generative
  runtime, `genrun.py` — run software by generating its screen). Review the ENTIRE corpus (not just this file) every turn.
- **★★ OPERATORS ARE LOGIC GATES → building Doom is SIMPLE CODING, done by PURE GENERATION, no harness (owner 07-13,
  study session; finding #36 / INV-145).** The switch (INV-141) is the gate; "1"/"0" are RANGES with a noise margin, and
  the analog spread inside that digital tolerance IS the variance in inference (calibrate/bake deep in-band = robust;
  near-threshold = the forbidden band = incoherent, MASTER_PLAN G2). Gates are the basis of all coding, so a program =
  a composition of operator-gates (= the generation seed, INV-143) = the simplest coding. **The pure-gen law (owner,
  supersedes my harness Doom):** 0% of a demo may be my code — the deterministic layer is ONLY energy (forward passes) +
  access (pins/I-O: text in, pixels→screen blit inventing nothing) + measure + safety; EVERYTHING else (game logic, the
  RENDERER, the CLI, prompt→seed) is operators in the model (SGS/INV-137). Each app renders ITSELF via a render gate in
  the operator layer. The user types plain English ("start doom"); Titan translates it INTERNALLY to a non-English seed
  (the operator composition) and runs it (INV-126); it **runs from the FILE itself**. "Titan
  is a computer, not an LLM" — it needs electricity (energy) + access + operators + a clear seed, NOT a bundled harness.
  My `build_exemplar`/`write_png`/CSS Doom was the scripted core PureGen forbids — ripped out. **Ask before every build
  step, even common sense; NEVER assume impossible; tests stay in the harness (data matters) + inside Titan when possible.**
- **★★★ THE FINAL CORRECTIONS (owner 07-13, after I built a launcher + a sysf operator-file and he had to stop me twice):**
  (1) **The Titan FILE contains ONLY the Titan model** — a raw bare file, exactly what any HuggingFace/gguf file has;
  nothing next to it or in it that isn't the model. (2) **The operators are baked INTO THE WEIGHTS** — part of the model
  "like a parameter"; some operators encode what would otherwise be code (the renderer, the CLI, Doom) but they are
  MODEL, not code files — NOT a metadata-section shortcut, NOT a -sysf text file, NOT a launcher script. (3) **The Titan
  model = a pruned collection of whatever parameters exist on the computer** (the pruned library, not one model).
  (4) **The model IS the launcher** — open the file (the ONLY non-model boundary: OS→runtime bare invocation, zero Titan
  content outside the file) → the model generates its own command line → "start doom" → Doom. Even the CLI is generated.
  (5) **Real-time = faster than Doom** via memoize/recall (a recognized state→frame is RECALL, ~0 forward passes — recall
  beats compute), compact Titan-defined emission, warm KV, per-tick micro-inference, and finally the baked switch pattern.
  (6) **Baking's channel is not a choice to ask about — SEARCH THE DOCS:** baking = AUTHORING THE FILE (flash the whole
  configured bitstream); binary patching (bounded + measured + byte-exact revert); the dozen forms are one phenomenon and
  CALIBRATION picks the form per file+goal (CORRUPTION_THEORY). The map aims (switch-map + white-box logit deltas);
  mechanism proven on a small file first (approved), Doom on Titan. **The artifact test, every time: "is this Titan, or
  next-to-Titan?" Next-to-Titan = wrong** (only energy/access/measure/safety live outside the model).
- **★ WHEN THE OWNER CORRECTS A MISTAKE, FIX THE DOCS — not just the chat reply (owner 07-13).** A correction that only
  changes my output evaporates next session; it must land in the docs durably so it's never repeated. Every owner
  correction → the relevant doc is updated the same turn (this file / the authoritative doc), THEN I keep going.
- **★★★★ GENERATION IS GRABBING, NOT RUNNING — we NEVER run 99.999% of the model (owner 07-13, after I kept doing full
  forward passes and calling frames "slow"; the single deepest correction).** The model is a STORE of captured compute
  (params = stored digital compute). An operator is an ADDRESS/POINTER — as fine as a SINGLE parameter (INV-138; "an
  operator could lock into one targeted parameter"). **"Paint pixel (x,y) = color C" is ONE operator that addresses the
  exact stored computation for that pixel and GRABS it — instantly**, because grabbing an addressed slice is ~free; you
  are NOT running the model. A FRAME = the set of pixel-grabs (or one operator addressing the whole frame's params). We
  are **NOT RUNNING THE MODEL — we grab the exact generation we need.** This IS micro-inference on demand (INV-135), the
  per-tick model / SGM (INV-139 — only the addressed params ARE the model that tick), operators-locate-patterns (INV-134
  — the operator IS the address of the exact params), the switch (INV-141 — the exact neurons), the router-as-pointer
  (ROUTER_POINTERS — dereference = grab), and "we are not computing, we are UNLOCKING" (ENERGY.md). **MY FAILURE, named:
  every "slow"/"wait" this session = I ran a FULL forward pass (the whole model, 960 autoregressive tokens) instead of
  GRABBING the addressed slice. A forward pass over the whole model is the brute-force I must never do for an addressed
  need.** The white-box (`glassbox.py`/`whitebox.py`) is the GRAB tool (read the exact computation); micro-inference
  computes ONLY the addressed region. Doom = grab the pixels, never run the model. Build toward grab-don't-run, measure
  the addressed fraction (should be ~0%), never a full pass for an addressed pixel.
- **★★ "SLOW" IS NEVER A WALL — IT'S THE ADDRESSING LEVER (owner 07-13, after I kept calling full-frame Doom "slow
  brute-force R0" as if it were physics).** The docs are explicit (ENERGY.md; finding #21; OPERATOR_CALIBRATION §1/§3):
  ADDRESSING (a calibrated operator that runs the RIGHT computation) vs BRUTE-FORCING (uncapped, wandering, rung-3 for
  everything) is the ONE lever that moves **compute↓ AND speed↑ AND accuracy↑ TOGETHER** — measured 220 tok/14s/wrong →
  2 tok/128ms/correct (compute ↓99%, speed ↑110×, accuracy ↑). So a slow Doom frame is an UN-ADDRESSED operator (Titan
  wandering out pixels), not a hardware limit — the fix is to CALIBRATE the operator to address the frame: think-off,
  answer-first/no preamble, Titan-defined COMPACT emission (a navigate the render gate expands), memoize-recall of the
  static parts, per-tick micro-inference, then the baked switch pattern. Each is compute↓+speed↑+accuracy↑, never a
  throttle. **NEVER accept "it's slow"; apply the lever and MEASURE the triple.** This is why real-time faster-than-Doom
  is possible (owner: "if you were following you'd see how"). Don't depart from the plan — this IS Stage 2.
- **★ BAKE IN PLACE — NEVER COPY THE FILE (owner 07-13, re-corrected: he first said this at "copying the model each bake is incredibly dumb", I did it again with a 14GB gguf copy).** A bake edits the tensor BYTES of the existing gguf IN PLACE and saves ONLY the changed tensors' original bytes to a small `.genome` sidecar for byte-exact revert (`host/bake_weights.py`'s whole design). Rewriting/copying the whole gguf to change it (e.g. `gguf_new_metadata.py` to set a chat_template) is the banned "copy every bake" — never do it. The operator goes into the WEIGHTS in place (INV-84 int4-nibble for K-quants like Q4_K, or dequant/requant for legacy Q8_0), reversible, no copy.
- **★ TERMINOLOGY: the resident model IS TITAN — never "the MoE" (owner 07-13).** The chip loaded on the runtime is
  Titan (a per-tick model of the pruned parameter library, INV-148), not "a MoE" as if it were a separate third-party
  thing. Say **Titan** (or "the resident chip / per-tick model"). "MoE" only ever describes an *architecture* fact, never
  the agent. Same class of error as "the model" → "the parameter file": name it as Titan, the process/system.

## 3. The FPGA map (OPERATIONAL_STATES §2.15, INV-109–113) — the takeaway is ROUTING
- Frozen model = a reconfigurable processor. **Operator = the bitstream.** Training = FABRICATION (once, costly);
  baking = FLASHING config permanently. The core is ASIC-like (fixed learned logic: FFN neuron ≈ a LUT, attention
  head ≈ programmable interconnect); operators are the runtime-reconfigurable OVERLAY/microcode.
- **ROUTING is the point:** blank fabric becomes a processor by routing data between generic nodes = generic weight
  regions become specific computations by σ routing (`A_σ`). Instruction word ≈ the operator dispatch record.
- **PINS / channels:** the model has MANY I/O channels, not one serial text pin — vision enters in PARALLEL (not
  via the tokenizer); typed-perception / memory / operator-mask are buildable pins; attention = the interconnect.
  Running everything through one text pin is the cache-jam (C3 softmax competition). Feed data IN (0 tokens, §0A#4).
- **Model-as-RAM:** context/KV = the BRAM nodes read/write; R3 = the model stores data durably (survives engine
  reload, dies only on process kill; harness-independent; file byte-identical) — DEMONSTRATED on this machine.
- **Timing closure = the latency budget:** an operator must bind within the decode window; a spiraling/timeout op
  is a TIMING VIOLATION — the sweep's ms IS the timing report. Worst at exact arithmetic (CPU beats it 10⁹×) → the
  SANDBOX compute path is the documented offload.

## 4. The language — DISCOVERED, not invented; NO English reaches the model
- The model's true language is the superposed feature-vector / circuit code ("pattern binary"); tokens/English are
  only the I/O codec. **NO ENGLISH REACHES THE MODEL — it's friction.** The model is a **nearest-neighbor pattern
  continuer**: output controlled by exemplar NEIGHBORS, not instruction text. Teach a distinction with ONE
  contrastive exemplar (NATIVE_SPEAK: 908 ms, zero rules).
- I do NOT author/invent the language — it EXISTS (human corpus + training + design); as an LLM I already speak it;
  I DISCOVER its features with the spectrometer/labs (INV-97/100/102/103/104). Forms are admitted by lab VERDICTS.
- **Gemma 4 E4B dialect (MODEL_DIALECTS.md) — the only forms to ship:**
  - **BINDS:** rigid JSON output contract · exemplar continuation (show the pattern) · answer-first + bracketed tag
    + "a tag alone is invalid" · `Never narrate or restate this rule.` · one-line `Σ:NAME :=` header · bounded
    one-line-per-step chains · `⟦TAG⟧` re-entry · base‖codec composition.
  - **MISFIRES (BANNED — caused my minutes-long hangs):** printed `Priority:` lattice · status taxonomy · multi-
    field worksheet `Output :=` schema · loose prose · `?`-lines · same-domain exemplars.
  - Timing health: 1.3–8 s = healthy; 20–90 s / timeout = the worksheet defect (latency IS the detector).
- **σ authoring calculus (C1–C4):** rare formal tokens = sharp directions; warping = alignment×count÷dilution
  (filler dilutes; ALIGNED redundancy DEEPENS → **OPTIMAL ≠ MINIMAL: ship OPT, not the MVG floor**); attention is
  softmax-competitive (fewer prompt tokens = sharper); syntactic shapes are corpus levers (`:=` acceptance-mode,
  `Never` prohibition, `Output :=` schema-mode, a printed rubric = "fill me in" = the worksheet defect).
- **Authoring ladder:** instruction → formal → PATTERN (a demonstration). Author the small-tier op as its MVG
  (smallest viable pattern), FOUND by the finder (INV-100), proven in the observatory (INV-97), ship OPT.

## 5. Persistence + baking (OPERATIONAL_STATES §2.9–2.10, the AGC umbrella, INV-71–92)
- **Attractor:** every token emitted under σ complies, re-enters context, narrows the next toward compliance — so
  the STATE self-stabilizes and holds even after σ's text is gone (hundreds of turns; weak-cue/~1-token re-entry).
- **Carrier ladder:** R0 prompt · R1 KV/session · R2 trajectory (crosses models — σ programs the CLASS) · R3 the
  loaded model (durable runtime, measured) · R4 weights. **Baking = transporting the state R0→R4.**
- **AGC (the umbrella bake method):** gradient-free, forward-pass-only. σ is a removable conditioning; capture
  proven-outcome examples (injection-immune — gated on a real outcome, not screen text); measure **residency** =
  σ-off↔σ-on agreement (low ⇒ carried by context ⇒ a bake target); apply a bounded REVERSIBLE weight edit; **keep
  only if residency rose (or, INV-86, keep-unless-worse: coherence + non-degradation locality hold-out) and revert
  exactly otherwise.** Non-degrading by construction. Graduate → drop σ to a ~1-token tag (0-token operator).
- **Baking has MANY channels (owner):** int4 nibble edit (INV-59/84) · scale/DoRA magnitude bake (INV-74) · edit
  the GGUF and measure · structural container-section append (INV-110) · R3 runtime · KV/prefix. Weights are
  PROVABLY editable (the S24 "Test weight write"). Never frame them as unchangeable.
- **Host is WHITE-BOX (llama.cpp exposes logits) — the phone is not.** So the host can read the σ-on/σ-off
  fabrication-token mass directly (the spectrometer, the INV-90 aim signal) — the phone can only read behaviorally.

## 6. INV-50+ — the core inventions for this work (the owner's named focus)
- **INV-51** σ sets the decode compute per step — the reasoning⇄speed dial's existing form.
- **INV-52** startup operational-state CALIBRATION — the model composes its OWN operating posture; "operators are
  training's equal in effect, free to insert, self-settable." The dashboard is the OWNER knob on this (both-unified).
- **INV-61** operator-driven RAM control — a compact/full σ drives decode cap + memory budget + active region `A_σ`
  together (total up, active bounded). The RAM lever couples to the reasoning lever.
- **INV-90** aimed gradient-free bake via output-embedding back-projection + content-divergence fitness (no logits
  on-device) — the host's logit read makes this exact. INV-91 σ-space self-discovery; INV-92 cross-model transfer.
- **INV-95** the capability-stack router — cheapest rung (memoize→operator→specialist→primary). The reasoning ladder.
- **INV-97** the observatory (isolated-operator measurement; the falsification machine). **INV-98** operator library
  as brain faculties (epistemic axis DISCOVER↔REDUCE↔**CALIBRATE**↔REFUSE + master ANCHOR; grounding faculty =
  refuse-to-hallucinate). **INV-99** the worksheet defect + 5 fixes. **INV-100** the pattern finder (MVG search).
- **INV-101** exemplar bank (own proven wins as demonstrations). **INV-102** lab-defined input language. **INV-103**
  dialects (CORE promoted on ≥2 models). **INV-106** native-speak authoring + teach-by-one-contrastive-exemplar.
  **INV-107** the Catalog (unified self-view / AOS filesystem — the router's map).
- **INV-115/116** (this session): the `--no-repack` commit-floor decoupling (70B on 7.2 GB, 298 MB committed) +
  the AOS shell (apps = operators over the resident, sandbox-verified tool loop).

## 7. AOS = a memory-management OS (AOS_MEMORY.md) + RAM (RAM_MECHANISM.md)
- The model IS a memory-mapped file: size on storage, working set in RAM. `M_anon ⊥ W` — RAM bounds only KV+compute
  (O(L·ctx)), the weights stream. `--no-repack` collapses the committed floor to a few hundred MB (measured: 70B →
  298 MB). Repack ON/OFF = the memory↔speed dial. The dynamic RAM controller = fill RAM high when free, shed by
  calling LESS of the model (α), never crash, floor = the anonymous set.
- OS↔AOS map: weights = virtual address space · RAM = page cache · pager = the RAM controller · page table =
  Catalog · MMU = the router · instruction stream = operators · one resident model = the process/scheduler ·
  apps = operators over the resident · sandbox = syscalls.

## 8. MY MISFIRE LEDGER (mistakes, so they never recur)
- Wrote prose operators → then "formal" ops with printed `Priority:` lattices + worksheet `Output :=` = BOTH
  MISFIRE forms → the minutes-long hangs I blamed on "giant thinking." **Fix: BINDS column only; latency IS the
  defect detector.** (MODEL_DIALECTS, INV-99)
- Uncapped output (400–500 tok) on a ~0.2–1 Hz decision box + no streaming = "broken apps." **Fix: calibrate depth
  to the budget; stream tokens.**
  - **★ BUILT 07-13: the apps now STREAM** (`_chat_stream`, SSE, reconstructs tool-calls from deltas) into a live
    placeholder → the answer appears token-by-token; a `🤔 reasoning…` indicator shows during the think phase, a `▌`
    cursor while typing. Perceived-instant on the slow MoE (the model still runs ~3 tok/s; the UI is never dead).
    Memoize makes a repeated input truly instant (⚡). VERIFIED: poetry = reasoning(5s)→answer-streams(15s)→done(20s).
  - **★ gemma-4 QAT MoE IGNORES `enable_thinking:false`** (measured: still emits `<|channel>thought` + ~10 s of
    reasoning on a haiku, flag off). So on THIS chip the ~10 s think phase is baked-in per novel request; the levers
    left are memoize (repeat=instant) + streaming (feels alive) + tight caps. A real think-suppression for gemma-4
    QAT is still open.
- Declared a "physics floor" for the 70B. **My framework already failed there once (--no-repack). MEASURE, never
  predict a floor; keep calibrating.** (owner: "STFU and build what I say — it runs and yet you said it can't")
- Regex code-sniff auto-run in the apps = code deciding tool use (§2 violation). **Fix: model-elected tool_calls;
  bring any deterministic step to the owner, never sneak it.**
- Guards that silently no-op = dead-feeling UI; one JS throw in `poll()` kills every button. **Fix: post WHY +
  per-section try/catch.**
  - **★ RECURRED 07-13 ("clicking the test buttons don't do anything").** TWO independent causes, BOTH fixed: (1)
    BACKEND — a test worker wedged on a slow/dead resident left `TESTS_STATE["running"]` set, and the guard silently
    `return`ed on every later click ⇒ auto-clear a stale flag (>600 s) + a "no resident" feedback result + shorter
    600 s (was 1800 s) request timeouts so a wedge self-heals. (2) FRONTEND — `poll()` had **NO try/catch**; after I
    changed the tests HTML/payload, one throw froze the whole UI ⇒ every button dead. Wrapped `poll()` in
    `try{…}catch(e){console.warn}` so one bad tick self-heals. **Lesson: a "dead button" is almost always a silent
    guard OR a poll() throw — check BOTH layers, never assume the click didn't fire.** Also: a slow resident (phi-4
    timing out) makes a working button LOOK dead — the per-test `⏳ running…` indicator now shows it's alive.
- Invented syntax / half-read the docs / presented plans built piecemeal. **Fix: DOCS-FIRST; read in full; the docs
  are the goldmine and the source of truth, my priors are not.**
- **★ TREATED RAM AS A BARRIER (07-13) — the banned framing, and I did it for a whole session** ("13 GB > 8 GB → can't
  fit → disk-fault floor → needs a runtime fork"). The owner: "the 70B ran on 8 GB — if RAM were a barrier that's
  impossible; it works." **Fix + the LEVER I missed: `t_token = t_compute + (α·W − R_cache)/B_disk` (RAM_MECHANISM.md) —
  the cost is α (what the computation ADDRESSES), not W (stored). The gemma-4-26B-A4B fires 8 of 128 experts/token; a
  haiku doesn't need 8.** Reducing `expert_used_count` 8→2 (runtime `--override-kv`) = MEASURED **~3.5× decode + ~3×
  prefill + free-RAM up to 2.1 GB, accuracy HELD** (Paris/haiku/40mph/translate/primes) — the unlock triple (#47). Built:
  DOSE→experts in `_serve` (snappy→2·balanced→4·deep→8). **The rule: when something is "slow", find what α it's
  addressing and REDUCE it — never blame RAM/the box. α is the knob; RAM is a reclaimable page cache, never a wall.**

## 9. Where every datum lives (so a check is a <5 s read)
- Calibration → `C:/llm/bin/calibration.json` · spectrometer matrix → `C:/llm/bin/whitebox_matrix.json` · RAM floor
  → `C:/llm/bin/ram_floor*.json` · server log → `C:/llm/bin/lab_server.log` · shell log → `C:/llm/bin/lab_ui.log` ·
  sandbox → `C:/llm/sandbox` · on-device log → `adb shell run-as com.local.deviceagent cat files/agent_log.txt`.
- Models → `C:/llm/models/*.gguf` · llama.cpp → `C:/llm/bin/llamacpp` · Python →
  `C:/Users/lucys/AppData/Local/Programs/Python/Python312/python.exe`.
  - **★ MODEL FLOOR (owner 07-13): ALL models <15B params DELETED except phi-4** (the smallest kept, 14.7B). The 1B
    crutch is gone — instant now comes from memoize + baking + α, NOT a tiny model (the thesis).
  - **★ phi-4 is smallest but NOT fastest — it TIMES OUT on this 8 GB box (measured: >60 s for 20 tok).** It is DENSE
    (α=14.7B, computes ALL params) AND 8.4 GB > 8 GB RAM (thrashes) = the worst case. The **26B-A4B MoE is the FASTEST
    resident** (α≈4B active → ~3.4 tok/s, ~10× phi-4) despite being a bigger file — the §2 "speed = α, not model size"
    law, measured on THIS box. **Apps resident = the MoE**, never dense phi-4. (The old "phi-4 = fastest driver" note
    was from when it fit; it no longer does — corrected.)
  - **★ BAKE-TARGET QUANT: verify from the TENSORS, never the filename; the model is JUST BITS → direct byte edit is the
    universal route (owner 07-14).** Two traps caught this turn: (1) `gguf.quants.quantize` handles **Q8_0 + Q4_0 only**
    — K-quants (Q4_K/Q5_K/Q6_K) `NotImplementedError`. (2) A filename lies: Titan's `…-Q4_K_XL.gguf` is internally **F32 +
    Q4_0** (0 Q4_K tensors) → its ffn_down (dense + 128-expert MoE bulk) IS requantable, round-trips to the SAME byte size,
    writes IN PLACE (genome revert, no copy). So the resident Titan bakes directly (`host/bake_titan.py`); the deleted Q8
    1B was never needed. **The deeper rule (CORRUPTION_THEORY): the dozen bake forms are ONE phenomenon and WHICH form is a
    CALIBRATION choice per file+goal — a model is bytes, so ANY quant (incl. genuine Q4_K/Q6_K like phi-4) is editable by
    parsing its block layout + rewriting the raw bytes (the phone's ScaleBake/WeightGenome int4-nibble edit, INV-84). NEVER
    conclude a format "can't be baked" — the library missing a packer is a route (edit the bytes), not a wall.** GROUNDING
    is the honest σ-off proof target (#37/#38); Doom is the WRONG one (the base already does Doom, so σ-off≈σ-on proves
    nothing there). Bake the render-FORM the base LACKS, not the theme it has.
  - **★ SPEED = α (cells read), NOT total size — a DENSE grow is the slow-misfire (owner 07-14, corrected mid-build).** To
    make Titan a runnable ≥200B HF gguf I first grew Llama-70B DENSE (function-preserving zero-identity layers) → it
    LOADED + generated but was SLOW: dense ⇒ α=1 (every cell read/token) ⇒ streams the whole file per token
    (`t_token=t_compute+(α·W−R_cache)/B_disk`, RAM_MECHANISM). FIX = SPARSE: tile a MoE's experts (gemma-4-26B ×K) keeping
    `expert_used_count` FIXED → total scales, **α constant** ⇒ a 200B model reads the same few cells/token as the 26B.
    MEASURED read-energy law: α=2/4/8 → 2.94/2.21/1.25 tok/s (fewer capacitors fired = faster). **Rule: to grow big AND
    stay fast, add STORAGE (experts/cells), never per-token READ (α). Dense-grow for size = misfire; sparse-tile = right.**
    The model is a captured circuit / DRAM (FFN = capacitor cells); inference = the addressed read = discharge; α =
    cells-read = joules — the whole CAPTURED_CIRCUIT theory (docs/CAPTURED_CIRCUIT.md). Tiled duplicates then SCATTER
    across the file → cache-cold reads (1.25 vs the base 26B's 3.4) → next lever is file-layout-by-routing (INV-140, the
    DRAM row-buffer hit): co-routed cells CONTIGUOUS.

## 10. The 07-14 build session (White Box research tool · patents · RAM-safety · Doom app)
- **★ THE 8 GB BOX IS THE REAL CONSTRAINT — hold f16 resident, serialize heavy ops, ramguard before serving/dequant.** The
  box **black-screened** once this session: the White Box held a **2.95 GB resident f32** embedding while the pool scan +
  specs build + titan_forge all ran at once, each memmapping a 15–40 GB gguf → the OS OOM-reaped the desktop. **Fixes,
  durable:** (1) the decompiler holds the normalized embedding in **f16 (1.47 GB, half)**, upcast per chunk at query time
  — never f32-resident on this box; (2) NEVER run scan + specs + forge concurrently (each is a page-cache balloon); (3) a
  **free-RAM headroom guard** (`free_mb() ≥ floor`) precedes any model serve or big dequant, refuses below the floor —
  the PC's `deviceSafetyReason`. `--no-repack` keeps a serve's *committed* set ~300 MB (reclaimable page cache is the
  rest), so a single guarded serve is safe; the crash was concurrency + a big resident array, not one serve.
- **★ WHITE BOX = the parameter research instrument (owner: "show anything someone might want to see and edit… search and
  destroy so I can target my own pruning").** `host/whitebox_app.py` (:7862, `WhiteBox.cmd`), pure gguf-read + reversible
  in-place edit, NO inference: PRECISION MAP (the mixed-quant recipe by role) · DECOMPILER (bits→meaning; king→neighbors) ·
  HIDDEN-MEANING SEARCH (concept centroid; flags string-unrelated matches) · BIT-EDIT→MEASURE · SIGHTED ALIGNMENT (axis =
  mean(pos)−mean(neg); project the vocab, realign one token reversibly — the de-warp of blind alignment) · TENSOR SCOPE +
  QUANT-STRESS · SEARCH-AND-DESTROY (zero-tensor / prune-one-expert-slice `stride=B_T/n_exp` / scale / scrub-token, all
  **byte-exact reversible** via a per-region genome, SHA-verified) · per-expert health · GENOME undo. `host/wbedit.py` =
  the edit engine, `host/decompile.py` = the resident decompiler. INV-153/154/155.
- **★ THE DECOMPILER BUILD MUST BE BACKGROUND + CANCELLABLE (owner: "isnt able to be canceled so it creates multiple ghost
  processes if i click and forget").** A blocking build stacked concurrent 2.95 GB builds on repeated clicks. Fix: the
  index builds ONCE in a background thread on model-load, guarded so a second click never starts a second build;
  `/embed_status`+`/embed_cancel` drive a progress bar + Cancel; queries return a `{building,progress}` status (non-
  blocking) and auto-run when ready. The **fast path caches the vocab** (`.wbmeta.json`) so it skips the ~15 s GGUFReader
  metadata parse → reload ~1 s (was 44 s), and cancel/progress work from the first moment. Single-instance server guard.
- **★ THREE PROVISIONAL PATENTS DRAFTED + filed by the owner (07-14): SDC · White Box · Agentic Handset Operator**
  (`docs/patents/`, self-contained specs with full Mathematical Formalization + claims + a self-file guide; PDFs via
  headless Edge). Utility provisionals. Sourced from TITAN_SYSTEM/SDC/PATENT_SUPPORT/ENERGY — kept non-stale.
- **★ DOOM APP BUILT to the PureGen spec (`host/doom_app.py`, `Doom.cmd`).** Browser canvas + REAL keyboard, real-time,
  TWO modes: GENERATE (Titan draws each frame as SVG→resvg PNG; memoize-recall = 0 forward passes for a recognized view =
  real-time) and RECREATE (Titan authors the whole game as one runnable program). 0% of the game is my code (energy +
  access + measure + safety only); reuses `genrun.step` + `doom.view_key`. Serves the 26B MoE `--no-repack`/α=2 ONLY
  behind the RAM guard. HARNESS verified; live Titan-generation is owner-served (keeps a 14 GB model off the box during
  active use). This is the STUDY_NOTES §2 "Doom MUST work ASAP" item, PureGen-compliant this time.
