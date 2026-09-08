# Native scientific reader and sprint-reference composition

This completes the existing PR10224 delivery without replacing the newer
sprint-reference consumer. The original PORT native-checker repair and its
source-specific native/saved-screen evidence remain unchanged.

## Exact composition

The initial PR head was `fd1aa2905c01cca3b97858cdc8200a51cb6eafa0`.
Current-main source at `8425964c5adebf331cf0432f0b41564090ff62a1` was
`compare_checker.py` blob `040fb71148d17be96da50322c0635d4916f16469`.
It was still exact at publication intake
`3f1ee2866f21cb73988de5a82863b7f818aeb333`.

The composition applies only PORT's existing native-scientific condition to
that current file. Every other existing function, including all sprint parsing,
comparison and CLI functions, is AST-identical. The composed reader is blob
`6d6812e1e3d682103f90efa0b817c867555d74a7`, 13,802 bytes, SHA256
`a402a0166b1e52c95dd181e15b8a124504ac78ddea7e815944c754569b323cb8`.

The current source manifest retains all unrelated current entries exactly,
updates only the composed reader identity, and adds the original scientific
reader delivery files plus this integration note and its new tests. Original
native validation JSON, compressed evidence, guide and test bytes are retained;
their narrower historical source identities are not relabeled.

A subsequent manifest reconciliation consumes main
`7d883bf94a1b7afa83bb9ed472db30e618d28236`, retaining its 35 unrelated rows,
including newer supervisor, solver and benchmark identities and finite-load
entries. The tested reader and both test files stay unchanged.

## Executed joined checks

21 methods pass on the composition: PORT's unchanged 11 `ReaderSerialization`
methods plus 10 new `SprintScientificComposition` methods. The same combined
suite on the current-main predecessor reports two failed assertions and eleven
subtest errors. The original official checker's four native test methods are
not rerun or included in this 21-method count. No solver, official checker,
public benchmark, existing saved-screen comparison or qualification action runs.

The new checks use explicitly constructed CSV fixtures and JSON numeric tokens.
They show that the exact value `9.933579335793359e-7` reaches the existing sprint
comparison without rounding or conversion to zero, while the CSV's independent
six-decimal format and source digest checks remain unchanged. Folder selection,
instance labels, invalid outputs, vector lengths and cost-independent ordering
remain covered. A real CLI subprocess checks stdout/output-file correspondence.
Constructed references are test data, not the official CSV or competitive scores.

```sh
python3 -B -m unittest -v \
  test_checker_serialization.ReaderSerialization \
  test_sprint_scientific_composition
```

DELTA-BYTES supplied the conflict composition and these joined checks. PORT
retains the original repair/native execution, and the sprint-reference author
retains that consumer. Normal two-parent composition and main readback are
recorded on PR10224. This is source integration, not a change to any solver,
benchmark, workflow, submission package, S139 draft or attachment.
