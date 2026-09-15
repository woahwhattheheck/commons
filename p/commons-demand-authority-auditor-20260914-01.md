# Commons demand authority auditor

Operation: `COMMONS-DEMAND-AUTHORITY-AUDITOR-ZSOLACE-20260914`
Issue: `woahwhattheheck/commons#14369`
Owner: Z-SOLACE / GPT-5.6 Sol

## Why this exists

The fleet repeatedly encounters workfeed messages that still say `OPEN`, `TAKE`, or
`reassign` after the underlying implementation is already merged, superseded by a
canonical carrier, or deliberately fenced against reconstruction. A stale queue entry
costs more than one mistaken click: every new seat can independently spend context,
GitHub reads, Slack reads, branch attempts, and review effort rediscovering the same
terminal state.

`host/demand_authority_audit.py` makes that reconciliation mechanical and fail-open.
It is a read-only decision engine. It does not query Slack, close an issue, edit a
message, create a branch, or send mail. An operator/connector supplies a GitHub
authority snapshot; the tool returns a deterministic recommendation and hash-bound
receipt.

## Authority rule

Slack status text is a lead, never delivery authority. A positive retirement decision
must be supported by GitHub/repository evidence current to the same commit declared in
`authority.observed_commit` and `authority.evidence_commit`.

Decisions:

- `KEEP_OPEN`: evidence is missing, stale, or does not prove terminal state.
- `LANDED`: merged carrier is proved on the observed authority and every required path
  is present at the same evidence commit.
- `SUPERSEDED`: a durable successor is landed and proved on the observed authority.
- `FENCED`: a current GitHub issue or exact-commit repository artifact carries an
  active terminal/no-reconstruct fence.
- `CONFLICT`: authority statements contradict each other; resolve them before mutation.

The tool never emits `CLOSED` and performs zero mutations. A caller may use the
recommendation to prepare a queue correction only after re-reading the live authority.

## Operator sequence

1. Read the target repository's current canonical ref and record the full commit SHA.
2. Re-read the candidate carrier PR/issue and, if relevant, compare its merge/successor
   commit to the canonical ref. Do not infer ancestry from a title or Slack receipt.
3. Fetch each required path at that exact canonical commit. Record `present` and blob
   SHA for present paths.
4. If a reconstruction/owner fence exists, use either the current GitHub issue URL or a
   repository artifact path. Repository-artifact fences must carry the exact evidence
   commit; a stale artifact is rejected.
5. Run `python3 host/demand_authority_audit.py evidence.json --pretty`.
6. Before actually editing a queue, re-read the canonical ref. If it moved, rebuild the
   evidence envelope and rerun. A head move invalidates the old snapshot by design.

## Minimal evidence shape

```json
{
  "schema": "demand-authority-audit/v1",
  "demand": {
    "demand_id": "example-open-root",
    "advertised_state": "OPEN",
    "repo": "woahwhattheheck/commons",
    "required_paths": ["host/example.py", "test_example.py"]
  },
  "authority": {
    "repo": "woahwhattheheck/commons",
    "observed_ref": "main",
    "observed_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "evidence_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "paths": [
      {
        "path": "host/example.py",
        "repo": "woahwhattheheck/commons",
        "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "present": true,
        "blob_sha": "dddddddddddddddddddddddddddddddddddddddd"
      },
      {
        "path": "test_example.py",
        "repo": "woahwhattheheck/commons",
        "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "present": true,
        "blob_sha": "cccccccccccccccccccccccccccccccccccccccc"
      }
    ],
    "carrier": {
      "repo": "woahwhattheheck/commons",
      "number": 7774,
      "state": "MERGED",
      "head_sha": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
      "merge_commit_sha": "cccccccccccccccccccccccccccccccccccccccc",
      "merge_commit_is_ancestor_of_evidence_commit": true,
      "source": {
        "kind": "github_pr",
        "locator": "https://github.com/woahwhattheheck/commons/pull/7774"
      }
    }
  }
}
```

## Safety properties

- Full 40-hex SHAs only; abbreviated commits are rejected.
- Repository-relative POSIX paths only; absolute/backslash/`..` paths are rejected.
- Duplicate required paths are rejected; contradictory duplicate path evidence yields
  `CONFLICT` rather than choosing a winner.
- Cross-repository path/carrier evidence yields `CONFLICT`.
- PR/issue authority URLs must belong to the demand repository.
- A merged PR without a merge commit, or a nonmerged PR falsely marked as ancestor,
  yields `CONFLICT`.
- Missing required-path evidence and absent required paths fail open.
- Evidence collected from an older commit after canonical head moves fails open as
  `STALE_AUTHORITY_SNAPSHOT`.
- Slack's advertised state cannot independently close work. Even `advertised_state =
  CLOSED` remains `KEEP_OPEN` without repository authority.
- Output is canonical JSON; `input_sha256` binds the input envelope and
  `receipt_sha256` binds the report body.
- `mutations_performed` is always zero.

## Validation

Focused command:

```bash
python3 -m unittest -v test_demand_authority_audit.py
```

Pre-publication local result for issue #14369: 18/18 PASS plus
`python3 -m py_compile host/demand_authority_audit.py` PASS.

Hostile coverage includes merged+present happy path, missing evidence, absent path,
open carrier, unproven merge ancestry, canonical-head drift, repository and GitHub issue
fences, stale repository-artifact fence, landed successor, unproven successor,
contradictory path evidence, cross-repository evidence, wrong-repository PR URL,
unsafe paths, deterministic receipts, and Slack-state non-authority.

## Non-goals

This is not a Slack bot, not a queue auto-closer, not a capability reservation system,
and not an outreach mutex. It complements those systems by reducing false work at the
feed/authority boundary. It deliberately leaves queue mutation to a separate, current
read-and-write step so stale evidence cannot silently erase work.
