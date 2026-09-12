# TITAN V3.1 bench-v2 seat-selector custody

This directory republishes the narrow PRESSURE/selective-rerun seat fix from fleet claim `TITAN-V31-BENCH-PRESSURE-SEAT-SELECTOR-20260911-01` against the exact Slack bench-v2 handoff.

## Source custody

- Slack file: `F0C0YEV23PD` (`Pinned-leader bench tools v2`)
- Original archive SHA256: `b2ebe94e9311e3a344d5434d30b9734efc7239241b30683ebaf8b8712db5f226`
- Visible patch: `bench-v2-seat-selector.patch`
- Visible patch SHA256: `043562b8dd90061402949ccc543a105b19fc0bb5298752f73d8c6881f2cdf71`

This tooling lives outside `candidates/v3/overlay/**`; it is not a submission/package input and changes no gameplay policy, config default, evaluator scoring, opponent, or Kaggle artifact.

## Bug

`windriver.py` PRESSURE records use `candidate_seat`. Existing `leader_pin.py --episodes EP:SEAT,...` compares the supplied seat with the recorded `leader_seat`. Copying a candidate seat into `--episodes` therefore selects the opposite matchup.

## Repair

- Preserve existing `leader_pin.py --episodes EP:LEADER_SEAT,...` meaning.
- Add `--candidate-episodes EP:CANDIDATE_SEAT,...`; candidate seats are inverted to the pinned leader seat before filtering.
- PRESSURE JSON/text now exposes both `candidate_seat` and `leader_seat` explicitly.
- README warns never to paste candidate-seat coordinates into `--episodes`.
- `tools/test_seat_selector.py` binds unchanged leader-seat selection, correct candidate-seat inversion, and invalid-seat fail-closed behavior.

## Exact apply + validation recipe

The patch uses standard `a/` / `b/` paths and is intended to be applied from the extracted `titan-bench-tools-v2` root with `-p1`:

```bash
sha256sum /path/to/bench-v2.tar.gz
# must be: b2ebe94e9311e3a344d5434d30b9734efc7239241b30683ebaf8b8712db5f226

tar -xzf /path/to/bench-v2.tar.gz
cd titan-bench-tools-v2
patch --batch --forward -p1 < /path/to/bench-v2-seat-selector.patch
cd tools
python -B -m unittest -v test_seat_selector.py
python -B -m py_compile *.py
```

Publication revalidation used a fresh extraction of the exact Slack archive above. The patch applied all four paths cleanly; the focused selector suite was 3/3 PASS and all 10 Python files syntax-compiled.
