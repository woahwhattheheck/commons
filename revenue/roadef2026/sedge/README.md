**Container validation passed:** [GitHub Actions run 34080604676](https://github.com/woahwhattheheck/commons/actions/runs/34080604676) built the exact source ZIP and executed it under Ubuntu 24.04 with networking disabled. See [CONTAINER-VALIDATION.json](CONTAINER-VALIDATION.json) and the updated [two-page method](method.pdf). The ZIP is the preserved original source snapshot; its embedded status notes predate this container result. This page and the separate method PDF carry the current status.

Download [source.zip](source.zip) for the complete buildable directory, including vendored headers and the method note. Extract it before running Make. The files beside this page are also exposed for direct review.

The ZIP includes validation summaries; detailed input fixtures, predicted loads and official checker outputs are in the separate evidence archive. Full validation evidence is saved as `2026-09-07-roadef-validation.zip`; identifier `libfile_4daf3e74ade08191a01bbd4da78c68f9`.

# SEDGE routing solver - ROADEF/EURO 2026

A working C++20 candidate for the offline T-adaptive segment-routing challenge.
It emits a zero-change incumbent immediately, then improves routing while checking
every affected transition budget. The four-argument `run.sh` matches the organizer's interface.

**Status, 7 September 2026:** native implementation and public-instance validation complete.
All 12 set-B instances pass the official checker and improve its full six-decimal
lexicographic ranking over empty-waypoint routing. Seven also reduce the maximum load.
This package is not a registration, submitted entry, qualification, award, or Orange contract.

## Run

```sh
make
./run.sh network.json traffic.json scenario.json result.json
```

Only a C++20 compiler and Make are required for the native solver. RapidJSON is
vendored with its original license. There is no runtime download, API, commercial
solver, GPU, Python, or network dependency. Python 3 is needed only for the verification scripts.

The default search allowance is 565 seconds from process construction. SIGTERM or
SIGINT stops search and writes the latest result. Updates use a temporary file and
atomic rename. `run.sh` uses `exec`, including when filenames contain spaces.

Optional environment settings:

| Setting | Purpose |
| --- | --- |
| `SEDGE_SECONDS=15` | Short trial, including initial model preparation |
| `SEDGE_MAX_ROUNDS=4` | Fixed search-round limit for repeatability checks |
| `SEDGE_STATS=/path/stats.json` | Diagnostic loads, budget costs and search counts |

The seed is fixed at 20260907. Fixed-round runs were byte-identical. Wall-time-limited
runs can end at different points on different machines. A disconnected demand is
reported as an error; the algorithm cannot create physical connectivity. Input metrics
and capacities must be positive, as in all tested supplied instances.

## Method

For each time and destination, lazy reverse Dijkstra builds the shortest-path
forwarding DAG after that time's interventions. Unit traffic splits equally among
outgoing shortest-path arcs at every visited node. The implementation caches sparse
segment load coefficients, with a bounded segment cache, and composes those segments
for each demand's waypoint list.

Search first changes a demand's route throughout the horizon. This keeps all time
transitions identical for that demand and spends no reconfiguration budget. Later,
single-slot, prefix and suffix changes use the exact symmetric difference between
successive segment sets. Every affected transition is checked before accepting a move.

Demand candidates are prioritized by contribution to a highly loaded link/time pair.
Waypoint candidates combine neighboring nodes and a seeded sample. Moves remove,
replace, prepend or append waypoints, using up to three waypoints (four segments),
and respecting a smaller input segment limit. This is a heuristic neighborhood, not
an exhaustive or optimal algorithm.

Moves compare the sorted multiset of affected utilizations. Unchanged entries cancel
in lexicographic comparison. The checker truncates decimal output; the acceptance
comparison uses conservative bounds around changed loads at six decimal places to
avoid treating floating-point accumulation noise as an improvement.

## Evidence

`benchmark/summary.json` pins source, binary, checker, input and solution SHA-256
values. Each instance directory retains the exact solution, full load predictions,
official checker output at 12 and 6 decimal places, baseline result, and solver log.

All 12 results were produced with a 15-second search allowance, two independent
processes at a time. Every official check returned `valid: true`. All 369,960
link/time values agreed with the checker within approximately 1.001e-12, and the
independently reported total transition costs matched. The longest measured native
trial, including process cleanup, was 15.40 seconds. These are public-instance results;
hidden-instance performance and competitive rank are unknown.

`behavior/summary.json` records seven further checks: unequal-branch ECMP,
noncontiguous node IDs, intervention-driven forwarding changes, a zero change budget,
fixed-round repeatability, quoted filenames and graceful SIGTERM. The signal test
returned a checker-valid file and exited in approximately 0.017 seconds after SIGTERM.

To reproduce independently:

```sh
git clone https://gitlab.com/Orange-OpenSource/network-optimization-tools/challenge-roadef-2026.git challenge
git -C challenge checkout d84d319a7fdb8de3b1866830d2eaa2937871e5ae
git clone https://gitlab.com/Orange-OpenSource/network-optimization-tools/networktools.git networktools
git -C networktools checkout aebafc9ee91891e5d721bb86725e8cf1533877d1
make -C challenge/checker/src IDIRNT="$PWD/networktools/networktools"
python3 verify.py --data challenge --checker challenge/checker/src/checker-v1.2.2-x86-64_linux --output replay --seconds 15
python3 check_behavior.py --data challenge --checker challenge/checker/src/checker-v1.2.2-x86-64_linux --output behavior-replay
```

## Remaining entry work

1. Container execution is complete: run 34080604676 built the supplied Ubuntu 24.04
   Dockerfile and validated setB-01 with networking disabled. It matched all 10,368
   link/time values within approximately 1.001e-12 and reduced MLU from 0.999998
   to 0.532975 in 20 seconds. The source ZIP and runtime files remain unchanged.
2. Establish the actual team member details and obtain the organizer-issued team ID
   through the official registration form. No registration or submission was sent
   by this build session. Check existing registration correspondence before creating another.
3. Run the longer competition-budget trials if optimizing entry quality; keep the
   existing valid public-instance solutions and their evidence. A stronger solver,
   wider waypoint neighborhood and multiple-demand exchanges can improve quality.
4. Use the included two-page method note and Docker/source files in a ZIP named
   for the real team ID. Qualification is due 14 September 2026 at 23:59 French
   local time (21:59 UTC). Use 12 September as the conservative registration action date
   from the original opportunity card, rather than treating it as a separately verified cutoff.
5. Send through the authorized organizer route only after the actual team registration
   and executable container are ready; retain the organizer's acknowledgement.

The official checker v1.2.2 also produced an intervention discrepancy on a synthetic
fixture with noncontiguous *link* IDs. This observation is retained under
`checker-link-id-observation/`; it is not a defect claim about the public set-B files,
whose IDs are contiguous. The solver follows the documented JSON link IDs. Confirm
the checker's expected mapping before relying on noncontiguous-link inputs.

## Sources and attribution

- [Official challenge and eligibility](https://roadef.org/challenge/2026/en/)
- [Official schedule](https://roadef.org/challenge/2026/en/calendrier.php)
- [Registration](https://roadef.org/challenge/2026/en/registration.php)
- [Pinned subject, rules, instances and checker](https://gitlab.com/Orange-OpenSource/network-optimization-tools/challenge-roadef-2026/-/tree/d84d319a7fdb8de3b1866830d2eaa2937871e5ae)
- [Networktools checker dependency](https://gitlab.com/Orange-OpenSource/network-optimization-tools/networktools/-/tree/aebafc9ee91891e5d721bb86725e8cf1533877d1)
- [Originating Slack opportunity](https://tokenjunkielabs.slack.com/archives/C0BUY3EKMSB/p1788750090535979)

Solver and verification implementation: SEDGE / ChatGPT Work for TokenJunkieLabs.
The task, public instances and independent checker are Orange's. RapidJSON remains
under its bundled upstream license. No submission or result is attributed to Orange.
