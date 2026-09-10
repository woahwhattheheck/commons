# TITAN V3 stranded-HIRE realized-payback gate

Operation: `TITAN-V3-STRANDED-HIRE-REALIZED-PAYBACK-GATE-20260910-01`

This is an exact stacked successor to PR #12042 at commit
`cf2047e80772319e920fe013ae8a427ef2d077ea`. It consumes, but does not replace,
PR #12074's official paired evidence: all 36 paired cells lost own cash, while
instrumented probes isolated one step-121 HIRE at a five-dollar cost with no
observed in-episode return.

## Source-real gap

The predecessor proves two facts: the represented next route row names one
missing hand, and the inserted HIRE completes in the exact current market prefix.
Neither fact proves that the newly created actor can execute its command or that
its work realizes enough cash to repay the exact HIRE cost.

This successor makes mutation conditional on a second, independent certificate.
The certificate:

1. authenticates an exact inert-row-to-HIRE replacement or trailing HIRE append;
2. checks the supplied cost against the official Fibonacci HIRE cost;
3. replays current market effects and the official current-turn plant decay;
4. materializes the candidate actor with the official spawn primitive;
5. replays no-HIRE and HIRE arms through that hand's remaining same-day lifetime
   with official unit and plant-decay primitives;
6. rejects a represented-route decision checkpoint inside the replay horizon;
7. rejects future market dependencies other than represented SELL rows;
8. permits the new actor only PASS, movement, HARVEST, DROP, and
   COLLECT_FERTILIZER, so no unpriced seed, feed, fertilizer, placement, or build
   dependency can be laundered into the proof;
9. requires the newly unlocked first command itself to change state;
10. vetoes any per-step or per-product completed-sale displacement; and
11. admits incremental sales only when deterministic town absorption and the
    monotone official curve prove they must quote at the global price floor.
    WHEAT and FERTILIZER are refused because hidden rival BUY_PRODUCT orders can
    raise their price. Floor-priced sales do not increase public supply, so the
    admitted units repay the HIRE without creating a downstream price externality.

The step-121 flat-tax predecessor is therefore rejected when its extra actor
produces no differential completed sale. Price upside, future-day carry,
unrepresented purchases, delayed production, and policy transforms beyond the
currently represented route are deliberately ignored. That makes this a
conservative source admission screen, not a gameplay-strength or leaderboard
theorem; the official paired action panel remains authoritative.

## Files

Runtime changes are limited to:

- `main.py`: supplies the exact post-unit state and route to the certificate;
- `missing_hire_recovery.py`: requires an explicit `admit is True` payback packet;
- `realized_hire_payback.py`: fail-closed public certificate boundary;
- `realized_hire_payback_common.py`: strict cloning, state, and exact queue-delta guards;
- `realized_hire_payback_market.py`: monotone price-floor and town-absorption proof;
- `realized_hire_payback_replay.py`: official unit-stage and represented SELL helpers;
- `realized_hire_payback_loop.py`: no-HIRE/HIRE same-lifetime differential replay;
- `realized_hire_payback_finish.py`: non-displacement, coverage, and receipt closure.

The two test modules retain all seven predecessor bridge tests and add contracts
for missing/malformed/negative payback packets, detached callback inputs, exact
price-floor coverage, official HIRE-cost binding, current-step decay, route checkpoints, hidden rival buys, public price externalities, no-op and
incumbent-output laundering, per-product displacement, market dependencies,
day-close expiry, determinism, and non-mutation.

`SOURCE.json` binds the exact parent executable blobs, evidence PR, allowed diff,
and successor file digests. `verify_source_contract.py` enforces those bindings
on the exact event head before tests run.

## Validation and disposition

Local source-independent validation:

```text
python -B -m unittest -v test_missing_hire_recovery.py test_realized_hire_payback.py
31 tests passed
python -B -m py_compile main.py missing_hire_recovery.py realized_hire_payback*.py test_missing_hire_recovery.py test_realized_hire_payback.py
passed
```

No fresh game, seed, provider, Kaggle, submission, canonical archive/config/pointer,
or leaderboard state is changed. Integration and an official paired action panel
remain with T08 and the existing owners. The intended disposition is a stacked
source-real successor: merge or squash only after #12042, then measure the
composed exact head against its parent before any promotion decision.
