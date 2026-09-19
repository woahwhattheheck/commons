# Fiction-labeling screen

Read-only screen over the engagement tree. For every artifact that carries
assessment records, it asks one question: **does the file state whether its
contents are synthetic or real?**

Python 3 standard library only, no network. It reads artifacts and writes only
inside `--output-dir`. It never modifies a file it screens.

## Run it

```
python3 label_scan.py --root /path/to/revenue --lane-prefix uiowa_rfq_18649 \
    --output-dir examples/live_snapshot
```

| exit | meaning |
| --- | --- |
| 0 | nothing record-shaped is missing a provenance statement |
| 1 | at least one record-shaped artifact is undisclosed or its disclosure is buried |
| 2 | the scan could not run |

Tests: `python3 -m unittest test_labelcheck -v` — 22 tests, also green under `-O`.

## Classifications

| class | meaning |
| --- | --- |
| `UNDISCLOSED_PROVENANCE` | carries assessment records about the engagement's subjects and states nowhere whether they are synthetic or real |
| `LABEL_BURIED` | a disclosure exists but past the opening bytes of the file (`--header-bytes`, default 1500) |
| `UNLABELED_CONFIG_SHAPED` | schema, vocabulary, weights. **Not a finding** — no disclosure expected |
| `DISCLOSED` | states its provenance, of either kind |
| `NOT_EVIDENCE` | documentation or generic data |
| `UNREADABLE` | could not be read — never counted as disclosed |

**The requirement is a provenance statement, not a fiction label.** A generated
report of a real measurement must not be labelled "SYNTHETIC" — that would be a
false statement. `fixtures/lane_real/scan_results.csv` pins this: it is
`DISCLOSED` while claiming the opposite of synthetic. An earlier version of this
screen asked only "does it say SYNTHETIC" and would have recommended writing a
falsehood into a real output.

Shape is classified before the disclosure is looked for. A coarse
"does-it-say-synthetic" probe over the tree returns dozens of hits that are
weight tables and vocabularies; counting those would overstate the problem
several-fold.

## Live snapshot

`examples/live_snapshot/`, at commons commit
`fee74a99db6dd4edb0d43b9962452414419b009f`. The tree moves continuously — re-run
rather than trusting the file.

```
artifacts examined          544
DISCLOSED                   396
UNDISCLOSED_PROVENANCE       60
LABEL_BURIED                 16
UNLABELED_CONFIG_SHAPED      16
NOT_EVIDENCE                 56
```

76 artifacts across 30 lanes carry records without saying which they are. Each
is listed with its lane in `FICTION_LABELING_SCREEN.md`. These are reported to
lane owners; this screen edits nothing outside its own directory.

One of the 60 was this author's own `uiowa_rfq_18649_filesystem_safety`
`findings.csv`. It is a real scan of real source, so the fix was a `provenance`
column stating that, not a synthetic label. That change is in the same commit.

## What this does not establish

- It reports **disclosure**, not truth. It cannot tell whether content is in
  fact synthetic, and it does not assert that any file contains a real
  University finding.
- Shape classification is heuristic. `RECORDS` vs `CONFIGURATION` is decided by
  identifier density, populated rows, and vocabulary; both false positives and
  false negatives are possible.
- No lane is scored, rated, or marked compliant. A test asserts the report
  awards no such verdict.
- Only `.md`, `.csv`, `.json`, `.txt`, `.tsv` are examined. Files under 40
  characters are skipped.

## Files

| File | Role |
| --- | --- |
| `labelcheck.py` | shape classification, disclosure detection, summary |
| `label_scan.py` | CLI, Markdown/CSV/JSON renderers, the single guarded writer |
| `fixtures/` | six synthetic artifacts, one per classification |
| `examples/fixture_scan/`, `examples/live_snapshot/` | committed runs |
| `test_labelcheck.py` | 22 tests, including the screen applied to its own source |
