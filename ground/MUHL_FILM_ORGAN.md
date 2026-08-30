# MUHL FILM ORGAN — REFERENCE VISOR

Inventor: Bryce Muhlnickel. Integrated by DEMON on 2026-08-30.

**State: SPEC_INTEGRATED. MOVIE_EXECUTED: NO.**

This closes the build gap honestly: the in-tree Life organ and deterministic source now have a validator and a public reference visor. It does not convert metadata into a feature-length execution receipt.

## Exact reference

- reel: `muhl/docs/FILM_REEL.pfc`
- bytes: **2,498,592**
- magic: **PFCGAME1**
- SHA-256: `27d8371e8968ed6bccc0fd27400e35e78fb7e7da87f7c472b175ba08a6901e88`
- source: deterministic 64×64 LCG seed 7 at 30% density
- deterministic live cells: **1,212 / 4,096**
- prior stub: **24 / 24** ticks from the historical film contract
- declared feature length: **129,600** pulses = 5,400 seconds × 24 fps
- executed feature pulses here: **0**

**129,600 pulses were not executed.** No byte-exact feature run is claimed. The existing 24/24 evidence remains a prior stub, not a movie.

## Boundary

No invented mouth or destination. No host frame simulation. No gate walk. No titan write. No fire 337, pulse 78, light 7913, or DC injection. No mp4, ffmpeg, private owner media, or pirated media. No auth. No gate.

The only `--go` path in the validator is an inert refusal that returns `REFUSED` and performs no mutation.

## Measure

    python3 host/muhl_film_organ.py --root .
    python3 host/muhl_film_organ.py --self-test
    python3 -m unittest -v test_muhl_film_organ.py

Public surface: [film.html](../film.html). Historical contracts remain byte-untouched: `muhl/docs/FILM_ORGAN.md`, `muhl/docs/FILM_GO.md`, and `muhl/docs/FILM_REEL.pfc`.
