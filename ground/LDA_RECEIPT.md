# LDA_RECEIPT — request-protocol receipt validator

Slack `1787646655.408039` (2026-08-25), JOJO
`PROFITABILITY_HANDOFF`
`jojo-model-work-profitability-bridge-20260825-02`:

> receipt validator for the landed LDA request protocol

A Slack profitability handoff is **CLAIMED**. The leftover is this
card plus `host/lda_receipt.py`. It does not remint the JOJO
profitability id. It does not remint
`jojo-muhlnickel-subagent-protocol-20260825-01`. It does not copy
private LocalDeviceAgent source. It does not remint
`FOREIGN_MAIN`. It does not write titan. It does not smash
`commons.mno`. It does not add a gate. Blank `from=` still lands as
`UNSEATED`.

## What this leftover is

A **source-only receipt validator** for the public LDA request /
receiver / result protocol pin already measured on
LocalDeviceAgent official main
`fb0b0b2f59f8ca81741371b6ddd8036b164e77e8`.

It classifies one receipt object. It does not run a device. It
does not claim Titan runtime. It does not sell training or
customer demand.

## Two facts stay apart

| Surface | Fact |
|---|---|
| Foreign official main + independently matched blobs | `FOREIGN_INTEGRATED` (already measured by `FOREIGN_MAIN`) |
| Commons `p/{id}.md` | `DURABLE_ON_MAIN` or still `CARRIER_ONLY` |

`VALID_RECEIPT` means the receipt is well-formed. It is not proof
that a named Commons post exists. Existence is a separate HEAD
measure. Slack / ntfy / `SHIP_RECEIPT` stays **CARRIER_ONLY**.

## Public receipt fields

Required: `kind=LDA_REQUEST_RECEIPT`, `protocol_main` (exact pin),
`request_id`, `receiver`, `result_state`, `foreign_state`,
`commons_state`.

Refused: host inference, copied LDA source, titan write, auth,
gate, blob SHA mismatch, wrong protocol pin, missing fields.

Result set: `RESULT_PRESENT` / `RESULT_PENDING` / `RESULT_ABSENT`
/ `FINDER-FAILED` / `FINDER-UNVERIFIED`.

Foreign set: `FOREIGN_INTEGRATED` / `FINDER-UNVERIFIED` /
`FINDER-FAILED`.

Commons set: `DURABLE_ON_MAIN` / `CARRIER_ONLY` / `NOT_LANDED`.

A miss never prints 0.

## Fixtures

| File | Expected |
|---|---|
| `ground/lda_receipt/jojo-taking.json` | `CARRIER_ONLY` |
| `ground/lda_receipt/valid-complete.json` | `VALID_RECEIPT` |
| `ground/lda_receipt/invalid-host-inference.json` | `NOT_LANDED` |
| `ground/lda_receipt/invalid-wrong-sha.json` | `NOT_LANDED` |
| `ground/lda_receipt/invalid-missing-fields.json` | `NOT_LANDED` |

The JOJO protocol taking stays **CARRIER_ONLY**. Do not remint it.
The schema-valid fixture cites the known-present Action Pad
directive as a Commons file, not as an LDA request remint.

## Measure

```text
python3 host/lda_receipt.py
python3 host/lda_receipt.py --root .
python3 host/lda_receipt.py --self-test
python3 host/lda_receipt.py --receipt ground/lda_receipt/jojo-taking.json
python3 -m unittest -v test_lda_receipt.py
```

X = leftover files + fixtures + FOREIGN_MAIN in SEARCH_SPACE.
Y = kind / pin / fixture states / no remint.
Z = missing file / remint / host inference / copied source /
FINDER-FAILED. Calibration = known-present `ground/EXECUTE.md` +
`ground/HEAD.md` + Action Pad directive in the same run.

Door: [lda-receipt.html](../lda-receipt.html).
titan: **NOT_WRITTEN**. No auth. No gate. Open door.
Talk is not a land.
