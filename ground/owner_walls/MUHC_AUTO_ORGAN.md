# MUHC auto organ — deterministic, complete-container selection

`muhc.py` already provides independently decodable v1 artifacts. The missing organ was honest automatic selection: the existing benchmark tries one stack setting, one fold setting, and only an evolve program supplied by its caller.

`host/muhc_auto.py` closes that gap with a bounded deterministic search:

- build raw, stack, fold, and evolve candidates as complete `.muhc` containers;
- decode every accepted candidate and require exact source bytes plus source SHA-256;
- count header, payload, and checksum—not an unframed entropy score;
- choose the smallest complete artifact, breaking equal-size ties by canonical candidate ID;
- keep all search state in memory and bind it to one source; no persistent cross-source ledger;
- report rejected candidates explicitly instead of turning an encoder failure into a zero.

Example:

```console
python host/muhc_auto.py select input.bin output.muhc --report output.json --width 200 --max-depth 2 --beam-width 4
```

The result report carries every candidate's complete size and artifact SHA. Landing the selector does not claim that any particular future source compresses, that hardware executed it, or that it produced revenue. Those claims require their own measured artifact.
