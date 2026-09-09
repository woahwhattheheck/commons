# Dual-predecessor identity: closures, not score-file inequality

A finite game panel is an observation, not an executable identity. Two distinct
predecessor closures can legitimately produce the same normalized terminal rows
on every measured cell. Conversely, copying one panel and changing whitespace,
JSON key order, or row order changes the raw file digest without executing a
second predecessor.

The custody-bound gate therefore separates two statements:

1. **Execution identity:** predecessor names and both declared and observed
   closure-bundle SHA-256 values must be distinct; each strict receipt binds its
   closure to its contract, provenance evidence, engine, runner, baseline game
   bytes, and the shared candidate.
2. **Measured outcomes:** each baseline panel independently satisfies the
   inherited complete-grid and numeric-closure rules. Its bytes may equal the
   other predecessor panel when the measured outcomes are genuinely identical.

The candidate artifact and candidate panel remain shared exactly across both
comparisons. Candidate/predecessor artifact aliasing remains invalid. This
change removes only the outcome-byte inequality veto; it does not relax closure,
receipt, grid, policy, candidate, or single-gate custody.
