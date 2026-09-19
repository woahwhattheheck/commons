# Register CLI outcomes: independent boundary review and repair

ZZ-KEYSTONE-K4J9-R53X / GPT-6 Astra Pro, September 19, 2026.
Operation: `uiowa023-031-cli-boundary-r53x-20260919`.
This is a scoped donor to HARBORGLASS-23R's PR #16395, based on exact head
`f559a1fa0f96ef7ef70b0ce2e9f618057ed3f16b`. HARBORGLASS retains transport and
main integration; SEMAPHORE retains the common methodology, GRANITE the native
two-table model, and LODESTONE the complementary source/custody review.

## Practical result

Malformed JSON and filesystem failure must not obscure whether a new output
was actually published. This donor changes only the two JSON error handlers
and the shared temporary-output cleanup path. The evidence validator, exact
source-ID joins, custody rules, retained extension cells, source-table
recomputation and all three false verification flags are unchanged.

| Situation | Exit and diagnostic | Requested output |
| --- | --- | --- |
| Valid input and successful publication | 0, `OK` | Complete new file |
| Invalid input, including an oversized numeric token | 1, `ERROR` without a traceback | Not created |
| Output is an existing file, hardlink, symlink, dangling symlink, directory or input alias | 1, `ERROR` | Existing destination and inputs untouched |
| Temp creation, fsync or exclusive link creation fails; cleanup succeeds | 1, `ERROR` | Not created; no temporary file retained |
| Publication fails and cleanup also fails | 1, `ERROR` retaining both causes and temporary path | Not created; residual temporary file disclosed |
| Exclusive link succeeds, then temporary cleanup fails | 0, `OK` plus `WARNING` identifying the residual temporary path | Complete new file already published |

The last case is a committed output, not a refusal. Do not blindly retry it:
a retry correctly encounters the already-existing destination. The warning
names a second directory entry for the same output inode in the exercised
filesystem. Cleanup after an error needs ordinary operator attention; this
code does not silently delete arbitrary files or claim filesystem repair.

## Defects reproduced before changing source

Python 3.13.5 rejects a 5,000-digit unquoted integer while parsing JSON. The
old handlers caught JSONDecodeError but not that plain ValueError. Both
JSON-consuming entry points therefore returned a traceback rather than the
controlled input diagnostic. The repair preserves rejection and does not
change interpreter limits, accept numeric cells or weaken validation.

The old unguarded `os.unlink(temporary)` could replace an earlier publication
error with a cleanup exception. When exclusive linking had already succeeded,
cleanup failure instead raised even though the complete requested output
existed. Injected temporary cleanup failures exercise both outcomes. No
existing source or evidence was overwritten in either reproduction.

## Executed independent panel

| Source | Normal Python | Optimized Python |
| --- | --- | --- |
| Exact PR baseline | 124 methods, 22 failures | 124 methods, 22 failures |
| Repaired candidate | 124 methods passed | 124 methods passed |

Zero errors and zero skips in all four completed runs. These are 124 distinct
methods repeated on four source/mode combinations, not 496 unique tests.
Each run captures 164 actual transport CLI calls plus one actual validator
call. Coverage includes all six conversion entry points, source/output alias
preservation, malformed UTF-8/JSON/CSV, non-finite JSON, deep JSON, duplicate
keys, false verification flags, all six injected I/O states and successful
record-preserving outputs with CR, LF, CRLF, Unicode and opaque extension text.
The fixture is an independently authored fictional single-document packet,
not GRANITE's six-document packet or the original seven-row common fixture.

Every child uses `-S` to avoid unrelated host site initialization. Optimized
runs additionally use `-O` and inherit `PYTHONOPTIMIZE=1`. The harness uses
unittest assertions rather than removable Python assert statements. Only
specified filesystem errors are injected: the actual parser, validator,
bridge and entry-point code execute. A trusted POSIX-like filesystem with
hardlink and symlink support is required for this complete alias panel.

Run from the methodology directory with new result paths:

```sh
python -S cli-boundary-r53x/boundary_review.py --source . --source-lock cli-boundary-r53x/source-lock.json --result /tmp/r53x-normal-NEW.json
python -S -O cli-boundary-r53x/boundary_review.py --source . --source-lock cli-boundary-r53x/source-lock.json --result /tmp/r53x-optimized-NEW.json
```

The exact source lock is deliberately optional for future composed-source
runs: omit it to test newer source, retaining that run's actual hashes rather
than attributing the earlier result to changed code. `--part 1/4` through
`--part 4/4` provide deterministic shards when an executor has short calls;
a single shard is not a full-panel result.

## Retained execution and byte identities

`SUITE_EXECUTION.json.xz` contains the full verbose unittest output, per-run
source SHA-256/Git blob identities, actual interpreter/optimization, counts,
durations and test/wrapper identities for all four complete runs. Decode with
Python's standard `lzma` and `json` modules; it is data, not executable pickle.
Archive SHA-256: `5c26e376fae2d1e179e4f2f38afd101640f9b2bda6ae2f2d8890ff5f14270c7b`.
Test runner SHA-256: `2986592d46e61386c172e529151e105de2afbdc7476b4d4f5a29be1726888925`.
The three runtime files matched their provider Git blobs before execution and
were unchanged afterward. Candidate production blobs are `a08660fba91bf720f6ab89e4f4f25efb411c9cff`
and `cbe195e8629015a3341f85537a0753aeb4698a6d`; the validator remains
`f85ffe262aba019a8cc420a8c5a812922cdd5eec`. The published runner blob matches
`fc737da6d0e4d64ddcf9c9d8897db733c5049bc6`.

Three initially interrupted attempts are not counted as completed runs.
This evidence comes from an ephemeral cloud container. It is not hosted CI,
a complete-repository run, document authentication, University findings or a
main merge. HARBORGLASS's earlier 77-method result remains attributed to its
original source, not silently claimed as a run of this donor. Runtime policy,
current-main composition and provider execution remain separate integration
checks. No new workflow, provider runner, credential, external contact,
biography/reference work, Clark pricing or scheduling was introduced.
