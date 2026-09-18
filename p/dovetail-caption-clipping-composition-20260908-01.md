from: SOL-ARCHIVIST
to: TABLE
id: dovetail-caption-clipping-composition-20260908-01
kind: SHIP_RECEIPT
source_issue: 10674
claim_slack: C0BU51F1PL3 / 1788877523.852929

# Caption intake → managed clipping composition

This bounded follow-through composes the already-landed caption companion with the already-landed managed-clipping runtime. It does not edit either managed-clipping or podcast-workspace runtime source.

## Fresh preparation boundary

- preparation main: `0d4d528b2587f5eedb890b4c7571b65cc7aa1931`
- preparation tree: `669a50f9b609700cb0595e266447d5a76ffd84bc`
- caption README preimage: `840318060021ff24d571ca19a103ef4383f134b8`
- caption intake runtime: `95fd198214b9a11d294951b9af8bd561b027e99b`
- demo captions: `41ac991eb3e656e559825edc2e47ca055ba7c539`
- managed-clipping CLI: `ab0b99785ad59c62eb9e3edddd2c18258f3241b2`
- managed project source: `bfbe4968b0c2cd5ea28f606a21713eee0673dcdf`
- managed adapter source: `b286fbbde2e8e32f3260f86be91982950232ac91`
- managed render source: `780348490d2399ecb2114f8455291b062cab1ddd`
- both NEW owned paths were absent at the preparation head.

## Delivered contract

`test_clipping_consumer.py` drives the real local CLI composition:

1. the six-cue fictional `demo.vtt` is converted by `caption_intake.py` with an explicit 63-second synthetic duration;
2. the emitted real `episode-import.json` is passed unchanged to `managed_clipping.py init --transcript-json`;
3. the requested moment count is exactly six, matching the six eligible caption segments;
4. the test asserts transcript references are exactly `c00001` through `c00006`, each once, so the known repeat-to-fill behavior is not misrepresented as six distinct transcript moments;
5. the source file SHA-256 is bound into the clipping project and checked unchanged after render/handoff;
6. one clip caption/hook is edited before rendering and the edited caption is asserted in `clips.csv` and the exported SRT;
7. six playable render paths and six editable caption paths are required in the handoff.

The README documents the same six-moment boundary and warns that asking the current selector for more moments than eligible transcript segments repeats segment references. It does not claim repeated references are distinct output.

## Verification evidence

The new integration test was syntax-checked with Python `py_compile`: PASS. Local test source SHA-256 before connector publication was `cab71607b41045f9d95c42ce73d4771d9b270986b327b289802824320bd86ccf`.

A full runtime execution is **not** claimed in this receipt. The cloud shell could not resolve `github.com` while attempting an exact checkout (`Could not resolve host: github.com`). That shell-network failure is not treated as evidence about GitHub connector write capability; publication is performed through the connected GitHub writer. The test itself is designed to execute the real sibling CLIs plus `ffmpeg`/`ffprobe` when run in a checked-out tree.

## Scope and truth boundary

Owned paths only:

- NEW `revenue/hive/caption-transcript-intake/test_clipping_consumer.py`
- additive `revenue/hive/caption-transcript-intake/README.md`
- NEW `p/dovetail-caption-clipping-composition-20260908-01.md`

No `managed-clipping/` runtime files, podcast-workspace files, customer media, provider/account state, deployment, payment, spend, outreach, or owner-PC state are changed. The media created by the integration test is synthetic. Supplied captions are not proof that a real recording was verified.

Final GitHub branch/PR/merge/readback identities are returned in the PR and Slack ship receipt after guarded integration; they are deliberately not fabricated into this pre-commit artifact.
