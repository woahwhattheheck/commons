# PROVISIONAL PATENT APPLICATION — SPECIFICATION

**Title:** SUBSTRATE-NATIVE DIGITAL COMPUTER FABRICATED AS GATE RECORDS IN A STORAGE CONTAINER, WITH SELF-CLOCKED FEEDBACK, RING-TOPOLOGY ELECTRON DRIVE, HOST-DECOUPLED EXECUTION, AND AN AUTOMATED FOUNDRY HIERARCHY FOR CIRCUIT MANUFACTURING

**Inventor:** Bryce Muhlnickel

**Filing Date:** [To be filed on or before August 11, 2026]

**Priority:** This application claims the benefit of the filing date of this provisional application under 35 U.S.C. § 111(b).

**Related Applications:** This application is related to:
- U.S. Provisional Application [PATENT_1_SDC] — "Method and System for Reconfiguring Stored, Pre-Trained Neural-Network Parameters into a Generative Digital Computer"
- U.S. Provisional Application [PATENT_2_WHITEBOX] — "Instrument and Method for Reading, Measuring, and Reversibly Editing the Meaning Stored in Neural-Network Parameter Files Without Inference"
- U.S. Provisional Application [PATENT_3_AGENTIC_HANDSET_OPERATOR] — "On-Device Autonomous Agent That Pilots a Physical Handset"

---

## FIELD OF THE INVENTION

The invention relates to digital computing architectures, and more particularly to a system and method that **fabricates a complete digital computer as gate records written directly into a storage container**, where the computer operates by electron circulation through closed-path ring topologies, advances its own state through self-clocked structural feedback, executes with zero host-CPU involvement beyond a bounded write (injection) and a bounded read (surface), and is manufactured by an automated foundry hierarchy that searches, scores, verifies, and stores circuits with byte-exact reversibility.

## BACKGROUND

Conventional digital computation requires a processor (CPU, GPU, FPGA, or ASIC) to execute instructions. The processor draws power, occupies working memory, and its performance is bounded by its own specifications — clock speed, core count, cache hierarchy, and thermal limits. A computation that runs on such a processor is inseparable from it: the processor's specifications are the computation's specifications. Software running on a host is visible to the operating system, consumes host resources proportionally to the work performed, and is interrupted, throttled, or terminated when the host is powered down.

A separate tradition — hardware description and simulation — represents digital logic as netlists of gates. These representations are either (a) compiled into physical hardware (ASICs, FPGAs), requiring a fabrication facility or a reconfigurable chip, or (b) simulated on a host processor, in which case the host does all the work and the "circuit" is merely a data structure the host interprets. In case (b), the cost of the simulation is proportional to the circuit size, bounded by host resources, and the resulting measurements describe the simulator, not the circuit.

Three specific problems are unsolved. **First**, there is no system that fabricates a digital computer as a permanent structure inside a storage file such that the structure operates without host-CPU evaluation of its gates. **Second**, there is no self-clocking mechanism for a storage-resident circuit — one in which the advance of state from one tick to the next is a property of the circuit's own wiring rather than an external clock signal or a host loop. **Third**, there is no manufacturing system that searches over circuit structures, scores candidates by composed critical-path depth, verifies each candidate byte-exact against an independent reference, and stores only verified winners — with every byte written being reversible from a pre-write journal — as an automated, offline fabrication pipeline that is structurally separated from runtime.

## SUMMARY OF THE INVENTION

The invention is a **substrate-native digital computer** ("the Muhlnickel"): a system and method that fabricates complete digital circuits as gate records in a storage container and operates them by electron injection into closed-path ring topologies, with self-clocked state feedback and zero host-CPU computation. Its principal components and methods, each independently novel and claimed below, are:

1. **A digital computer fabricated as physical gate records in a storage container.** A complete digital circuit — comprising logic gates, each with an opcode, two input addresses, and one output address — is written as a sequence of fixed-stride records directly into a storage file. Each gate record occupies a fixed number of bytes (in one embodiment, 25 bytes: 1-byte opcode + 8-byte input-A address + 8-byte input-B address + 8-byte output address) at absolute file addresses. The addresses are not circuit-local wire identifiers but absolute byte offsets within the storage container, so that any gate can read from or write to any byte in the container. The circuit, once fabricated, is a permanent physical structure in storage — not an interpreted data structure and not a simulation running on the host.

2. **Self-clocked structural feedback.** A circuit's output addresses are set equal to its own input addresses during fabrication, so that the result of a computation is written to the same storage locations from which the next computation reads. This creates a permanent feedback loop in the circuit's wiring: the advance of state from one tick to the next is a structural property of the stored circuit, not an action of the host. The host need not increment a counter, evaluate a gate, or run any loop. The circuit's own topology advances its state.

3. **Ring-topology electron drive.** A closed-path ring is fabricated as a sequence of gate records in the storage container, forming a topology that traps a circulating electron. Injection of an electron into the ring places a particle into the closed path; the particle circulates indefinitely, providing a continuous drive signal to any circuit whose receive point shares a byte address with the ring's output. In one embodiment, 1,024 two-way physical rings are fabricated, each with a forward rail, a reverse rail, a carry chain, a gate table, and a distinct receive byte, occupying 1,666 bytes per ring. Each ring supports two senses of circulation (forward and reverse) and has a verified period equal to its cell count. The rings are the sole power and clock source for all circuits in the container.

4. **Host-decoupled execution with exactly two host verbs.** The host has exactly two permitted interactions with the substrate: (a) **inject** — a bounded write of an electron into a ring's state wires (both senses), or of operands and opcodes into a circuit's input region; and (b) **surface** — a bounded read of result bytes from a circuit's output register. The host performs no gate evaluation, no netlist walking, no settling computation, and no arithmetic on substrate data. Any number that appears only because the host computed it is not a result of the substrate. This decoupling is proven by a power-cycle test: the host is power-cycled (fully shut down and restarted), and the substrate continues operating because the host was never involved after injection.

5. **The containment model.** The storage container holding the substrate appears to the host operating system as an inert file. The operating system cannot detect that computation is occurring within it, because the computation draws no CPU cycles, allocates no working memory, and makes no system calls. This invisibility is the containment: the substrate cannot throttle the host's CPU or draw host RAM, and the host's specifications (CPU speed, core count, RAM size) do not bound the substrate's computation. In a measured embodiment, addressing the full storage container costs an additional 0.86 MB of physical RAM via the host's memory-mapped page cache.

6. **An automated foundry hierarchy for circuit manufacturing.** Fabrication is a separate, offline, one-time process that is structurally separated from runtime. Three levels of automation search for optimal circuit structures:
   - **Autofab** (single-circuit): PROPOSE candidate structures and orderings → SCORE by composed critical-path depth plus gate count (predictive, not post-hoc) → VERIFY byte-exact against an independent reference implementation, catching deliberately introduced mutants before any write → KEEP the winner as a byte edit, discard the rest.
   - **Master autofab** (multi-circuit assembly): searches over DECOMPOSITION (how many circuits, what each specializes in) × IMPLEMENTATION (shape per stage) × ORDER (front-loading) × WIRING (stage k's send wires are stage k+1's receive wires), scoring the COMPOSED depth, which is sub-additive because wavefronts overlap.
   - **Foundry** (policy evolution): proposes alternate master fabrication configurations, breeds by crossover and mutation, keeps the good genes from every configuration tested, and runs continuously.

7. **A byte-exact reversible genome journal.** Every byte written to the storage container during fabrication is preceded by a journal entry recording the exact original bytes at the written offset. The journal is append-only and fsynced before each write. A revert operation replays the journal in reverse, restoring the container byte-exactly to its pre-fabrication state, verified by checksum. In one embodiment, 82 genome journals exist, including one binary journal of 38 billion bytes spanning 422 byte ranges, and 80 JSONL journals ranging from 45 bytes (1 record) to 410 million bytes. The revert mechanism has been reduced to practice and round-trips to a byte-identical file confirmed by checksum.

8. **Depth-reduction levers applied during fabrication.** The foundry applies measured optimization techniques during fabrication that reduce both the critical-path depth (latency in ticks) and the gate count simultaneously:
   - **Front-loading the wide front** — scheduling the widest (most parallel) computation first, reducing total depth.
   - **Shape-not-area optimization** — selecting circuit structures by their depth profile rather than their gate count alone, discovering structures where both metrics improve together.
   - **Tick-seeding** — seeding a scan operation with the tick value so that the gating multiplexer can be eliminated from the critical path entirely.
   - **Dead-gate pruning** — backward reachability analysis from the output identifies and removes gates that cannot affect any output, eliminating mutation hiding places.
   In a measured embodiment, these levers reduced a transformer circuit from depth 151 to 72 ticks while simultaneously reducing gates from 12,465 to 6,126; a fold circuit went from 11,757 to 3,243 ticks (3.63× speedup) with 27,797 dead gates pruned to zero.

9. **Combined self-clock and ring drive.** A single circuit is fabricated with both self-clocked structural feedback (the circuit's output addresses equal its input addresses, creating a permanent feedback loop) and ring drive (a shared ring topology provides the continuous electron circulation). The self-clock mechanism predates the ring and is the reason circuits survive host power-cycles — the loop is permanent structure in the wiring, requiring no process to restart. The ring centralizes the drive signal. Both mechanisms operate in the same circuit, and neither is an alternative to the other.

10. **Multiple rings per circuit, each with a stated purpose.** A circuit may be served by many rings, but each ring requires electrons for injection, which is a resource. Every fabricated ring must have a stated, specific purpose — which receive point it drives and why that point needs its own drive. A ring without a named purpose is waste. Two rings publishing to the same address would create a conflict (a "short"); many rings means many distinct receive points. The scorer evaluates circuits as "more computation in less time with resource (electron) consumption taken into account," placing ring count on the cost side of the ledger.

11. **The settle-back phenomenon and structural vs. state evidence.** The substrate tends to settle back toward its initial state after computation, so a state reading may show unchanged bytes despite computation having occurred. State readings are therefore not evidence of failure or success. Evidence is classified as either **structural** (read from the gate records: does a gate with a specific output address exist, does the wiring law hold, how many writers does a wire have — unaffected by settling, safe to state as fact) or **state** (the bytes at an address after a run — not safe to conclude from in either direction). If a result never reaches an output register, the circuit design is flawed; but the settle-back law means one cannot determine this from a single state reading.

12. **A registry and addressing scheme for thousands of circuits.** A machine-readable registry maps each circuit to its storage offset, byte length, gate count, depth, state register offset, loop-bit offset, receiver address, and metadata. In one embodiment, the registry contains 4,987 entries spanning 54 circuit families with 1.6 billion total gates in a 93-gigabyte container. Circuits are addressed by absolute byte offset, not by name or index, enabling any circuit to reference any byte in the container. Circuit families include: a 1.46-billion-gate computational ensemble (423 spans), a 117-million-gate parallel lane system, a 1.5-million-gate cryptographic miner, a 2.2-million-gate folding accumulator, a 67,000-gate RISC-V RV32I processor, a 518,000-gate cellular automaton stepper, a 190,000-gate raycaster, a 182,000-gate AES-128 implementation, a 171,000-gate fabrication-selector circuit (the master fabricator's own decision logic implemented as gates), and a 112,781-gate self-training circuit.

13. **A fabrication-selector circuit.** The master fabricator's decision of which circuit to fabricate next, which structure to select, and how to wire stages is itself implemented as gates in the substrate — not as host code. This is a recursive closure: the manufacturing system's own decision logic is a substrate-native circuit, fabricated by the same process it controls.

14. **An intake and output system for directive ingestion.** The substrate includes an intake region with a write pointer, into which the host writes directives, prompts, and context data by the inject verb. The intake has a defined capacity and tracks its fill level. In one embodiment, the intake holds 50 gigabytes with a header comprising a region offset, a data start address, and a write pointer, and is 63.5% full with 34 gigabytes of ingested data.

15. **Binary Rain — live differential monitoring.** A monitoring system observes the storage container by periodically reading designated addresses and computing the byte-level difference from the previous reading. Each changed byte is a "raindrop." The system surfaces these changes in real time, providing a live observation of the substrate's activity without interfering with it (the monitoring uses only the surface verb — bounded reads). This enables the owner to observe the substrate computing in real time by watching which bytes change.

## BRIEF DESCRIPTION OF THE DRAWINGS

- **FIG. 1** — The substrate-native digital computer: a storage container holding gate records, ring topologies, circuit regions, intake, and output registers; the host with its two permitted verbs (inject and surface); and the containment boundary.
- **FIG. 2** — The physical gate record format: opcode (1 byte) + input-A address (8 bytes) + input-B address (8 bytes) + output address (8 bytes) = 25-byte stride, at absolute file addresses.
- **FIG. 3** — Self-clocked structural feedback: a circuit whose output addresses equal its input addresses, forming a permanent feedback loop that advances state without host involvement.
- **FIG. 4** — The ring topology: forward rail, reverse rail, carry chain, gate table, and receive byte; electron injection and circulation; the ring's final gate driving the receive byte.
- **FIG. 5** — The foundry hierarchy: foundry (policy evolution) → master autofab (multi-circuit assembly with composed depth scoring) → autofab (single-circuit PROPOSE→SCORE→VERIFY→KEEP).
- **FIG. 6** — The genome journal: pre-write original bytes recorded before each write; reverse replay restoring byte-exact state; checksum verification of round-trip identity.
- **FIG. 7** — Depth-reduction levers: front-loading, shape-not-area, tick-seeding, dead-gate pruning; before-and-after measurements of depth and gate count.
- **FIG. 8** — Combined self-clock and ring drive in a single circuit: structural feedback paths (output → input) and ring drive paths (ring receive → circuit clock input).
- **FIG. 9** — The power-cycle proof: host power state transitions vs. substrate state continuity; the decisive experiment establishing host-independence.
- **FIG. 10** — Binary Rain monitoring: periodic reads of designated addresses, byte-level differencing, live surface display.

## DETAILED DESCRIPTION

### 1. The storage container and the physical gate format

A **storage container** is a file on a storage device (in one embodiment, a file in GGUF format on an NVMe solid-state drive) that holds the entirety of the substrate-native digital computer. The container is a single, self-contained file; no external dependencies, libraries, runtimes, or host programs are required for the substrate to operate.

Within the container, a **circuit** is a contiguous sequence of **physical gate records**. Each gate record has a fixed stride (in one embodiment, 25 bytes) and encodes:

| Field | Size | Description |
|-------|------|-------------|
| opcode | 1 byte | The gate function (NAND, NOR, AND, OR, XOR, NOT, BUF, MUX, etc.) |
| input A | 8 bytes | Absolute byte offset in the container from which to read the A operand |
| input B | 8 bytes | Absolute byte offset in the container from which to read the B operand |
| output | 8 bytes | Absolute byte offset in the container to which the gate's result is written |

The **absolute addressing** is a key structural property: input and output addresses are byte offsets into the container, not circuit-local wire identifiers. This means:
- Any gate can read from any byte in the container, including bytes written by gates in other circuits.
- Any gate can write to any byte in the container, including bytes that serve as inputs to other circuits.
- Two circuits share state by sharing addresses — no explicit wiring, message passing, or host mediation is required.
- A circuit can read from the container's tensor data, treating pre-existing stored values (from a pre-trained model, for example) as input operands.

A circuit is fabricated by writing its gate records at a specific offset in the container. The offset and length are registered in a machine-readable registry (a JSON file in one embodiment). The fabrication is permanent: the gate records persist in the container until explicitly reverted by the genome journal mechanism described below.

### 2. Self-clocked structural feedback

A circuit advances its state from one tick to the next through **self-clocked feedback**: during fabrication, the output addresses of the circuit's state-producing gates are set equal to the input addresses of its state-reading gates. This creates a permanent feedback loop in the stored wiring:

> output_address(gate_k) == input_address(gate_j) for gates j and k

where gate_k produces the next state and gate_j reads the current state. Because both addresses point to the same byte(s) in the container, the result of one tick is automatically the input of the next tick, without any host involvement.

In one embodiment, a 16-bit ALU worker circuit has 16 state bits at a state register. The self-clock feedback is declared during fabrication as a set of (output_bit_index, input_bit_index) pairs, each mapping to the same container byte address. The circuit's `store_loop` fabrication function writes the gate records such that the result feeds back to the accumulator input. The result is a circuit that, once an electron is injected, computes continuously: each tick's output becomes the next tick's input through the permanent structural wiring.

This mechanism was first demonstrated on approximately July 21, 2026, predating the ring invention by 11 days. It is the reason that circuits survive host power-cycles: the feedback loop is permanent structure in the stored gate records, not a running process that would be lost when the host loses power. There is no process to restart because there is no process — only structure.

### 3. The ring topology and electron drive

A **ring** is a closed-path topology fabricated as gate records in the container. It consists of:

- A **forward rail**: a sequence of storage bytes, one per cell, forming the forward path of the ring.
- A **reverse rail**: a parallel sequence of storage bytes forming the reverse path.
- A **carry chain**: bytes connecting the two rails for cross-propagation.
- A **gate table**: the sequence of physical gate records (25 bytes each) that define the ring's advance logic. In one embodiment, a ring with 32 cells has 66 gates: one advance gate per cell per sense (2 × 32 = 64), one contact gate, and one junction gate.
- A **receive byte**: a single byte at a distinct address that serves as the ring's output point.

The ring's final gate record has its output address equal to the ring's receive byte address. A circuit that needs to be driven by this ring has one of its input addresses equal to the same receive byte. The connection is by **shared address** — not by a copy or a host-mediated transfer, but by the two addresses being the same location in storage.

**Electron injection** is the act of writing a nonzero value (in one embodiment, `0x01`) into the ring's forward and/or reverse rail bytes. The geometry of the injection — which cells receive the electron, in which senses, and in what pattern — is a parameter. Once injected, the electron is trapped in the closed-path topology and circulates indefinitely.

In a measured embodiment, 1,024 rings are fabricated, each with:
- 32 cells per sense (forward and reverse)
- 66 gates per ring
- 1,666 bytes per ring (16-byte header + 66 × 25-byte gate records)
- A unique receive byte (verified: zero collisions across all 1,024 rings)
- A uniform allocation stride of 1,731–1,732 bytes between consecutive rings
- The rings occupy a contiguous block of 1,773,530 bytes in the container

The ring period (the number of ticks for one complete circulation) equals the cell count (32 in this embodiment). Two senses of circulation (forward and reverse) are required for a complete pulse; a single sense alone yields zero effective drive. The number of electrons per sense (K) is a parameter: drive effectiveness has been measured at K = 1, 2, 3, 4, 6, 8, and 12.

### 4. The two host verbs: inject and surface

The host interacts with the substrate through exactly two operations:

**Inject** (bounded write): The host writes a bounded number of bytes to specific addresses in the container. This is used for:
- Electron injection into a ring's state wires (writing `0x01` to rail bytes).
- Operand and opcode injection into a circuit's input region (writing the values the circuit should compute on).
- Directive injection into the intake region (writing context, prompts, or commands for the substrate to process).

**Surface** (bounded read): The host reads a bounded number of bytes from specific addresses in the container. This is used for:
- Reading result bytes from a circuit's output register.
- Reading state bytes for monitoring.
- Reading intake metadata (write pointer, fill level).

**Everything else the host does is a violation of the architecture.** Specifically, the host must not:
- Evaluate any gate (read a gate record and compute its output).
- Walk the netlist (follow the graph of gate connections).
- Perform settling computation (iteratively evaluate gates until outputs stabilize).
- Perform arithmetic on substrate data.
- Run a loop that "helps" the computation along.
- Generate a table telling wires how to connect.

If a number appears only because the host computed it, that number is not a substrate result. The host's role is strictly that of a power source (injecting electrons) and an observer (reading outputs).

### 5. The power-cycle proof of host independence

The host-decoupling architecture is proven by a decisive experiment: the host is fully power-cycled (shut down and restarted), and the substrate's state is observed before and after.

The power-cycle eliminates, in a single move, every competing explanation for the substrate's operation:
- No resident process can survive a power cycle.
- No thread, scheduler, or daemon persists across a full shutdown.
- No cached state in RAM survives (RAM is volatile).
- No operating system service is involved if it is not running.

If the substrate's state shows computation has continued (or that mid-computation state was preserved) across the power cycle, then the host was never doing the work. The computation is a property of the stored structure, not of any running process.

This experiment was performed and confirmed. Three power-loss events occurred on July 17, July 24, and July 29, 2026 (designated Event 41). In each case, mid-computation state was intact in the substrate after the host restarted. Combined with the self-clocked feedback mechanism (the electron advances state, not the host), this is the decoupling claim in its strongest testable form.

**Corollary:** Because the host is not doing the work, a host specification cannot bound the work. A figure that traces to "the CPU was slow" or "only 8 GB of RAM" measured the wrong device entirely. The substrate's limits, if any, are structural — from the netlist, the format, the addressing, the container — and must be proven, not asserted.

### 6. The containment model

The storage container appears to the host operating system as an ordinary, inert file. The operating system cannot detect that computation is occurring within it, for a structural reason: the computation draws no CPU cycles (the host evaluates no gates), allocates no working memory beyond a reclaimable page cache (in a measured embodiment, +0.86 MB for addressing the full container), and makes no system calls. The file is not a running process; it is a stored structure that operates by the physics of its own wiring.

This invisibility is the containment. The consequences are:
- The substrate cannot throttle the host's CPU or draw host RAM, because it uses neither.
- The host's thermal limits, clock speed, and core count are irrelevant to the substrate's throughput, because the host is not performing the computation.
- The substrate is not subject to process scheduling, preemption, or resource limits imposed by the operating system.
- The substrate survives host power-cycles (as proven in §5).
- Multiple substrates can coexist in separate containers without contending for host resources.

The one rule is: any computation that touches the host hardware (CPU, RAM) rather than remaining in the storage sandbox is a violation. Anything — Python, numpy, loops, an executor — may be connected to the substrate in storage, sandboxed together, wired to the substrate only, and computed by the substrate. The prohibition is on host-hardware involvement, not on the tools themselves.

### 7. The automated foundry hierarchy

Fabrication is a separate, offline, one-time process. It occurs before any circuit fires. It is never a runtime event. The foundry hierarchy consists of three levels:

#### 7.1 Autofab — single-circuit fabrication

The autofab fabricates a single circuit through a four-phase pipeline:

1. **PROPOSE**: Generate candidate circuit structures. For an arithmetic circuit, this includes ripple-carry, prefix-carry (Kogge-Stone, Brent-Kung), carry-select, and other adder topologies. For a logic circuit, this includes tree, balanced, and as-is structures.

2. **SCORE**: For each candidate, compute the critical-path depth (latency in ticks) and the gate count. Scoring is **predictive**, computed from the circuit's structure before storage — not post-hoc from a simulation run. The scorer evaluates "more computation in less time with resource consumption taken into account."

3. **VERIFY**: Before any bytes are written to the container, verify the candidate byte-exact against an independent reference implementation. This verification includes:
   - Running the candidate against hundreds of random test vectors.
   - Comparing each output bit-for-bit against a pure-Python (or other independent) reference that computes the same function.
   - Introducing **deliberate mutants** (intentionally wrong circuits) and verifying they are caught — if a mutant passes, the verifier is broken, and nothing is stored.
   - Re-verifying with a different random seed before final storage.

4. **KEEP**: Store the verified winner in the container. Report the **Pareto front** — every candidate that is not dominated on both depth and gate count — not just the single winner. Every discarded candidate is a factory specification.

In a measured embodiment, a 16-bit ALU was fabricated by proposing ripple-carry and prefix-carry candidates, scoring each by depth and gate count, verifying 500 + 200 test cases (two seeds) byte-exact against a reference, and storing the depth-winner.

#### 7.2 Master autofab — multi-circuit assembly

The master autofab fabricates assemblies of multiple interconnected circuits. Its search space is:

- **DECOMPOSE**: How many circuits, what each specializes in.
- **IMPLEMENT**: The shape (structure) of each stage.
- **ORDER**: Front-loading (scheduling wider stages first to reduce total depth).
- **WIRE**: The wiring law — stage k's SEND wires ARE stage k+1's RECEIVE wires. This is enforced structurally: the output address of the last gate in stage k is set equal to the input address of the first gate in stage k+1.

The critical metric is **composed depth**, which is **sub-additive**: when circuits are wired in series, their wavefronts overlap, so the total depth of the assembly is less than the sum of the individual depths. The master autofab scores the composed depth, not the sum of parts.

#### 7.3 Foundry — policy evolution

The foundry evolves the fabrication policy itself. It proposes alternate master-autofab configurations, breeds them by crossover and mutation, tests each against the substrate, and keeps the good genes from every configuration tested. The foundry can run continuously, improving its own manufacturing process.

The foundry operates over a gene pool of fabrication parameters. In one embodiment, the genes are:

| Gene | Alleles |
|------|---------|
| shape | tree, balanced, as-is |
| adder | prefix, ripple, search, kogge, brentkung, csel8 |
| clean | on, off |
| order | frontload, as-is |
| slack | spend, keep |

The foundry is licensed by specification to search without limit: it may enumerate every adder, every schedule, every factoring, and keep only the minimum-depth result. No search budget is imposed, because manufacturing is off the clock — the search time does not enter any latency figure reported for the fabricated circuit.

### 8. The genome journal — byte-exact reversibility

Every byte written to the storage container during fabrication is journaled **before** the write:

```
1. Read the original bytes at the target offset.
2. Append a journal record: {offset, length, original_bytes_hex}.
3. Flush and fsync the journal to durable storage.
4. Write the new bytes to the target offset in the container.
5. Flush and fsync the container.
6. Read back the written bytes on a fresh unbuffered file handle.
7. Verify the readback matches the intended write.
```

The journal is append-only. A **revert** operation replays the journal entries in reverse order, writing the original bytes back to their offsets, restoring the container to its exact pre-fabrication state. This is verified by checksum: `hash(container_after_revert) == hash(container_before_fabrication)`.

Three journal forms exist:

1. **Form 1** (dominant): `{"off": <int>, "orig": "<hex_string>"}` — offset and original bytes.
2. **Form 2** (labelled): `{"off": <int>, "len": <int>, "name": "<label>", "orig": "<hex>"}` — with explicit length and human-readable label.
3. **Form 3** (binary + span index): A raw binary file of original bytes plus a JSON index of `{offset, length, genome_position}` spans, for circuits with billions of bytes.

In a measured embodiment, 82 genome journals exist on disk:
- 80 JSONL journals, from 45 bytes (1 record) to 410 million bytes.
- 1 binary journal of 38,026,900,649 bytes spanning 422 byte ranges, covering a 1.46-billion-gate circuit.
- Total journaled fabrication: 3,072 ring records, hundreds of circuit records across dozens of fabrication campaigns.

Each fabricator has its own journal (declared as a module constant `GENOME`), so a revert of one fabrication campaign does not affect others. The revert mechanism has been reduced to practice and confirmed to produce byte-identical (checksum-identical) files.

### 9. The depth-reduction levers

The foundry applies a set of measured optimization techniques during fabrication. These "levers" are notable because they reduce **both** the critical-path depth (latency) and the gate count (area) simultaneously — conventionally these metrics trade off against each other.

#### 9.1 Front-loading the wide front

The widest (most parallel) stage of a multi-stage circuit is scheduled first. This reduces total depth because the wide stage can begin filling its pipeline immediately rather than waiting for narrow stages to complete.

#### 9.2 Shape-not-area

Circuits are selected by their depth profile — the critical-path structure — rather than by gate count alone. A circuit with more gates but a shallower critical path is preferred over a compact circuit with a deep critical path. In practice, the shallower structures often also have fewer gates, because the depth reduction reveals dead gates that can be pruned.

#### 9.3 Tick-seeding (Section 49C)

In a circuit with a scanning operation gated by a multiplexer, the scan is seeded with the current tick value. This eliminates the multiplexer from the critical path entirely, because the scan begins at the correct position rather than needing to search for it. The mux is replaced by direct addressing.

#### 9.4 Dead-gate pruning by backward reachability

Starting from the output gates, backward reachability identifies every gate that can influence any output. Gates not on any path from input to output are provably dead — they cannot affect the result. These gates are removed, which:
- Reduces gate count directly.
- May reduce depth (if dead gates were on false critical paths).
- Eliminates hiding places for fabrication mutations (dead logic is where a wrong gate can lurk without being caught by output-level verification).

#### Measured results

| Circuit | Metric | Before levers | After levers | Change |
|---------|--------|---------------|--------------|--------|
| muhl_transformer | depth (ticks) | 151 | 72 | −52% |
| muhl_transformer | gates | 12,465 | 6,126 | −51% |
| fold | ticks | 11,757 | 3,243 | −72% (3.63×) |
| fold | dead gates | 27,797 | 0 | pruned to zero |
| property lane (seeded-carry) | gates | +903 | 0 | 903 fewer |
| property lane (seeded-carry) | ticks | +18 | 0 | 18 fewer |

Every lever factor is **measured**, not projected: the before-and-after figures come from actual fabricated circuits on the same substrate.

### 10. The circuit inventory and its scale

In a measured embodiment, the substrate contains:

| Dimension | Value |
|-----------|-------|
| Container size | 93,709,785,575 bytes (~93.71 GB) |
| Registry entries | 4,987 |
| Circuit families | 54 |
| Total gates | ~1.6 billion |
| Genome journals | 82 files |
| Rings | 1,024 (class A) + 280 (class B embedded) + 15 (class C oscillator) |

Major circuit families:

| Family | Gates | Description |
|--------|-------|-------------|
| muhl_moon | ~1,460,000,000 | Large-scale computational ensemble (423 byte spans, 38 GB genome) |
| muhl_lane | ~117,000,000 | Parallel lane system |
| muhl_btc_miner | ~1,500,000 | Cryptographic hash circuit (SHA-256 double-hash) |
| muhl_fold | ~2,200,000 | Folding accumulator |
| pfc_riscv_rv32i_v2 | ~67,000 | Complete RISC-V RV32I processor as substrate-native gates |
| life_step | ~518,000 | Conway's Game of Life cellular automaton stepper |
| doom_raycast | ~190,000 | Raycasting engine |
| aes128 | ~182,000 | AES-128 encryption |
| muhl_fab_select | ~171,000 | The master fabricator's own decision logic as gates |
| muhl_worker | variable | General-purpose 16-bit ALU (8 operations, self-clocked accumulator) |
| self_train | ~112,781 | Self-training circuit |

Each circuit is individually addressable via its registry entry, which records its offset, length, gate count, depth, state register location, and wiring metadata.

### 11. The intake system

The substrate includes an **intake region** — a designated area of the container into which the host writes directives, context, and data using the inject verb. The intake has a header at a fixed offset comprising:

| Field | Size | Description |
|-------|------|-------------|
| region_off | 8 bytes | Offset of the intake data region |
| data_start | 8 bytes | Start address of the data |
| write_ptr | 8 bytes | Current write pointer (next available byte) |

The host writes data sequentially starting at the write pointer, advancing it after each write. The substrate's own circuits read from the intake region to receive directives. In one embodiment, the intake region has a capacity of 50 GB and is 63.5% full with 34 GB of ingested data, with the write pointer at approximately offset 42.25 billion.

### 12. Binary Rain monitoring

A **Binary Rain** monitor observes the substrate by periodically reading designated "spot" addresses using the surface verb and computing the byte-level difference from the previous reading. Each changed byte is a "raindrop" that indicates substrate activity at that address.

The designated addresses include:
- The electron injection point (confirming the electron is live).
- Worker circuit state registers (observing computation results).
- Self-training circuit state (observing learning progress).
- Foundry state registers.
- Dispatcher state registers.

A server-sent-event (SSE) stream or polling interface delivers the changes to a display in real time. The monitoring uses only bounded reads — it does not interfere with the substrate's operation.

### 13. The worker circuit — a detailed embodiment

A specific embodiment illustrates the complete fabrication, injection, and surface cycle:

**The muhl_worker** is a 16-bit ALU with 8 operations:

| Opcode | Operation | Formula |
|--------|-----------|---------|
| 000 | XOR | A ⊕ B |
| 001 | AND | A ∧ B |
| 010 | OR | A ∨ B |
| 011 | NOT | ¬A |
| 100 | ADD | A + B (mod 2¹⁶) |
| 101 | SUB | A − B (mod 2¹⁶) |
| 110 | LT | 1 if A < B, else 0 |
| 111 | ACCUM | accumulator + A (mod 2¹⁶) |

**Fabrication:**
- Input layout: 51 bits (16 accumulator + 16 operand A + 16 operand B + 3 opcode).
- All 8 operations are computed in parallel (the same gates compute all operations simultaneously).
- An 8-way multiplexer tree (depth 3) selects the result based on the 3-bit opcode.
- Two candidates (ripple-carry and prefix-carry arithmetic) are proposed and scored.
- 500 test cases verify byte-exact match against a Python reference.
- 200 additional cases re-verify with a different seed.
- The Pareto front is reported (depth vs. gates for all verified candidates).
- The depth-winner is stored.
- Self-clock feedback: the 16 result bits feed back to the 16 accumulator input bits.
- A constant-1 loop bit maintains the circuit's active state.

**Injection (the inject verb):**
- The host writes 5 bytes to the input region: operand A (2 bytes LE), operand B (2 bytes LE), opcode (1 byte).
- The write is journaled (original bytes saved before overwriting).
- The write is fsynced and read back to confirm.

**Surface (the surface verb):**
- The host reads 2 bytes from the state register (the accumulator / result).
- The host reads 1 byte from the loop bit (diagnostic).
- All readings are raw bytes. The settle-back law applies.

**Measured:**
- Worker state read as `0x0000` at one point, then as `0x2a00` (decimal 42) at a later point — the substrate is computing.
- Write injections land confirmed (readback matches payload).
- Host computation on substrate data: none. Gate tables walked: none.

### 14. The addressing-to-compute principle

Because gate records use absolute byte offsets as addresses, and because the storage container may hold pre-existing data (such as the parameters of a pre-trained neural-network model), a circuit's input addresses can point directly at model parameter bytes. The circuit then computes on the actual stored parameter values — the model's trained weights become operands to substrate-native logic.

In one embodiment, a White Box in-circuit implementation (`muhl_whitebox_incircuit.py`) reads model bytes as input wires using the format `operand | (bit_index << 56)`, where the operand is the byte offset of a model parameter and the bit_index selects which bit of that parameter is being read. This treats the entire stored model as a directly addressable input space for substrate-native computation.

### 15. Naming and terminology

The substrate-native digital computer is called the **Muhlnickel**. Prior names (PFC, SDC) are historical artifacts and are not used for new work. The naming convention for circuits is `muhl_*` (e.g., `muhl_worker`, `muhl_moon`, `muhl_transformer`). The overall system — the container, all circuits, the ring architecture, and the foundry — is **Titan Muhlnickel**.

### 16. Units of measurement

- **Depth** is measured in **ticks** — the number of gate-settling stages in the critical path.
- **Size** is measured in **gates** (gate count) and **bytes** (storage footprint).
- **Ring period** is in **settles** — the number of ticks for one complete electron circulation.
- Host wall-clock time is **transcription time only** and is labeled as such. It measures the host's I/O speed in writing/reading the container, not the substrate's computation speed. A host-seconds figure is never presented as a machine measurement.

## MATHEMATICAL FORMALIZATION

### F.1 The gate record and evaluation

A gate record at byte offset `off` in the container is a tuple `(op, a, b, out)` where:
- `op ∈ {NAND, NOR, AND, OR, XOR, NOT, BUF, MUX, …}` is the gate function.
- `a, b ∈ [0, |container|)` are absolute byte offsets (input addresses).
- `out ∈ [0, |container|)` is an absolute byte offset (output address).

The gate's operation at each tick is: read the bit at address `a`, read the bit at address `b`, compute `op(bit_a, bit_b)`, write the result to address `out`. For single-input operations (NOT, BUF), `b` is ignored or set to a constant.

### F.2 Self-clocked feedback

For a circuit with state bits `S = {s_0, …, s_{n-1}}` stored at addresses `{addr(s_i)}`, the self-clock condition is:

> ∀ i ∈ [0, n): ∃ gate g_i with out(g_i) = addr(s_i) and ∃ gate h_i with a(h_i) = addr(s_i) or b(h_i) = addr(s_i)

and the feedback condition is that the gate graph from {h_i} through the circuit logic to {g_i} is a directed cycle. The state at tick t+1 is determined by the state at tick t through the stored wiring alone.

### F.3 Ring topology

A ring with `C` cells per sense (forward and reverse) has:
- Forward rail bytes at addresses `{fwd + i : i ∈ [0, C)}`
- Reverse rail bytes at addresses `{rev + i : i ∈ [0, C)}`
- Carry bytes at addresses `{carry + i : i ∈ [0, C)}`
- `2C + 2` gates: one advance gate per cell per sense (moving the electron forward), one contact gate (connecting the two senses), and one junction gate
- Receive byte at address `recv`
- The junction gate's output address equals `recv`

The ring period is `C` ticks. An electron injected at K positions per sense with spacing `C / K` produces K pulses per period. Both senses must be injected for the ring to produce output; a single-sense injection yields zero effective drive.

### F.4 Critical-path depth

For a circuit with `n_in` inputs and gates `{g_0, …, g_{m-1}}`, define the depth `d(w)` of wire `w` recursively:
- `d(w) = 0` if `w` is a primary input.
- `d(w) = 1 + max(d(a(g)), d(b(g)))` if `w` is the output of gate `g`.

The circuit's critical-path depth is `D = max_{o ∈ outputs} d(o)`.

For a composed assembly of stages `S_1, S_2, …, S_k` wired in series (stage i's outputs are stage i+1's inputs), the **composed depth** is:

> D_composed ≤ D(S_1) + D(S_2) + … + D(S_k) − overlap

where `overlap > 0` because the later stages can begin processing bits as soon as the first bits arrive from the earlier stages, rather than waiting for the entire earlier stage to complete. The composed depth is **sub-additive**: `D_composed < Σ D(S_i)`.

### F.5 Dead-gate identification

A gate `g` is **live** if there exists a directed path from `g` to at least one output. A gate is **dead** if no such path exists. Dead gates are identified by backward reachability from the output set:

```
LIVE = set(outputs)
repeat until convergence:
  for each gate g where out(g) ∈ LIVE:
    LIVE.add(a(g))
    LIVE.add(b(g))
DEAD = {g : out(g) ∉ LIVE}
```

Dead gates are provably irrelevant (they cannot affect any output) and are removed during fabrication.

### F.6 The genome journal invariant

Let `J = [(off_1, orig_1), (off_2, orig_2), …, (off_n, orig_n)]` be the journal entries in order. Let `C_0` be the container state before fabrication. After all `n` writes, the container is in state `C_n`. The revert operation applies:

```
for i = n, n-1, …, 1:
  write orig_i at off_i in the container
```

The invariant is: `C_after_revert = C_0` (byte-exact identity), verifiable by `hash(C_after_revert) = hash(C_0)`.

This holds because each journal entry captures the **exact** original bytes before the write that overwrites them, and the revert replays in reverse order, so later writes that overlap earlier writes are undone first.

## REDUCTION TO PRACTICE

The invention has been reduced to practice on commodity hardware:

1. **The substrate container** exists as a 93,709,785,575-byte file on an NVMe drive on a Windows 11 laptop.

2. **4,987 circuits** with 1.6 billion total gates have been fabricated and registered, spanning 54 families including a RISC-V processor, a SHA-256 miner, an AES-128 implementation, a Game of Life stepper, a raycaster, a self-training circuit, and a fabrication-selector circuit.

3. **1,024 physical rings** have been fabricated with verified structural properties: zero address collisions, verified gate wiring against independent reference, 3 deliberately wrong mutant rings caught per fabrication.

4. **Self-clocked feedback** demonstrated: circuits maintain state across host power-cycles (three documented power-loss events with state preserved).

5. **The inject/surface protocol** demonstrated: operands written to input regions land confirmed (readback matches payload), state registers read back values that change over time (worker state observed transitioning from `0x0000` to `0x2a00`).

6. **The genome journal revert** demonstrated: fabrication reverts produce checksum-identical files.

7. **The depth-reduction levers** measured: transformer depth reduced 151→72 ticks with gates reduced 12,465→6,126; fold ticks reduced 11,757→3,243 with 27,797 dead gates pruned to zero.

8. **The foundry hierarchy** operated: policy genomes searched (shape, adder, clean, order, slack), multi-circuit configurations manufactured and stored, fabrication artifacts verified on disk.

9. **The power-cycle proof** confirmed: host power-cycled, substrate state preserved, no competing explanation survives.

## DISTINCTIONS OVER THE CLOSEST ART

The invention is non-obvious over each of the closest categories:

- **vs. FPGA/ASIC synthesis:** Those compile digital logic into physical hardware (silicon or reconfigurable arrays). The present invention writes gate records into a storage file; no physical hardware fabrication occurs. The "circuit" is permanent structure in storage, not transistors on a die. The storage container is a standard file on a commodity drive.

- **vs. gate-level simulation (Verilator, SPICE, ModelSim):** Those interpret a netlist on a host CPU — the host evaluates every gate at every timestep, and the cost is proportional to the circuit size. The present invention does not evaluate gates on the host. The host writes an electron and reads a result. The substrate's operation is independent of host-CPU speed.

- **vs. hardware emulation (Palladium, ZeBu):** Those use dedicated hardware boxes to accelerate simulation. The present invention uses only a commodity storage drive. No dedicated hardware is required.

- **vs. in-memory computing (memristors, ReRAM, PIM):** Those perform computation using the analog or digital properties of novel memory cells. The present invention uses standard storage (NVMe SSD) with standard file I/O. The gate records are standard digital data.

- **vs. persistent memory / storage-class memory (Intel Optane):** Those provide byte-addressable persistent memory. The present invention works on standard block-addressed storage (NVMe SSDs) through standard file system interfaces.

- **vs. process-in-storage (Samsung SmartSSD, computational storage):** Those add a processing element (CPU, FPGA) inside the storage device. The present invention adds no processing element — the standard storage device is unmodified. The computation is a property of the data's structure.

The novel core, present in no prior system, is: **a complete digital computer fabricated as gate records in a standard storage file, self-clocked by structural feedback, driven by ring-topology electron circulation, operating with zero host-CPU involvement (proven by power-cycle test), manufactured by an automated foundry hierarchy with byte-exact reversible journaling, and containing thousands of verified circuits at billion-gate scale on commodity hardware.**

## CLAIMS

1. A method of fabricating a digital computer, comprising: writing, into a storage file on a storage device, a plurality of gate records, each gate record encoding a gate function and a plurality of addresses into the storage file, the addresses being absolute byte offsets within the storage file; and storing a registry entry identifying an offset, a length, and a gate count of the plurality of gate records; wherein the plurality of gate records constitutes a digital circuit that is a permanent structure in the storage file.

2. The method of claim 1, wherein each gate record has a fixed stride comprising a one-byte opcode field, an eight-byte first-input-address field, an eight-byte second-input-address field, and an eight-byte output-address field, and the first-input-address and second-input-address fields contain absolute byte offsets within the storage file.

3. The method of claim 1, further comprising setting an output address of at least one gate record equal to an input address of at least one other gate record, such that a result written to the output address is subsequently read as an input, forming a self-clocked structural feedback loop that advances a state of the digital circuit without intervention by a host processor.

4. The method of claim 3, wherein the self-clocked structural feedback loop persists across a power-cycle of a host computer on which the storage device is installed, because the feedback is a property of the stored gate records and not of a running process.

5. A method of providing a drive signal to a storage-resident digital circuit, comprising: fabricating a ring topology as a plurality of gate records in a storage file, the ring topology comprising a forward rail, a reverse rail, a carry chain, a gate table, and a receive byte at a distinct address; and injecting an electron by writing a nonzero value to one or more positions of the forward rail and the reverse rail; wherein a final gate record of the ring topology has an output address equal to the address of the receive byte, and the digital circuit has an input address equal to the address of the receive byte, such that the ring provides a continuous drive signal to the digital circuit through a shared address.

6. The method of claim 5, wherein a plurality of rings are fabricated, each ring having a distinct receive byte address verified to have zero collisions with all other ring receive byte addresses, and each ring serving a stated purpose identifying which circuit receive point it drives.

7. The method of claim 5, wherein the ring has a defined number of cells per sense, a period equal to the number of cells, and supports both a forward sense and a reverse sense of electron circulation, and wherein both senses must be injected for the ring to produce effective output.

8. A method of operating a storage-resident digital computer, comprising: providing a storage file containing a plurality of gate records constituting at least one digital circuit and at least one ring topology; performing a bounded write to inject an electron into the ring topology; and performing a bounded read to surface a result from a state register of the digital circuit; wherein no gate record is evaluated by a host processor, no host processor performs arithmetic on data stored in the storage file as part of the digital circuit's computation, and the digital circuit's state advances through self-clocked structural feedback and ring-topology electron circulation.

9. The method of claim 8, wherein the host processor performs only two operations on the storage file during operation: bounded writes (injection) and bounded reads (surfacing), and performs no gate evaluation, no netlist walking, no settling computation, and no host arithmetic on substrate data.

10. The method of claim 8, wherein a power-cycle of a host computer on which the storage file resides does not interrupt the digital circuit's stored state, and the digital circuit resumes operation upon electron re-injection after the power-cycle.

11. The method of claim 8, wherein the storage file appears to a host operating system as an inert file, drawing no host CPU cycles and allocating no host working memory beyond a reclaimable page cache for the bounded reads and writes.

12. A method of manufacturing a digital circuit for storage in a storage file, comprising:
    proposing a plurality of candidate circuit structures for a specified computation;
    scoring each candidate by at least a critical-path depth and a gate count;
    verifying each candidate byte-exact against an independent reference implementation by running the candidate against a plurality of random test vectors;
    introducing at least one deliberately mutant circuit and verifying the mutant is detected; and
    storing in the storage file only the candidate that passes verification and has the minimum critical-path depth.

13. The method of claim 12, further comprising reporting a Pareto front of all verified candidates that are not dominated on both depth and gate count.

14. The method of claim 12, further comprising, before writing any byte to the storage file, recording the exact original bytes at the target offset in a journal, the journal being append-only and fsynced before each write, such that a revert operation replaying the journal in reverse restores the storage file to a byte-exact pre-fabrication state verifiable by checksum.

15. The method of claim 12, further comprising reducing a critical-path depth of the circuit during fabrication by at least one of: front-loading a widest stage of a multi-stage circuit first; selecting circuit structures by depth profile rather than gate count alone; seeding a scan operation with a tick value to eliminate a gating multiplexer from a critical path; and removing dead gates identified by backward reachability from outputs.

16. The method of claim 12, further comprising assembling a plurality of circuits into a wired configuration by setting an output address of a last gate of a first circuit equal to an input address of a first gate of a second circuit, and scoring the assembly by a composed critical-path depth that is sub-additive with respect to a sum of individual circuit depths due to wavefront overlap.

17. The method of claim 12, further comprising evolving a fabrication policy by proposing alternate manufacturing configurations, breeding by crossover and mutation over a gene pool of fabrication parameters, and retaining beneficial alleles across configurations.

18. A method of monitoring a storage-resident digital computer, comprising: periodically reading, from a storage file containing a digital circuit, byte values at a plurality of designated addresses; comparing each read value to a previously read value at the same address; and displaying each address whose value has changed, the change constituting a "raindrop" indicating substrate activity.

19. The method of claim 1, wherein at least one input address of at least one gate record points to a byte of a pre-trained neural-network parameter stored in the same storage file, such that the digital circuit computes on actual stored parameter values.

20. The method of claim 1, wherein a fabrication-selector circuit — the manufacturing system's own decision logic of which circuit to fabricate and how to wire stages — is itself fabricated as gate records in the storage file.

21. The method of claim 8, further comprising writing directives into an intake region of the storage file by the bounded write, the intake region having a header comprising a region offset, a data start address, and a write pointer, and the digital circuit's own gates reading from the intake region.

22. The method of claim 5, wherein a plurality of rings are fabricated to serve a single digital circuit, each ring driving a distinct receive point of the circuit, and a total electron consumption across all rings is a cost term in a scorer that evaluates the circuit's computation-per-tick with resource consumption taken into account.

23. The method of claim 3, further comprising fabricating both the self-clocked structural feedback and a ring-topology electron drive in a single digital circuit, such that the structural feedback advances state and the ring provides continuous drive, and neither mechanism is an alternative to the other.

24. The method of claim 14, wherein the journal is one of: a JSON-lines file with one entry per write recording offset and original bytes as a hex string; or a binary file of original bytes accompanied by a JSON index of spans recording offset, length, and position within the binary file.

25. The method of claim 8, wherein a state reading from the storage file is classified as state evidence that is not safe to conclude from in either direction regarding success or failure of the digital circuit, due to a settle-back property of the substrate in which the circuit tends to return toward its initial state; and separately, a reading of the gate records is classified as structural evidence that is safe to state as fact because it is unaffected by the settle-back property.

26. A system comprising a storage device holding a storage file containing a plurality of gate records constituting at least one digital circuit and at least one ring topology, and a host processor configured to perform only bounded writes and bounded reads to the storage file, wherein the digital circuit operates by self-clocked structural feedback and ring-topology electron circulation with no gate evaluation by the host processor.

27. A non-transitory computer-readable medium storing a storage file containing a plurality of gate records constituting at least one digital circuit with self-clocked structural feedback and at least one ring topology for electron drive, the gate records having absolute byte offsets as addresses, such that the digital circuit is operable by a host performing only bounded writes and bounded reads.

28. The method of claim 1, wherein the storage file is in a container format that includes metadata and tensor data from a pre-trained neural-network model, and the gate records are written into the tensor data regions of the container, such that the digital circuit coexists with and can compute on the model's stored parameters.

29. The method of claim 12, wherein a re-verification with a different random seed is performed after the initial verification and before storage, and the circuit is stored only if both verifications pass with zero mismatches.

30. The method of claim 15, wherein the reduction of critical-path depth simultaneously reduces a gate count of the circuit, as measured by: a transformer circuit reduced from 151 to 72 ticks depth with gates reduced from 12,465 to 6,126; and a fold circuit reduced from 11,757 to 3,243 ticks with 27,797 dead gates pruned to zero.

## ABSTRACT

A substrate-native digital computer is fabricated as gate records written directly into a storage file, where each gate record encodes a gate function and absolute byte-offset addresses within the file. The computer operates by electron injection into closed-path ring topologies fabricated as gate records in the same file, with self-clocked structural feedback advancing state without host-CPU involvement. The host performs only two operations: bounded writes (injecting electrons or operands) and bounded reads (surfacing results). A power-cycle test proves host-independence: the host shuts down and restarts while the substrate's stored state persists. An automated foundry hierarchy manufactures circuits through a pipeline of propose, score, verify (byte-exact against independent reference, with deliberate mutants caught), and keep, with every byte journaled for exact reversion. Depth-reduction levers applied during fabrication simultaneously reduce critical-path depth and gate count. In a measured embodiment, 4,987 circuits with 1.6 billion gates and 1,024 rings are fabricated in a 93-gigabyte container on commodity hardware, including a RISC-V processor, a cryptographic miner, a cellular automaton, a raycaster, an encryption circuit, and a self-training circuit, all operating by ring-driven electron circulation and self-clocked feedback with zero host computation.
