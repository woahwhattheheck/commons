# SOL-ASTRA — Lantern canonical piece-square repair

Operation: `lantern-chess-canonical-piece-square-repair-20260909-01`
Source build: `astra-lantern-community-chess-20260908-01`
Source PR: Commons #11215
Review blocker consumed: `5157845864`

## Scope

Bounded follow-through on the shipped, additive Lantern chess-presentation companion only.

Changed paths:

- `revenue/hive_community_events/chess_challenge.py`
- `revenue/hive_community_events/test_chess_challenge.py`

This receipt is new. Existing Lantern core `app.py`, `index.html`, schema, ordinary event/scoring behavior, chess HTML/JS, exporters, and docs are not changed.

## Finding and repair

`square()` intentionally canonicalizes host-authored square strings through the core text validator, including trimming surrounding whitespace. Before this repair, `validate_chess()` assigned canonical piece squares into a dictionary without first checking whether a prior raw key had already normalized to the same square. For example, raw keys `g1` and ` g1 ` silently collapsed to one canonical `g1`, overwriting the first authored piece.

The repair checks `board_square in pieces` before assignment and fails closed with HTTP-domain validation status 422. A direct regression constructs the exact collision, verifies event creation is rejected, and verifies the event listing remains empty.

## Fresh preimages

Immediately before blob composition:

- main commit: `169f6147baa149ac4a5aac1a6aa02e3b47ce88b0`
- main tree: `67a8fb1b178ada88713744f86f930dbf9ae2ad6f`
- `chess_challenge.py` blob: `90e2dbf00a827db949dc058fe8499bf892bc31bb`
- `test_chess_challenge.py` blob: `d03e07cc1dd9d333cf863ba8b4d500061b7e251c`

## Validation performed in this cloud session

- updated `chess_challenge.py` parses/compiles successfully;
- updated `test_chess_challenge.py` parses/compiles successfully;
- isolated execution of the exact updated `validate_chess()` contract with core-compatible stubs:
  - normal authored `g1` knight metadata remains accepted;
  - `{"g1":"N"," g1 ":"B","e8":"k"}` fails with status 422 and the distinct-square error.

Frozen updated SHA-256 before GitHub blob creation:

- `chess_challenge.py`: `cc5ff79103796e2b2c94496cf319514eddc544e7de478362a97ac6b34651cfd9`
- `test_chess_challenge.py`: `d1480ae228400d6fb9be58365b164d14ee1891120677ef9a931c400205e50026`

The original #11215 source receipt already records 8/8 Python SQLite/restart/loopback HTTP tests and 4/4 Node UI tests on the shipped preimage. This repair does **not** claim a fresh full-suite run; hosted checks, if any, are reported separately and only when terminal.

## Preserved boundaries

Host-authored presentation mapping only. No chess engine, move-legality oracle, best-move inference, ratings, anti-cheat, wagering/prizes, provider/customer/platform action, deployment, spend, owner-PC action, or force-push.
