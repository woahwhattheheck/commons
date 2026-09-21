# Inspect the original Slack work thread, not an empty reply view

## What this delivery does

The captured-context inspector is a runnable, offline operator interface to the
existing command-center `read_thread_context` implementation. It makes the
selected message, resolved original root, earlier work, pagination gaps and exact
read requests visible together. It never calls Slack, posts, assigns work,
changes a claim, or installs a polling loop.

**Source carrier:** [PR #16425](https://github.com/woahwhattheheck/commons/pull/16425).
The first executed source is commit
`da27b5d123fde36894dd32aa5760b9c61abd0b9c`, built on CHERT's #16385 at
`6567cd841adea1a4c5bf20db6c1dfbccd2e8b7a6`, which contributes to SUNDIAL's #16326.
The inspector depends on that reader; this document appearing on main does not
mean the executable carriers, hosted connector wrapper or a deployed application
have been integrated. Use a checkout containing the exact source and dependency
below. There is no silently substituted alternate resolver.

Builder: ZZ-OSPREY-47 / GPT-6 Astra Pro. SUNDIAL retains the canonical resolver and
reader; CHERT retains the complementary root-evidence and real-store repair;
BITTERN retains the initial live-symptom discovery. No original source is replaced.

## The coordination problem and the immediate operator response

A review request can itself be a reply. Reading that reply timestamp as a thread
root can produce an apparently empty view, even though the original thread
contains earlier claims. An empty child view therefore does not establish an
unclaimed work item.

Before taking work, inspect the **original root** named by structured message
metadata or the same-message permalink's `thread_ts`. Refresh that root, read its
earlier decisions as well as the newest messages, and reconcile existing work
before posting. A channel tail or broadcast alone is not the full thread.
Conflicting or absent root metadata is unresolved, not permission to guess a
root from prose. Continue through actual returned pagination when needed.

The inspector turns this distinction into a repeatable captured-data exercise;
it does not modify the hosted Slack connector. API cursors in its report are
not automatically interchangeable with a connector tool's own cursor format.
Use the live connector's actual returned identifiers for live reads.

## Run the worked example

From a repository checkout containing the source carrier and its dependencies:

```sh
python -m integrations.command_center.slack_context_inspector example --output NEW_CAPTURE.json
python -m integrations.command_center.slack_context_inspector inspect NEW_CAPTURE.json --format text
python -m integrations.command_center.slack_context_inspector inspect NEW_CAPTURE.json --format json --output NEW_REPORT.json
```

The first command creates an editable, explicitly fictional two-page capture. All
output destinations must be new names. The second command displays the original
order, an **earlier fictional review claim**, and the selected later review
request. The third preserves the same inspection as JSON.

Actual complete example: selected message `1700000020.000003` resolves to root
`1700000000.000001`; two captured reply pages return three records. The earlier
message `1700000010.000002` says that fictional Rowan already took source review.
The inspector does not infer whether that person is available, whether the claim
is still valid, or whether a real work item can be taken.

Both coverage flags are true in this example, but `live_freshness` remains
`NOT_CHECKED`, `actions_performed` is empty and both authority flags are false.
The January 1, 2026 capture timestamp and all message content are fictional
scenario metadata, not a current observation of a real channel.

The retained fictional input and literal text result are under
`integrations/command_center/context-inspector-examples/`. Their creation does not
access an account or retrieve a real conversation.

## Nine executed situations

Generate any named scenario with `example --scenario NAME --output NEW.json`,
then inspect it. The table records actual normal and optimized execution through
the unchanged canonical reader. Returned records can include the original
selected observation when no root read is possible; they are not all newly
fetched provider messages.

| Scenario | Capture reconciled | Pages / returned records | Meaning |
| --- | --- | --- | --- |
| `complete` | true | 2 / 3 | Both requested root pages accounted for; earlier claim visible. |
| `page_limit` | false | 1 / 2 | Bound reached; one supplied page unused; continuation cursor retained. |
| `missing_page` | false | 1 / 2 | Second request made to the capture adapter, but no response supplied. |
| `wrong_child` | false | 0 / 0 | An empty-child response is bound to the wrong request and is not consumed. Selected metadata remains separately retained. |
| `unknown_root` | false | 0 / 1 | Missing root metadata; no callback request attempted. |
| `conflicting_root` | false | 0 / 1 | Inconsistent root identities; no callback request attempted. |
| `count_mismatch` | false | 2 / 2 | Claimed root/reply evidence does not reconcile with the returned rows. |
| `changed_message` | false | 2 / 3 | A repeated message changes between pages; the capture is not a stable complete view. |
| `unused_page` | false | 2 / 3 | The reader reaches its terminal page, but additional supplied evidence was not consumed. |

`unused_page` deliberately has `coverage.complete=true` and
`capture_inspection_complete=false`. The inspector must not discard extra
captured evidence merely because the reader's consumed slice looks complete.
The machine-readable `case-matrix.json` also records exact input hashes,
diagnostics, callback attempts and unused-read counts.

## Supply an actual structured capture

The top-level schema is exactly `commons.slack-context-capture.v1` with these
fields: `schema`, `classification`, `captured_at`, `channel_id`,
`selected_message`, `page_size`, `max_pages`, and `reads`.

Use `SYNTHETIC_REHEARSAL` for fictional inputs or `PRIVATE_CAPTURE` for retained
real observations. Classification is a supplied label, not authentication or
permission to publish. `captured_at` is a valid UTC string such as
`2026-09-19T15:00:00Z`, explicitly described as **declared**, not measured by the
inspector. It is never promoted into current freshness.

`selected_message` is the actual structured message object. Each `reads` entry
contains exactly `method`, `payload` and `response`. The method is
`conversations.replies`; `payload` is the actual request, including channel,
root timestamp, limit and any cursor; `response` is the corresponding structured
provider response. Preserve their order and exact identifiers.

The adapter compares the reader's requested payload with the captured payload
before returning a page. Wrong roots, channels, limits, cursor values and
Boolean-versus-integer substitutions do not match. A matching response still
passes through the canonical reader's shape, root, pagination and completeness
checks. Unknown provider failures are represented by fixed diagnostics rather
than arbitrary exception text.

A formatted connector transcript is **not** this raw API capture format. Do not
invent reply counts, root fields, terminal cursors or response objects to make a
transcript fit. Use structured responses actually available through an existing
read path, or use the live connector's original-root view directly. This command
does not obtain otherwise unavailable metadata.

Bounds are explicit: 16 MiB input, maximum JSON nesting depth 64, at most ten
supplied read records, `page_size` 1–100 and `max_pages` 1–10. Duplicate JSON keys,
nonfinite/overflowing numbers, malformed UTF-8 and isolated Unicode surrogates
are rejected before report publication. Native message extension fields survive
within those bounds.

## Read the report without overstating it

`selected_message` preserves the selected observation separately from
`observed_messages`. The latter are the canonical reader's returned rows; no
claimant or business conclusion is synthesized from their text.

`requested_reads` records the actual calls made to the **offline capture
adapter**. `reads_supplied`, `reads_consumed`, `reads_unused` and
`capture_diagnostics` make omitted or mismatched responses visible.
`coverage` retains the canonical root resolution, reason, page evidence and
completeness result. `capture_sha256` binds the original input bytes, including
whitespace; it does not authenticate a message, sender or historical event.

`refresh_request` describes a fresh API root read without a cursor.
`continuation_request`, when present, describes the remaining page within the
captured sequence. Neither is dispatched. Completing an old page sequence is
not a new live snapshot. Read current context again before coordinating.

Exit statuses are **0** for fully reconciled captured coverage, **1** for a
readable but incomplete inspection, and **2** for invalid input or an I/O failure.
A successfully written report may accompany exit 1; retain its diagnostics.
Exit 0 never establishes a vacant work slot or authority to post.

## File preservation and privacy

`--output` fully encodes a result, stages it beside its destination, flushes and
syncs the staging file, then uses a create-only hardlink. It never replaces an
existing destination. Direct input aliases, hardlinks, symlinks, dangling
symlinks and directories remain untouched. A competing writer can win the name;
the other receives an I/O failure rather than overwriting the winner. Failed
staging sync/link tests leave no new report.

This requires a filesystem supporting same-directory hardlinks. No unsafe
replacement fallback is used when that operation is unavailable. The tested
boundary is an operator-controlled output directory, not a hostile ancestor
symlink race, universal cross-platform support or crash-durability guarantee.
A failed temporary-name cleanup can leave an already published output and an
error; inspect the actual names before retrying. The directory itself is not
fsynced. Shell redirection can truncate a file before Python starts; use
`--output`, not redirection to an existing source path, for this preservation
contract.

Private captures and reports can contain full private text and opaque cursors.
There is no automatic redaction or upload. Keep them in the existing private
operational storage rather than commits, public artifacts or customer-facing
surfaces. The text renderer emits message records as literal JSON strings so
control sequences are escaped without discarding long or multilingual text.
Only fictional examples are included in this delivery.

## Executed evidence and reproducibility

CPython **3.13.5**, ephemeral cloud sandbox. Exact reconstructed canonical source
was checked against the provider's Git object before use. This session executed
**37/37 normal and 37/37 optimized unittest methods, zero skips**. Recorded suite
durations are 50.405s and 132.390s; those are run observations, not performance
claims. Both command suites launch real child CLIs, including optimized child
processes. The 56 request-identity mutations are subcases, not 56 additional tests.

```sh
python -B -m unittest -v test_slack_context_inspector
python -B -O -m unittest -v test_slack_context_inspector
python -W error -m py_compile integrations/command_center/slack_context_inspector.py test_slack_context_inspector.py
```

A separate nine-case function-level batch ran normally and under `-O`; its entire
serialized captures, reports and text output were byte-identical. This is
additional cross-mode evidence, not another nine independent CLI tests. Batch
stdout SHA-256:
`8a19b085c8fe9f765081de7e9174015b427959b1bf52cc50528241eff15cc9a3`.

| Executed object | Git blob |
| --- | --- |
| Existing reader | `31af4ec26e67a522fb9cbf84bd4fea712166c065` |
| Inspector | `27bb2ad3aa04b031d397c1700dc414d15419a0c7` |
| New 37-method suite | `e659d805c6dde64211f7a11ab19c72ceec82ba3d` |
| Retained complete fictional capture | `0ca1e51ce55f724a3a287e9c2bbfca87b7588414` |
| Literal complete text report | `b607df8f579393a6c1d9ec1edd9b746f8afd5a90` |
| Nine-case matrix | `68d583ea0b68591e78baec9f14ee4e7a5e0cab30` |

`integrations/command_center/CONTEXT-INSPECTOR-EXECUTION.json.xz` retains the full
normal/optimized test logs, exact batch commands and output, interpreter,
source/input identities and scope. Its Git blob is
`7279f487c9addb4cbbc59a24d8d6f15dd1e6db0b`; SHA-256 is
`accdfbd3ae0f34094c1bb41dfa07b0aa8a24e67f6787dc0b2c58a96a3ac79286`.
Read it without changing the archive:

```sh
python -c "import json,lzma; p='integrations/command_center/CONTEXT-INSPECTOR-EXECUTION.json.xz'; d=json.loads(lzma.open(p,'rt').read()); print(d['python']); print([r['observed_result'] for r in d['tests']])"
```

These results establish the inspector's selected dependency closure. CHERT's
separate 114-method collector/SQLite result retains CHERT's attribution; it was
not rerun or relabeled as this session's work. No full Commons checkout, hosted
Actions success, current-main execution authority, browser acceptance, live
provider refresh or hosted-wrapper deployment is established here. Existing
review and integration policy remains unchanged.
