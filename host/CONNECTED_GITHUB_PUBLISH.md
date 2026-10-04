# Publish a source change with native GitHub tools

`host/connected_github_publish.cjs` packages the connected-tool publication path
used by cloud sessions: current base → exact file-version comparison → optional source blobs →
tree → commit → new branch → pull request → optional merge → source readback.
It needs no Git checkout, shell command, credential export, package install, or
network client. The caller supplies the actual discovered GitHub tool bindings.

Use this for an already-authorized change to regular source files. Existing
repository rules, source ownership, permission boundaries, and required product
execution still apply. The helper does not grant permission or decide whether a
change is ready. It does not discover tools, merge another worker's patch,
delete files or branches, run tests, or deploy anything. The separate
`advanceGitHubContribution` export advances an existing contribution ref;
`reconcileGitHubContribution` reads a retained outcome without writing.

## Call contract

Read the current native tool definitions before first use. The shipped adapter
uses the installed `mcp__codex_apps__github_*` schemas for `fetch`, `fetch_file`,
`create_blob`, `create_tree`, `create_commit`, `create_branch`,
`create_pull_request`, and optionally `merge_pull_request` and `fetch_blob`. `create_blob` is
required when the change contains base64 input or an `expected_new_blob_sha` pin.
Unpinned UTF-8 files use the native tree writer's inline `content` field together
in one request. A caller may supply
`options.bindings` to map these action names to equivalent observed bindings;
their argument and result contracts must remain the same. A partial discovery
is not an account-permission verdict: keep doing useful independent work and
repeat discovery until the required bindings are present.

`fetch_blob` is an optional read-only continuation for omitted large text. Its
absence does not prevent publication or ordinary readback. When present, it is
called once for an observed nonempty text blob whose file response omitted the
body. Binary files, ordinary text responses, actual empty files, and failed
file-reader calls do not use this continuation.

From a Node host that already has those native tool bindings:

```javascript
const {publishGitHubChange} = require('./host/connected_github_publish.cjs');
const result = await publishGitHubChange(tools, {
  repository_full_name: 'OWNER/REPOSITORY',
  base_branch: 'main',
  branch_name: 'work/YOUR-UNIQUE-OPERATION',
  title: 'Describe the resulting behavior',
  body: preparedPullRequestDescription,
  commit_message: 'Describe the source change',
  files: preparedFiles,
  merge: true,
  merge_method: 'merge',
}, {onProgress: state => retainOperationProgress(state)});
```

`preparedFiles` is a nonempty array of:

| Field | Meaning |
|---|---|
| `path` | Repository-relative regular-file path. |
| `content` | Complete UTF-8 source string, or base64-encoded binary bytes. |
| `encoding` | `utf-8` by default; `base64` is also supported. |
| `expected_blob_sha` | Exact Git blob SHA read before editing; explicitly `null` for a new file. |
| `expected_new_blob_sha` | Optional independently observed Git blob SHA for UTF-8 or base64 source; checked against the native blob result before tree creation. |
| `mode` | Optional `100644` or `100755`; otherwise retain the existing mode, or use `100644` for a new file. |

Pass actual prepared source, not excerpts. The expected SHA identifies the
**previous** file. For UTF-8 files the helper confirms the complete published
content, then records the native SHA returned by readback. With a new-source pin,
UTF-8 also requires that returned SHA to match the pin. The native blob writer
supplies new SHAs before tree creation for base64 and pinned UTF-8 files. Base64 input
must use ordinary padded encoding without line breaks. UTF-8 input rejects
unpaired surrogate characters instead of silently changing them.

For a file transferred by `collectFileChunks`, pass its complete `base64` as
`content`, set `encoding: 'base64'`, and carry the independently observed source
hash used as `expected_git_blob_sha1` into `expected_new_blob_sha`. Keep
`expected_blob_sha` set to the previous repository file's SHA. The two pins
identify different versions. A producer-reported hash alone does not establish
independent source identity.

The optional new-source pin must be a lowercase 40-character Git SHA and is
accepted with UTF-8 or base64 input. Pinned UTF-8 uses one native `create_blob`
call per file, then places the verified blob SHA in the tree request. A mismatch
throws `GitHubPublishError` at
`create_blobs`, with the expected and actual SHA and `source_pin_matches: false`
in the affected progress entry. Native blob objects may already have been
created, but no tree, commit, branch or PR is created by that invocation. The
check also precedes the unchanged-source return. Matching entries record
`source_pin_matches: true`; an unattempted check remains `null`. Omitting the
field preserves the existing behavior, including UTF-8 batching.

For complete UTF-8 source already retained in the caller's runtime, keep the
default encoding and set `expected_new_blob_sha` to the independently observed
Git blob of those accepted bytes. No base64 conversion or local exporter is
needed. Keep the previous-version pin in `expected_blob_sha`; supplying a new
pin does not replace source execution or establish the correctness of the code.

`merge` defaults to `false`, leaving a normal open PR when that is the requested
outcome. For Commons work that is already authorized to land under `RULES.md`,
pass `merge: true`; this is a call option, not an added review gate. The helper
uses the newly created commit as `expected_head_sha`. Merge methods are `merge`,
`squash`, or `rebase`, subject to the repository's existing settings.

In a code-mode runtime without filesystem imports, first fetch the complete,
trusted source through the connected file reader and verify its returned Git
blob identity, as with any source loaded into that runtime. The file contains
no imports and can then be loaded in that isolate:

```javascript
const {publishGitHubChange} = new Function(
  trustedCompletePublisherSource + '\nreturn {publishGitHubChange};'
)();
const result = await publishGitHubChange(tools, preparedChange, {
  onProgress: state => store('my-operation-publish-progress', state),
});
text(result); // Source content and the PR body are not copied into progress.
```

## What it preserves

The helper reads the current base branch once, then traverses its exact,
nonrecursive Git trees. Entry and mode comparisons use complete trees. A bounded
absence fallback can handle a new immediate leaf when its known parent tree
cannot be transported; its limits are described below. The helper compares every
source file with the caller's expected version **before the first write**. This
lets unrelated main-branch changes compose naturally while stopping an obsolete
postimage from overwriting a changed file. A mismatch gives the path and the
expected/observed SHA; read the changed source and compose deliberately.

All provider writes are sequential. The commit has the observed base as its
parent. Existing file modes are retained. The branch primitive creates a new
branch; use a unique operation name. `publishGitHubChange` does not update an existing branch; the explicit
contribution operation below provides a nonforce continuation on the original PR. Unpinned UTF-8 entries share one tree request, saving a
separate blob call per text file. Identical source/mode changes return
`status: no_source_changes` without a commit, branch, or PR. An unchanged UTF-8
batch with unpinned text is recognized by the returned tree SHA matching the
observed base tree; an unchanged batch containing only base64 or pinned UTF-8
files also skips the tree request after its blob checks.

Readback compares every submitted UTF-8 file's complete source with the returned
UTF-8 content at the merge commit, or at the published commit when the PR stays
open. Text outcomes have `content_matches`; `expected_blob_sha` is the requested
new-source pin, or `null` for unpinned text. Both the complete content and any
requested pin must match before `matches: true` or before the returned native
`observed_blob_sha` replaces the corresponding file's `blob_sha`. In a mixed batch this also checks submitted text
files that ultimately remained unchanged. Binary files retain base64 readback
and comparison with their created blob SHA, and are never decoded as UTF-8
merely to check their identity. `readback_ref` names that exact source
snapshot. It does not claim that a later current-main tip is
unchanged, that a running service reloaded it, or that it is deployed. Source
execution and product acceptance remain the caller's work.

### New files under an unreadable parent tree

An oversized directory can make the native Git-tree reader return
`transport_closed` even when an exact file read works. After that specific
failure, or an explicitly truncated response for the requested tree SHA, the
helper can make one narrower `fetch_file` request for an immediate leaf. It
uses the already-captured immutable base commit, requests only the first line,
and uses metadata rather than interpreting the source body. The preceding
complete-tree reads must have established every parent prefix as a tree.

Only the native structured `NOT_FOUND` response with HTTP 404 and `Not Found`
establishes absence in this context. A caller's `expected_blob_sha: null` then
matches normally, and its requested new-file mode applies as usual. The new
file may be UTF-8 (pinned or unpinned) or base64; source-pin checks and all remaining base
version checks still finish before the relevant tree, commit, branch and PR
writes. An explicit absence conflicts with an expected existing blob.

A positive file response must identify the exact repository, immutable commit
and path in its native `display_url`, and supply a valid blob SHA. A different
SHA proves a version conflict. A matching existing SHA **does not** permit the
fallback to continue: the observed native file reader omits Git type and mode.
The Contents renderer also omits those fields, and GitHub's
[Contents API](https://docs.github.com/en/rest/repos/contents#get-repository-content)
can dereference an in-repository symlink. Neither `mode: '100644'` nor an
unverified expected-mode assertion can establish the previous entry. An
existing file therefore still requires its exact complete-tree type and mode
evidence. The helper never converts an unresolved existing path into a new
regular file or silently resets its executable bit.

The fallback does not apply when the root tree is unreadable, when an
intermediate prefix remains unresolved, or when a successfully read prefix is
not a directory. A 401/403, timeout, unrecognized error, malformed tree, wrong
tree identity, wrong file URL, or omitted file SHA stops the operation. Error
text alone, an empty body and a partial directory listing never prove absence.
No failed tree or file call is retried. An eligible failed parent tree is cached
for that invocation, so several new leaves under it share one failed tree read
and each receive one exact file read. Native response-size limits still apply.

`progress.preimage_fallbacks` appears only when this narrower read is attempted.
Each row retains the path, immutable base commit, parent tree SHA, exact read
request, reason and outcome. Outcomes are `pending`, `absent`, `existing_blob`
or `unavailable`; an existing-blob row explicitly records that type and mode
were not observed. The original bounded tree error remains attached even if
the absence read succeeds. No source body is copied into progress. Ordinary
complete-tree publications retain their previous calls and progress shape.

Open-PR merge continuation uses the same rule against its freshly read base.
It can re-establish that a previously new leaf is still absent; an appeared
file or unresolved existing entry stops before the merge. Already-merged PRs
continue straight to their actual immutable readback as before. Prior
invocations and their errors remain part of the caller's retained history.

The file reader can return a large file's SHA with an empty body. For text,
an empty returned body with a nonempty blob identity is recorded as
`error_code: readback_content_unavailable`, `content_available: false`, and
`content_matches: null`. If the optional `fetch_blob` binding is available, the
helper reads that immutable blob and compares its complete text with the prepared
source. A recovered row records `blob_readback_attempted: true`,
`readback_source: blob`, and `file_content_available: false`; its full comparison
determines whether it matches. This performs one additional read and no write.

Without the binding, or if the blob body is also unavailable, the row remains
`readback_content_unavailable`. A failed blob read retains that observed file SHA
and unknown comparison, plus `blob_readback_error` and any bounded `tool_error`.
Metadata alone never establishes a content match. An actual empty Git blob remains
a normal comparison, and binary files retain their created-blob SHA comparison.

For read-only continuation, the exported `inspectReadback(file, source, data)`
uses the same comparison as publication. Pass the retained `progress.files`
entry, its prepared source entry (including `encoding`), and the unpacked
native file response at `readback_ref`. It performs no provider operation; it
records a text `blob_sha` on that file entry only after full content and any
requested new-source pin match.

The exported async `resolveReadback(file, source, data, readBlob)` applies the
same optional recovery used during publication. The first three arguments match
`inspectReadback`; the optional callback receives the observed blob SHA and must
return the unpacked native blob payload. It is called only for unavailable text.
This supports continuation from an already-retained file response without
repeating its read or any publication write. Omitting the callback preserves the
synchronous inspector's outcome.

### Recover omitted UTF-8 content by blob identity

For a text row still marked `readback_content_unavailable`, the separate native
`github_fetch_blob` reader can retrieve content by the observed blob SHA.
Use the SHA retained from the file read at `readback_ref`, and compare the
complete returned text with the original prepared source:

```javascript
const pending = progress.readback.find(
  row => row.error_code === 'readback_content_unavailable'
);
if (!pending) throw new Error('No omitted text readback is pending');
const file = progress.files.find(row => row.path === pending.path);
const source = preparedChange.files.find(row => row.path === pending.path);
if (!file || !source || (source.encoding ?? 'utf-8') !== 'utf-8') {
  throw new Error('Retain the original prepared UTF-8 source for this path');
}
const response = await tools.mcp__codex_apps__github_fetch_blob({
  repository_full_name: progress.repository_full_name,
  blob_sha: pending.observed_blob_sha,
});
if (response.isError || typeof response.structuredContent?.content !== 'string') {
  throw new Error('The blob reader did not return complete text');
}
const continued = inspectReadback(file, {...source, encoding: 'utf-8'}, {
  // This is the immutable SHA requested above; the blob response supplies content.
  sha: pending.observed_blob_sha,
  content: response.structuredContent.content,
});
store('my-operation-readback-continuation', {
  readback_ref: progress.readback_ref,
  publication_status: progress.publication_status,
  ...continued,
});
text(continued);
```

Load `inspectReadback` from the same trusted helper as `publishGitHubChange`.
Keep each remaining readback outcome explicit; one recovered file does not
complete a batch with other unresolved files. This continuation performs one
read and no publication write.

This route recovered the complete 2,237,659-byte `delta.json` at Commons commit
`3e01b7a7c9e5feb2f9659e67ba909e999214ab6b`. The bytes matched the independently
retained source and its Git blob `77b7cdede94f84346e9020f96c8962bc00818023`;
`inspectReadback` then recorded a full content match. The blob reader is
UTF-8 oriented: the observed binary archive call failed decoding. Do not use
this text continuation as evidence that binary bytes were retrieved.

## Failures and continuation

No provider error is automatically retried. The helper throws
`GitHubPublishError` with `progress`, the original `cause`, and the last native
`response` when one is available. Progress records the stage, call counts,
previous/new file SHAs (unpinned text SHAs become available at readback), tree/commit,
branch creation, PR, merge result, and all
readback outcomes. `publication_status` records a confirmed `pull_request_open`
or `merged` independently of `status`, which stays `incomplete` when readback
fails. `readback_status` is `complete`, `content_unavailable`, or `incomplete`.
The failure also sends the latest progress to `onProgress`, including these
outcomes and the frozen `readback_ref`. It does not include source contents or
the PR description.

```javascript
try {
  const result = await publishGitHubChange(tools, preparedChange, options);
  text(result);
} catch (error) {
  store('my-operation-publish-progress', error.progress);
  text({message: error.message, progress: error.progress});
  // Inspect error.cause / error.response privately when needed.
}
```

Sequential native tool refusals add a bounded `tool_error` object to the thrown error and
failure progress, with the action, a stable error code, an HTTP status when the
native structured response supplies one, and its connector error code when
available. The message is generated locally; raw provider bodies are not copied
into progress. Failed parallel readback rows retain their own `tool_error`
objects so their provider facts stay attached to the affected file.

The exported `inspectToolError(action, nativeResponse)` returns the same metadata
for an already-retained native tool error, or `null` for a non-error response. It
performs no provider call. Current specific codes are `base_branch_modified`
for GitHub's explicit HTTP 405 base-move refusal and `transport_closed` for the
native transport failure; other reported errors remain `native_tool_error`.
These describe observations, not retry permission or account-wide capability.

For `base_branch_modified`, read the named PR and current base first. If the PR
has already merged, continue its readback. Otherwise, confirm its retained head
and reconcile the affected file versions before continuing that same intended
merge with `expected_head_sha`. Keep the existing branch and PR; do not restart
the publication sequence. The publisher does not automatically continue or retry
an error. The separate explicit continuation below packages those native steps.

### Continue the same known pull request

`continueGitHubMerge(tools, preparedChange, previousProgress, options)` finishes
the merge of a pull request already confirmed by this publisher. Invoke it only
when that same merge is authorized. Keep the original prepared source and file
versions, the complete retained progress, and set `merge: true` explicitly. This
also supports an intentional open-PR publication followed by an authorized merge.

```javascript
const {continueGitHubMerge} = require('./host/connected_github_publish.cjs');
const result = await continueGitHubMerge(tools, {
  ...preparedChange,
  merge: true,
}, retainedPublishProgress, {
  onProgress: state => retainOperationProgress(state),
});
```

Load this export from the trusted source in code mode in the same way as the
publisher. Its additional native action is `get_pr_info`; it accepts the same
`options.bindings` override convention. It needs `fetch_file` for source readback,
optional `fetch_blob` for omitted UTF-8, and `fetch` plus `merge_pull_request` only
when the PR is still open. It never calls a blob, tree, commit, branch, or PR writer.

The continuation validates that the retained repository, branches, commit, PR
head, and previous file versions belong to the prepared change. The original
prepared contents must remain unchanged; binary identity uses the native new
blob SHA retained by publication. It then reads the named PR from GitHub and
requires the same head commit, base branch, and source branch in that repository.
An already-merged PR goes directly to its actual merge commit's source readback,
recording `merge_skipped: already_merged`; no merge binding or call is needed.

For pinned UTF-8 or base64 source, continuation compares the retained blob SHA
with `expected_new_blob_sha` before any native call. A retained pin cannot be
changed or removed. Older unpinned progress remains supported: an optional new
pin can be added only when a valid retained blob SHA exists and matches. For
unpinned UTF-8, that SHA becomes available after complete content readback; an
omitted or failed earlier readback does not establish the missing identity.
Adding a pin checks identity for this continuation; it does not assert that the
original publication checked a pin before creating its tree. The check compares
SHA values directly, without trusting a saved match flag.

For an open PR, it reads the current base and its exact nonrecursive trees,
using the same bounded new-leaf absence fallback if eligible, then compares
every affected previous blob and file mode. An unrelated base
change can proceed; an affected-file change must be composed deliberately.
It makes one merge call with the original `expected_head_sha` and requested
merge method. A concurrent base or head change may still be refused by GitHub.
That native result is retained without a retry. A later explicit invocation
starts with provider reconciliation again, including checking whether the
previous call actually merged.

The result has `operation: merge_continuation`, fresh per-invocation call counts,
the retained publication identities, any observed `current_base_commit_sha` and
`current_base_tree_sha`, and the same frozen content readback and error metadata
as publication. UTF-8 comparison, optional immutable-blob recovery, binary SHA
comparison, and `onProgress` behavior use the existing contracts. A confirmed
merge remains `publication_status: merged` even if its readback is incomplete.
Retain the prior progress as well when keeping the history of earlier calls;
this result does not combine call counts from separate invocations.

**Do not blindly rerun a failed publication.** A timeout can occur after a
provider accepts a write. Reconcile the named branch, PR, or merge before
continuing with the existing native tools. For example, a readback failure after
`merge_result.merged: true` does not mean the merge failed; finish the readback.
A branch-creation failure does not authorize replacing that branch. An account
or integration-scope error is specific to the observed operation, not a reason
to invent a new login or declare all tools unavailable.

The optional `onProgress` callback receives copied metadata after completed
steps. Its errors are collected in `progress_callback_errors` and do not block
the already-authorized publication. This is an observer, not a dispatch or
approval mechanism. Durable execution/restart is not built in; retain progress
using the existing host and reconcile provider truth after interruption.

## Advance an existing contribution pull request

Use `advanceGitHubContribution` for an already-authorized continuation on the
original contribution branch. It does not create a branch or PR, edit the PR
body, merge upstream, or rewrite prior commits. The new commit's sole parent is
the exact observed contribution head.

```javascript
const {advanceGitHubContribution} = require('./host/connected_github_publish.cjs');
const result = await advanceGitHubContribution(tools, {
  repository_full_name: 'CONTRIBUTOR/FORK',
  pull_request_repository_full_name: 'UPSTREAM/REPOSITORY',
  pull_request_number: existingPullRequestNumber,
  branch_name: existingContributionBranch,
  base_branch: observedUpstreamBaseBranch,
  expected_head_sha: observedContributionHead,
  expected_base_sha: observedUpstreamBase,
  commit_message: preparedCommitMessage,
  files: preparedFiles,
}, {onProgress: state => retainOperationProgress(state)});
```

The two repositories may be the same. Branch names may also be the same when
the contribution is in a fork. Both SHAs and both branch names are required:
they identify the PR context that the caller actually inspected. `files` uses
the existing complete-content, previous-blob, encoding, optional new-blob pin,
and mode contract. Supply no title, body, merge options, or force option to this
operation. PR description publishing and external acceptance remain separate
operations with their own existing permission boundaries.

The native bindings are `fetch`, `fetch_file`, `create_tree`, `create_commit`,
and `update_ref`, plus `create_blob` when base64 or a source pin needs it, and
optional `fetch_blob` for omitted UTF-8 content. The generic reader accesses the
full native PR, Git commit, tree and branch-ref resources. It uses the same
`options.bindings`, `onProgress`, `GitHubPublishError`, and bounded native-error
diagnostics as the other exports.

The operation performs these steps:

1. Read the original PR and compare its repositories, branches, open/unmerged
   state, head and base with the supplied observations.
2. Read that immutable head's commit and complete recursive tree. Compare every
   affected previous blob and regular-file mode before creating any object.
3. Create the prepared tree and a commit with that head as its sole parent.
   Pinned UTF-8 and base64 use the existing native blob checks; unpinned UTF-8
   stays in one inline tree request. An identical tree returns
   `no_source_changes` without a commit or ref update.
4. Read the created commit and complete recursive tree. Require the intended
   sole parent, tree and exact commit message. Compare every unrequested leaf
   and its mode/type, as well as directories outside the prepared paths'
   ancestors. Record `tree_comparison.changed_paths` and
   `unchanged_leaf_count`; do not copy the complete tree into progress.
5. Read every prepared file at that immutable commit. UTF-8 must match the
   complete submitted text and the tree's blob SHA. Base64 retains the existing
   native-created-blob identity comparison. Optional immutable blob recovery
   handles omitted text as in ordinary publication.
6. Read the PR and original branch ref again. Both must still identify the
   observed old head; the PR must remain open/unmerged at the observed base.
   Persist the known commit and an uncertain ref-update state, then make one
   native `update_ref` call with `force: false`.
7. Read the same PR and ref again. Both must identify the prepared commit.
   The earlier content comparison remains bound to that immutable commit; the
   helper does not duplicate those file reads. The final PR state and
   `base_changed` observation remain explicit.

This is a fresh-head comparison plus GitHub's nonforce update, not an atomic
compare-and-swap API. The exposed ref writer has no expected-old-head argument.
A concurrent divergent branch update can cause GitHub to refuse the write.
A concurrent base movement after the last comparison can appear in the final
observation. A PR closure or merge by someone else is reported as observed;
this helper never requests either action. No failed or inconclusive operation
is automatically retried, and no previous ref is restored.

Both recursive tree responses must be complete and identify the requested
immutable tree. A truncated, malformed, oversized, or unavailable tree stops
the operation. This full unchanged-path comparison does not infer coverage
from partial listings and does not use the new-leaf fallback described for
`publishGitHubChange`. Before the first object write, an unreadable parent
therefore leaves the original branch untouched. A later failure may leave
unreferenced prepared objects; their known identities remain in progress.

Progress has `operation: contribution_advance`, the original PR and repository
identities, `parent_commit_sha`, `parent_tree_sha`, prepared `tree_sha` and
`commit_sha`, file versions/modes, immutable readback and per-call counts.
Each bounded current-head observation records the PR head/base/state and
branch-ref SHA. Source strings and commit-message contents are not copied.

| Outcome | Meaning |
|---|---|
| `status: contribution_branch_updated` | Both final reads identify the prepared commit, and immutable source readback is complete. |
| `publication_status: update_confirmed` | The native ref writer returned success; a later readback may still be incomplete. |
| `publication_status: unknown` | The ref request was about to be sent or did not return a confirmed result. Reconcile provider state before another write. |
| `ref_update_state: not_converged` | Current PR/ref observations do not both identify the prepared commit. Their actual SHAs remain available. |
| `status: no_source_changes` | No contribution commit or ref update was needed; any earlier native blob/tree creation is still counted. |

### Reconcile a retained contribution without writing

After an uncertain update or incomplete readback, retain the same complete
prepared change and all progress. Call `reconcileGitHubContribution` explicitly:

```javascript
const {reconcileGitHubContribution} = require('./host/connected_github_publish.cjs');
const result = await reconcileGitHubContribution(
  tools, preparedContribution, retainedContributionProgress,
  {onProgress: state => retainReconciliationProgress(state)}
);
```

This export requires a known prepared commit and tree. It does not require or
call any writer binding. It checks the retained operation identity and previous
versions/modes, re-reads the original parent and prepared commit/trees, compares
the complete prepared text, and reads the current original PR/ref. Requested
source pins cannot be changed or removed; adding a pin needs a matching
retained blob identity. Base64 uses the original native-created blob identity,
so the caller must retain the original binary input rather than substituting
new base64 under an old progress record.

If both current heads equal the prepared commit, the result is
`contribution_branch_updated`. If both equal the original parent, it is
`contribution_branch_not_updated` with
`publication_status: previous_head_observed`; the prepared objects exist,
but this read-only call did not publish them. Any other combination stays
incomplete with the actual observations. Current upstream base movement is
recorded without blocking these read-only checks. Historical confirmed/uncertain
writer status remains in `previous_publication_status` and
`previous_ref_update_state`.

There is deliberately no automatic write continuation. When a later deliberate
publication is appropriate, use the existing native tools with the retained
commit and freshly reconciled branch/PR context. Do not rerun the object
creation path, create a replacement PR, force the branch, or infer successful
maintainer checks from source publication. Reconciliation can finish a known
source/readback outcome; it cannot establish deployment, sponsor acceptance or
test execution.

## Observe only the remaining contribution heads

`observeGitHubContributionHead` reads the current PR and original branch ref
without repeating an accepted immutable source comparison. Use it when the
caller retains the earlier commit/tree/full-file verification and write result
and needs only these remaining observations. It is also a read-only view of a
specified existing PR/branch; it never infers that any prior publication occurred.

```javascript
const {observeGitHubContributionHead} = require('./host/connected_github_publish.cjs');
const observation = await observeGitHubContributionHead(tools, {
  repository_full_name: retainedContribution.repository_full_name,
  pull_request_repository_full_name: retainedContribution.pull_request_repository_full_name,
  pull_request_number: retainedContribution.pull_request_number,
  branch_name: retainedContribution.branch_name,
  base_branch: retainedContribution.base_branch,
  expected_commit_sha: retainedContribution.commit_sha,
  expected_base_sha: retainedContribution.expected_base_sha,
}, {onProgress: state => retainHeadObservation(state)});

retainHeadObservation(observation);
// Keep the native response bodies privately; print only the needed projection.
show({
  status: observation.status,
  source_verification: observation.source_verification,
  heads_agree: observation.heads_agree,
  base_changed: observation.base_changed,
  pull_request: observation.observations.pull_request,
  branch_ref: observation.observations.branch_ref,
  errors: observation.errors,
});
```

All seven target fields are required. `expected_commit_sha` is the prepared
commit whose current visibility is being checked, rather than the old
`expected_head_sha` used to authorize an advancement. The repositories, PR
number, branches and lowercase 40-character SHAs are validated before any
provider call. Extra target fields, including source files or retained writer
state, are refused so they cannot be mistaken for evidence this reader checked.

The reader starts exactly two concurrent native `fetch` calls after validation:
the upstream PR resource and the contribution repository's branch-ref resource.
It reuses the publisher's native-error decoder and contribution PR identity
checks. It requires the ref response to identify the requested short branch
and a commit object. Both outcomes are consumed even when one fails.

| Status | Meaning |
|---|---|
| `expected_head_observed` | Both valid resource responses identify `expected_commit_sha`. |
| `not_converged` | Both responses are valid, but at least one identifies another commit. Their actual SHAs are retained; no cause is inferred. |
| `incomplete` | At least one fetch, response decode, or resource-identity check failed. Successful independent observations and per-resource errors remain available. |

`source_verification` and `publication_verification` are always `not_performed`;
`writes` is always zero. The function does not return the full publisher's
success status, alter the retained publication record, or prove commit
parentage, tree contents, file bytes, authorization, CI, merge or acceptance.
A matching head can accompany a closed/merged PR or a changed base. The observed
PR state and `base_changed` flag remain explicit; base movement does not change
the meaning of the head comparison. The base flag is retained even when only
the PR read succeeds; agreement flags remain null until both resources are valid.

`requests` records the two exact URLs. `responses.pull_request` and
`responses.branch_ref` preserve each original returned tool envelope, including
a returned native error; a thrown call has no invented response. `observations`
contains only validated resource identities, and `errors` records the failed
resource separately. The raw PR response can contain a long body, so two calls
are an operation-count bound, not a response-byte limit. `snapshot: false`
records that independent GitHub reads are not an atomic snapshot.

Only `options.bindings.fetch` and `options.onProgress` are supported. There is
no writer binding, retry, sleep, poll, local process or new timeout policy;
native connector deadlines apply. Invalid targets/options or a missing binding
throw `GitHubPublishError` with zero-call progress. Read/identity failures return
`incomplete` after both outcomes settle. Progress callback errors are retained
without changing the read result.

Keep using `reconcileGitHubContribution` when the immutable source comparison
itself is missing, uncertain, or needs to be established again. Its complete
source/tree reconciliation remains unchanged.
