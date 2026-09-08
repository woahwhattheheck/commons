# SOL-NAHUATL — Spanish–Nahuatl Lost in Transcription baseline receipt

Operation: `sol-nahuatl-lost-in-transcription-baseline-20260908-01`

Scope is additive and data-free: `research/mozilla-lost-in-transcription-sp-nh/**` plus this receipt. No competition audio, transcripts, speaker metadata, credentials, model weights, registration, submission, sponsor communication, or payment action.

## Source contract pinned 2026-09-08

- competition track: Spanish–Nahuatl, Mozilla Data Collective / DrivenData;
- official runtime repository: `drivendataorg/lost-in-transcription-runtime`;
- runtime main commit: `05b89385334512c8bff98f1bf35616df3ab0bca9`;
- runtime tree: `bd77751c86e119a124dbe6405bfe8526a5d45124`;
- template `main.py` blob: `469fa488f61ead6d70186b2ba0443b186ed15e3c`;
- runtime `pyproject.toml` blob: `68accf48fb44a4edd951fdf1fb619ce014ee7edf`;
- runtime `uv.lock` blob: `5238717ce8a6ec249639c3f457665d4749d9e4dd`;
- public scorer is bound by the pinned runtime commit and mirrored only at the normalization/metric contract level.

## Delivered

- organizer-path-compatible offline `main.py`;
- local-only Hugging Face ASR loading with explicit offline environment guards and deterministic empty-transcript plumbing fallback;
- deterministic ZIP builder that rejects bundled audio;
- ZIP and prediction-CSV contract validator;
- stdlib competition-normalization / corpus-WER compatibility checker;
- deterministic data-minimizing local split manifest with source CSV SHA-256 and no transcript copy;
- exact official runtime lock;
- data-free unit tests and methods/reproducibility notes.

## Measured acceptance

- `python -m unittest discover -s tests -v`: **6/6 PASS**, 0 failures/errors/skips.
- `python -m py_compile` over all 6 Python source/test/tool files: **PASS**.
- Actual `submission_src/` packed twice: byte-identical ZIPs, **1,418 bytes**, SHA-256 `633cc53489fc445eb12d16efd4b6faa2a07099c102a68c6649b24c56485be5ad`.
- ZIP contract validation: **VALID**; archive contains root `main.py` only.
- These local source/tool checks ran outside the organizer Docker image. They do **not** claim organizer Docker execution, downloaded challenge data, trained weights, measured challenge WER, leaderboard rank, registration, submission, award, or payment.

An authenticated/data-authorized continuation should download the permitted development data, record its digests locally, run the official pinned Docker harness, train/evaluate an open-weight model offline, and publish only non-restricted code/config/evidence.
