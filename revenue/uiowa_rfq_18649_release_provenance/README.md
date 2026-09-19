# Release provenance and integrity assessment kit

UIOWA-057 · operation `uiowa-057-release-provenance-p57b-20260919` · ZZ-KESTREL-P57B

This is a working offline interview and artifact-review aid. It traces a supplied deployment record through the exact artifact digest, producing build, recorded inputs, source repository and revision, and approval evidence. It diagnoses missing links separately from contradictory records. Every included example is **fictional**; none describes the University of Iowa or a live service.

## Run the complete rehearsal

Python 3.10 or later; standard library only. Run from this directory:

```sh
python provenance.py fixtures.json --case complete --artifact-root . --format markdown
python provenance.py fixtures.json --case missing-build --format markdown
python provenance.py fixtures.json --case digest-mismatch --format json
python provenance.py --schema
python -m unittest -v test_provenance.py
```

The complete case returns exit **0**, `LINKED_RECORDS`, and a full `d1 → a1 → b1 → s1` trace. It also hashes the actual supplied `demo-artifact.txt` when `--artifact-root .` is present. The missing-build case returns exit **1**, `GAPS`, and exactly identifies `deployments/d1.build_id`. The mismatch case returns exit **1**, `CONTRADICTORY_RECORDS`, identifying `deployments/d1.artifact_digest`. Invalid JSON, malformed records, duplicate record IDs and unreadable packet files return exit **2** with a diagnostic on standard error and no fabricated report.

Exit 0 means the assessed record links agree under this model. It is **not** a release approval or an authenticity verdict. Without `--artifact-root`, no artifact bytes are read and the report says `NOT_REQUESTED`. With it, individual byte-check results still determine whether the requested inspection succeeded.

## Included deliverables

| File | Purpose |
|---|---|
| `provenance.py` | Importable inspector and command-line JSON/Markdown renderer |
| `packet.schema.json` | Versioned record contract, generated from the inspector's schema |
| `fixtures.json` | Complete, missing-build, and conflicting-digest packets |
| `synthetic-records.md` | Fictional source evidence with section locators |
| `demo-artifact.txt` | Exact non-executable bytes used by the complete rehearsal |
| `interview-worksheet.md` | Evidence matrix, questions, interpretation and practical improvement options |
| `make_fixtures.py` | Deterministic fixture/schema regeneration |
| `test_provenance.py` | Standalone regression and command-line suite |

Regenerate the fixture and schema files with `python make_fixtures.py`; this intentionally overwrites only the three generated files in this kit. Tests check that generated and checked-in forms agree. It never modifies an assessment packet.

## Record contract and adapter rules

Root fields are `schema_version=1`, `packet_id`, `data_class`, and the five arrays `evidence`, `sources`, `builds`, `artifacts`, `deployments`. All fields declared in the schema are required. An unavailable nullable field is explicitly `null`, not an empty string, fabricated digest, guessed timestamp, or copied value from another record. An absent referenced record may remain absent and produces a recoverable gap. Missing structural fields or unknown fields are errors so adapter mistakes do not silently disappear.

Record IDs are unique within each array. Deployments reference one artifact; artifacts reference one build attempt; builds reference one source revision. Different attempts and releases must use distinct IDs even when their labels match. Shared inputs and evidence may be referenced across chains. A source record includes both the intended revision and the revision that the approval record actually identifies. A build records its observed repository/revision; the inspector compares both independently, not just the commit hash.

SHA-256 values use 64 lowercase hexadecimal characters. Source revisions accept full 40- or 64-character lowercase Git object identifiers; short display hashes are not sufficient. Timestamps include seconds and an explicit UTC offset. Comparisons normalize offsets. Builds may precede source approval, but approval must not postdate the recorded deployment. Timestamp disagreements are questions about records and clocks, not allegations.

`input_coverage=declared_complete` is a producer statement, **not independently established completeness**. Each material records an input URI and digest; partial/unknown/empty inventories remain gaps. A repeated input URI is ambiguous in this schema: include the resolved role/version in the URI rather than overwriting another input. Recipe digest and builder identity are retained but not checked against a root of trust. Version labels and digests are compared independently; a label disagreement needs reconciliation even when bytes match.

Evidence locators are opaque metadata, not fetched or executed. The inspector checks that referenced evidence rows exist, records their type, and requires owner-role/capture-time metadata. It does **not** open or validate locator contents. Interview evidence without artifact corroboration remains UNKNOWN. Synthetic evidence cannot support an `assessment` packet. An interviewer must inspect the actual source and locator separately before using a record as a finding.

Only chains reachable from supplied deployments receive semantic assessment. Unused rows undergo structural validation but do not become implied findings about all applications or all releases. Empty deployment collections are never a pass. Each trace identifies its range in the report's `checks` array. Aggregate status preserves any contradiction, then any unknown; there is no average, maturity score, confidence score, or employee ranking.

## Local bytes and operational boundaries

The optional artifact root selects a directory of already supplied copies. Only contained relative paths are read; absolute paths, parent traversal, backslashes and symlinks resolving outside that root are not inspected. Inputs and artifacts are never executed, downloaded, rewritten or deployed. Hashing is streamed. Inspect stable copied artifacts; a concurrently modified file is not a transactional snapshot.

The CLI accepts at most 4 MiB of JSON and rejects duplicate JSON keys and non-finite constants. These are format safeguards, not a general hostile-file sandbox. Prefer a disposable analysis environment for unfamiliar material. Output is written to standard output only; the caller chooses whether to redirect it into a report. Preserve real institutional evidence within its established handling arrangements. This public kit includes no private records or credentials.

## Assessment use, not a new release mechanism

1. Ask the service owner for one ordinary release and one exception/recovery example. Record the sample boundary and why these examples were selected.
2. Copy metadata into the contract while retaining original evidence locators. Use `null` and absent links where evidence is genuinely unavailable.
3. Inspect records; optionally hash an already supplied artifact. Review every UNKNOWN/MISMATCH with the worksheet rather than interpreting the exit code as a verdict on the team.
4. Preserve a supported strength, the exact unresolved link, the service consequence, and the next evidence request. Re-run after a corrected export as a new packet version; retain the original.

This is an assessment-native schema, **not an in-toto statement, SLSA attestation parser, signing system, policy enforcement mechanism, or deployment gate**. It does not verify signatures, builder trust, approval authority, live environment state, transitive dependency completeness, source-code behavior, or any SLSA level. Consistent fictional or forged inputs can look internally linked; a mismatch alone does not establish compromise.

## Reference basis

The distinction between build provenance and source provenance informs the separate build/source records. See the approved [SLSA 1.2 provenance overview](https://slsa.dev/spec/v1.2/provenance), reviewed 2026-09-19. This kit's approval and deployment interview fields are an assessment design choice, not a claim that SLSA prescribes this exact schema.

SLSA's [artifact-verification guidance](https://slsa.dev/spec/v1.2/verifying-artifacts) describes artifact-digest binding, signature verification, trusted builders and comparison with expected build parameters. Those additional authenticity checks explain why this metadata-consistency inspector expressly does **not** call its output SLSA verification. No compliance or procurement recommendation follows from these references.
