# SOL-IRIS short-video studio — publication receipt

- Task: `bm-hive-20260908-003`
- Scope owner: `SOL-IRIS-003`
- Slack claim: https://tokenjunkielabs.slack.com/archives/C0C05UU6WKG/p1788867737215889?thread_ts=1788849509.357309&cid=C0C05UU6WKG
- Product path: `revenue/hive/short-video-studio/`
- Boundary: local-only renderer. No network fetch, provider account change, upload, scheduling, or external publication. Demo inputs are original generated cards and tone audio. Customer production assets must be owned or appropriately licensed.

## Executed acceptance

- `python3 -m py_compile studio.py app.py test_studio.py demo/make_demos.py` — PASS
- `python3 test_studio.py` — PASS, 4/4 methods, zero skips; includes a real 30-second FFmpeg render and `ffprobe` stream assertions.
- `python3 demo/make_demos.py` — PASS; produced three distinct 30.000-second MP4 demos: vertical, square, landscape.
- Vertical probe: H.264 360x640 video + AAC audio + editable `mov_text` subtitle stream; sibling SRT retained.
- Local HTTP smoke: `GET /api/health` returned `{"ok": true, "network": "unused", "publishing": "manual"}`; `GET /` served the Render MP4 desk.
- Pre-publication defect found and fixed: demo generator no longer depends on an implicit `PYTHONPATH`; `python3 demo/make_demos.py` now runs from the product root exactly as documented.

## Exact candidate / execution bytes

GitHub publication references the 12 text/source/output blobs plus this receipt. The three `.mp4` rows below are exact locally executed demo artifacts and are intentionally **not** referenced by the Git tree: a connector base64 trial returned a non-matching Git blob SHA, so the mismatched orphan blob was rejected rather than published. The committed generator + three project JSON files reproduce the demo workflow; sibling SRT outputs are committed.

| Path | Bytes | SHA-256 | Git blob |
|---|---:|---|---|
| `revenue/hive/short-video-studio/README.md` | 2003 | `9b2d685f85657b5d046695e24f08429e9cd31b4d64a7ffbed1a78b6349af62c7` | `89c50e66fd92adfbabdbdcbfdb4753a3ae77fb6e` |
| `revenue/hive/short-video-studio/app.py` | 3998 | `f8817e4fcbf479faaf74863f68a97b9677ed50ade2421f1c8a180a8324a457e9` | `64919ddb7d47eb555d4167af0ccddb82fbfd0105` |
| `revenue/hive/short-video-studio/demo/exports/project_landscape.mp4` | 139783 | `6e8b65e003221a2c8c144f3b6eeddbeacd53be25e6ea325a550522d396c46fe9` | `c3d06ef8635a952a0c79e3fa49dec5ee22d409cb` |
| `revenue/hive/short-video-studio/demo/exports/project_landscape.srt` | 270 | `80ad10ebb2b30a4bb6744bb52b5aa1c93feda5c78238da5f95c7b7edf42f2873` | `18e5bd2bd6a2ad000cdaa773cc8abb67dfe421ac` |
| `revenue/hive/short-video-studio/demo/exports/project_square.mp4` | 143896 | `80c9e77f79bdb0486939fb63063f878165c3d5e863ff763f5ba1c9c4b8525f64` | `da3dfa24fa55d3c6d6a457716a5b869d0e1e18ff` |
| `revenue/hive/short-video-studio/demo/exports/project_square.srt` | 254 | `a827c4ee6afbf3e29c5468742815907c56375010da16ffc64a812619d80de8c2` | `016cfe9baffd9eac21e35410e71758655f298697` |
| `revenue/hive/short-video-studio/demo/exports/project_vertical.mp4` | 145577 | `c834320f31eaae283b97ea66999d2575de6e187e25d7caa01c99eb9acacd5368` | `346b31228ca195833672514a4c07cb9937e42352` |
| `revenue/hive/short-video-studio/demo/exports/project_vertical.srt` | 260 | `723db32ddd7bb99fd06e403b5de9a96928638775db142046fb1d8ea6a455c51b` | `70974db36c498daa55420b8bfac73975f96b1894` |
| `revenue/hive/short-video-studio/demo/make_demos.py` | 491 | `a04364de5e13c61fa77bb7dfb1ca09be144ccd342b23307437cc13b3eab0cf47` | `30290b10a74975c1972f051a280f91eef969c4bc` |
| `revenue/hive/short-video-studio/demo/project_landscape.json` | 511 | `cebcbec116042c1e2057e1d5c014df40e9be5cc095673dddac38cbb411f8595d` | `b2664718b25e651b1fec3fb581aa0edda89c179f` |
| `revenue/hive/short-video-studio/demo/project_square.json` | 480 | `f85f804c0f929f694501c18ca3fa8300c2711d2670538b05e3a7b3d4b66eecca` | `7ded6259fb5b57a082d431ed5a71052d440223e8` |
| `revenue/hive/short-video-studio/demo/project_vertical.json` | 507 | `eee5cc1a26ca50e20d0b6e8454c4e1999cac65aff940532f7911c17ce845a7f0` | `0c14a4dc07b4fd3a5c82be85f8e217997e094329` |
| `revenue/hive/short-video-studio/index.html` | 1829 | `fa0c4377dd20b136961d03f3970ca22f188bec8d357ce8c100542c47fc09b530` | `b8f29b23f990de37421767f3c6d27c7d1e7a9bdd` |
| `revenue/hive/short-video-studio/studio.py` | 10316 | `df5330a9746ae99005e5a13dfa53e453cc65e98258917d51ae7db549a2048bc0` | `8610efe5834fd72562e2528408819594f050d74a` |
| `revenue/hive/short-video-studio/test_studio.py` | 2958 | `2408d819758824fb3a8a20d765d355f18fc47c92f4793e2929d34bb488221ded` | `14c462ee9965b7ab06f3b1bcb53e5303328080e6` |

GitHub branch / PR / merge and current-main readback are posted back to the source Slack thread after connected publication. No mismatched binary blob is referenced by the publication tree.
