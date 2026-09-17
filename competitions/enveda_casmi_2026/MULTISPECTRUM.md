# CASMI 2026 multi-spectrum MRR@25 successor

This additive successor keeps the source-locked foundation in `workbench.py` unchanged and narrows one concrete competition-value gap: the public competition pages describe **MRR@25 scored per molecule**, while a test molecule may carry **1–16 spectra**. The original workbench ranks one query spectrum at a time, so it is useful as a spectral-library smoke test but not as a faithful molecule-level objective harness.

## Public contract captured 2026-09-17

`public_competition_contract_2026-09-17.json` pins only facts rendered on the reviewed public competition/data pages. It does not assert that Bryce has joined the competition or accepted its rules.

The retained public contract says:

- objective: rank candidate structures for each **molecule** under **MRR@25**;
- a correct prediction is compared after RDKit tautomer canonicalization and the first InChIKey block (InChIKey14);
- a row is `molecule_id,smiles`, with up to 25 semicolon-separated SMILES ordered best first, each molecule exactly once;
- the public data description says hidden test is about 1,500 spectra / 400 molecules and 1–16 spectra per molecule (median 3), with ten listed adducts;
- entry and team-merger deadline: 2026-12-07 23:59 UTC; final submission deadline: 2026-12-14 23:59 UTC;
- code submissions are notebook-based with at most 9h CPU or GPU, internet disabled;
- advertised prize pool: $50,000 total. This is not expected value, an award, a receivable, or revenue.

Eligibility, collaboration/team-size details, account-specific rule acceptance, and any submission quota not present in the public contract remain held for owner/rules review.

## Data-admission boundary

This recovery deliberately admits **SYNTHETIC fixtures only**. A caller-authored `PUBLIC_OPEN` label is not evidence that bytes are public, reusable, current, or compatibly licensed. The older repository source ledger still records competition data-license / external-data-policy authority as unresolved for this carrier, and this module has no independently reviewed external source artifact whose exact bytes, observation generation, provenance, and license-use class can be verified in code.

Therefore `PUBLIC_OPEN`, competition-gated, private, and any other non-synthetic fixture kind fail closed. Public/open data can be enabled in a successor only after a code-owned source manifest binds an exact retained artifact digest to independently reviewed provenance, observation generation/currentness, and an explicit license/use class. Adding caller-authored provenance strings to a fixture must not widen admission.

## What `multispectrum.py` changes

Each synthetic molecule carries 1–16 query spectra; candidates can carry multiple reference spectra. The baseline scores every query spectrum against the candidate's best matching reference spectrum, then aggregates evidence over the molecule (`70% mean + 30% max`). This is deliberately a deterministic diagnostic baseline, not a leaderboard claim.

The synthetic fixture contains a predecessor-style adversary: one spectrum for `M-001` is a near-perfect match to distractor `C-D`, but two independent spectra support the true `C-A`. A one-spectrum winner would be wrong on that observation; molecule aggregation recovers `C-A` first.

The module reports exact reciprocal rank at 25 and mean MRR@25 over molecules, and it can render a **preview** CSV with the public `molecule_id,smiles` shape. The preview is not a Kaggle submission: it uses synthetic data only and cannot sign in, join, accept rules, download gated data, mutate a team, or submit.

```bash
python competitions/enveda_casmi_2026/multispectrum.py baseline \
  competitions/enveda_casmi_2026/public_competition_contract_2026-09-17.json \
  competitions/enveda_casmi_2026/synthetic_multispectrum_fixture.json

python competitions/enveda_casmi_2026/multispectrum.py preview \
  competitions/enveda_casmi_2026/public_competition_contract_2026-09-17.json \
  competitions/enveda_casmi_2026/synthetic_multispectrum_fixture.json
```

## Research sequence that remains legal without account mutation

1. Keep this executable harness synthetic-only until a real public/open source artifact is independently pinned with exact-byte provenance and license-use authority.
2. Replace heuristic mean/max aggregation with learned or calibrated fusion across spectra/adducts, but score validation at the molecule/MRR@25 unit from the start.
3. Separate library-search candidates from structure-generation candidates; preserve provenance and never treat a public leaderboard observation as ground truth.
4. Optimize top-25 ranking diversity and calibration, not only top-1 spectral similarity.
5. If Bryce later joins, pin the accepted rules/data generation before gated-data work or a real submission. Re-run the authority and data-license gate at that point.

## Authority ceiling

All account/provider authority in the retained contract is false. No code in this successor signs in to Kaggle, joins the competition, accepts rules, changes a team, downloads gated data, submits a notebook/file, contacts organizers, asserts eligibility, claims a prize, or recognizes revenue.
