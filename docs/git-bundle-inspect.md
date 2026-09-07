# Recover available Git-bundle objects offline

`host/git_bundle_inspect.py` inspects a local bundle using only Python 3.10+
standard-library modules. It neither needs a Git installation nor invokes Git,
network access, hooks, filters, or recovered content. Inspection does not write
files. This complements normal `git bundle verify` / `git fetch`; it does not
replace either operation or validate a complete application build.

## Use

```sh
python3 host/git_bundle_inspect.py /path/to/handoff.bundle
python3 host/git_bundle_inspect.py /path/to/handoff.bundle --extract recovered-objects
python3 -m unittest test_git_bundle_inspect -v
```

The test suite needs Git to independently generate and restore interoperability
fixtures. The runtime inspector does not. An unavailable Git executable skips
those four interoperability tests, rather than reporting them as passes.

`--extract` requires a new directory with an existing parent. It writes raw
payloads as `<object-id>.<type>` plus `manifest.json`. It does not write loose
objects into `.git`, reconstruct working-tree paths, create symlinks, or set
executable permissions. Reference names and tree filenames never become output
paths. An existing destination is refused, not overwritten. Extraction can leave
a partial new directory on an I/O failure; inspect its manifest/results and use
a different new directory for a retry. Keep recovered payloads private when the
source handoff is private.

## Interpret the result

- `recovery_status: partial`: prerequisites, unavailable object links, unresolved
  deltas, or a declared filter remain. Available complete objects can still be
  useful; the unavailable ones were not fabricated.
- `recovery_status: self_contained_objects`: all parsed object links and
  advertised refs resolve inside the recovered set, with no declared prerequisite
  or filter. Gitlinks refer to separate repositories and do not count as missing
  objects in this bundle.
- `restore_verified` is **always false**. Even a self-contained object set is not
  a claim that Git's complete semantic checks, repository restore, or application
  tests have run. Use real Git in the intended repository when the prerequisite
  history is available. The fixture tests separately exercise Git verification,
  clone, and fsck; the inspector never executes them for the user's bundle.

The report includes the whole-bundle SHA-256, verified pack checksum, declared
prerequisites, reference IDs, object inventory, unresolved delta bases/offsets,
and missing links. Pack checksum validation detects accidental corruption; it
is not sender authentication. Compare the bundle SHA-256 with a trusted receipt
when one is available. Object types/sizes are reconstructed and hash-identified,
not inferred from a filename.

## Supported formats and limits

Supported: bundle v2 and v3; SHA-1 and v3 `object-format=sha256`; pack v2 and v3;
commit/tree/blob/tag objects; offset/reference deltas and available delta chains.
Reference deltas may precede their bases. Missing external delta bases are
reported without making an external request. Unknown capabilities are rejected;
`filter` is recorded without pretending the missing filtered objects exist.
Canonical tree modes are checked. This is not an exhaustive substitute for
`git fsck` and does not offer arbitrary historical-format compatibility.

Defaults bound input to 64 MiB, the header to 1 MiB, each packed/result object to
16 MiB, total decoded bytes to 128 MiB, entries to 50,000, delta depth to 64, and
checked object links to 250,000. The aggregate decoded budget includes delta
instruction buffers and reconstructed outputs; it is not a process-RSS promise.
Decompression is chunked and bounded by the declared size. Malformed size fields,
truncated streams/instructions, invalid offsets/opcodes, out-of-range copies,
wrong dependency types, and extra pack data fail explicitly. No silent
unlimited fallback is used. Tune input with `--max-input-bytes`; library callers
can pass a `Limits` instance for other budgets.

## Executed evidence (September 6, 2026, America/Chicago)

Thirty focused tests passed on Python 3.13.5 / Git 2.47.3 in isolated Linux.
Real-Git cases covered a full bundle and actual clone/fsck, an incremental bundle
that cannot verify in an empty repository, actual delta-packed history compared
byte-for-byte with `git cat-file`, and a real SHA-256 repository bundle.
Additional deterministic fixtures cover both delta encodings, forward bases,
missing bases, invalid data, bounded expansion, metadata limits, raw extraction,
and CLI errors. These are local tests, not a claim about repository-wide CI.

The real B1 handoff acceptance was also executed: a 4,012-byte bundle with SHA-256
`f702c6dbaa10cde1d43b212405e27337aa8a205401ed1523b60064affe4d53f7` yielded two
complete objects from eleven pack entries and retained nine unresolved deltas.
The recovered 8,957-byte test blob
`9a19a6feee4dfc37f0894ea7ec044d5e579c5fab` matched the existing receipt SHA-256
`ff32ca5f6f6e6b76745a7969aedef96acdc6aa7abaf8849c0c1d4f80ff885307`.
The result remained partial and did not claim the missing base was restored.
Neither the handoff bytes nor its private working paths are included here.
LATTICE retains App type/Jest/lint execution ownership; this feature does not
change or retest that candidate.

Format references: [Git bundle format](https://git-scm.com/docs/gitformat-bundle)
and [Git pack format](https://git-scm.com/docs/gitformat-pack).
