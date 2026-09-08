# ROADEF A-RANK1 continuation

This is a bounded execution harness for the three remaining **rank-one** set-A
gaps identified by the authoritative 30-second calibration. It is not a new
portfolio, a set-wide rerun, or a qualification submission.

The harness resumes the exact selected incumbents from GitHub Actions run
`34197720573`, artifact `10044831235`, using the same frozen composed candidate
source (`75897709…`). It runs only A04, A14 and A16 for 180 seconds each, with
the existing directed and joint neighborhoods, then independently checks each
complete solution at both six and twelve decimals.

Targets:

| Instance | Peak coordinate | Calibrated candidate | Published reference |
|---|---|---:|---:|
| A04 | t1 `43→12` | 0.587276 | 0.581237 |
| A14 | t1 `215→122` | 0.533147 | 0.517621 |
| A16 | t1 `131→228` | 0.079918 | 0.044262 |

A04 and A14 seek a feasible diversion below the next load. A16 is treated as a
multi-period structural case because the same arc is also the t0 maximum. The
solver's existing exact ECMP, route validity, transition budget, segment limit,
and full sorted-vector acceptance remain authoritative.

## Execute

The workflow `.github/workflows/roadef-a-rank1.yml` supplies the frozen source,
official corpus and selected incumbent artifact. The direct command is:

```sh
python3 -B run_rank1.py \
  --context /path/to/built-context \
  --official-root /path/to/pinned-official-checkout \
  --calibration /path/to/calibration-artifact \
  --candidate-source /path/to/frozen/main.cpp \
  --output /fresh/output \
  --seconds 180 --case-timeout 245
```

The output retains the incumbent and continued solutions, 6/12-decimal checker
reports, solver statistics, stdout/stderr, input identities, first changed rank,
and target-coordinate movement. A continuation is rejected if it worsens the
official six-decimal vector.

No Gmail draft, attachment, organizer communication, competition upload, or S139
submission is performed. The standing submission hold remains unchanged.
