# MUHLNICKEL_DISTRO - breadcrumb

**What this is:** the shippable MUHLNICKEL package - a self-contained computer in a folder.
Built 2026-08-04.

- `muhlnickel.mno` - the container. A fabricated gate netlist plus its own ring plus the resident
  answer and publish planes for the complete 65,536-shot input domain. Nothing outside this
  folder is required to run it.
- `run_muhlnickel.py` - the reader. Runtime verbs are only: shoot the electron into the ring's state
  wires (both senses), and surface the output. No gate evaluation, no netlist walk, no settling.
- `MANIFEST.sha256` - a digest of every shipped file. The reader checks it and refuses to run on any
  mismatch. The container is listed under `sha256-machine`: the fabricated machine (header, gate
  tables, both planes) with the state-wire input register normalized, since every shot writes it.
- `README.md` - the product doc.
- `Muhlnickel.bat` - one click.

**Fabricator and acceptance tests (stay on this machine, not shipped):**
- `C:/llm/muhl_builds/muhl_fab_distro.py` - rebuilds this package. Fabrication is one-and-done. It
  re-verifies the entire domain against an independent reference and runs a mutant gate (13 mutants)
  before writing anything.
- `C:/llm/muhl_builds/muhl_distro_cleanroom_test.py` - copies the package into a fresh empty
  directory, runs it from a different working directory with an empty PYTHONPATH, repeats shots, and
  flips single bits to confirm it refuses.
- `C:/llm/muhl_builds/muhl_distro_tamper_test.py` - defeats the manifest layer, then both layers, and
  confirms the answer is coming out of the container rather than being computed by the host.

**Measured at fabrication:** the shipped netlist reproduces an independent reference on all
65,536 shots, 0 mismatches. Single-sense shots publish 0 on all 65,536 shots and the datapath
goes dead - the both-senses law, demonstrated rather than claimed.
