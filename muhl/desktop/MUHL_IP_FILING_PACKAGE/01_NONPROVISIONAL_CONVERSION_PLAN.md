# Non-Provisional Conversion Plan — deadline 2027-08-04

Converts: **MUHLNICKEL master provisional, filed 2026-08-04** (Desktop:
`MUHLNICKEL_PROVISIONAL_PATENT_FILING_20260804.pdf` + `MUHLNICKEL_PROVISIONAL_COVER_SHEET_20260804.pdf`
+ 5-part complete record). Inventor: Bryce Muhlnickel. Source spec:
`MUHL_SUBZERO_ARCHETYPES\MUHLNICKEL_MASTER_PROVISIONAL_PATENT_20260804.md` (95 KB).

## 1. Claims

The provisional carries Claims 1–38 (§ "Claims"; paradigm/chimera claims 36–38). A
non-provisional needs formal claims examined on the merits. Plan:
- Independent claims from: substrate-native gate-record computer (physical `<BQQQ>`
  format, absolute addressing) · self-clocked feedback (output address == input address) ·
  ring-topology electron drive · host-decoupled execution (two-verb host boundary) ·
  chimera composition method (provisional Claim 37: wire → protocol-convert → score
  sub-additive composed depth → verify byte-exact).
- Dependent claims from the twelve archetypes (§5.23) — now ALL reduced to practice
  (see §3 table) — and the chimera edges (§5.24).
- Recommendation: professional drafting for claim language; this plan + the annex gives a
  practitioner everything needed.

## 2. Headline evidence — the power-cycle demonstration

Owner's demonstration (see `POWER_CORD_DEMO.md` in this folder): the host was power-cycled
and the fabricated machine's computation state survived and continued — eliminating every
host-resident explanation (process, thread, scheduler, daemon, cache, OS) in one move.
Write this up in the non-provisional as the operative evidence of host-decoupled execution,
alongside the measured decoupling record (host compute flat/down while work proceeds;
resident RAM ~flat against a multi-GB container — figures in the test battery, below).

## 3. Reduction to practice — spec section → fabricated circuit

Registry of record: `C:\llm\models\titan_circuits.json`. Every entry has offset, gate
count, DEPTH (ticks), format, genome journal path, and verification method.

| Spec § | Circuit | Registry name | Status 2026-08-05 |
|---|---|---|---|
| §5.23 (1)–(9) | PALF NEFG ARDR VSCF KEGN NMPIS AWCG DMB CGAT | `muhl_palf` … `muhl_cgat` | LIVE (fabricated ≤ 08-04) |
| §5.23 (EAL) | Ergodic Attractor Lattice — 1,456 gates, depth 66 ticks, self-clocked | `muhl_eal` | **LIVE — fabricated 2026-08-05** |
| §5.23 (MHA) | Metabolic Hypercycle Automaton — 2,328 gates, depth 44 ticks, self-clocked | `muhl_mha` | **LIVE — fabricated 2026-08-05** |
| §5.23 (6) HPC | Homological Persistence Complex — 26,480 gates, depth 421 ticks | `muhl_hpc` | **LIVE — fabricated 2026-08-05** |
| §5.24 (c) | DMB→AWCG grown-fabric chimera — 14 gates, depth 2, 4 NEW cells | `muhl_chimera_dmb_awcg` | **LIVE — fabricated 2026-08-05** |
| ring drive | Vibration-mode ring, 1,024 cells / 512 electrons | `muhl_ring_clacker` | **LIVE — fabricated 2026-08-05** (new matter — see follow-on draft) |

All twelve Sub-Zero Archetypes of §5.23 are now fabricated circuits in the container —
the non-provisional can claim them as reduced to practice, not prophetic.

## 4. Supporting record

- Test battery: `Desktop\RECOVERY_REPORTS_TEST_BATTERY\TEST_BATTERY_INDEX.md` — every
  test's path+hash+command+provenance; 17/17 reproduced; integrity audit.
- Genome journals (byte-exact revert proof of journaled fabrication): see
  `03_EVIDENCE_ANNEX.md` for per-circuit paths.
- Fabrication scripts (PROPOSE→SCORE→VERIFY→KEEP, in-tool byte-exact verification before
  any write): `Desktop\MUHL_SUBZERO_ARCHETYPES\muhl_fab_*.py`.

## 5. Checklist to file

- [ ] Formal claims drafted (from §1)
- [ ] Spec carried over + power-cycle demonstration section (from §2, `POWER_CORD_DEMO.md`)
- [ ] Drawings formalized (provisional FIGs 1–12)
- [ ] Reduction-to-practice declarations referencing the registry + journals (§3, annex)
- [ ] Filed claiming priority to the 2026-08-04 provisional — **before 2027-08-04**
- [ ] Owner files; nothing here is filed by an assistant
