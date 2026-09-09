# Lantern canonical chess-square collision repair

Operation: `lantern-chess-canonical-square-repair-20260909-01`
Source package: `astra-lantern-community-chess-20260908-01`
Source PR: #11215
Independent review blocker: `5157845864`

## Finding

The landed chess metadata validator normalized piece-square keys with the shared `text(..., maximum=2)` helper but did not reject duplicate canonical squares after normalization. A host payload containing both `"g1"` and `" g1 "` was therefore accepted and silently allowed the later piece to overwrite the earlier authored piece at canonical square `g1`.

That behavior contradicted the package's fail-closed malformed-metadata boundary and made board provenance ambiguous.

## Repair

`validate_chess()` now rejects a piece square if its canonical value already exists in the board map, before assigning the piece. The existing invalid-metadata test now includes the canonical-collision reproducer and continues to verify that rejected metadata creates no event.

No core `app.py`, schema, browser UI, authored move mapping, answer scoring, scheduling, retry, reconnect, leaderboard, results export, provider, customer, or platform semantics changed.

## Exact preimages

- `revenue/hive_community_events/chess_challenge.py`: Git blob `90e2dbf00a827db949dc058fe8499bf892bc31bb`
- `revenue/hive_community_events/test_chess_challenge.py`: Git blob `d03e07cc1dd9d333cf863ba8b4d500061b7e251c`
- current Lantern core `app.py` remained blob `6d039f0c17312eb023979a567c56ed3dd3b318b8`

## Acceptance

- `python3 -m py_compile app.py chess_challenge.py test_chess_challenge.py` — PASS
- `python3 -B -m unittest -v test_chess_challenge.py` — 8/8 PASS using real SQLite/reopen and loopback HTTP
- `node --test test_chess_ui.cjs` — 4/4 PASS; UI helper is unchanged
- canonical collision `pieces={"g1":"N"," g1 ":"B","e8":"k"}` now returns HTTP/domain validation status 422 and leaves event listing empty
- scheduled state still exposes no questions/board metadata; open state still hides `correct`; finished scoring/reconnect semantics remain core-owned

## Boundaries

Additive bounded repair only. No provider/customer/platform install, outreach, payment, wagering, production action, owner-PC action, force-push, or unrelated Hive/TITAN mutation.
