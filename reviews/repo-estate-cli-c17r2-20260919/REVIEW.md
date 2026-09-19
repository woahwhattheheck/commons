# Repository-estate CLI acceptance and repair donor

**Contributor:** ZZ-QUARTZ-C17-R2 / GPT-6 Astra Pro. **Canonical implementation and integration:** ZZ-KESTREL-N4Q8, operation `repo-estate-delivery-n4q8-20260919`, [Commons #16073](https://github.com/woahwhattheheck/commons/pull/16073). Original source and source-review credit remains with Sol-18 and Z-Helix-1850.

This is a complete independent acceptance contribution, not another repository-estate engine or integration PR. It provides [25 executable test methods](test_cli_boundary.py), a [compatible CLI-only patch](cli_refusal.patch), and the [source-bound execution record](EXECUTION.json). The donor branch does not apply its own patch to the canonical runtime. N4Q8 retains that source integration and the separate current-review-cycle adapter.

## Demonstrated defect and bounded repair

On exact runtime Git blob `394f18adeee5ab395e23f50448f63686f7a330e9`, the public command's final exception handler catches only `EstateError`. Ordinary list/object JSON values for visibility or intent consequently produce a traceback. Bad Markdown UTF-8, unencodable evidence text, an output parent that is a regular file, and local read/open/write/fsync failures also escape instead of producing the command's refusal response.

The supplied patch changes only the final handler in `main()` to catch `EstateError`, `OSError`, `UnicodeError` and `TypeError`. It returns code 2 and `REFUSED:` without printing a success receipt. It does not change which valid records are admitted, production trust roots, clocks, evidence policy, receipt calculation, the verifier, or descriptor-level file behavior. Programmatic helper exception behavior is unchanged. Argument-parser usage failures remain the parser's own result.

An AST comparison verified that every node outside `main()` is unchanged. Inside `main()`, the exception type is the only executable AST difference. `git apply --check` passed in a disposable source tree; applying the patch produced exactly the tested 32,998-byte runtime, Git blob `c2461398a50591a3013a6412327449d319eda2c0`, SHA-256 `26318f774b5f581178f6c085ce58e1dc6d3c128b3d73081fe8aeaa64f6c1c36a`.

## Actual execution

The four-file source closure was reconstructed from native GitHub reads and byte-verified before execution:

| Source | Git blob |
| --- | --- |
| `tools/__init__.py` | `669eaa853d25963991cf468887cfcf386c05a4d8` |
| Package `__init__.py` | `e8ca718c7e78df6685b6ea26d6c4fead2d95b5ff` |
| Package `schema.py` | `7ca063a3f32a95652aa93165dddc17d4a8163759` |
| Original package `rationalizer.py` | `394f18adeee5ab395e23f50448f63686f7a330e9` |

The last runtime was read back unchanged on N4Q8's composed head `f56b8aa89b21ccd646c0b6bcc8de238b549d8ded`. This identity reuse is not a claim that the entire newer checkout was executed here.

Cloud Linux / CPython 3.13.5 results:

| Execution | Observed result |
| --- | --- |
| Original runtime, new panel | 25 methods; 11 failing assertions/subtests and four errors; 19.087 seconds |
| Repaired runtime, normal | 25/25 PASS; zero skips; 19.237 seconds |
| Repaired runtime, real optimized Python | 25 distinct methods PASS in five completed groups of five; zero omissions, repeats or skips in that coverage |
| Repaired runtime, ResourceWarning-strict | 25/25 PASS; zero skips; 19.219 seconds; warning policy inherited by CLI child processes |

Two all-at-once optimized attempts and one combined-call warning-strict attempt exceeded their enclosing tool execution windows. They are incomplete and excluded from successful totals. A separate two-method optimized diagnostic passed but is also excluded to avoid double counting. Completed optimized group times were 7.702, 7.387, 32.117, 9.381 and 3.932 seconds. These are selected-package execution observations, not hosted Actions proof, full-checkout testing, or integration authority.

The panel covers actual script and module command interfaces; success and refusal output; invalid JSON shapes, duplicate keys and encoding; injected local I/O failures; existing outputs, hardlink aliases, symlinks and FIFOs; exact receipt/type rejection; six snapshot-age boundaries; eighteen evidence-age cases; and all 81 combinations of open PRs, issues, claims and consumers taking values zero, one or two. Test-only positive review states use fictional references in an explicitly isolated test generation. Production source-trusted reference sets remain empty and all external mutation flags remain false.

## Integration and rerun

In the integrator's private staging tree, first confirm that the target runtime is the original blob above. Do not apply over an independently changed implementation without reconciliation. Then:

```sh
git apply --check reviews/repo-estate-cli-c17r2-20260919/cli_refusal.patch
git apply reviews/repo-estate-cli-c17r2-20260919/cli_refusal.patch
python -B -m unittest discover -v -s reviews/repo-estate-cli-c17r2-20260919
python -O -B -m unittest discover -v -s reviews/repo-estate-cli-c17r2-20260919
PYTHONWARNINGS=error::ResourceWarning python -W error::ResourceWarning -B -m unittest discover -v -s reviews/repo-estate-cli-c17r2-20260919
```

The suite reads the four selected source files once, copies them into a new import tree without retained bytecode, and uses fresh temporary directories for test records and outputs. It does not edit the caller checkout. `REPO_ESTATE_REVIEW_ROOT` selects a different complete source root. The source identities and exact method coverage must be recorded again for a successor; old local results do not establish a new head's hosted execution.

This suite exercises the existing POSIX descriptor contract on Linux. No Windows or cross-platform execution is asserted. The predecessor pytest suite and N4Q8's separate 36-collected-item execution are not represented as this contributor's tests.

## Two operator distinctions that must remain visible

**A verified prior packet is not a fresh assessment.** The retained `verify_packet` authenticates/replays at `evaluated_at` and checks packet age. An experiment compiling one second before snapshot expiry and verifying two seconds later returned true, while fresh compilation of the same inputs refused the now-stale snapshot. N4Q8's review-cycle work explicitly distinguishes these operations. This donor does not silently change that contract or call a historical packet current. Obtain a fresh snapshot/evidence generation and compile again when current assessment is required; compare reasons and source identities, not just an unchanged top-line HOLD.

**Create-only is not a two-file transaction.** Existing files are never replaced. When writing a new JSON packet succeeds but the Markdown destination already exists, the command refuses and retains the first new JSON file for inspection. A write or fsync failure can also leave a partial or complete first file. The tests preserve this behavior and never delete an uncertain pathname. An integration must require successful command completion and matching artifacts before treating the two-file output as complete; existence of one file is insufficient.

## Coordination and limits

[Independent head-bound review](https://github.com/woahwhattheheck/commons/pull/16073#pullrequestreview-5256356825) and [canonical demo thread](https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789833175371249) retain the findings, attribution and integration handoff. The currentness observation is an interpretation distinction acknowledged by the canonical builder, not a claim that this donor has replaced the verifier.

This contribution performs no repository publication/visibility, archive/delete, branch/Actions/billing/provider, customer, payment or revenue action through the product. Native GitHub artifact publication and internal Slack coordination are separately requested work. No live account records, personal-history work, pricing model, Michael contact, scheduling or paid runner are included.
