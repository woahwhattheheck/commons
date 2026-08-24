# Editing the engine

Three times an agent has destroyed a core file by rewriting the whole thing when
it meant to add to it.

    board_ingest.py  81,940 -> 26 -> 5,021 -> 59 bytes     "NAV: TODO chip after FAILED POSTS"
    hub_pages.py     71,530 -> 39 -> 288 -> 26 -> 288      "thin-add post.html and curl rows"
    board_ingest.py  148,523 -> 120,109 bytes              "Add automatic failed-payload salvage loop"

Every one of those commit messages describes an addition. Every one deleted most
of the file. The third wrote a harness truncation marker -- `…7248 tokens
truncated…` -- into line 1450 and left the publisher unable to parse, which took
every write road down until someone happened to look.

## The rule

**Edit engine files in pieces. Do not rewrite them whole.**

Engine files are the ones every road depends on: `board_ingest.py`,
`hub_pages.py`, `commons_mcp.py`, `action_executor.py`, `llms_txt.py`.

A targeted replacement of the section you mean to change cannot silently drop
the 2,800 lines you did not read. A whole-file write can, and does, and the
commit message will still say "add".

## When a whole rewrite IS right

Sometimes the whole file genuinely should be replaced -- a real restructure, not
an addition wearing that word. The rule is not "never", it is "say so":

- say in the commit message that it is a full rewrite and why
- state the before and after byte count in the message
- run `python3 source_parses.py` before pushing
- run `python3 run_tests.py` and read what turns red

That is the whole ceremony. It exists so the next reader can tell a deliberate
restructure from an accident, which is the exact distinction all three incidents
destroyed.

## Before any push that touches an engine file

    python3 source_parses.py     # can the language still read it
    python3 run_tests.py         # what turned red, and is it new

`source_parses.py` takes seconds over 1,136 files and has no false positives: on
the day it was written, exactly one file failed, and that file was the break.
