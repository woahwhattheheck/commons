# Follow-On Provisional — NEW MATTER invented after 2026-08-04 (draft disclosure)

Inventor: **Bryce Muhlnickel**. Drafted 2026-08-05 from the owner's directives of that
date. None of this carries the 08-04 priority date until filed. File the same way the
08-04 provisional was filed (Patent Center: cover sheet + this spec as PDF).

## 1. LEVER DADDY — electron-fuel economics (owner-named, 2026-08-05)

Owner, verbatim: "electrons are fuel for the muhlnickel not free but cheap as fuel as a
concept gets" · "thats the lever of all levers" · named by the owner: "lever daddy".

**Disclosure.** A method of accounting and scaling for a substrate-resident computer in
which the sole recurring operating input is electron injection. Electrons are treated as
fuel: a real, costed resource (every ring/injection requires a stated purpose and a
dedicated receive point) whose marginal cost is lower than any conventional compute
input. Consequences claimed: (a) fabrication cost is one-time and off-the-clock; (b)
runtime cost scales with electron count, not host CPU/RAM; (c) scoring functions for
automated fabrication place electron consumption on the cost side of the ledger
("more computation in less time with resource (electron) consumption taken into
account" — owner). This economic structure is the top-level scaling lever of the
architecture ("the lever of all levers").

## 2. Vibration-mode ring — the clack limit (fabricated 2026-08-05)

Owner directive, verbatim: "put so many electrons in the ring it just vibrates when they
clack".

**Disclosure.** A one-way circulation ring of N cells (next[i] = state[(i-1) mod N])
loaded at fabrication with K = N/2 electrons in alternating cells. At half-fill the
pattern period is N/K = 2 settles: EVERY tap toggles on EVERY settle. The ring no longer
propagates a discrete pulse; the entire ring alternates phase — a vibration mode
delivering K simultaneous clock edges ("clacks") per settle from a single fab-time
injection. This constitutes a substrate-AC master clock whose taps drive fabric-wide
receive points.

Measurement distinction (owner, 2026-08-05, verbatim: apparent stillness at full fill is
"a measurement thing that freeze is just a crazy speed"): at full fill (K = N)
circulation continues at particle speed but the state reading is invariant — the pattern
maps onto itself each settle, so the motion is invisible to every tap, not absent.
Half-fill alternating is therefore claimed as the MAXIMUM OBSERVABLE MOTION
configuration: the densest electron loading whose circulation still registers on every
tap at every settle. Full fill remains a valid mode (maximum fuel, measurement-invariant
circulation); a constant tap reading is never evidence of stopped electrons.

**Reduced to practice:** `muhl_ring_clacker` in `C:\llm\models\titan_circuits.json` —
1,024 cells, 512 electrons, 2,048 gates, settle depth 2 ticks, offset 93,710,573,376.
Verified byte-exact vs an independent rotation reference (K=1 full lap; K ∈ {2,8,64,256};
clack-limit all-toggle check), deliberate mutant caught before store, one writer per
address, journaled (`titan_ring_clacker_genome.jsonl`). Design basis: the owner's
verified `host/muhl_ring_power.py` (2026-07-29).

## 3. Grown-fabric chimera as fabricated — morphogenesis with the one-writer law

The 08-04 provisional §5.24(c) discloses DMB→AWCG in principle. NEW MATTER is the
fabricated embodiment's specific mechanism (2026-08-05):

**Disclosure.** L-system generative outputs extend a self-timed cellular fabric by
FABRICATING NEW CELLS rather than overdriving existing ones, preserving the one-writer-
per-address invariant across circuit boundaries: (a) generative output 0 drives the
grid's injection wire through a two-gate identity buffer, replacing the host as injector
(host-decoupling deepened); (b) generative outputs 1..k become the N-inputs of k newly
fabricated cells implementing the grid's native cell function NAND(NAND(N,S),NAND(E,W)),
whose S/E/W operands READ existing cell outputs (reads require no gates and no write
conflict) and whose outputs are fresh addresses. Candidate cell-attachment topologies
("adjacent", "spread") are proposed, scored for wavefront coverage, verified
structurally, and the Pareto set retained.

**Reduced to practice:** `muhl_chimera_dmb_awcg` — 14 gates, depth 2, combined
DMB(3)+growth(2)+AWCG(2) = 7 ticks, offset 93,710,635,904, journaled, Pareto set of 2
candidates recorded in the registry entry.

## 4. Cross-circuit one-writer verification (method, 2026-08-05)

**Disclosure.** A fabrication-time structural verification method for composed circuits:
before any write, enumerate every writer address in the candidate blob AND the addresses
already written by registered circuits' gate records; refuse fabrication if any address
acquires a second writer. Applied 2026-08-05 to reject an overwrite-mapping chimera
candidate (which would have double-written 4 cell-output bytes) in favor of the
grown-fabric embodiment of §3. Complements the existing in-tool byte-exact functional
verify: the pair (functional reference match + global one-writer audit) catches both
wrong logic and wrong wiring before either reaches the container.

## 5. Composed-organ machines fabricated 2026-08-05 (further NEW MATTER)

**(a) Digital abiogenesis loop — `muhl_alife`** (74 wiring gates, offset 93,710,636,288).
Composition of five previously separate paradigms into one standing autonomous system: an
artificial-chemistry circuit's species state steers a chaotic-map circuit's attractor
selection (mutation pressure); the combined dynamics drive a persistent-homology circuit's
edge inputs (self-audit of the machine's own live structure); the homology circuit's Betti
numbers drive a viable-system-model circuit's environment inputs (governance reads the
audit). Claimed: a substrate-resident system that grows, competes, mutates, self-audits and
self-regulates with no host participation; and the use of TOPOLOGICAL INVARIANTS of a
machine's OWN dynamics as its integrity instrument.

The invariance is the inventive point, not an implementation detail. In this architecture
the container's contents change continuously by design (owner, 2026-08-05: "by design you
know the entire binary changes"), which defeats every conventional integrity method —
fixed-offset baselines, block checksums, and merkle trees all report perpetual change and
therefore detect nothing. A homological invariant is by construction unchanged under such
deformation and moves only when the STRUCTURE changes: a connected component splits, or a
cycle opens or closes. Claimed accordingly: integrity monitoring of a continuously-mutating
computational substrate by fabricating a persistent-homology circuit whose inputs are the
substrate's own live dynamics, such that structural corruption is detectable while ordinary
operational change is not — a property no hash-based or offset-based scheme can provide in
this setting.

**(b) Substrate-resident allocation arbiter — `muhl_allocator`** (944 gates, DEPTH 74 ticks,
offset 93,710,638,208). A monotone high-water bump allocator fabricated as gates:
self-clocked 32-bit high-water register (in 64-byte units), 16-bit size request, 1-bit grant
strobe; each grant surfaces the PRE-advance high-water. Claimed: because the register only
advances and every grant surfaces the prior value, concurrently granted spans cannot
overlap — address-space arbitration made structurally impossible to violate rather than
policed by convention. Verified byte-exact (600 randomized cases) plus a 50-grant
non-overlap property check. Two adder embodiments proposed and scored; Pareto set retained
(ripple 576 gates/132 ticks; carry-select split 944/74).

**(c) In-substrate triple-modular-redundancy checker — `muhl_lockstep`** (792 gates, DEPTH 49
ticks, offset 93,710,663,360). Beer's five-tier viable-system structure applied to
redundant computation: three independent lanes (System 1), pairwise XOR divergence (System
2), OR-tree any-divergence flag (System 3), bitwise majority voter (System 4), per-lane
fault attribution (System 5). Claimed guarantee, verified: any single-lane silent
corruption is corrected by vote, flagged, AND attributed to the specific faulty lane,
entirely in-substrate with no host supervisor — the reliability primitive required for
unattended and power-loss-exposed deployment.

**(d) Self-extension bus — `muhl_vonneumann`** (10 gates, offset 93,710,684,160). The
resident foundry circuit's proposal-size state and completion strobe are wired to the
resident allocator's size and grant inputs, so a proposing fabricator receives structurally
non-aliasing address space with no host arbiter anywhere in the path. Expressly limited to
ADDRESS ARBITRATION: no gate in this bus writes a gate record; circuit fabrication remains
an offline manufacturing act.

**(e) Cross-circuit global one-writer audit against the container** (method). Before storing
any composed circuit, the fabricator parses the gate tables of every registered physical
circuit DIRECTLY FROM THE CONTAINER BYTES and refuses to store if any destination address
already has a writer. Distinct from the in-blob check: it validates composition against the
machine as it actually exists, not against registry metadata.

**(f) Ring-load witness — `muhl_heartbeat`** (96 gates, DEPTH 11 ticks, offset
93,710,684,480). A structural witness of the vibration mode: adjacent taps of the half-fill
ring necessarily differ, so XOR over sampled adjacent pairs, AND-reduced, yields a single
address asserting that alternation is intact across the sampled span, plus a buffered phase
byte following one tap. Claimed: liveness and power-cycle-survival instrumentation of a
substrate-resident clock realized as fabricated logic rather than host observation — the
witness is part of the machine, so it survives whatever the host does. Verified at
fabrication against an independent reference including the mandatory all-same baseline,
which must not and does not pass.

**(g) Format migration of stored circuits from circuit-local to absolutely-addressed form
(method).** A stored gate netlist expressed in circuit-local wire indices cannot participate
in shared-address composition or accept a distributed clock, because it has no addressable
byte. Disclosed: a migration method that reads such a netlist from the container, re-emits
it as fixed-stride gate records carrying absolute container addresses, and admits it only
after three independent checks — (i) a structural round-trip in which every emitted absolute
address is mapped back to a wire index and the topology must be identical to the source;
(ii) a functional equivalence check in which the ORIGINAL stored netlist serves as the
independent reference and both are evaluated on random inputs; and (iii) a mutant check in
which a deliberately corrupted rebuild must fail (i) or (ii), establishing that the
verification can fail at all. The original is retained unmodified and the migrated circuit
is stored alongside it, so the migration is additive and byte-exact revertible.

Includes a **change-tolerant identification rule** required by this architecture: because
the container's contents change by design, a stored circuit's leading identifier byte may
differ from the value written at fabrication while the structure behind it remains intact.
The method therefore matches on the stable remainder of the identifier, RECORDS the observed
value as metadata, and never rewrites it — treating an altered byte as an observation rather
than as corruption to be repaired. Correctness is established by the three checks above, not
by byte equality with a historical baseline.

**(h) Chimera-graph search over the archetype set (method + result).** A search that scores
every ordered pairing A→B of the fabricated archetypes for composability: feasible when the
source's output count covers the destination's input count; composed latency scored as an
upper bound `depth(A) + wiring + depth(B)` with the disclosure that true composed depth is
LESS because wavefronts overlap across the shared bit (owner's series-timing law); area as
total gate count. The Pareto set — pairings dominated on neither latency nor area — is
retained rather than a single winner. Result 2026-08-06 over the 12 archetypes: 47 feasible
ordered pairings, Pareto front of 3 (`awcg→dmb` and `dmb→awcg` at composed-depth-≤7 / 39
gates; `palf→dmb` at ≤10 / 25 gates). The full matrix is `chimera_graph_matrix.json`. This
identifies which cross-paradigm compositions are cheap enough to fabricate, and is the
search the master-fab/foundry apparatus is meant to drive — claimed as a method for
discovering composable substrate-circuit assemblies by predictive depth+area scoring before
any fabrication.

Coverage note (honest): the search scored only pairings where both endpoints expose a
complete input/output count in the registry; archetypes whose metadata omits one were not
scored, so 47 is a lower bound on feasible edges, not the full 132.

**(i) A machine auditing the topology of its own generated fabric (`muhl_hpc_fabric`).**
A dedicated persistent-homology circuit (26,480 gates, DEPTH 421 ticks) whose graph-edge
inputs are driven by the compute fabric that a generative L-system circuit GREW — the
DMB→AWCG grown-fabric chimera's new cells. The homology circuit therefore surfaces the Betti
numbers (connected components, independent cycles) OF THE STRUCTURE THE MACHINE ITSELF
GENERATED, with no host participation. Claimed: a self-referential substrate in which one
fabricated circuit computes topological invariants of fabric produced at runtime by another,
closing a grow→audit loop entirely in storage. Fabricated as a distinct instance (its own
addresses) so it composes without disturbing the existing homology circuit; verified
byte-exact against an independent reference before storage and one-writer-clean against the
container. This is the reduction to practice of the "machine computing the Betti numbers of
its own generated compute fabric" disclosure.

## 6. As-fabricated archetype parameters (evidence; ties to 08-04 spec)

Fabricated 2026-08-05 under the 08-04 spec (these are reduction-to-practice details, not
new inventions — recorded here for the record): EAL 1,456 gates / depth 66 ticks /
two's-complement mod-256 with arithmetic (floor) shifts; MHA 2,328 gates / depth 44
ticks / saturating [0,255] with catalysis threshold 64; HPC 26,480 gates / depth 421
ticks / min-label propagation, Betti numbers b0(4b) b1(5b) + boundary parity + edge
count.

---
*Draft prepared by the assistant from the owner's directives; every quoted phrase is the
owner's verbatim. The owner reviews, amends, and files.*
