# L3 rival-gate fail-closed repair proof

This directory is a **package-neutral repair proof** for PR #12448 exact parent `20675ba6358dd51aaec3abdc88ba89ba3ad0ffba`.

It does not modify `overlay/**`, `FILES.json`, `V3-MANIFEST.json`, generated config, or any package artifact on the branch. `repair.patch` is applied only inside the dedicated CI job, tested, and reverted before the job exits. The parent owner can consume the proven source delta and then perform the required deterministic package/manifest rebuild in its own integration mutation.

## Safety theorem

The current #12448 gate fails open: partial, unreadable, or a single divergent public opening sample can return `False`, which the call site interprets as permission to enable the risky L3 late-sale suppression.

The repair changes the classifier contract to:

- L3 remains **OFF** / incumbent E184 remains authoritative unless the complete public opening steps 1..143 are observed contiguously;
- every sampled `step`, `player`, farm cardinality, farmer coordinate shape, and coordinate scalar is strict JSON/Python integer structure with booleans, floats, strings, `None`, gaps, and malformed state rejected;
- exactly 143 valid opening samples are required before OFF_TAPE may be certified;
- the existing `RIVAL_GATE_SHARE = 0.8` threshold is evaluated only at the complete-window boundary;
- once certified, the decision is frozen until rewind/new-game reset;
- incomplete, gapped, malformed, late-start, or otherwise ambiguous evidence is treated as on-tape for this gate, preserving incumbent E184;
- malformed outer `step`/`player` values return the exact parent action rather than arming the L3 wrapper through coercion.

This preserves the parent’s positive complete-observation hypothesis while removing the ambiguity fail-open. It is **not** an economics, package, default-on, merge, or Kaggle claim. After source acceptance, the owner still needs to rebuild exact package metadata and rerun the 41-game confusion/economics receipt, including the three previously negative cells.
