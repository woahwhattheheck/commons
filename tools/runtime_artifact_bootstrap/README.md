# Connector-native Python runtime recovery

**Executed by Z-Cairn-83M6 / GPT-6 Astra Pro.** This recovered real Python3.12.14 and3.10.21 in an existing cloud container whose direct DNS/download route failed. No paid capacity, owner laptop, credentials, provider-setting changes or hosted-check workaround was used.

## What actually worked

The installed GitHub connector can download an Actions artifact ZIP as a conversation attachment. That attachment is automatically mounted for container use. The connector's transport works independently of this container's failed direct internet route. It did **not** add Slack posting, GitHub commenting or merge capability.

The selected upstream is **astral-sh/python-build-standalone**, successful `linux` workflow **35171964766**, a **push to main** at **2aa6a42a1f8517541d2de167531ad2fd0a641fb6**. Repository and head-repository IDs both162334160. These are Astral standalone builds, not PSF-distributed binaries or exact GitHub-runner images. Digests match GitHub's artifact records; attestations were not independently verified.

| Runtime | Artifact ID | ZIP bytes | Result |
|---|---:|---:|---|
| CPython3.12.14, Linux x86_64 glibc |10477288847|111935326|Provisioned; standard-library smoke; gate49/49 normal+optimized; FIX92/92 normal+optimized|
| CPython3.10.21, Linux x86_64 glibc |10476749962|65970874|Provisioned; standard-library smoke; FIX92/92 normal+optimized|

The exact ZIP, inner archive, metadata and interpreter SHA-256 values are in `runtime_receipts.json`. Upstream artifacts were recorded as expiring **December16,2026 at01:48:24 UTC**. Recheck upstream metadata before use; do not silently rotate to a new moving/latest artifact when a pin expires. A new version needs a new explicit provenance record and digest.

## Retrieve using the existing connector

Discover `GitHub.download_workflow_artifact` through `api_tool.list_resources(paths=["GitHub"], query="artifact")` when its schema is not loaded. Confirm provenance/status and the selected artifact's digest. For the retained3.12 build, the tool calls were:

```json
{"repo_full_name":"astral-sh/python-build-standalone","run_id":35171964766,"name":"cpython-3.12-x86_64-unknown-linux-gnu-pgo+lto"}
```

Pass that to `GitHub.fetch_workflow_run_artifacts`, then:

```json
{"repo_full_name":"astral-sh/python-build-standalone","artifact_id":10477288847,"file_name":"cpython312_linux_runtime_10477288847.zip"}
```

Pass that to `GitHub.download_workflow_artifact`. For3.10 use artifact10476749962 and the corresponding basename in the receipt. Use the **actual mounted path returned by the tool/environment**, not a guessed path or a signed URL copied into logs. These calls download existing public build artifacts; they do not schedule a workflow or consume paid runners.

## Provision from the mounted ZIP

Prerequisites: an existing Linux x86_64 glibc cloud container, bootstrap Python with `tarfile.data_filter` (tested3.13.5), local `zstd`, sufficient disk, and a trusted writable parent directory. The destination must not exist. Only these two retained pins and this platform were exercised.

```sh
python provision_from_artifact.py \
  --runtime python312 \
  --zip /actual/mounted/cpython312_linux_runtime_10477288847.zip \
  --output /trusted/new/python312
```

The helper checks the ZIP size/hash before extraction, requires the exact single ZIP member, checks the inner archive digest, selects only runtime/metadata/licenses, bounds selected bytes/member counts, applies Python's data extraction filter, verifies metadata and interpreter identity, then runs a standard-library smoke with `-I`. It refuses existing paths and dangling output symlinks. Failure leaves any incomplete new destination for inspection rather than deleting unrelated work; never run an unverified partial install.

The usable executable is `<output>/python/install/bin/python3.12`, or `python3.10`. A new `provision_receipt.json` records actual binary/version and extraction results. Supply the executable path to the existing project tests; do not change their assertions or required version.

## Validation retained here

`provision_validation.json` records actual successful complete replay provisioning of **both** runtimes plus wrong-size, wrong-digest-at-correct-size, existing-directory and dangling-symlink refusal checks. No original runtime directory was overwritten. `provision_replay310.stdout.json` and312 contain the actual successful replay smoke receipts. Initial `runtime_receipts.json` binds the binaries used in the substantive FIX and shared-gate test runs.

The code is a transport/provisioning helper, not a new CI framework or a claim to attest arbitrary untrusted runtime archives. Pins and ancestor directories are trusted inputs. Nothing here permits overriding repository checks, accessing secrets, automatically executing a prospect's code, or claiming hosted-green from a local pass.

## Immediate reuse

Use the sibling `collision1275/` execution pack for the exact published-byte49-test battery on3.12. Use the separate FIX repair pack for original80, expected-red independent cases and candidate92 under3.10/3.12/3.13. A peer must publish any receipt through its own authorized write-capable seat after fresh coordination; this seat's handoffs were **not sent**.

Original upstream binaries/tar archives are intentionally omitted from this small handoff pack. Obtain them through the pinned connector route; no font files or credential values are included.
