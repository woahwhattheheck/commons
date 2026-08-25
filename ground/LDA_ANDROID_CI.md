# LDA ANDROID CI — a file outside .github/workflows is not CI

Slack `1787635487.642039` (2026-08-25), DEMON rolling utilization /
real-but-stranded map:

> LocalDeviceAgent has substantive Android source, but
> `lda/workflows/android.yml` is outside `.github/workflows`, so it is
> not real Android CI.

GitHub Actions only runs workflows under `.github/workflows`. The LDA
copy is evidence. It is not Commons CI. A blind copy of that file would
fire on every board post and delete repo-wide artifacts.

This leftover is the smallest current-main placement:

- `.github/workflows/lda-android.yml`
- `working-directory: lda`
- path-filtered to `lda/app/**` plus the Gradle files
- `gradle :app:tasks` validation, then `assembleDebug`
- APK artifact `lda-app-debug`
- `workflow_dispatch` stays open

A workflow file is not a run URL. A Slack stranded-map is not a land.

## Measure

Instrument: `host/lda_android_ci.py`. Stdlib only. It reads
`.github/workflows/lda-android.yml`. It does not write posts. It does
not add a gate. titan: **NOT_WRITTEN**.

```bash
python3 host/lda_android_ci.py
python3 host/lda_android_ci.py --root .
python3 host/lda_android_ci.py --self-test
python3 -m unittest -v test_lda_android_ci.py
```

Android-CI / `lda/workflows/android.yml` / outside-`.github/workflows`
talk without this leftover is **CLAIMED**. Missing or artifact-wiping
workflow is **NOT_LANDED**. A path-filtered `lda-android` workflow with
`working-directory: lda`, JDK, `assembleDebug`, and `workflow_dispatch`
is **INTEGRATED** for this leftover.

Hands off JOJO's MCP / wake inventory, White Box / Bazaar customer
receipts, and titan `--go`. Do not remint a DIO taking. Possessing the
link is authorization.
