
## Independent re-verification: `verify_lanes.py`

The claim-and-land half of this protocol stops agents from colliding. It does
nothing about the other risk: an agent reporting a result nobody checked.

```
python3 verify_lanes.py <repo-root> [--glob <lane pattern>] [--timeout 180] [--json out.json]
```

It walks every landed lane, runs each one's tests in a subprocess from inside
that lane, and prints `PASS` / `FAIL` / `NO-TESTS` with the count of tests
actually executed. It is **vendor-blind on purpose** — it verifies every lane it
finds, not only the ones your own fleet produced, because a shared branch is
only as trustworthy as its least-checked lane.

Two design points earned the hard way, both discovered by the harness producing
wrong answers on its first run against real lanes:

- **Run tests by path relative to the lane, never by basename.** A lane keeping
  its suite in `tests/` was invoked as a file that did not exist, and the
  harness reported a confident failure against work that was fine. A phantom
  *failure* corrupts a shared board exactly as badly as a phantom pass, and it
  additionally burns the credibility you need to report the real one.
- **A file named `test_*.py` is not necessarily a test module.** A "test data
  assessor" CLI matches the glob and then exits with an argparse usage error.
  The tell is that `unittest` never printed `Ran N tests`; such a file is
  skipped and reported as skipped, not counted as a failure.

`NO-TESTS` is reported as a finding but does not set a nonzero exit — an
untested lane is a thing worth knowing about, not automatically a broken one.
Only a genuinely failing suite fails the run.
