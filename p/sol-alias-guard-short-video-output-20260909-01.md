# SOL Alias Guard — Hive003 output/source collision repair

Operation: `sol-alias-guard-short-video-output-20260909-01`
Demand: `bm-hive-20260908-003` follow-through
Slack claim: `C0C05UU6WKG / 1788974439.244109`

## Scope

Only:
- modified `revenue/hive/short-video-studio/studio.py`
- new `revenue/hive/short-video-studio/test_output_alias.py`
- this receipt

No UI, provider, customer, publishing, spend, TITAN, or other Hive paths are changed.

## Fresh-main preimage

Publication base: `b9e8f85b191f6343941310e9ead74c1281a51b70`
Base tree: `8146a2e72113a4a1d48e21b86bebfd9527061148`
A preparatory base (`d0ae73bfea49f8f054ec8e38b31a304d77dbe791`) advanced disjointly before tree creation; the owned preimage and both new-path absences were re-audited on this final base.
Existing `studio.py` Git blob: `ba19814ceb97ae25b377f96bdbfb12e158bc3145`
The two new destination paths were 404/absent on that base.

The locally reconstructed preimage hashed byte-for-byte to the same Git blob `ba19814ceb97ae25b377f96bdbfb12e158bc3145` before modification.

## Reproduced defect

Current `render_project()` parsed an editable project and then allowed the render output to alias that same file. A valid JSON project named `editable-project.mp4` was passed as both project and output. Baseline result:

- before: JSON, 294 bytes
- after: MP4, 134,877 bytes
- source bytes changed: yes

That violates the product's source-preservation/editability contract.

## Repair

The renderer now rejects canonical-path and existing-file identity aliases before creating the output directory or writing captions. Both render and caption outputs are protected from aliasing:

- the editable project file;
- every validated local segment image asset;
- validated file-backed audio sources;
- each other.

Existing hard links are detected with `Path.samefile`, in addition to resolved path/symlink identity.

## Acceptance

Command:

`python3 -m unittest -v test_studio.py test_numeric_bounds.py test_app_errors.py test_output_alias.py`

Result: **15/15 PASS**, zero failures/errors/skips in this cloud runtime, including the original real FFmpeg/ffprobe render.

New cases prove no mutation for:
1. render output == editable project;
2. caption sidecar == editable project;
3. render output hard-linked to a segment asset;
4. render output == file-audio source.

`python3 -m py_compile studio.py app.py test_studio.py test_numeric_bounds.py test_app_errors.py test_output_alias.py` also passed.

Candidate hashes before connector publication:
- `studio.py` SHA-256 `87bc9869f2ffb30ec0fbd148c7d6dfb926262e9d2f322c22f7978a905084c1ab`; Git blob `06019a9832ebb9ad39a08d1878218e9998bb83c0`
- `test_output_alias.py` SHA-256 `0b93e2208fd54c9f89e42e5b501826d7517666cb2b72baaf6087c39ac882eee1`; Git blob `41988eff4e250dd826261951678f9c72482a1184`

No external customer/provider action or force-push is part of this repair.
