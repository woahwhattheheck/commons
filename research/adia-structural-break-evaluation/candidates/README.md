# Frozen empirical-window candidate

Run the commands below from `research/adia-structural-break-evaluation/`.
The parent [workbench README](../README.md) describes source fetching and the
synthetic corpus/scoring contract.

`candidates/calibrated.py` is an additive research candidate, **not an automatic
replacement for the existing competition submission**. Its exact SHA-256 is
`24b3afcb5e096de264dab9889512375fa935f13481fa3dd7922e95be5abef8f1`.
The model, test source, development range 10000-10015, previously inspected
baseline range 20000-20063, and fresh held-out range 30000-30063 were locked in
`candidates/experiment_lock.json`. The model hash and fresh range were also posted
in the [specialist Slack thread before evaluation](https://tokenjunkielabs.slack.com/archives/C0BVDDS04G2/p1789460126337379).
No candidate parameters were changed after held-out outcomes were observed.

The candidate retains the original multiscale feature idea and two-full-horizon
plus current-point corroboration, while making three substantive changes. It
estimates each window statistic's dispersion from rolling historical windows,
adds 128/256-point horizons, and adds a bounded continuous current-evidence term
to the output logit. The last change reduces low-score ties: it affects ranking
well before the 0.5 alarm threshold. The output is a ranking score, **not a
calibrated posterior probability**. Initialization uses NumPy; persistent online
state is bounded. Causal prefix, restart/interleaving, shift/scale invariance,
warm-up, isolated impulses, historical outliers, and invalid-input behavior have
19 dedicated regression tests, all passing normally and under `python -O`.

On the frozen fresh-seed panel, **1,152 series / 383,040 predictions per model**,
TS-AUC is **0.9193785618737772** versus the unchanged reference's
**0.8475423360426424**. Candidate-minus-reference is **+0.0718362258311348**;
500 paired whole-seed-cluster bootstrap replicates give a 95% percentile interval
of **[+0.06751012460077083, +0.07757183472577286]**, with zero degenerate replicates.
This interval is conditional on the designed synthetic mixture, not the unknown
organizer distribution. The experiment does not estimate prize odds.

At threshold 0.5, false-alarm counts out of 64 null series are:

| Null process | Reference | Candidate |
| --- | ---: | ---: |
| AR(0.85) | 27 | 3 |
| GARCH | 17 | 8 |
| Heavy tails | 1 | 0 |
| Independent Gaussian | 0 | 0 |
| Outlier contamination | 2 | 2 |
| Stable seasonality | 0 | 0 |

`candidates/heldout_report.json` retains metrics, source/corpus/trace/core-report
and full-summary hashes, per-change diagnostics, bootstrap, versions, and the
canonical CLI exit-zero receipt. The full raw traces regenerate with the command
below. A staged execution and a separate canonical CLI execution produced exactly
the same candidate/reference summaries and paired comparison. Two earlier
blocking-tool attempts timed out without completion markers; neither was counted
as successful execution. The canonical run completed in 39.85 seconds on this
cloud sandbox; timings are descriptive, not portable performance guarantees.

```bash
python -m unittest discover -s candidates -p 'test_calibrated.py' -v
python -O -m unittest discover -s candidates -p 'test_calibrated.py' -v
python stress.py --detector candidates/calibrated.py \
  --expected-sha256 24b3afcb5e096de264dab9889512375fa935f13481fa3dd7922e95be5abef8f1 \
  --reference "$SOURCES/detector.py" \
  --reference-sha256 1f4c94475e91fc76905b4ad0351d4391c35f7b20f1a1c26eba89ad828a386ae7 \
  --seed-start 30000 --seeds 64 --bootstrap 500 --out /tmp/adia-candidate-new-run
```

### Attribution rather than a single-cause story

After the frozen held-out test, three one-factor ablations were executed **only
on the development range**, without tuning or reselecting the candidate. The
literal patches, source hashes and results are in `candidates/ablation_report.json`;
run `python candidates/replay_ablation.py` to reproduce all three. Each row removes
one feature from the complete new candidate, not from the original reference:

| Development model | TS-AUC | AR null alarms / 16 | GARCH null alarms / 16 |
| --- | ---: | ---: | ---: |
| Complete frozen candidate | 0.918813 | 1 | 1 |
| Replace empirical dispersion with independent-observation scaling | 0.912863 | 9 | 4 |
| Remove 128/256-point horizons | 0.900460 | 1 | 1 |
| Remove the continuous low-score ranking term | 0.866798 | 1 | 1 |

Empirical dispersion is valuable for dependent-null alarm control, but **the
continuous score term explains much of the observed ranking gain**. These
one-factor contrasts interact and must not be added as independent contributions.
The retained generator also includes very short online series where both models
have limited warm-up opportunities. Further work should test real permitted
organizer data and broader distribution shifts, preserving this candidate as a
frozen comparator rather than tuning repeatedly on these now-observed seeds.
