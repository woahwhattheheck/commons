# TITAN joint-capacity canonical adoption

## Change

The existing deterministic TITAN builder adopted the landed shared-capacity prior-sale source into the one current package. Default configuration and policy selection are unchanged.

- source Git blob: `7967fb43c64bc3154fe7da609497873163c773eb`
- previous archive SHA-256: `26e19f9abe986ab93873ff993cea38042921d685f099d65a96fd5edc795a43b2` (289487 bytes)
- current archive SHA-256: `501695d66c2642d452180b2f129d181ba0ede02647b70ddd74ebd82e3762011c` (290630 bytes)
- current source-manifest SHA-256: `6ebc0f3c6e6d6e9815623920cbbaacd49efdc5bb96acb6def2ad8677b4bff555`
- packaged runtime files: `78`

The archive member `reference/titan-history/selected_action_history.py` is byte-identical to the landed repository source. The superseded current archive is retained under its digest when the bytes changed.

## Validation

- `python3 -B build_integrated.py`
- `python3 -B build_integrated.py --check`
- focused shared-capacity tests
- existing history-archive, terminal-history, and release-consistency tests

This is source-closure adoption only: no default/configuration change, game, seed, strength attribution, provider upload, or submission.
