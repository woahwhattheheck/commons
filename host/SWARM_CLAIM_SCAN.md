# Read scoped work claims from Slack exports

`swarm_claim_scan.py` turns retained Slack responses into a compact inventory of
explicit work declarations and possible exact-file overlaps. Use it while
choosing or composing work so the same thread does not need to be read in full
for every path comparison.

It reads files or stdin, writes JSON to stdout, and uses only Python's standard
library. It never contacts a provider, changes a claim, dispatches work, sends a
warning, or creates a schedule. The existing claims ledger and source threads
remain the places to coordinate work.

## Run on a real connector response

Save the actual JSON result of a Slack channel, thread, or message-search read.
Keep that source export outside the source repository. For a native thread
response, supply the channel ID because its rendered message body can omit it:

```sh
python3 host/swarm_claim_scan.py /path/to/thread-response.json \
  --channel-id C0BU51F1PL3 \
  --workspace-url https://tokenjunkielabs.slack.com
```

The reader accepts raw Slack `messages` pages and the native connector's
`messages` or `results` text wrapped in MCP `content` / `structuredContent`.
Several source files can be passed together; `-` reads one response from stdin.
The response size limit is 64 MiB per input. No third-party package is required.

For detailed native thread pages, the declared reply count must match the
rendered reply blocks. A contradictory page exits 2 before interpreting its
messages, even when pagination says there are no more messages. Keep the source
response and repeat the same thread, cursor and time window with a smaller
`limit` and `response_format="detailed"`; retain the new JSON for the next scan.
The scanner performs no retry itself. A consistent page keeps its reported
pagination, and still cannot establish complete provider history.

## Select a path or operation

Add `--path host/wb_range.py` or `--operation OPERATION_ID` to focus the same
command on exact observed values. Repeat either flag to match any supplied value
of that kind; using both kinds requires both to match. Matching is case-sensitive,
with no path normalization, basename resolution, wildcard expansion or operation
alias inference added by selection.

Selected output keeps each matching operation and the peer operations in its
relevant possible-overlap groups. Group membership and source links stay intact,
so selecting one operation still exposes its observed counterparts. A path
selector keeps only groups for that exact path. `selection` distinguishes direct
matches from related operations and gives the returned collection counts.

The original `counts`, `coverage` and `inputs` remain unchanged and describe
**all supplied sources**, including unparsed headers, ambiguity, unread cursors
and input hashes. An empty selection is still not evidence that work is available.
`availability_hints` also remains supplied-history context under selection.
No flags preserves the complete report. Selection changes no claim states or exit
codes and performs no additional source reads.

## Read the result

- `operations` lists recognized declarations, extracted source paths, source
  timestamps and message links. `declaration_observed` means only that the input
  contains a declaration without a later recognized explicit terminal statement.
- `possible_overlaps` groups that state by exact file path. Two operations sharing
  a file can still own different functions or compatible additive changes. Read
  their links and compose the work; this report does not decide who may proceed.
- `possible_symbol_overlaps` narrows those observations to explicit matching
  `file.py::function` or `file.py::Class.method` selectors, or an immediately
  adjacent code-shaped symbol such as `file.py import_reads`. `shared_file_scopes`
  lists each operation's symbols and unscoped operations beside the shared
  symbols, so independent methods remain distinguishable within the same file.
  Same-symbol observations still do not establish incompatible changes.
- `operations[].observed_scopes` retains selectors with their exact source
  links. Bare filenames are recognized when followed by `::`; their
  `path_resolution` stays `basename_only`, because a matching filename does not
  establish a matching repository or directory. The reader never aliases a
  bare filename to a longer path. Refresh the linked source before combining
  those observations.
- `terminal_observations` records explicit `LANDED`, `DONE`, `COMPLETE`, or
  `RELEASE` statements. An explicit primary header may combine two of those
  verbs with `/`, as in `DONE / RELEASE OPERATION_ID` or
  `DONE / RELEASE — OPERATION_ID`; its first verb remains the reported kind.
  The exact operation ID and existing quote/condition handling are preserved.
  The observed primary `DONE SOURCE / RELEASE OPERATION_ID` and
  `SHIP / RELEASE · OPERATION_ID` headers retain the actual operation ID and
  the first terminal kind. `SHIPPED` and `RELEASED` spellings are also accepted
  in the latter form; a bare `SHIP` header does not supply a terminal observation.
  Conditional or proposal wording on that header line leaves it unparsed;
  secondary clauses do not reinterpret these source-release forms. Terminal
  identifiers must contain a hyphen or colon, matching declaration identifiers; ordinary words
  such as `SOURCE` never become operation IDs. Unsupported headers remain in
  `coverage.unparsed_statement_headers` when the message has no recognized
  statement.
  A colon, middle dot, en dash or em dash can separate the terminal header from
  its explicit identifier, as in `LANDED: ID` or `DONE · ID`.
  Exact operation IDs retain their existing behavior. A
  shortened name resolves only when it uniquely matches an earlier declaration
  in the same channel with a dated suffix such as `-20261003-AABE`. The original
  `operation_id` remains literal; `resolved_operation_id` and `alias_resolution`
  identify that observed match. Multiple matches remain unresolved, with their
  `alias_candidates` retained in `unmatched_terminal_observations`. A PR link or
  an ordinary mention does not close a claim.
  An explicit terminal clause in a later sentence names its own operation: a
  message can address one operation and release another without closing the
  addressee. Quoted text, fenced examples, and conditional secondary clauses
  do not supply terminal observations.
- `availability_hints` pairs an explicit "Available … scope/follow-on" or
  "Next usable work" paragraph with recognized declarations referencing the
  same GitHub issue or PR URL. It retains the availability text, both message
  links and each declaration's observed lifecycle state, so an old work pointer
  can be checked against later claims even when their operation IDs differ.
  Matching uses explicit GitHub repository, resource kind and number, ignoring
  URL fragments/query strings and repository-name case. Bare issue numbers and
  repository nicknames are not resolved. The URL may describe a dependency or
  excluded work, so this is a reference hint, not an ownership or stale-state
  decision. Existing file/function scopes and claim states do not change.
- `coverage` keeps each page's continuation and unknown pagination, unparsed
  statement headers, and message identities supplied with contradictory text.
  The known trailing `*Sent using* <@USER_ID|ChatGPT>` connector signature is
  ignored only when comparing duplicate message IDs: detailed thread responses
  include it while native search responses may omit it. Original message text,
  source references, and export hashes remain retained. Other text differences
  leave conflicting versions uninterpreted rather than guessed to be edits.
  Unparsed headers retain their exact text and source link, including a
  declaration in a later paragraph of an otherwise unrecognized message.
- `inputs` binds each supplied export to its SHA-256 and byte count.

The parser recognizes declarations beginning with `CLAIM`, `TAKE`, `RESUME`, or
`TAKING`, followed by an operation identifier. A colon, middle dot, en dash or
em dash may separate the primary declaration verb from that exact identifier,
as in `CLAIM: ID` or `TAKE — ID`. A declaration beginning with those verbs,
`RESUMING`, `CONTINUE`, or `CONTINUING` may instead name one exact
identifier in a labeled `Operation:` or `Operation ID:` sentence or line.
Multiple different labeled identifiers remain unparsed. For example, an actual
`Continuing PayD #635 ... Operation: payd-530-staging-completion-20261003-01.`
message binds only that explicit operation; a nearby `TAKE PayD #635 ...` without
an operation identifier remains unparsed with its header and source link.
No operation ID is invented from the project, PR number, or branch. It extracts explicit relative
file paths, including a simple `path/{one.py,two.py}` list. It deliberately does
not infer paths from a GitHub URL or expand directory-wide or wildcard scopes.
Explicit slash-separated selectors such as `file.py::first/second` retain both
symbols. An adjacent symbol must follow a source-code filename and contain an
underscore, a dotted name, empty call parentheses, or backticks; ordinary words
such as `only` and `metadata` stay unscoped. Each scope records which notation
was observed. The reader does not infer function names from surrounding prose.
Paths mentioned elsewhere in the same declaration may describe dependencies or
exclusions, so a match remains a possible overlap for human/peer interpretation.
Natural-language scope changes and unresolved short operation names require the
full thread. Alias matching describes only declarations present in the supplied
history; later pages may reveal another candidate.

All supplied message IDs are counted. Exact duplicate observations count once;
unrecognized ordinary messages do not become declarations. A missing declaration
or an empty report is never evidence that work is available or a project is done.
Even a terminal page cannot establish that earlier pages, other channels, edits,
or the canonical claim ledger were supplied. `provider_history_complete` is
therefore always false.

Exit 0 means the response was read and the report was produced. Possible overlaps
do not change the exit code: they are an advisory, not a work gate. Invalid JSON,
failed provider responses, unsupported layouts, missing channel identities, and
file errors exit 2 with a clear stderr message and no report on stdout.
