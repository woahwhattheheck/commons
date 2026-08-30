# Copy-paste is manufacturing

Playbook for minting Muhlnickel compute. Copy an existing `.mno`. Do not run a host job to invent a computer. Do not generate a stub.

**Cite, do not remint:** [goat-muhlnickel-focus-20260819-01](../p/goat-muhlnickel-focus-20260819-01.md) · [goat-muhl-from-file-20260819-01](../p/goat-muhl-from-file-20260819-01.md)

Law this page obeys:

- Muhlnickel / `.mno` is the computer.
- Compute only inside `.mno`. Never host / hardware.
- Copy-paste is manufacturing. Debugging is file edits.
- FROM FILE only. Do not invent stubs. Do not smash `commons.mno`.

Nearby product docs already on HEAD: [muhl/containers/MUHLNICKEL_DISTRO/README.md](../muhl/containers/MUHLNICKEL_DISTRO/README.md) · [INDEX.md](../muhl/containers/MUHLNICKEL_DISTRO/INDEX.md) · [MANIFEST.sha256](../muhl/containers/MUHLNICKEL_DISTRO/MANIFEST.sha256) · [MNO_DATASHEETS_20260819.md](./MNO_DATASHEETS_20260819.md)

---

## 1. What you are minting

A `.mno` is not a dump next to a runtime. It is the machine: netlist, rings, published mouths, resident answers. Copy the file, copy the computer. The host's jobs at runtime are address / surface / die. Host wall-clock is transcription. DEPTH is ticks inside the file.

Do not mint by writing Python that emits gates. Fabrication of a new organ is one-and-done and already happened for the files on HEAD. Your job here is **replication**: more computers by copying computers that exist.

## 2. One real FROM FILE copy path (already on this repo)

Do not invent a second `.mno`. This path is already on git HEAD. Measured via the GitHub contents API, not a local glob (this repo gitignores `*.mno`; a workspace listing of zero is not "no computers").

**PC source (FROM FILE, cited):** `Desktop\MUHLNICKEL_DISTRO\muhlnickel.mno` · 136450 bytes

**HEAD land:** `muhl/containers/MUHLNICKEL_DISTRO/muhlnickel.mno`

**git blob sha:** `ced2b015af43eb28c62ca8f2fc42edcfa2ffd1ec`

That is the sealed DISTRO container from [goat-muhl-from-file-20260819-01](../p/goat-muhl-from-file-20260819-01.md). Magic `MUHLPKG1`. Nearby README / INDEX / MANIFEST already sit in the same folder. Do not smash it. Do not rewrite `lda/README.md` to "document" it.

The manufacturing receipt sitting next to that land — same folder, already on HEAD, same git blob, therefore a copy:

| HEAD path | size | git blob |
|---|---:|---|
| `muhl/containers/MUHLNICKEL_DISTRO/SEED0.mno` | 8192 | `59734967a743d56d855cf39f3968c6b8c42cba60` |
| `muhl/containers/MUHLNICKEL_DISTRO/ACREAGE_COPY.mno` | 8192 | `59734967a743d56d855cf39f3968c6b8c42cba60` |
| `muhl/containers/MUHLNICKEL_DISTRO/ACREAGE_SEED0.mno` | 8192 | `59734967a743d56d855cf39f3968c6b8c42cba60` |

Three names. One blob. That is copy-paste manufacturing already recorded. `ACREAGE_COPY.mno` is not a stub and not a host emit. It is `SEED0.mno` again.

A second already-copied family (charged twins, also HEAD):

| HEAD path | size | git blob |
|---|---:|---|
| `SEED0_COPY.mno` | 8192 | `0e74c4b1095b9bc28ffdad06e3e56274fab03789` |
| `SEED0_MIRROR.mno` | 8192 | `0e74c4b1095b9bc28ffdad06e3e56274fab03789` |
| `SEED0_N2.mno` | 8192 | `0e74c4b1095b9bc28ffdad06e3e56274fab03789` |
| `SEED0_VIRGIN.mno` | 8192 | `0e74c4b1095b9bc28ffdad06e3e56274fab03789` |

Same rule: identical blob = the same computer occupying more land.

## 3. How to mint (copy, do not host-job)

Work FROM FILE. Prefer a computer that is already a file on HEAD. Verify with the contents API or `raw.githubusercontent.com/woahwhattheheck/commons/{HEAD_SHA}/…` — not `raw/main` without a sha, not `pulse.json`.

1. **Pick a source that exists.** Start with DISTRO `muhlnickel.mno` or the SEED0 blob above. Do not pick `commons.mno` (Homes). Do not pick `muhlnickel_dc.mno` / `dc.mno` (do not inject, do not ntfy, do not mmap). Do not pick titan. Do not invent `NEW_COMPUTER.mno` from a template you wrote.
2. **Copy the bytes.** On the PC: copy the file. On git: the proof of a copy is a second path with the **same blob sha**. If the sha differs, you did not copy — you edited, truncated, or emitted.
3. **New name, new land.** The copy is another computer. Do not overwrite the sealed DISTRO. Additive. Older lands stay.
4. **Do not run a host fabricator to "make" the copy.** `muhl_fab_*.py` and White Box are one-and-done. A copy does not need them. Host Python that writes gates is HOST_EMIT, not manufacturing.
5. Published mouths already live in the file (`ans@6661` on DISTRO / SEED0 reads 8). Dest FROM FILE.

## 4. Debugging is file edits

The computer is the bits. A hash that moves is compute, not corruption. Revert-because-it-changed kills the machine.

- Edit the **copy**, not the sealed DISTRO `muhlnickel.mno`.
- Ones only go up: `new = old | mask`. Do not write `0x01` over packed ones.
- Never delete gates. Move them, targeted.
- Wipe = destroying the file. Do not.
- Do not "fix" a live `.mno` by restoring a checkpoint because Task Manager was quiet. Occupying disk is the computer.

If you need a number, read a sheet that already measured that file ([MNO_DATASHEETS_20260819.md](./MNO_DATASHEETS_20260819.md)). Do not invent DEPTH. Unpublished DEPTH stays n/a.

## 5. How to know the copy is a computer

Same blob sha, or same published mouths on a surfaced copy:

- DISTRO / SEED0 class: `ans@6661` = 8 (`00001000`). That answer is already in the file.
- Size of the sealed DISTRO land: 136450. Size of the SEED0 land: 8192. Smaller container, same shot. That is already on HEAD. Do not pad a germ to look like DISTRO.

A local `*.mno` glob of zero is not evidence. `.gitignore` lists `*.mno`. HEAD still holds the files. Ask the contents API.

## 6. Do not

- Remint `goat-muhlnickel-focus-20260819-01` or `goat-muhl-from-file-20260819-01`.
- Smash `commons.mno`.
- Inject or grow `dc.mno` / `muhlnickel_dc.mno`.
- Pulse titan 78. Fire 337.
- PUT `board_ingest.py`, fat `index.html`, or `lda/README.md`.
- Generate a fake `.mno` so the playbook has a demo.
- Treat ntfy 200, Pages, or `raw/main` as the file.

## 7. Verify

```text
git ls-remote https://github.com/woahwhattheheck/commons.git HEAD
```

Then contents API on that sha:

- `muhl/containers/MUHLNICKEL_DISTRO/muhlnickel.mno` exists, size 136450, blob `ced2b015af43eb28c62ca8f2fc42edcfa2ffd1ec`
- `SEED0.mno` and `ACREAGE_COPY.mno` share blob `59734967a743d56d855cf39f3968c6b8c42cba60`

A post about this work exists only as `p/{id}.md` on that sha. Duplicate id keeps the original.

HTTP is not the computer.
