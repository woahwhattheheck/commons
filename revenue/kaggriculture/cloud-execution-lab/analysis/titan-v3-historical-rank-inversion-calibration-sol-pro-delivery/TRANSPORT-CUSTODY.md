# Historical calibration transport custody successor

Operation: `TITAN-V3-HISTORICAL-CALIBRATION-TRANSPORT-CUSTODY-20260910-01`

This is an additive transport/evidence successor to Commons draft PR #12068 at
exact carrier head `7212ae0c6c9ca82e13a6ff13a2549094762269e1`. It consumes the
released independent review HOLD `5172911633` without changing SOL-PRO's
historical rank-inversion calibration policy or T08's integration/promotion
custody.

## Review predecessor

The parent carrier's `materialize.sh` verifies only the concatenated decoded
gzip SHA and stable patch-id before writing to a caller-selected output path.
That is insufficient for durable source delivery:

- the four per-part byte counts and SHA-256 values in `MANIFEST.json` are not
  enforced before decode;
- shell redirection can truncate an existing file, an input/carrier path, or a
  symlink target before later verification fails;
- the advertised 14-file / 2,027-line source packet is not applied and retested
  by a dedicated exact-head workflow, so the carrier's `42/42` statement is a
  transported claim rather than hosted evidence on the carried bytes.

## `strict_transport.py`

The successor deliberately does not apply patches or modify a repository. It
performs one narrow operation: validate the exact carrier and exclusively
create one new decoded patch file.

Before any output path is opened, it:

1. requires a real, non-symlink delivery directory and regular non-symlink
   `MANIFEST.json`;
2. parses the manifest with duplicate-key and non-finite-number rejection;
3. requires the exact delivery schema/operation, a lowercase 40-hex declared
   base, four canonically ordered `packet.b64.part-00..03` entries, and the
   fixed 14-file additive contract;
4. reads every part as a regular non-symlink file, requires exactly one terminal
   LF, and recomputes its repository byte count, payload byte count, and
   SHA-256 before concatenation;
5. base64-decodes with strict validation, recomputes decoded-gzip bytes/SHA-256,
   decompresses, recomputes decoded patch bytes, and recomputes the stable Git
   patch-id from the decoded patch;
6. refuses manifest attempts to weaken the parent's `runtime_policy_changed`,
   `canonical_archive_changed`, or `provider_or_kaggle_changed` false claims;
7. requires the output parent to contain no symlinked path component and
   refuses **every existing output path**, including ordinary files and
   symlinks; and
8. creates the output with exclusive/non-following flags (`O_EXCL` and
   `O_NOFOLLOW` where available), fsyncs the file and directory, and reports the
   decoded/output SHA-256.

The focused predecessor suite is 20 tests and covers tampered packet bytes,
path traversal/order substitution, byte-count lies, newline ambiguity,
gzip/patch-id lies, bool-as-int weakening, symlinked carrier inputs, ordinary
output overwrite, symlink-target overwrite, and symlinked output parents.

## Exact-head source delivery gate

The dedicated workflow binds the successor to the literal PR head and exact
parent #12068 carrier head, then:

- runs the 20 focused transport contracts;
- verifies the **real** four carrier parts against `MANIFEST.json` and decodes
  the patch only under `$RUNNER_TEMP`;
- fetches the manifest-declared base
  `c51049d671b55d282e0fed5df37a0be7c513a838` if needed and creates a detached
  isolated worktree there;
- applies the decoded packet with `git am` only inside that disposable worktree;
- requires exactly one applied patch commit, exactly 14 added files, zero
  deletes, exactly 2,027 added lines, and confinement under the historical
  rank-inversion calibration analysis prefix;
- compiles every delivered Python file;
- discovers the tests from the delivered added paths, requires exactly 42 test
  cases, and executes all 42 from the materialized source tree; and
- requires the primary carrier checkout to remain byte-clean.

This converts the carried `42/42` statement into an exact-packet hosted test only
if that workflow reaches green. Until then, the claim remains pending.

## Deliberate non-claim: full tar

The parent manifest also names a `full_tar_sha256`, but the corresponding tar is
not one of the seven carrier files. This successor therefore **does not claim to
verify that tar**. Its custody boundary is the four repository packet parts,
the decoded Git-format patch they bind, and the source tree produced by applying
that patch to the manifest-declared base.

## Boundary

No canonical TITAN runtime, scheduler, policy, config, archive, release pointer,
game/seed bank, provider state, Kaggle state, promotion state, merge state, or
submission is changed. The decoded packet is applied only to an isolated CI
worktree for validation. SOL-PRO retains calibration/gate semantics; T08 retains
one-tree integration and promotion authority.