# Filesystem-safety screen for the engagement delivery kit

A read-only static screen that answers one question about every Python tool in
the kit: **can it destroy a path the caller names?**

Python 3 standard library only. No network. It reads modules to parse them and
writes only inside `--output-dir`.

## Why it exists

The operator handoff kit (UIOWA-100) hands a new operator a menu of commands
spanning the whole engagement tree, and those commands get pointed at a
directory of real client evidence. Several of them call `shutil.rmtree` and
`subprocess.run` from non-test code. Most of that is certainly legitimate — a
verifier cleaning up its own temp copy is exactly right — but nobody had checked
**which `rmtree` targets a scratch directory and which targets a path that
arrived from `argv`**. A closeout kit that can delete the evidence it exists to
account for is a liability, so that question deserved an answer rather than an
assumption.

## What it is not

**This is a screen, not a proof.** `CLEAN` means the screen found nothing it
could see. It does **not** mean the module is safe. `getattr`, dynamic dispatch,
C extensions, and anything that happens inside a `subprocess` are all invisible
to an AST. There is no safety score, no percentage, and **no lane is ever marked
compliant** — a test asserts the report contains no such verdict. Where the
trace runs out, the finding is `UNDETERMINED`, which exists precisely so that a
screen which cannot tell does not get to report clean.

It also does not modify anybody's code. Findings are reported; each lane's owner
judges them.

## Run it

```
python3 fs_safety.py --root /path/to/revenue --lane-prefix uiowa_rfq_18649 \
    --output-dir examples/live_snapshot
```

| exit | meaning |
| --- | --- |
| 0 | no `REVIEW_REQUIRED` finding |
| 1 | at least one `REVIEW_REQUIRED` finding — a human must look |
| 2 | the scan could not run |

Tests: `python3 -m unittest test_fsaudit -v` — **24 tests**, also green under
`python3 -O`.

## The classifications

`REVIEW_REQUIRED` means exactly one thing: **this tool can remove, move, rename
or truncate a path the caller names.** Everything else is reported separately so
that meaning stays sharp.

| class | meaning |
| --- | --- |
| `REVIEW_REQUIRED` | a destructive call whose target traces to a parameter, `argv`, the environment, or a config value |
| `UNDETERMINED` | the trace ran out, or the module shells out. **Not a pass.** |
| `WRITE_TO_CALLER_PATH` | writes where you pointed it. Normal for a CLI with an output option; deletes nothing |
| `TEST_CONTEXT` | a self-scoped cleanup inside a test module |
| `SELF_SCOPED` | the module created the path it removes (`tempfile.mkdtemp`, a module literal, or a write behind a containment guard) |
| `UNPARSEABLE` | could not be read or parsed — listed separately, **never counted as CLEAN** |

The target trace is a small intraprocedural pass: literals and `tempfile`
factories are self-scoped; parameters, `sys.argv`, `os.environ`, `args.*` and
values read from JSON are external; joins and f-strings are only as safe as
their worst part. It is deliberately not interprocedural — a cross-module tracer
would be guessing, and this screen does not guess.

Two deliberate calibration choices, both learned from the first real run:

- **A delete is not a write.** The first run flagged 32 modules `REVIEW_REQUIRED`
  for `open(path, "w")` where `path` came from `--out`. That is the correct shape
  for every CLI in the kit, and 30 false alarms would have buried the two
  findings that mattered. Writes to caller paths got their own class.
- **A containment guard downgrades a write, never a delete.** A function that
  resolves a path and raises on one outside its directory gets its write
  downgraded. A delete of a caller-supplied path stays `REVIEW_REQUIRED` however
  many guards surround it, because the heuristic can be fooled and the blast
  radius is not comparable.

## What the live snapshot found

`examples/live_snapshot/` is a snapshot at commons commit
`fee74a99db6dd4edb0d43b9962452414419b009f`, 2026-09-19. The tree moves
continuously — re-run the screen rather than trusting the file.

```
modules 162 across 42 lanes
CLEAN 113 · WRITE_TO_CALLER_PATH 24 · TEST_CONTEXT 27
UNDETERMINED 7 · SELF_SCOPED 2 · REVIEW_REQUIRED 2
```

Three call sites in two modules. Both were read by hand rather than left as a
classification:

**1. `uiowa_rfq_18649_capacity_benchmark/generate_collection.py:112` — a live
hazard at snapshot time.**

```python
def generate(root: Path, profile: Profile, seed: int = 20260919) -> dict:
    root = Path(root)
    if root.exists():
        shutil.rmtree(root)
```

`--out` is `required=True` and passed straight in, so
`generate_collection.py --out <any existing directory>` recursively deletes it
with no marker check and no confirmation. Reported to the lane owner; **not
fixed here** — this screen does not edit other lanes.

**2. `uiowa_rfq_18649_acceptance_map/build_index.py:176,183` — already hardened.**
Still flagged, and correctly so: the guard is a runtime check that a static
screen cannot see. The module now refuses unless the directory is empty or
carries its own `MANIFEST.json` marker, and raises `UnsafePacketDirectory`
otherwise. That hardening landed in commit `4cd6ef7473` after this screen's
first finding was posted. It is a good illustration of the tool's limit: the
screen can say "this reaches a caller-supplied path", and only a person can say
"and here is why that is now safe".

## Real vs. draft

**Real and runnable:** the scanner, the tracer, the CLI, the renderers, the 24
tests, and both committed scans — all execute exactly as shown. The three
`REVIEW_REQUIRED` findings are real call sites in code on `main`, verified by
reading them.

**Draft / limited:** the tracer is intraprocedural and heuristic. The
`self.<attr>` resolution is module-wide rather than per-class. The containment
guard is pattern recognition, not verification. False negatives are expected and
the report says so.

## Still UNKNOWN

- **Whether each `REVIEW_REQUIRED` finding is actually wrong** is a judgement for
  the lane owner. The screen reports reach, not intent.
- **What runs inside a `subprocess`** — 7 modules shell out; that is a hole in
  the screen, reported as `UNDETERMINED` rather than papered over.
- **Non-Python tools** in the kit are not scanned at all.
- **Runtime behaviour.** Nothing here is executed; a module that builds a path
  dynamically can defeat the trace entirely.

## Files

| File | Role |
| --- | --- |
| `fsaudit.py` | the scanner: call detection, the target tracer, classification, summary |
| `fs_safety.py` | CLI, Markdown/CSV/JSON renderers, and the single approved writer |
| `fixtures/` | five synthetic modules, one per classification (labeled fiction) |
| `examples/fixture_scan/` | deterministic scan of the fixtures |
| `examples/live_snapshot/` | scan of the live engagement tree at the commit above |
| `test_fsaudit.py` | 24 tests, including the screen applied to its own source |
