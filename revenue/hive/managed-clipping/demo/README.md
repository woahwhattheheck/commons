# Hive020 retained demo artifact

`managed-clipping-demo-bundle.zip` is the complete **SELF-AUTHORED SYNTHETIC DEMONSTRATION** package. It contains:

- `demo_source.mp4` — the original 30-second generated source;
- `project.json` — editable source-synchronized project state;
- `clips.csv` — editable handoff table;
- `clips/clip-01.mp4` through `clips/clip-20.mp4` — 20 playable exports;
- `captions/clip-01.srt` through `captions/clip-20.srt` — sidecar captions.

Clip 07 is intentionally at revision 2 in the retained artifact: its boundary and caption were edited, then only that clip was rerendered from the unchanged source. `SHA256SUMS.txt` records the retained inspection copies and every playable clip inside the ZIP.

The standalone `project.json` and `clips.csv` beside the ZIP are inspection copies. Extract the ZIP to use the complete runnable demo because the source media is intentionally stored inside the bundle rather than duplicated in the repository.
