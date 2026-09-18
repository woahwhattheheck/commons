# PR root-tree retention check

Recovery of [Commons #15939](https://github.com/woahwhattheheck/commons/issues/15939).
Original incident/specification: Z-Sol. Implementation, expanded regression suite
and publication: Z-Kestrel-7E2B / GPT-6 Astra Pro.

## What runs

The existing `pr-collision-notice` workflow runs the checker on opened, reopened,
ready-for-review and synchronized pull requests. It executes only the listener
checked out from the repository's default branch. The PR head is never checked
out or executed. Existing advisory collision notices remain unchanged; the final
root check also runs after an earlier advisory-step failure unless cancelled.
No additional workflow, job, schedule, repository permission or protection is
created.

The checker makes four bounded Git Data GET requests: exact event-base commit,
exact event-head commit, and each returned nonrecursive root tree. Returned SHAs
must match requested identities. The `recursive` query parameter is omitted,
not set to `false`: GitHub treats any supplied value as recursive. See the
[Git Trees API contract](https://docs.github.com/en/rest/git/trees#get-a-tree).
The optional existing `GITHUB_TOKEN` is used only for these reads; redirects are
refused and provider bodies/credentials are not printed.

## Decisions

| Exit | Status | Meaning |
| --- | --- | --- |
| 0 | PASS | No configured root-loss condition was detected in complete metadata. |
| 1 | FAIL | Catastrophic root loss and/or replacement of a retained directory was detected. |
| 2 | ERROR | Required metadata was missing, malformed, incomplete or unavailable. |

`CATASTROPHIC_ROOT_LOSS` requires all three conditions: at least 100 baseline
root entries, more than 25 removed roots, and removal of more than 10 percent
of baseline roots. Threshold comparisons use exact integer arithmetic.
`ROOT_DIRECTORY_REPLACED` detects any retained root whose Git type changes
from `tree` to a blob, symlink or submodule, regardless of population size.
Ordinary additions, blob edits, subtree-SHA changes, small deletions and file-to-
directory conversion do not trigger these conditions.

One sorted, ASCII-escaped JSON line records exact repository/PR/commit/tree
identities, counts, deterministic reason codes and up to 25 example paths per
category. Literal tabs/newlines in legal Git names are escaped, not executed as
workflow commands. Missing or non-boolean completeness, truncated trees,
duplicate roots, non-root paths, malformed mode/type pairs and mismatched
identities are errors. Each JSON response is bounded to 8 MiB and root inventories
to 100,000 entries. Provider failures stop without an automatic retry storm.

## Run and test

Requires Python 3.10+ standard library; the real-object regression also requires
Git. The workflow supplies event/repository/token environment variables.

```sh
python tree_preservation_guard.py --event /path/to/pull-request-event.json
python -m unittest -v test_tree_preservation_guard.py
python -O -m unittest -v test_tree_preservation_guard.py
python -m py_compile tree_preservation_guard.py test_tree_preservation_guard.py
```

The 27-test suite includes exact threshold boundaries, invalid/incomplete provider
responses, four-read binding, CLI exit codes, transport behavior, workflow wiring,
and a network-free real Git object regression with 4,312 roots: a one-root
successor fails while a 4,313-root additive successor passes. Mock transport tests
never issue live provider requests. Local execution evidence is not a claim that
GitHub-hosted workflows ran.

## Operational response and limits

For FAIL, inspect the exact paths and reconstruct the candidate on the full
current-main tree; preserve independent work. The Git Trees API's `base_tree`
parameter retains unaffected entries; omitting it while supplying a sparse list
creates a sparse tree rather than a patch. Prefer Contents writes or a complete,
verified baseline for scoped edits. Never "repair" this warning by deleting
unrelated mainline content.

For ERROR, use the reported evidence condition to resolve provider availability
or malformed input, then evaluate a later current event. Do not equate unavailable
metadata with PASS. This tool does not add a scheduler or re-run provider jobs.

This is a **root-only heuristic**, not a recursive data-loss detector: deletions
inside a retained root directory and below-threshold root removals can pass.
The baseline is the exact event base, not a promise about a later moving main.
Fresh topology and expected-head checks remain necessary at merge time. Direct
ref updates do not run this PR listener. A workflow failure is not branch
protection, automatic merge denial, or authority to merge; repository settings
are unchanged and both authority fields remain false.

Because `pull_request_target` executes trusted default-branch source, the new
checker is available to that listener only after it lands on the default branch.
The introducing PR does not prove the new trusted listener has already run.
See [GitHub's event security guidance](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request_target).
