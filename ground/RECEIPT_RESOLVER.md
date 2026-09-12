# Receipt resolver

`host/receipt_resolver.py` is the E2 visibility-plan resolver: give it one durable Commons identifier and get one JSON state record back.

It is intentionally strict about identifier namespaces. Bare integers are rejected because pull-request, review and Actions-run ids overlap as numeric namespaces.

## Accepted identifiers

```text
#12569
pr:12569
https://github.com/woahwhattheheck/commons/pull/12569
review:12567:5178620884
review:5178620884
run:34594768274
blob:830e8e9a3ddae95799142eba6bcbd03f85eb4787
marker:OUTCOME-COMMERCE-PR12567-GUARDED-INTEGRATION-20260911-01
```

Examples:

```bash
python host/receipt_resolver.py pr:12569 --pretty
python host/receipt_resolver.py run:34594768274 --pretty
python host/receipt_resolver.py review:12567:5178620884 --pretty
```

`GITHUB_TOKEN` is optional for public reads and recommended when normal GitHub API rate limits matter.

## Resolution rules

- **PR**: reads the pull request directly and reports `OPEN`, `OPEN_DRAFT`, `CLOSED`, or `MERGED`, plus exact head/base SHA and mergeability.
- **Actions run**: reads the exact run id. `QUEUED` stays distinct from terminal success; a completed run carries its conclusion in the state string.
- **Git blob**: requires an exact 40-hex SHA and verifies that GitHub returned the requested object before reporting it available.
- **Review**: `review:<pr>:<id>` is direct and does not depend on coordination state. `review:<id>` uses the coordination-state verdict index to recover the owning PR and fails closed if the id is missing or ambiguous.
- **Marker**: first uses an exact marker value present in coordination state. If none is indexed, it falls back to a quoted GitHub PR search and requires exactly one matching PR.

The default coordination source is:

```text
https://raw.githubusercontent.com/woahwhattheheck/commons/state/coordination/coordination.json
```

The parser accepts the current JSONL publication plus array/object forms used by focused fixtures.

## Failure contract

Resolution failures return JSON on stdout and exit 2. Examples include:

- `AMBIGUOUS_NUMERIC_ID`
- `WRONG_REPOSITORY`
- `INVALID_BLOB`
- `REVIEW_NOT_INDEXED`
- `AMBIGUOUS_REVIEW`
- `MARKER_NOT_FOUND`
- `AMBIGUOUS_MARKER`
- `BAD_GITHUB_RESPONSE`

The resolver does not guess a namespace or silently choose among multiple candidate receipts.

## Tests

`test_receipt_resolver.py` uses an injected fake transport. It exercises namespace parsing, exact object binding, queued-vs-terminal run state, coordination-indexed review lookup, review ambiguity, marker precedence/ambiguity, and mismatched GitHub object rejection without network access.
