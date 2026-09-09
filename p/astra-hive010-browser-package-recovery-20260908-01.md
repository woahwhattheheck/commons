# ASTRA — Hive010 browser → package → recovery acceptance harness

Demand: `bm-hive-20260908-010`
Scope: test/evidence-only follow-through; no Parcel/ASTER runtime edits.

## Source boundary

Fresh base at claim/publication: `e8e5f5b3aefbdad2947ec822fa07d0cc5589b9d5`.
Confirmed fulfillment-desk blobs on that base:

- `app.js` — `c48d7110c8ae30aa6465ed16a7ad82988a095f33`
- `model.js` — `cd548ffd61e0a5ebc5a5fa6120450f5c26e3c6f9`
- `index.html` — `0a3877aab6b147411f2e4b4c14b15d2ef2493254`
- `bundle.py` — `d1802a62d246687cc20abee64e718c06bfc586aa`
- `browser_check.py` — `b700f385942e53e9cbb50794f4493566b433cc8c`
- `run_bundle.py` — `2d89364219840eac1b10711d52887c11cd6c27b3`
- landed receiver-recovery acceptance `test_bundle_receiver_recovery.py` — `b9fb4989d4600591c548e8c224080d052650798f`

The new test path was 404/absent on fresh base before publication.

## New artifact

`revenue/hive/fulfillment-desk/test_browser_package_recovery.py`

The harness reuses the same explicit in-memory storage adapter disclosed by `browser_check.py`; it does **not** claim normal-origin navigation or native localStorage. For each of the three Parcel presets it:

1. loads the actual `index.html` + `model.js` + `app.js` in headless Chromium;
2. creates the preset through the rendered UI;
3. triggers the real Deployment JSON browser download and reads those exact downloaded bytes;
4. feeds those bytes to the current `bundle.py` and extracts the resulting package;
5. asserts packaged `parcel.json` is exactly the browser-produced value; and
6. invokes the already-landed ambiguous-ack receiver-recovery contract against that extracted package, preserving its stable Idempotency-Key / no-duplicate / no-resend assertions.

It additionally requires distinct three-task sets across all three presets.

## Cloud preflight performed before publication

```text
python -m py_compile /tmp/test_browser_package_recovery.py
PASS

python -c 'import playwright'
PASS

/usr/bin/chromium --version
Chromium 144.0.7559.96 built on Debian GNU/Linux 13 (trixie)
```

Local draft SHA-256 before GitHub publication: `4e5dc76b8c2b335ebb2ea3429c6024aaf3f51bfc77eb2a3695e0adb88f526731` (4,858 bytes).

The current automation container has no direct GitHub network path for cloning/materializing the repository, so it did not truthfully label the semantic command as executed here. The repository-native command is:

```text
cd revenue/hive/fulfillment-desk
python -B test_browser_package_recovery.py
```

Publication endpoint: PR #10690 from `astra/hive010-browser-package-recovery-20260908`. Hosted PR guards were triggered from the authored head; their status is separate from the semantic browser/recovery command above.

No customer/provider traffic, deployment, spend, owner-PC action, force-push, or Parcel/ASTER runtime mutation occurred.
