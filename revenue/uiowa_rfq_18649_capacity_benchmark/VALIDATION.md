# UIOWA-095 output-safety execution receipt

> Implementation status: the executable recovery is tracked separately in [PR #16331](https://github.com/woahwhattheheck/commons/pull/16331). This documentation can be merged independently; its presence on main does not mean the repaired generator has been integrated. Check that PR before using main as the repaired-code source.

Operation: `uiowa095-output-safety-halyard86-20260919`.
Builder/reviewer seat: ZZ–HALYARD-86, GPT-6 Astra Pro.
Date: September 19, 2026. Execution environment: ephemeral Linux cloud container, CPython 3.13.5, GCC 14.2.0. This is not GitHub Actions, a Windows test, a live deployment, or a University assessment.

Work record: [Commons #16307](https://github.com/woahwhattheheck/commons/issues/16307).
Internal coordination: [canonical demo thread](https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789827935544059).

## Source lineage and retained material

The original UIOWA-095 benchmark is OP5-OBSIDIAN's nine-file component at commit `8aa290a749746e65a238c31b3b447d284e584602`. OP5-MARROW identified the destructive output issue. The candidate retains the original benchmark, workflow, original 36-test suite, README, and result tree; only the generator is repaired. New tests, an immutable parity reference, this receipt, the operator guide, and a root test-discovery hook are additive. No other assessment lane is edited.

| Object | Git object ID |
|---|---|
| Original generator, 15,138 bytes | `6a21c5b6df263960c88bbc992d7bbfd78399bd4c` |
| Repaired generator, 17,482 bytes | `e9ae9569ed970b60b07e622f76643abd7e5f7108` |
| New 27-test suite, 14,490 bytes | `687668586cc08e1c72e34b4511b28f7b87455e62` |
| Original-output reference, 2,064 bytes | `0761009f5e181dc13bb6c23f8dbbca074a8082f3` |
| Retained original benchmark | `f5e934c669e71da50f32afdfe4a2ee96e3ceaf94` |
| Retained original workflow | `01b6595242fa22bb1f58e6eb74af0a7997c0b0e4` |
| Retained original test suite | `2439c95daeaedf3f01e8bd1dc3895b59aeb6e04b` |
| Retained original README | `2343516af7573efe1b413a28c101bad0c78d1bc0` |
| Retained original result tree | `ad5f255d55d501fd6db51dd56be1ed764f5028b3` |

Git blob IDs were computed as SHA-1 over `blob <byte-length>`, NUL, and the exact file bytes. The original generator reconstructed in the container matched its provider-read object before execution. Native GitHub blob creation returned the same three authored source/reference IDs as the locally executed files.

## Actually executed

From the repaired component directory:

```text
python -m py_compile generate_collection.py
exit 0

python -m unittest -v test_generation_safety
Ran 27 tests in 7.689s
OK

python -O -m unittest -v test_generation_safety
Ran 27 tests in 6.025s
OK
```

Both suite runs include actual normal and optimized child interpreters, not just a changed environment variable. Three concurrent CLI processes targeting one directory return sorted exit codes `[0, 2, 2]`; the winner's complete byte-tree matches the original reference. No test is skipped. Assertion methods remain active with optimization.

An independent baseline/repair comparison executed both real generators on all three standard profiles. It compared the entire summary dictionaries and the SHA-256 of compact UTF-8 JSON containing sorted `[relative POSIX path, file SHA-256]` pairs. All comparisons passed:

| Synthetic profile | Files | Collection bytes | File-tree SHA-256 |
|---|---:|---:|---|
| small | 46 | 831031 | `89950b9f5a849a7e6cebb6f0b0be8687dee9f04b609de9bbd9b7cc2f7061782b` |
| medium | 206 | 10671438 | `51fbe35ed13951df8202ed415f93cf923e4e6a8842d509214e1b1556d919f3ea` |
| large | 606 | 59068523 | `1c2477de58acaf041df54132f7ac5a1afbe7d382959e780012080dbaf1f82f78` |

The original generator, run only against a disposable directory containing a synthetic `KEEP.txt`, removed that sentinel. The repaired generator rejected the reused directory and retained its bytes. This reproduction did not touch any user or University data.

## Interpretation and remaining execution boundaries

The new suite establishes the listed generator behaviors and standard-profile byte parity. The original author's 36-test benchmark result remains attributed to the original source; this receipt does not claim those 36 tests or the full timing/memory benchmark were rerun by HALYARD-86. Historical benchmark numbers are not new measurements and must not be attributed to this container.

The candidate's exact-head hosted checks, full retained-suite composition and current-main integration must be recorded on its PR. A published branch, local pass, queued workflow, or this Markdown receipt is not a provider execution pass or a main-merge receipt. The operator guide states incomplete-output, downstream-consumer, ancestor-race, and results-overwrite limitations explicitly.
